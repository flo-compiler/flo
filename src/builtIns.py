
from context import Context
from llvmlite import ir
import flotypes as ft


def get_instrinsic(name):
    m = Context.current_llvm_module
    i8_ptr_ty = ir.IntType(8).as_pointer()
    i32_ty = ir.IntType(32)
    cfn_ty = ir.FunctionType(i32_ty, [], var_arg=True)
    if m.globals.get(name, None):
        return m.globals.get(name, None)
    if name == "printf":
        return m.declare_intrinsic("printf", (), cfn_ty)
    elif name == "scanf":
        return m.declare_intrinsic("scanf", (), cfn_ty)
    elif name == "pow":
        return m.declare_intrinsic("llvm.pow", [ir.DoubleType()])
    elif name == "memcpy":
        return m.declare_intrinsic("llvm.memcpy", [i8_ptr_ty, i8_ptr_ty, i32_ty])
    elif name == "malloc":
        return m.declare_intrinsic("malloc", (), ir.FunctionType(i8_ptr_ty, [i32_ty]))
    elif name == "realloc":
        return m.declare_intrinsic("realloc", (), ir.FunctionType(i8_ptr_ty, [i8_ptr_ty, i32_ty]))
    elif name == "free":
        return m.declare_intrinsic("free", (), ir.FunctionType(ir.VoidType(), [i8_ptr_ty]))


def debug(builder, *args):
    arg_zero = ft.FloStr.create_global_const(
        " ".join([arg.print_fmt for arg in args]))
    call_printf(builder, [arg_zero]+list(args))


def call_printf(main_builder: ir.IRBuilder, args):
    printf_fmt = args[0]
    c_strs = [arg.print_val(main_builder) for arg in args[1:]]
    main_builder.call(get_instrinsic("printf"), [printf_fmt]+c_strs)
    return ft.FloVoid()


def call_scanf(main_builder: ir.IRBuilder, _):
    scanf_fmt = ft.FloStr.create_global_const("%d", main_builder)
    tmp = main_builder.alloca(ft.FloInt.llvmtype)
    main_builder.call(get_instrinsic("scanf"), [scanf_fmt, tmp])
    return ft.FloInt(main_builder.load(tmp))


def new_ctx(*args):
    ctx = Context(*args)
    Context.current_llvm_module = ir.Module(str(args[0]))

    print_alias = ft.FloInlineFunc(lambda builder, args: call_printf(builder,
                                                                     [ft.FloStr.create_global_const(
                                                                         args[0].__class__.print_fmt), args[0]]
                                                                     ), [ft.FloType], ft.FloVoid)
    ctx.symbol_table.set("print", print_alias)
    println_alias = ft.FloInlineFunc(lambda builder, args: call_printf(builder,
                                                                       [ft.FloStr.create_global_const(
                                                                           args[0].__class__.print_fmt + "\n"), args[0]]
                                                                       ), [ft.FloType], ft.FloVoid)
    #TODO: Check for proper types
    len_alias = ft.FloInlineFunc(lambda builder, args: args[0].get_length(builder), [ft.FloType], ft.FloInt)
    ctx.symbol_table.set("println", println_alias)
    ctx.symbol_table.set('len', len_alias)
    ctx.symbol_table.set("input", ft.FloInlineFunc(call_scanf, [], ft.FloInt))
    ctx.symbol_table.set("true", ft.FloBool.true())
    ctx.symbol_table.set("false", ft.FloBool.false())
    return ctx
