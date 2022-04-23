
from pathlib import Path
from context import Context, SymbolTable
from llvmlite import ir, binding
import flotypes as ft

i32_ty = ir.IntType(32)
void_ty = ir.VoidType()
double_ty = ir.DoubleType()
byte_ty = ir.IntType(8)
byteptr_ty = byte_ty.as_pointer()

def get_instrinsic(name):
    m = Context.current_llvm_module
    if m.globals.get(name, None):
        return m.globals.get(name)
    elif name == "pow":
        return m.declare_intrinsic("llvm.pow", [double_ty])
    elif name == "memcpy":
        return m.declare_intrinsic("llvm.memcpy", [byteptr_ty, byteptr_ty, i32_ty])
    elif name == "va_start":
        return m.declare_intrinsic("llvm.va_start", (), ir.FunctionType(void_ty, [byteptr_ty]))
    elif name == "va_end":
        return m.declare_intrinsic("llvm.va_end", (), ir.FunctionType(void_ty, [byteptr_ty]))
    elif name == "malloc":
        return m.declare_intrinsic("malloc", (), ir.FunctionType(byteptr_ty, [i32_ty]))
    elif name == "realloc":
        return m.declare_intrinsic("realloc", (), ir.FunctionType(byteptr_ty, [byteptr_ty, i32_ty]))
    elif name == "free":
        return m.declare_intrinsic("free", (), ir.FunctionType(ir.VoidType(), [byteptr_ty]))
    elif name == "memcmp":
        return m.declare_intrinsic("memcmp", (), ir.FunctionType(i32_ty, [byteptr_ty, byteptr_ty, i32_ty]))
    elif name == "sprintf":
        return m.declare_intrinsic("sprintf", (), ir.FunctionType(i32_ty, [byteptr_ty, byteptr_ty], var_arg=True))

binding.initialize()
binding.initialize_native_target()
binding.initialize_native_asmprinter()
target_machine = binding.Target.from_default_triple().create_target_machine()
target_data = target_machine.target_data

def new_ctx(*args):
    filename = Path(args[0]).name
    global_ctx = Context(*args)
    Context.current_llvm_module = ir.Module(name=filename)
    Context.current_llvm_module.triple = binding.get_default_triple()
    Context.current_llvm_module.data_layout = str(target_data)
    global_ctx.set("true", ft.FloConst.make_constant(None, 'true', ft.FloBool(True)))
    global_ctx.set("false", ft.FloConst.make_constant(None, 'false', ft.FloBool(False)))
    return global_ctx
