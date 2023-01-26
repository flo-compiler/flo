CC=clang-15

LLVM_BUILD_PATH=/lib/llvm-15

LLVM_BIN_PATH=$(LLVM_BUILD_PATH)/bin

LDFLAGS=`$(LLVM_BIN_PATH)/llvm-config --ldflags --libs --system-libs`

FLO_INSTALL_PATH=~/flo


define compile_and_link_fc
	./$(1) src/main.flo -o $(1).o -O 3
	$(CC) -no-pie $(1).o llvm-bind.so $(LDFLAGS) -o $(2)
endef

all: flo

flo: llvm-bind src/*.flo
	$(call compile_and_link_fc,flo.py,$@)

install: check
	cp -f flo $(FLO_INSTALL_PATH)
	sudo ln -f $(FLO_INSTALL_PATH) /usr/bin/flo

bootstrap: stage1
	$(call compile_and_link_fc,$^,flo)

stage1: stage0
	$(call compile_and_link_fc,$^,$@)

stage0: bootstrap/flo.ll llvm-bind
	$(CC) $< llvm-bind.so $(LDFLAGS) -o $@

llvm-bind: src/llvm/FloLLVMBind.cpp
	$(CC) -c src/llvm/FloLLVMBind.cpp -o $@.so

check: flo
	./runtests.py

clean:
	rm -f flo stage0 stage1
