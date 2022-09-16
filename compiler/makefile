CC = clang++
all: 
llvmbindings:
	$(CC) -c codegen/llvm/llvm_functions.cc
compiler:
	python ../src/flo.py codegen/llvm.flo
	clang llvm.o llvm_functions.o -o llvm -lstdc++ -lllvm
clean:
