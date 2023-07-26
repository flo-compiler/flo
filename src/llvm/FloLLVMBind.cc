
#include <llvm/IR/Function.h>
#include <llvm/Support/TargetSelect.h>
extern "C" llvm::FunctionType* LLVM_GetFunctionType(llvm::Function* func){
    return func->getFunctionType();
}
extern "C" void LLVM_InitializeAllTargetInfos (){
    return llvm::InitializeAllTargetInfos();
}
extern "C" void LLVM_InitializeAllTargets (){
    return llvm::InitializeAllTargets();
}

extern "C" void LLVM_InitializeAllTargetMCs (){
    return llvm::InitializeAllTargetMCs();
}

extern "C" void LLVM_InitializeAllAsmPrinters (){
    return llvm::InitializeAllAsmPrinters();
}

extern "C" void LLVM_InitializeAllAsmParsers (){
    return llvm::InitializeAllAsmParsers();
}

extern "C" void LLVM_InitializeAllDisassemblers(){
    return llvm::InitializeAllDisassemblers();
}
extern "C" int LLVM_InitializeNativeTarget(){
    return llvm::InitializeNativeTarget();
}

extern "C" int LLVM_InitializeNativeAsmParser(){
    return llvm::InitializeNativeTargetAsmParser();
}
extern "C" int LLVM_InitializeNativeAsmPrinter(){
    return llvm::InitializeNativeTargetAsmPrinter();
}
extern "C" int LLVM_InitializeNativeDisassembler(){
    return llvm::InitializeNativeTargetDisassembler();
}


#if defined(__linux__)
#include <unistd.h>
extern "C" size_t get_self_path(char* buff, size_t buffsize){
    return readlink("/proc/self/exe", buff, buffsize);
}

#elif defined(_WIN32)
#include <windows.h>
extern "C" size_t get_self_path(char* buff, size_t buffsize){
    return GetModuleFileNameA(NULL, buff, &buffsize);
}
#elif defined(__APPLE__)
#include <mach-o/dyld.h>
extern "C" size_t get_self_path(char* buff, uint32_t buffsize){
    if (_NSGetExecutablePath(buff, &buffsize) == 0){
        return buffsize;
    } else {
        return 0;
    }
}
#endif