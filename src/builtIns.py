
from context import Context
from llvmlite import ir
import flotypes as ft


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
        return m.declare_intrinsic("llvm.memcpy", [ft.FloStr.llvmtype, ft.FloStr.llvmtype, ft.FloInt.llvmtype])

def debug(builder, *args):
    arg_zero = ft.FloStr(" ".join([arg.print_fmt for arg in args]), builder)
    call_printf(builder, [arg_zero]+list(args))

def call_printf(main_builder: ir.IRBuilder, args):
    printf_fmt = args[0].value
    c_strs = [arg.print_val(main_builder) for arg in args[1:]]
    main_builder.call(get_instrinsic("printf"), [printf_fmt]+c_strs)
    return ft.FloVoid()

def call_scanf(main_builder: ir.IRBuilder, _):
    scanf_fmt = ft.FloStr("%d", main_builder).value
    tmp = main_builder.alloca(ft.FloInt.llvmtype)
    main_builder.call(get_instrinsic("scanf"), [scanf_fmt, tmp])
    return ft.FloInt(main_builder.load(tmp))



def new_ctx(*args):
    ctx = Context(*args)
    Context.current_llvm_module = ir.Module(str(args[0]))

    print_alias = ft.FloInlineFunc(lambda builder, args: call_printf(builder, 
            [ft.FloStr(args[0].__class__.print_fmt, builder), args[0]]
        ), [None], ft.FloVoid)
    ctx.symbol_table.set("print", print_alias)
    println_alias = ft.FloInlineFunc(lambda builder, args: call_printf(builder,
            [ft.FloStr(args[0].__class__.print_fmt + "\n", builder), args[0]]
        ), [None], ft.FloVoid)
    ctx.symbol_table.set("println", println_alias)
    ctx.symbol_table.set("input", ft.FloInlineFunc(call_scanf, [], ft.FloInt))
    ctx.symbol_table.set("true", ft.FloBool.true())
    ctx.symbol_table.set("false", ft.FloBool.false())
    return ctx


# global_types_symbol_table = SymbolTable()
# global_types_symbol_table.set("true", Types.BOOL)
# global_types_symbol_table.set("false", Types.BOOL)
# global_types_symbol_table.set("print", fncType(Types.VOID, [Types.ANY]))
# global_types_symbol_table.set("println", fncType(Types.VOID, [Types.ANY]))
# global_types_symbol_table.set("input", fncType(Types.INT, []))


# def create_ctx(fn: str, type: int = 0) -> Context:
#     context = Context(fn or "<exec>")
#     context.symbol_table = global_types_symbol_table
#     return context
