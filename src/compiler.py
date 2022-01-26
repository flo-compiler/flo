import os
from pathlib import Path
import re
from errors import CompileError
from flotypes import FloNum, FloStr, FloRef, FloBool, floType
from itypes import Types
from lexer import TokType
from interfaces.astree import *
from context import Context
from ctypes import CFUNCTYPE, c_int
from llvmlite import ir
import llvmlite.binding as llvm
from termcolor import colored

llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()
formats = {}


def ll_string(value: str):
    encoded = value.encode(encoding="utf-8", errors="xmlcharrefreplace")
    return ir.Constant(ir.ArrayType(ir.IntType(8), len(encoded)), bytearray(encoded))


def create_global_format(m, fmt):
    fmt_name = "fstr" + re.sub(r"[^a-zA-Z]+", "", fmt) + ("n" if "\n" in fmt else "")
    if formats.get(fmt_name) != None:
        return formats.get(fmt_name)
    c_fmt = ll_string(fmt)
    global_fmt = ir.GlobalVariable(m, c_fmt.type, name=fmt_name)
    global_fmt.linkage = "internal"
    global_fmt.global_constant = True
    global_fmt.initializer = c_fmt
    formats[fmt_name] = global_fmt
    return global_fmt


def get_fmt_from_type(var):
    type = var.value.type
    if isinstance(type, ir.IntType):
        if type.width <= 32:
            return "%i\0"
        else:
            return "%lld\0"
    elif isinstance(type, ir.DoubleType):
        return "%f\0"
    elif isinstance(type, ir.ArrayType):
        return "%s\0"


def fill_lang_constants(m: ir.Module, context: Context):
    # print declaration
    voidptr_ty = ir.IntType(8).as_pointer()
    cfn_ty = ir.FunctionType(
        ir.IntType(32), [], var_arg=True
    )  # creation of the printf function begins here and specifies the passing of a argument
    printf = ir.Function(m, cfn_ty, name="printf")
    scanf = ir.Function(m, cfn_ty, name="scanf")

    def call_printf(args, main_builder: ir.IRBuilder):
        fmt = args[0]
        c_str = args[1]
        c_str_val = c_str
        if isinstance(c_str.type, ir.ArrayType):
            c_str = main_builder.alloca(c_str_val.type)
            main_builder.store(c_str_val, c_str)
        printf_fmt = create_global_format(m, fmt)
        fmt_arg = main_builder.bitcast(printf_fmt, voidptr_ty)
        return main_builder.call(printf, [fmt_arg, c_str])

    def call_scanf(_, main_builder: ir.IRBuilder):
        scanf_fmt = create_global_format(m, "%d\0")
        fmt_arg = main_builder.bitcast(scanf_fmt, voidptr_ty)
        tmp = main_builder.alloca(ir.IntType(32))
        main_builder.call(scanf, [fmt_arg, tmp])
        return FloNum(main_builder.load(tmp))

    context.symbol_table.set(
        "print",
        lambda args, builder: call_printf(
            [get_fmt_from_type(args[0]), args[0].value], builder
        ),
    )
    context.symbol_table.set(
        "println",
        lambda args, builder: call_printf(
            [get_fmt_from_type(args[0]).replace("\0", "\n\0"), args[0].value], builder
        ),
    )
    context.symbol_table.set("input", call_scanf)
    context.symbol_table.set("true", FloBool.true())
    context.symbol_table.set("false", FloBool.false())


class Compiler(Visitor):
    def __init__(self, context: Context):
        super().__init__(context)
        self.context = context
        self.module = ir.Module(context.display_name)
        fill_lang_constants(self.module, self.context)
        function = ir.Function(self.module, ir.FunctionType(ir.VoidType(), []), "main")
        main_entry_block = function.append_basic_block("entry")
        builder = ir.IRBuilder(main_entry_block)
        self.function = function
        self.builder = builder
        self.i = 0

    def incr(self):
        self.i += 1
        return self.i

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
            trace = str(self.module).replace(
                lines[2], colored("->" + lines[2], "red", attrs=["bold"])
            )
            CompileError(
                colored(lines[0] + ";" + lines[1] + " at", "white", attrs=["bold"]) + "\n" + trace
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
                os.system(f"gcc {basename}.o -o {basename}")
        # Execute code
        if options.execute:
            with llvm.create_mcjit_compiler(llvm_module, target_m) as engine:
                engine.finalize_object()
                cfptr = engine.get_function_address("main")
                cfn = CFUNCTYPE(c_int, c_int)(cfptr)
                cfn(0)

    def visitNumNode(self, node: NumNode):
        return FloNum(node.tok.value)

    def visitStrNode(self, node: StrNode):
        return FloStr(node.tok.value)

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
            return a

    def visitStmtsNode(self, node: StmtsNode):
        for stmt in node.stmts:
            v = self.visit(stmt)
        return v

    def visitTypeNode(self, node: TypeNode):
        if node.type == Types.NUMBER:
            return ir.IntType(32)
        elif node.type == Types.STRING:
            return ir.PointerType(ir.IntType(8))
        elif node.type == Types.VOID:
            return ir.VoidType()

    def visitFncDefNode(self, node: FncDefNode):
        fn_name = node.var_name.value
        rtype = self.visit(node.return_type)
        arg_types = []
        arg_names = []
        for arg_name, arg_type in node.args:
            arg_names.append(arg_name.value)
            arg_types.append(self.visit(arg_type))
        fn = ir.Function(
            self.module, ir.FunctionType(rtype, arg_types, node.var_name.value), fn_name
        )
        fn_entry_block = fn.append_basic_block(f"{fn_name}.entry")
        fn_builder = ir.IRBuilder(fn_entry_block)

        def call(args, main_builder: ir.IRBuilder):
            args_vals = []
            for arg in args:
                args_vals.append(arg.value)
            return floType(None, main_builder.call(fn, args_vals))

        self.context.symbol_table.set(fn_name, call)
        outer_symbol_table = self.context.symbol_table.copy()
        for i in range(len(arg_names)):
            self.context.symbol_table.set(
                arg_names[i], floType(arg_types[i], fn.args[i])
            )
        outer_fn = self.function
        outer_builder = self.builder
        self.function = fn
        self.builder = fn_builder
        val = self.visit(node.body)
        self.context.symbol_table = outer_symbol_table
        self.function = outer_fn
        self.builder = outer_builder
        try:
            if isinstance(rtype, ir.VoidType):
                fn_builder.ret_void()
            else:
                if val == None:
                    val = FloNum.zero()
                fn_builder.ret(val.value)
        except:
            pass

    def visitUnaryNode(self, node: UnaryNode):
        value = self.visit(node.tok)
        if node.op.type == TokType.MINUS:
            if isinstance(value.type, ir.IntType):
                return self.builder.neg(value)
            elif isinstance(value.type, ir.DoubleType):
                return self.builder.fneg(value)
        elif node.op.type == TokType.NOT:
            return self.builder.not_(value)
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
        return ref.load()

    def visitVarAccessNode(self, node: VarAccessNode):
        ref = self.context.symbol_table.get(node.var_name.value)
        if isinstance(ref, FloRef):
            return ref.load()
        return ref

    def visitIfNode(self, node: IfNode):
        def ifCodeGen(cases: List[Tuple[Node, Node]], else_case):
            (comp, do) = cases.pop(0)
            cond = self.visit(comp)
            # If it's a number convert it to bool
            if isinstance(cond, FloNum):
                cond = cond.cmp(self.builder, "!=", FloNum.zero())
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

        ifCodeGen(node.cases, node.else_case)

    def visitForNode(self, node: ForNode):
        self.visit(node.init)
        cond_for_block = self.builder.append_basic_block(f"for.cond{self.incr()}")
        entry_for_block = self.builder.append_basic_block(f"for.body{self.i}")
        incr_for_block = self.builder.append_basic_block(f"for.incr{self.i}")
        end_for_block = self.builder.append_basic_block(f"for.end{self.i}")
        self.break_block = end_for_block
        self.continue_block = incr_for_block
        self.builder.branch(cond_for_block)
        self.builder.position_at_start(cond_for_block)
        cond = self.visit(node.cond)
        self.builder.cbranch(cond.value, entry_for_block, end_for_block)
        self.builder.position_at_start(entry_for_block)
        self.visit(node.stmt)
        self.builder.branch(incr_for_block)
        self.builder.position_at_start(incr_for_block)
        self.visit(node.incr_decr)
        self.builder.branch(cond_for_block)
        self.builder.position_at_start(end_for_block)

    def visitWhileNode(self, node: WhileNode):
        while_entry_block = self.builder.append_basic_block(f"while.entry{self.incr()}")
        while_exit_block = self.builder.append_basic_block(f"while.entry{self.i}")
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
        call = self.visit(node.name)
        args = [self.visit(arg) for arg in node.args]
        return call(args, self.builder)

    def visitReturnNode(self, node: ReturnNode):
        if node.value == None:
            return self.builder.ret_void()
        val = self.visit(node.value)
        return self.builder.ret(val.value)

    def visitBreakNode(self, _: BreakNode):
        self.builder.branch(self.break_block)

    def visitContinueNode(self, _: ContinueNode):
        self.builder.branch(self.continue_block)

    def visitForEachNode(self, node: ForEachNode):
        pass

    def visitIncrDecrNode(self, node: IncrDecrNode):
        pass

    def visitArrayNode(self, node: ArrayNode):
        pass

    def visitArrayAccessNode(self, node: ArrayAccessNode):
        pass

    def visitArrayAssignNode(self, node: ArrayAssignNode):
        pass

    def visitDictNode(self, node):
        pass

    def visitImportNode(self, node):
        pass
