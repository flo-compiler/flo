
from pathlib import Path
from context import Context
from llvmlite import ir, binding
import flotypes as ft
import struct
machine_word_size = struct.calcsize('P') * 8
sizet_ty = ir.IntType(machine_word_size)
void_ty = ir.VoidType()
double_ty = ir.DoubleType()
byte_ty = ir.IntType(8)
byteptr_ty = byte_ty.as_pointer()
int32_ty = ir.IntType(32)
def get_instrinsic(name):
    m = Context.current_llvm_module
    if m.globals.get(name, None):
        return m.globals.get(name)
    elif name == "printf":
        return m.declare_intrinsic("printf", (), ir.FunctionType(int32_ty, [], var_arg=True))
    elif name == "atoi":
        return m.declare_intrinsic("atoi", (), ir.FunctionType(int32_ty, [byteptr_ty]))
    elif name == "atof":
        return m.declare_intrinsic("atof", (), ir.FunctionType(double_ty, [byteptr_ty]))
    elif name == "pow":
        return m.declare_intrinsic("llvm.pow", [double_ty])
    elif name == "memcpy":
        return m.declare_intrinsic("llvm.memcpy", [byteptr_ty, byteptr_ty, sizet_ty])
    elif name == "va_start":
        return m.declare_intrinsic("llvm.va_start", (), ir.FunctionType(void_ty, [byteptr_ty]))
    elif name == "va_end":
        return m.declare_intrinsic("llvm.va_end", (), ir.FunctionType(void_ty, [byteptr_ty]))
    elif name == "malloc":
        return m.declare_intrinsic("malloc", (), ir.FunctionType(byteptr_ty, [sizet_ty]))
    elif name == "realloc":
        return m.declare_intrinsic("realloc", (), ir.FunctionType(byteptr_ty, [byteptr_ty, sizet_ty]))
    elif name == "free":
        return m.declare_intrinsic("free", (), ir.FunctionType(ir.VoidType(), [byteptr_ty]))
    elif name == "memcmp":
        return m.declare_intrinsic("memcmp", (), ir.FunctionType(sizet_ty, [byteptr_ty, byteptr_ty, sizet_ty]))
    elif name == "sprintf":
        return m.declare_intrinsic("sprintf", (), ir.FunctionType(sizet_ty, [byteptr_ty, byteptr_ty], var_arg=True))

binding.initialize()
binding.initialize_native_target()
binding.initialize_native_asmprinter()
target_machine = binding.Target.from_default_triple().create_target_machine()
target_data = target_machine.target_data


def print_wrapper(builder: ir.IRBuilder, args):
    fmt = [arg.fmt for arg in args]
    c_fmt = ft.FloConst.create_global_str(" ".join(fmt)).value
    args = [c_fmt]+[arg.cval(builder) for arg in args]
    builder.call(get_instrinsic("printf"), args)

def println_wrapper(builder: ir.IRBuilder, args):
    end_arg = ft.FloType(ft.FloConst.create_global_str("\n").value)
    print_wrapper(builder, args+[end_arg])

def syscall_wrapper(builder: ir.IRBuilder, args):
    regs = "{rax}", "{rdi}", "{rsi}", "{rdx}", "{r10}", "{r8}"
    arg_tys = [arg.llvmtype for arg in args]
    arg_vals = [arg.value for arg in args]
    fn_ty = ir.FunctionType(sizet_ty, arg_tys)
    rval = builder.asm(fn_ty, "syscall","=r,"+",".join(regs[:len(args)]), arg_vals, True)
    return ft.FloInt(rval)

def realloc_wrapper(builder: ir.IRBuilder, args):
    new_size = args[1]
    ptr: ft.FloPointer = args[0]
    new_mem = ft.FloMem.realloc(builder, ptr.mem, new_size)
    return ptr.new(new_mem)

def new_ctx(*args):
    byte_flo_ptr_ty = ft.FloPointer(ft.FloInt(None, 8))
    filename = Path(args[0]).name
    global_ctx = Context(*args)
    Context.current_llvm_module = ir.Module(name=filename)
    Context.current_llvm_module.triple = binding.get_default_triple()
    Context.current_llvm_module.data_layout = str(target_data)
    syscall_fnc = ft.FloInlineFunc(syscall_wrapper, [ft.FloType], ft.FloInt(None), True)
    realloc_fnc = ft.FloInlineFunc(realloc_wrapper, [byte_flo_ptr_ty,  ft.FloInt(None)], byte_flo_ptr_ty)
    print_fnc = ft.FloInlineFunc(print_wrapper, [ft.FloType], ft.FloVoid(None), True)
    println_fnc = ft.FloInlineFunc(println_wrapper, [ft.FloType], ft.FloVoid(None), True)
    global_ctx.set("syscall", syscall_fnc)
    global_ctx.set("realloc", realloc_fnc)
    global_ctx.set("print", print_fnc)
    global_ctx.set("println", println_fnc)
    return global_ctx
