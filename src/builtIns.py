from analyzer import Types, fncType
from context import SymbolTable, Context
from llvmlite import ir
from flotypes import FloBool, FloInt, FloStr


def get_instrinsic(name):
    m = Context.current_llvm_module
    cfn_ty = ir.FunctionType(ir.IntType(32), [], var_arg=True)
    if m.globals.get(name, None):
        return m.globals.get(name, None)
    if name == "printf":
        return m.declare_intrinsic("printf", (), cfn_ty)
    elif name == "scanf":
        return m.declare_intrinsic("scanf", (), cfn_ty)
    elif name == "llvm.pow":
        return m.declare_intrinsic("llvm.pow", [ir.DoubleType()])
    elif name == "llvm.pow":
        return m.declare_intrinsic("llvm.pow", [ir.DoubleType()])
    elif name == "llvm.memcpy":
        return m.declare_intrinsic("llvm.memcpy", [FloStr.llvmtype, FloStr.llvmtype, FloInt.llvmtype])


def new_ctx(*args):
    ctx = Context(*args)
    Context.current_llvm_module = ir.Module(str(args[0]))

    def call_printf(args, main_builder: ir.IRBuilder):
        printf_fmt = args[0].value
        c_str = args[1].string_repr_(main_builder)
        return main_builder.call(get_instrinsic("printf"), [printf_fmt, c_str])

    def call_scanf(_, main_builder: ir.IRBuilder):
        scanf_fmt = FloStr("%d").value
        tmp = main_builder.alloca(FloInt.llvmtype)
        main_builder.call(get_instrinsic("scanf"), [scanf_fmt, tmp])
        return FloInt(main_builder.load(tmp))

    ctx.symbol_table.set(
        "print",
        lambda args, builder: call_printf(
            [FloStr(args[0].__class__.print_fmt), args[0]], builder
        ),
    )
    ctx.symbol_table.set(
        "println",
        lambda args, builder: call_printf(
            [FloStr(args[0].__class__.print_fmt + "\n"), args[0]], builder
        ),
    )
    ctx.symbol_table.set("input", call_scanf)
    ctx.symbol_table.set("true", FloBool.true())
    ctx.symbol_table.set("false", FloBool.false())
    return ctx


global_types_symbol_table = SymbolTable()
global_types_symbol_table.set("true", Types.BOOL)
global_types_symbol_table.set("false", Types.BOOL)
global_types_symbol_table.set("print", fncType(Types.VOID, [Types.ANY]))
global_types_symbol_table.set("println", fncType(Types.VOID, [Types.ANY]))
global_types_symbol_table.set("input", fncType(Types.INT, []))


def create_ctx(fn: str, type: int = 0) -> Context:
    context = Context(fn or "<exec>")
    context.symbol_table = global_types_symbol_table
    return context
