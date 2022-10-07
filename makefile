
FC=hostcompiler/flo.py

FCFLAGS=--opt-level=3

CXX=clang++

CXXFLAGS := -fno-rtti -O3 -g

LLVM_BUILD_PATH = $$HOME/llvm-project/build

LLVM_LIB_PATH:=$(LLVM_BUILD_PATH)/lib

LLVM_BIN_PATH := $(LLVM_BUILD_PATH)/bin

LLVM_CXXFLAGS=`$(LLVM_BIN_PATH)/llvm-config --cxxflags`

LLVM_LDFLAGS=`$(LLVM_BIN_PATH)/llvm-config --ldflags --libs --system-libs`

all: flo

flo: flo.o
	$(CXX) $(LLVM_CXXFLAGS) $^ $(LLVM_LDFLAGS) -o $@ 

flo.o: src/*.flo
	$(FC) $(FCFLAGS) src/main.flo -o flo

clean:
	rm -f *.o flo *.so *.ll
