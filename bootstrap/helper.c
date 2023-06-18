#include <stdio.h>
#include "llvm-c/Types.h"
#include "llvm-c/Core.h"
#include "llvm-c/IRReader.h"
#include "llvm-c/TargetMachine.h"
int main(int argc, char** argv){
    char* Errors = "";
    LLVMMemoryBufferRef MemBuf;
    LLVMModuleRef Module;
    LLVMContextRef Context = LLVMContextCreate();
    LLVMCreateMemoryBufferWithContentsOfFile(argv[1], &MemBuf, &Errors);
    LLVMParseIRInContext(Context, MemBuf, &Module, &Errors);

    LLVMInitializeAllTargetMCs();
    LLVMInitializeAllTargets();
    LLVMInitializeAllTargetInfos();
    LLVMInitializeAllAsmPrinters();

    char* Triple = LLVMGetDefaultTargetTriple();
    LLVMTargetRef Target;

    LLVMGetTargetFromTriple(Triple, &Target, &Errors); 
    char * CPUFeatures = LLVMGetHostCPUFeatures();
    LLVMTargetMachineRef TargetMachine = LLVMCreateTargetMachine(Target, Triple, "", CPUFeatures, LLVMCodeGenLevelNone, LLVMRelocDefault, LLVMCodeModelDefault);

    LLVMTargetDataRef TargetDatatLayout = LLVMCreateTargetDataLayout(TargetMachine);
    LLVMSetDataLayout(Module, (const char *) TargetDatatLayout);
    LLVMTargetMachineEmitToFile(TargetMachine, Module, argv[2], LLVMObjectFile, &Errors);
    
    LLVMDisposeModule(Module);
    LLVMDisposeTargetMachine(TargetMachine);
    LLVMDisposeTargetData(TargetDatatLayout);
    LLVMContextDispose(Context);
    LLVMDisposeMessage(Triple);
    LLVMDisposeMessage(CPUFeatures);
}   