
FC=hostcompiler/flo.py

FCFLAGS=-O 3

CXX=g++

CXXFLAGS := -g3 -O1

LLVM_BUILD_PATH = /lib/llvm-15#$$HOME/llvm-project/build

LLVM_LIB_PATH:=$(LLVM_BUILD_PATH)/lib

LLVM_BIN_PATH := $(LLVM_BUILD_PATH)/bin

LLVM_CXXFLAGS=`$(LLVM_BIN_PATH)/llvm-config --cxxflags`

LLVM_LDFLAGS=`$(LLVM_BIN_PATH)/llvm-config --ldflags --libs --system-libs`

FLO_INSTALL_PATH = ~/flo

all: flo

flo: flo.o
	$(CXX) $(LLVM_CXXFLAGS) $^ $(LLVM_LDFLAGS) -o $@ 

flo.o: src/*.flo
	$(FC) $(FCFLAGS) src/main.flo -o flo

install: all
	cp -f flo $(FLO_INSTALL_PATH)
	ln -f $(FLO_INSTALL_PATH) /usr/bin/flo

build: bootstrap/flo.ll
	clang-15 $^ $(LLVM_LDFLAGS) -o stage0
	./stage0 $(FCFLAGS) src/main.flo -o flo.o
	flo

clean:
	rm -f *.o flo