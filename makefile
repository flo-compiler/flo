
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

define compile_and_link_fc
	./$(1) src/main.flo -o $(1).o
	$(CXX) $(LLVM_CXXFLAGS) $(1).o $(LLVM_LDFLAGS) -o $(2)
endef

all: flo

flo: src/*.flo
	$(call compile_and_link_fc,$(FC),flo)

install: all
	cp -f flo $(FLO_INSTALL_PATH)
	ln -f $(FLO_INSTALL_PATH) /usr/bin/flo

bootstrap: stage0 stage1
	$(call compile_and_link_fc,stage1,flo)

stage0: bootstrap/flo.ll
	clang-15 $^ $(LLVM_LDFLAGS) -o $@

stage1: stage0 src/main.flo
	$(call compile_and_link_fc,stage0,$@)

clean:
	rm -f *.o flo stage0 stage1