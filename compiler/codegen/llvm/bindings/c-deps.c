
#include <llvm-c/Target.h>
int FloLLVMInitializeNativeTarget(){
    return LLVMInitializeNativeTarget();
}
int FloLLVMInitializeNativeAsmParser(){
    return LLVMInitializeNativeAsmParser();
}
int FloLLVMInitializeNativeAsmPrinter(){
    return LLVMInitializeNativeAsmPrinter();
}