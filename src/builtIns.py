
from context import Context
from llvmlite import ir
import flotypes as ft


def get_instrinsic(name):
    m = Context.current_llvm_module
    i8_ptr_ty = ir.IntType(8).as_pointer()
    i32_ty = ir.IntType(32)
    double_ty = ir.DoubleType()
    cfn_ty = ir.FunctionType(i32_ty, [], var_arg=True)
    if m.globals.get(name, None):
        return m.globals.get(name, None)
    if name == "printf":
        return m.declare_intrinsic("printf", (), cfn_ty)
    elif name == "scanf":
        return m.declare_intrinsic("scanf", (), cfn_ty)
    elif name == "pow":
        return m.declare_intrinsic("llvm.pow", [double_ty])
    elif name == "log10":
        return m.declare_intrinsic("llvm.log10", [double_ty])
    elif name == "memcpy":
        return m.declare_intrinsic("llvm.memcpy", [i8_ptr_ty, i8_ptr_ty, i32_ty])
    elif name == "malloc":
        return m.declare_intrinsic("malloc", (), ir.FunctionType(i8_ptr_ty, [i32_ty]))
    elif name == "realloc":
        return m.declare_intrinsic("realloc", (), ir.FunctionType(i8_ptr_ty, [i8_ptr_ty, i32_ty]))
    elif name == "free":
        return m.declare_intrinsic("free", (), ir.FunctionType(ir.VoidType(), [i8_ptr_ty]))
    elif name == "memcmp":
        return m.declare_intrinsic("memcmp", (), ir.FunctionType(i32_ty, [i8_ptr_ty, i8_ptr_ty, i32_ty]))
    elif name == "atoi":
        return m.declare_intrinsic("atoi", (), ir.FunctionType(i32_ty, [i8_ptr_ty]))
    elif name == "sprintf":
        return m.declare_intrinsic("sprintf", (), ir.FunctionType(i32_ty, [i8_ptr_ty, i8_ptr_ty], var_arg=True))
    elif name == "strlen":
        return m.declare_intrinsic("strlen", (), ir.FunctionType(i32_ty, [i8_ptr_ty]))
    elif name == "atof":
        return m.declare_intrinsic("atof", (), ir.FunctionType(double_ty, [i8_ptr_ty]))


def call_printf(builder: ir.IRBuilder, *args):
    c_args = []
    for arg in args:
        if isinstance(arg, str):
            c_args.append(ft.FloStr.create_global_const(arg))
        else:
            c_args.append(arg)
    builder.call(get_instrinsic("printf"), c_args)


def input_caller(main_builder: ir.IRBuilder, _):
    scanf_fmt = ft.FloStr.create_global_const("%[^\n]")
    str_ptr = main_builder.alloca(ir.IntType(8))
    main_builder.call(get_instrinsic("scanf"), [scanf_fmt, str_ptr])
    str_buffer = ft.FloMem(str_ptr)
    str_len = ft.FloInt(main_builder.call(get_instrinsic("strlen"), [str_ptr]))
    return ft.FloStr.create_new_str_val(main_builder, str_buffer, str_len)


def print_caller(builder: ir.IRBuilder, args):
    return args[0].print_val(builder)


def println_caller(builder: ir.IRBuilder, args):
    print_caller(builder, args)
    return call_printf(builder, "\n")

def len_caller(builder: ir.IRBuilder, args):
    return args[0].get_length(builder)


def new_ctx(*args):
    ctx = Context(*args)
    Context.current_llvm_module = ir.Module(str(args[0]))

    print_alias = ft.FloInlineFunc(print_caller, [ft.FloType], ft.FloVoid)
    ctx.symbol_table.set("print", print_alias)
    println_alias = ft.FloInlineFunc(println_caller, [ft.FloType], ft.FloVoid)

    # TODO: Check for proper types
    len_alias = ft.FloInlineFunc(len_caller, [ft.FloType], ft.FloInt)
    ctx.symbol_table.set("println", println_alias)
    ctx.symbol_table.set('len', len_alias)
    ctx.symbol_table.set("input", ft.FloInlineFunc(
        input_caller, [], ft.FloStr))
    ctx.symbol_table.set("true", ft.FloBool.true())
    ctx.symbol_table.set("false", ft.FloBool.false())
    return ctx
