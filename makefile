CC=clang-15

LLVM_BUILD_PATH=/lib/llvm-15

LLVM_BIN_PATH=$(LLVM_BUILD_PATH)/bin

LDFLAGS=`$(LLVM_BIN_PATH)/llvm-config --ldflags --libs --system-libs`

FLO_INSTALL_PATH=~/flo


define compile_and_link_fc
	./$(1) src/main.flo -o $(1).o -O 0
	$(CC) -c src/llvm/TargetInitializationMacros.c -o $(1).so
	$(CC) -no-pie $(1).o $(1).so $(LDFLAGS) -o $(2)
	rm -rf *.o *.so
endef

all: flo

flo: src/*.flo
	$(call compile_and_link_fc,flo.py,$@)

symlink: all
	cp -f flo $(FLO_INSTALL_PATH)
	sudo ln -f $(FLO_INSTALL_PATH) /usr/bin/flo

bootstrap: stage1
	$(call compile_and_link_fc,$^,flo)

stage1: stage0
	$(call compile_and_link_fc,$^,$@)

stage0: bootstrap/flo.ll
	$(CC) -c src/llvm/TargetInitializationMacros.c -o $@.so
	$(CC) $^ $@.so $(LDFLAGS) -o $@

check: flo
	./runtests.py

clean:
	rm -f flo stage0 stage1
