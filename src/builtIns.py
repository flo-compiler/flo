
from pathlib import Path
from context import Context, SymbolTable
from llvmlite import ir, binding
import flotypes as ft

i32_ty = ir.IntType(32)
void_ty = ir.VoidType()
double_ty = ir.DoubleType()
byte_ty =ir.IntType(8)
i8_ptr_ty = byte_ty.as_pointer()
def get_instrinsic(name):
    m = Context.current_llvm_module
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
    elif name == "va_start":
        return m.declare_intrinsic("llvm.va_start", (), ir.FunctionType(void_ty, [i8_ptr_ty]))
    elif name == "va_end":
        return m.declare_intrinsic("llvm.va_end", (), ir.FunctionType(void_ty, [i8_ptr_ty]))
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
    return ft.FloStr(str_buffer)


def print_caller(builder: ir.IRBuilder, args):
    for arg in args:
        arg.print_val(builder)
        if len(args) > 1:
            call_printf(builder, " ")
    return 


def println_caller(builder: ir.IRBuilder, args):
    print_caller(builder, args)
    return call_printf(builder, "\n")

def len_caller(builder: ir.IRBuilder, args):
    return args[0].get_length(builder)

builtins_sym_tb = SymbolTable()
binding.initialize()
binding.initialize_native_target()
binding.initialize_native_asmprinter()
target_machine = binding.Target.from_default_triple().create_target_machine()
target_data = target_machine.target_data

def new_ctx(*args):
    filename = Path(args[0]).name
    ctx = Context(*args)
    Context.current_llvm_module = ir.Module(name=filename)
    Context.current_llvm_module.triple = binding.get_default_triple()
    Context.current_llvm_module.data_layout = str(target_data)
    print_alias = ft.FloInlineFunc(print_caller, [ft.FloType], ft.FloVoid, True)
    builtins_sym_tb.set("print", print_alias)
    println_alias = ft.FloInlineFunc(println_caller, [ft.FloType], ft.FloVoid, True)
    len_alias = ft.FloInlineFunc(len_caller, [ft.FloType], ft.FloInt)
    builtins_sym_tb.set("println", println_alias)
    builtins_sym_tb.set('len', len_alias)
    builtins_sym_tb.set("input", ft.FloInlineFunc(
        input_caller, [], ft.FloStr))
    builtins_sym_tb.set("true", ft.FloBool.true())
    builtins_sym_tb.set("false", ft.FloBool.false())
    ctx.symbol_table = builtins_sym_tb.copy()
    return ctx
