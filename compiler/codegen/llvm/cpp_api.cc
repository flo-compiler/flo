#include <iostream>

#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/IRBuilder.h"
llvm::LLVMContext* LLVMContextCreate(){
    llvm::LLVMContext* context = new llvm::LLVMContext();
    return context;
}
llvm::Module* LLVMModuleCreateWithNameInContext(char* name, llvm::LLVMContext context){
    auto* module = new llvm::Module(name, context);
    return module;
}