#include <llvm-c/Target.h>
void LLVM_InitializeAllTargetInfos (){
    return LLVMInitializeAllTargetInfos();
}
void LLVM_InitializeAllTargets (){
    return LLVMInitializeAllTargets();
}

void LLVM_InitializeAllTargetMCs (){
    return LLVMInitializeAllTargetMCs();
}

void LLVM_InitializeAllAsmPrinters (){
    return LLVMInitializeAllAsmPrinters();
}

void LLVM_InitializeAllAsmParsers (){
    return LLVMInitializeAllAsmParsers();
}

void LLVM_InitializeAllDisassemblers(){
    return LLVMInitializeAllDisassemblers();
}
int LLVM_InitializeNativeTarget(){
    return LLVMInitializeNativeTarget();
}

int LLVM_InitializeNativeAsmParser(){
    return LLVMInitializeNativeAsmParser();
}
int LLVM_InitializeNativeAsmPrinter(){
    return LLVMInitializeNativeAsmPrinter();
}
int LLVM_InitializeNativeDisassembler(){
    return LLVMInitializeNativeDisassembler();
}