CXX=clang-15

LLVM_BUILD_PATH=/lib/llvm-15#$$HOME/llvm-project/build

LLVM_BIN_PATH=$(LLVM_BUILD_PATH)/bin

LLVM_CXXFLAGS=`$(LLVM_BIN_PATH)/llvm-config --cxxflags`

LLVM_LDFLAGS=`$(LLVM_BIN_PATH)/llvm-config --ldflags --libs --system-libs`

FLO_INSTALL_PATH=~/flo

FLO_COMPILER_SRC=src/main.flo

define compile_and_link_fc
	./$(1) $(FLO_COMPILER_SRC) -o $(1).o -O 0
	$(CXX) -c src/llvm/TargetInitializationMacros.c -o $(1).so
	$(CXX) -no-pie $(1).o $(1).so $(LLVM_LDFLAGS) -o $(2)
endef

all: flo

flo: src/*.flo
	$(call compile_and_link_fc,hostcompiler/flo.py,$@)

install: all
	cp -f flo $(FLO_INSTALL_PATH)
	ln -f $(FLO_INSTALL_PATH) /usr/bin/flo

bootstrap: stage1
	$(call compile_and_link_fc,$^,flo)

stage1: stage0
	$(call compile_and_link_fc,$^,$@)

stage0: bootstrap/flo.ll
	$(CXX) -c src/llvm/TargetInitializationMacros.c -o $@.so
	$(CXX) $^ $@.so $(LLVM_LDFLAGS) -o $@

clean:
	rm -f *.o *.a .*so flo stage0 stage1