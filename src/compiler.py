from pathlib import Path
from errors import CompileError, TypeError
from flotypes import FloArray, FloFunc, FloInlineFunc, FloInt, FloFloat, FloIterable, FloStr, FloRef, FloBool, FloVoid
from lexer import TokType
from interfaces.astree import *
from context import Context
from ctypes import CFUNCTYPE, c_int
import llvmlite.binding as llvm
from termcolor import colored

llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()

class Compiler(Visitor):
    def __init__(self, context: Context):
        self.context = context
        self.module = Context.current_llvm_module
        self.fn =  FloFunc([], FloVoid(), "main")
        self.ret = self.fn.ret
        self.builder = self.fn.builder

    def visit(self, node: Node):
        return super().visit(node)

    def compile(self, node: Node, options):
        self.visit(node)
        self.builder.ret_void()
        # Check for any errors
        try:
            llvm_module = llvm.parse_assembly(str(self.module))
            llvm_module.verify()
        except RuntimeError as e:
            lines = e.args[0].split("\n")
            trace = str(self.module).split("\n")
            lineNo = int(lines[1].split(":")[1]) if len(lines[1].split(":")) > 1 else 1
            trace[lineNo-1] = trace[lineNo-1].replace(
                lines[2], colored("->" + lines[2], "red", attrs=["bold"])
            )
            CompileError(
                colored(lines[0] + ";" + lines[1] + " at", "white",
                        attrs=["bold"]) + "\n" + "\n".join(trace)
            ).throw()
        # Passes
        pass_manager_builder = llvm.create_pass_manager_builder()
        pass_manager_builder.opt_level = int(options.opt_level)
        pass_manager = llvm.create_module_pass_manager()
        pass_manager_builder.populate(pass_manager)
        pass_manager.run(llvm_module)
        if options.print:
            print(llvm_module)
        # Write executable
        target_m = llvm.Target.from_default_triple().create_target_machine(
            codemodel="default"
        )
        if not options.no_output:
            basename = Path(self.context.display_name).stem
            basename = options.output_file.replace("<file>", basename)
            with open(f"{basename}.o", "wb") as object:
                object.write(target_m.emit_object(llvm_module))
                object.close()
        # Execute code
        if options.execute:
            # And an execution engine with an empty backing module
            backing_mod = llvm.parse_assembly("")
            with llvm.create_mcjit_compiler(backing_mod, target_m) as engine:
                engine.add_module(llvm_module)
                engine.finalize_object()
                engine.run_static_constructors()
                cfptr = engine.get_function_address("main")
                cfn = CFUNCTYPE(c_int, c_int)(cfptr)
                cfn(0)

    def visitIntNode(self, node: IntNode):
        return FloInt(node.tok.value)

    def visitFloatNode(self, node: FloatNode):
        return FloFloat(node.tok.value)

    def visitStrNode(self, node: StrNode):
        return FloStr(node.tok.value, self.builder)

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
            pass
        elif node.op.isKeyword("as"):
            try:
                return a.cast_to(self.builder, b)
            except Exception as e:
                TypeError(
                    node.range, f"Cannot cast {a.str()} to {b.str()}"
                ).throw()
        elif node.op.isKeyword("is"):
            return FloBool(isinstance(a, b))

    def visitStmtsNode(self, node: StmtsNode):
        for stmt in node.stmts:
            v = self.visit(stmt)
        return v

    def visitTypeNode(self, node: TypeNode):
        return node.type

    def visitFncDefNode(self, node: FncDefNode):
        fn_name = node.var_name.value
        rtype = self.visit(node.return_type)
        arg_types = []
        arg_names = []
        for arg_name, arg_type in node.args:
            arg_names.append(arg_name.value)
            arg_types.append(self.visit(arg_type))
        outer_builder = self.builder
        outer_symbol_table = self.context.symbol_table.copy()
        outer_ret = self.ret
        if not node.is_inline:
            fn = FloFunc(arg_types, rtype, fn_name)
            self.context.symbol_table.set(fn_name, fn)
            self.context.symbol_table = fn.extend_symbol_table(self.context.symbol_table, arg_names)
            self.builder = fn.builder
            self.ret = fn.ret
            self.visit(node.body)
        else:
            def inline_call(builder, args):
                self.ret = fn.ret
                for arg_val, arg_name in zip(args, arg_names):
                    self.context.symbol_table.set(arg_name, arg_val)
                self.builder = builder
                self.visit(node.body)
                self.ret = outer_ret
            fn = FloInlineFunc(inline_call, arg_types, rtype)
        self.ret = outer_ret
        self.context.symbol_table = outer_symbol_table
        self.context.symbol_table.set(fn_name, fn)
        self.builder = outer_builder

    def visitUnaryNode(self, node: UnaryNode):
        value = self.visit(node.value)
        if node.op.type == TokType.MINUS:
            return value.neg()
        elif node.op.type == TokType.NOT:
            return value.not_(self.builder)
        else:
            return value

    def visitVarAssignNode(self, node: VarAssignNode):
        var_name = node.var_name.value
        value = self.visit(node.value)
        ref = self.context.symbol_table.get(var_name)
        if ref == None:
            ref = FloRef(self.builder, value, var_name)
        else:
            ref.store(value)
        self.context.symbol_table.set(var_name, ref)
        return value

    def visitVarAccessNode(self, node: VarAccessNode):
        ref = self.context.symbol_table.get(node.var_name.value)
        if isinstance(ref, FloRef):
            return ref.load()
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
        self.builder.position_at_start(for_end_block)

    def visitWhileNode(self, node: WhileNode):
        while_entry_block = self.builder.append_basic_block(
            f"while.entry")
        while_exit_block = self.builder.append_basic_block(
            f"while.entry")
        self.break_block = while_exit_block
        self.continue_block = while_entry_block
        cond = self.visit(node.cond)
        self.builder.cbranch(cond.value, while_entry_block, while_exit_block)
        self.builder.position_at_start(while_entry_block)
        self.visit(node.stmt)
        cond = self.visit(node.cond)
        self.builder.cbranch(cond.value, while_entry_block, while_exit_block)
        self.builder.position_at_start(while_exit_block)

    def visitFncCallNode(self, node: FncCallNode):
        fn = self.visit(node.name)
        args = [self.visit(arg) for arg in node.args]
        return fn.call(self.builder, args)

    def visitReturnNode(self, node: ReturnNode):
        if node.value == None:
            return self.ret(None)
        val = self.visit(node.value)
        return self.ret(val, self.builder)

    def visitBreakNode(self, _: BreakNode):
        self.builder.branch(self.break_block)

    def visitContinueNode(self, _: ContinueNode):
        self.builder.branch(self.continue_block)

    def visitIncrDecrNode(self, node: IncrDecrNode):
        value = self.visit(node.identifier)
        incr = FloInt.one().neg() if node.id.type == TokType.MINUS_MINUS else FloInt.one()
        nValue = value.add(self.builder, incr)
        if isinstance(node.identifier, VarAccessNode):
            ref: FloRef = self.context.symbol_table.get(
                node.identifier.var_name.value)
            ref.store(ref.load().add(self.builder, incr))
            self.context.symbol_table.set(node.identifier.var_name.value, ref)
        elif isinstance(node.identifier, ArrayAccessNode):
            index = self.visit(node.identifier.index)
            array = self.visit(node.identifier.name)
            array.set_element(self.builder, index, nValue)
        return nValue if node.ispre else value

    def visitForEachNode(self, node: ForEachNode):
        iterable: FloArray = self.visit(node.iterator)
        with FloIterable.foreach(iterable, self.builder) as (item, index, continue_block, break_block):
            self.continue_block = continue_block
            self.break_block = break_block
            self.context.symbol_table.set(node.identifier.value, item)
            self.visit(node.stmt)

    def visitArrayAccessNode(self, node: ArrayAccessNode):
        index = self.visit(node.index)
        if not isinstance(node.name, VarAccessNode):
            value = self.visit(node.name)
        else:
            ref = self.context.symbol_table.get(node.name.var_name.value)
            value = ref.load()
        return value.get_element(self.builder, index)

    def visitArrayNode(self, node: ArrayNode):
        return FloArray([self.visit(elm_node) for elm_node in node.elements], self.builder)

    def visitArrayAssignNode(self, node: ArrayAssignNode):
        index = self.visit(node.array.index)
        array = self.visit(node.array.name)
        value = self.visit(node.value)
        return array.set_element(self.builder, index, value)

    def visitImportNode(self, node):
        raise Exception("Unimplemented!")
