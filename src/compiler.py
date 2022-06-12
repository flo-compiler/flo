from pathlib import Path
from typing import Dict
from errors import CompileError, TypeError
from flotypes import FloArray, FloClass, FloConst, FloEnum, FloFunc, FloGeneric, FloInt, FloFloat, FloMethod, FloObject, FloPointer, FloRef, FloVoid, create_array_buffer
from lexer import TokType
from astree import *
from context import Context
from ctypes import CFUNCTYPE, POINTER, c_char_p, c_int
from builtIns import target_machine, target_data
from llvmlite import binding as llvm

saved_labels = []


def save_labels(*args):
    saved_labels.append(list(args))


def pop_labels():
    return saved_labels.pop()


class Compiler(Visitor):
    def __init__(self, context: Context):
        self.context = context
        self.module = Context.current_llvm_module
        self.builder = None
        self.ret = None
        self.break_block = None
        self.continue_block = None
        self.class_within = None
        self.generics: Dict[str, GenericClassNode] = {}
        self.generic_aliases = {}

    def visit(self, node: Node):
        return super().visit(node)

    def compile(self, node: Node, options):
        self.visit(node)
        llvm.initialize_native_asmparser()
        llvm_module = llvm.parse_assembly(str(self.module))
        llvm_module.verify()
        # Passes
        pass_manager_builder = llvm.create_pass_manager_builder()
        pass_manager_builder.opt_level = int(options.opt_level)
        pass_manager = llvm.create_module_pass_manager()
        pass_manager_builder.populate(pass_manager)
        pass_manager.run(llvm_module)
        basename = Path(self.context.display_name).stem
        if options.emit:
            with open(f"{basename}.ll", "w") as object:
                object.write(str(llvm_module).replace(
                    "<string>", self.module.name))
                object.close()
        # Write executable
        if not options.no_output:
            basename = options.output_file.replace("<file>", basename)
            with open(f"{basename}.o", "wb") as object:
                object.write(target_machine.emit_object(llvm_module))
                object.close()
        # Execute code
        if options.execute:
            # And an execution engine with an empty backing module
            if self.context.get("main") == None:
                CompileError("No main method to execute").throw()
            backing_mod = llvm.parse_assembly("")
            with llvm.create_mcjit_compiler(backing_mod, target_machine) as engine:
                engine.add_module(llvm_module)
                engine.finalize_object()
                engine.run_static_constructors()
                cfptr = engine.get_function_address("main")
                cfn = CFUNCTYPE(c_int, c_int, POINTER(c_char_p))(cfptr)
                args = [bytes(arg, encoding='utf-8') for arg in options.args]
                args_array = (c_char_p * (len(args)+1))()
                args_array[:-1] = args
                cfn(len(args), args_array)

    def visitIntNode(self, node: IntNode):
        return FloInt(node.tok.value)

    def visitFloatNode(self, node: FloatNode):
        return FloFloat(node.tok.value)

    def visitCharNode(self, node: CharNode):
        return FloInt(node.tok.value, 8)

    def visitStrNode(self, node: StrNode):
        str_val = node.tok.value
        str_buff = FloConst.create_global_str(str_val)
        str_len = FloInt(len(str_val.encode('utf-8')))
        string_class = FloClass.classes.get("string")
        return string_class.constant_init(self.builder, [str_buff, str_len])

    def visitNumOpNode(self, node: NumOpNode):
        a = self.visit(node.left_node)
        b = self.visit(node.right_node)
        if node.op.type == TokType.PLUS:
            return a.add(self.builder, b)
        elif node.op.type == TokType.MINUS:
            return a.sub(self.builder, b)
        elif node.op.type == TokType.MULT:
            return a.mul(self.builder, b)
        elif node.op.type == TokType.DIV:
            return a.div(self.builder, b)
        elif node.op.type == TokType.MOD:
            return a.mod(self.builder, b)
        elif node.op.type == TokType.POW:
            return a.pow(self.builder, b)
        elif (
            node.op.type == TokType.EEQ
            or node.op.type == TokType.NEQ
            or node.op.type == TokType.GT
            or node.op.type == TokType.LT
            or node.op.type == TokType.LT
            or node.op.type == TokType.LTE
            or node.op.type == TokType.GTE
            or node.op.type == TokType.LEQ
        ):
            return a.cmp(self.builder, node.op.type._value_, b)
        elif node.op.type == TokType.SL:
            return a.sl(self.builder, b)
        elif node.op.type == TokType.SR:
            return a.sr(self.builder, b)
        elif node.op.isKeyword("or"):
            return a.or_(self.builder, b)
        elif node.op.isKeyword("and"):
            return a.and_(self.builder, b)
        elif node.op.isKeyword("xor"):
            return a.xor(self.builder, b)
        elif node.op.isKeyword("in"):
            return b.in_(self.builder, a)
        elif node.op.isKeyword("as"):
            try:
                return a.cast_to(self.builder, b)
            except Exception as e:
                TypeError(
                    node.range, f"Cannot cast {a.str()} to {b.str()}"
                ).throw()
        elif node.op.isKeyword("is"):
            return FloInt(isinstance(a, b), 1)

    def visitStmtsNode(self, node: StmtsNode):
        for stmt in node.stmts:
            v = self.visit(stmt)
        return v

    def init_generic(self, generic: FloGeneric):
        previous_aliases = self.generic_aliases.copy()
        generic_name = generic.str()
        if self.context.get(generic_name): return
        generic_node = self.generics.get(generic.name)
        for key_tok, ty in zip(generic_node.generic_constraints, generic.constraints):
            self.generic_aliases[key_tok.value] = ty
        generic_node.class_declaration.name.value = generic_name
        self.visit(generic_node.class_declaration)
        self.generic_aliases = previous_aliases

    def visitTypeNode(self, node: TypeNode):
        type_ = node.type
        if isinstance(type_, FloGeneric):
            self.init_generic(type_)
        if isinstance(type_, FloObject):
            if isinstance(type_.referer, Token):
                alias = self.generic_aliases.get(type_.referer.value)
                if alias:
                    return alias
            type_.referer = self.context.get(type_.referer.name)
        return type_
    
    def visitFncNode(self, node: FncNode):
        arg_types = []
        arg_names = []
        rtype = self.visit(node.return_type)
        for arg_name, arg_type, _ in node.args:
            arg_names.append(arg_name.value)
            arg_types.append(self.visit(arg_type))
        return arg_types, arg_names, rtype

    def evaluate_function_body(self, fn, arg_names, node: StmtsNode):
        outer_ret = self.ret
        outer_builder = self.builder
        self.ret = fn.ret
        if node:
            self.context = fn.get_local_ctx(self.context, arg_names)
            self.builder = fn.builder
            self.visit(node)
            self.context = self.context.parent
            self.builder = outer_builder
        self.ret = outer_ret

    def visitFncDefNode(self, node: FncDefNode):
        fn_name = node.func_name.value
        arg_types, arg_names, rtype = self.visit(node.func_body)
        if node.func_body.body:
            fn = FloFunc(arg_types, rtype, fn_name, node.func_body.is_variadic)
        else:
            fn = FloFunc.declare(
                arg_types, rtype, fn_name, node.func_body.is_variadic)
        self.context.set(fn_name, fn)
        self.evaluate_function_body(fn, arg_names, node.func_body.body)
    
    def visitMethodDeclarationNode(self, node: MethodDeclarationNode):
        method_name = node.method_name.value
        arg_types, arg_names, rtype = self.visit(node.method_body)
        fn = FloMethod(arg_types, rtype, method_name,
                        node.method_body.is_variadic, self.class_within)
        fn.class_within = self.class_within
        self.class_within.add_method(fn)
        self.evaluate_function_body(fn, arg_names, node.method_body.body)


    def visitUnaryNode(self, node: UnaryNode):
        if node.op.type == TokType.AMP:
            if isinstance(node.value, ArrayAccessNode):
                array: FloArray = self.visit(node.value.name)
                index = self.visit(node.value.index)
                return array.get_pointer_at_index(self.builder, index)
            var_name = node.value.var_name.value
            var: FloRef = self.context.get(var_name)
            return FloPointer(var.referee).new(var.mem)
        value = self.visit(node.value)
        if node.op.type == TokType.MINUS:
            return value.neg(self.builder)
        elif node.op.type == TokType.NOT:
            return value.not_(self.builder)
        else:
            return value

    def visitConstDeclarationNode(self, node: ConstDeclarationNode):
        const_name = node.const_name.value
        const_val = FloConst(node.value)
        self.context.set(const_name, const_val)

    def visitVarAssignNode(self, node: VarAssignNode):
        var_name = node.var_name.value
        value = self.visit(node.value)
        ref = self.context.get(var_name)
        if ref == None:
            ref = FloRef(self.builder, value, var_name)
            self.context.set(var_name, ref)
        else:
            ref.store(value)
        return value
    
    def visitPropertyDeclarationNode(self, node: PropertyDeclarationNode):
        property_name = node.property_name.value
        property_type = self.visit(node.type)
        self.class_within.add_property(property_name, property_type)

    def visitVarAccessNode(self, node: VarAccessNode):
        ref = self.context.get(node.var_name.value)
        if isinstance(ref, FloRef):
            return ref.load()
        elif isinstance(ref, FloConst):
            return ref.load(self)
        return ref

    def visitIfNode(self, node: IfNode):
        def ifCodeGen(cases: List[Tuple[Node, Node]], else_case):
            (comp, do) = cases.pop(0)
            cond = self.visit(comp)
            end_here = len(cases) == 0
            # Guard
            if end_here and else_case == None:
                with self.builder.if_then(cond.value):
                    self.visit(do)
                    return
            # Recursion
            with self.builder.if_else(cond.value) as (then, _else):
                with then:
                    self.visit(do)
                with _else:
                    if end_here:
                        self.visit(else_case)
                    else:
                        ifCodeGen(cases, else_case)

        ifCodeGen(node.cases.copy(), node.else_case)

    def visitForNode(self, node: ForNode):
        for_entry_block = self.builder.append_basic_block(f"for.entry")
        self.builder.branch(for_entry_block)
        self.builder.position_at_start(for_entry_block)
        self.visit(node.init)
        for_cond_block = self.builder.append_basic_block(
            f"for.cond")
        for_body_block = self.builder.append_basic_block(f"for.body")
        for_incr_block = self.builder.append_basic_block(f"for.incr")
        for_end_block = self.builder.append_basic_block(f"for.end")
        save_labels(self.break_block, self.continue_block)
        self.break_block = for_end_block
        self.continue_block = for_incr_block
        self.builder.branch(for_cond_block)
        self.builder.position_at_start(for_cond_block)
        cond = self.visit(node.cond)
        self.builder.cbranch(cond.value, for_body_block, for_end_block)
        self.builder.position_at_start(for_body_block)
        self.visit(node.stmt)
        self.builder.branch(for_incr_block)
        self.builder.position_at_start(for_incr_block)
        self.visit(node.incr_decr)
        self.builder.branch(for_cond_block)
        [self.break_block, self.continue_block] = pop_labels()
        self.builder.position_at_start(for_end_block)

    def visitWhileNode(self, node: WhileNode):
        while_entry_block = self.builder.append_basic_block(
            f"while.entry")
        while_exit_block = self.builder.append_basic_block(
            f"while.entry")
        save_labels(self.break_block, self.continue_block)
        self.break_block = while_exit_block
        self.continue_block = while_entry_block
        cond = self.visit(node.cond)
        self.builder.cbranch(cond.value, while_entry_block, while_exit_block)
        self.builder.position_at_start(while_entry_block)
        self.visit(node.stmt)
        cond = self.visit(node.cond)
        self.builder.cbranch(cond.value, while_entry_block, while_exit_block)
        [self.break_block, self.continue_block] = pop_labels()
        self.builder.position_at_start(while_exit_block)

    def visitFncCallNode(self, node: FncCallNode):
        fnc = self.visit(node.name)
        args = [self.visit(arg) for arg in node.args]
        return fnc.call(self.builder, args)

    def visitReturnNode(self, node: ReturnNode):
        if node.value == None:
            return self.ret(FloVoid)
        val = self.visit(node.value)
        return self.ret(val)

    def visitBreakNode(self, _: BreakNode):
        self.builder.branch(self.break_block)

    def visitContinueNode(self, _: ContinueNode):
        self.builder.branch(self.continue_block)

    def visitIncrDecrNode(self, node: IncrDecrNode):
        value = self.visit(node.identifier)
        incr = FloInt(-1) if node.id.type == TokType.MINUS_MINUS else FloInt(1)
        nValue = value.add(self.builder, incr)
        if isinstance(node.identifier, VarAccessNode):
            ref: FloRef = self.context.get(
                node.identifier.var_name.value)
            ref.store(ref.load().add(self.builder, incr))
            self.context.set(node.identifier.var_name.value, ref)
        elif isinstance(node.identifier, ArrayAccessNode):
            index = self.visit(node.identifier.index)
            array = self.visit(node.identifier.name)
            array.set_element(self.builder, index, nValue)
        return nValue if node.ispre else value

    def visitArrayAccessNode(self, node: ArrayAccessNode):
        index = self.visit(node.index)
        value = self.visit(node.name)
        if isinstance(value, FloObject):
            return value.get_property(self.builder, '__getitem__').call(self.builder, [index])
        return value.get_element(self.builder, index)

    def visitArrayNode(self, node: ArrayNode):
        elems = [self.visit(elm_node) for elm_node in node.elements]
        if node.is_const_array:
            return FloArray(elems, len(elems))
        else:
            array_class: FloClass = FloClass.classes.get("Array<"+elems[0].str()+">")
            length = FloInt(len(elems))
            llvm_ty = elems[0].llvmtype
            size = llvm_ty.get_abi_size(target_data) * len(elems)
            pointer = create_array_buffer(self.builder, elems)
            return array_class.constant_init(self.builder, [pointer, length, FloInt(size)])

    def visitClassDeclarationNode(self, node: ClassDeclarationNode):
        parent = None
        if node.parent:
            parent = self.visit(node.parent).referer
        class_obj = FloClass(node.name.value, parent)
        previous_class = self.class_within
        self.class_within = class_obj
        self.context.set(node.name.value, class_obj)
        self.visit(node.body)
        class_obj.create_vtable()
        self.class_within = previous_class
    
    def visitGenericClassNode(self, node: GenericClassNode):
        self.generics[node.class_declaration.name.value] = node

    def visitRangeNode(self, node: RangeNode):
        start = self.visit(node.start)
        end = self.visit(node.end)
        range_class = FloClass.classes.get("Range")
        return range_class.constant_init(self.builder, [start, end])

    def visitPropertyAccessNode(self, node: PropertyAccessNode):
        root = self.visit(node.expr)
        property_name = node.property.value
        if isinstance(root, FloEnum):
            return root.get_property(property_name)
        return root.get_property(self.builder, property_name)

    def visitEnumDeclarationNode(self, node: EnumDeclarationNode):
        enum_name = node.name.value
        self.context.set(enum_name, FloEnum(
            [token.value for token in node.tokens]))

    def visitPropertyAssignNode(self, node: PropertyAssignNode):
        root = self.visit(node.expr.expr)
        value = self.visit(node.value)
        if not isinstance(root, FloObject):
            TypeError(
                node.range, f"Can't set attribute {node.expr.property.value} of type {root.str()}").throw()
        root.set_property(self.builder, node.expr.property.value, value)

    def visitNewMemNode(self, node: NewMemNode):
        typeval = self.visit(node.type)
        args = [self.visit(arg) for arg in node.args]
        return typeval.construct(self.builder, args)

    def visitArrayAssignNode(self, node: ArrayAssignNode):
        index = self.visit(node.array.index)
        array = self.visit(node.array.name)
        value = self.visit(node.value)
        if isinstance(array, FloObject):
            return array.get_property(self.builder, '__setitem__').call(self.builder, [index, value])
        return array.set_element(self.builder, index, value)

    def visitImportNode(self, node: ImportNode):
        for imported_node in node.resolved_as:
            self.visit(imported_node)
