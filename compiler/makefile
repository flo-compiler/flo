
CC=clang
CFLAGS=-g `llvm-config --cflags`
SHAREDFLAGS=-shared
LD=clang++
LDFLAGS=`llvm-config --cxxflags --ldflags --libs core executionengine mcjit interpreter analysis native bitwriter --system-libs`

compiler:
	../src/flo.py codegen/llvm/llvm.flo -o compiler
	$(CC) -c codegen/llvm/bindings/c-deps.c -o clib.o && llvm-ar rc cdepslib.a clib.o
	$(LD) compiler.o cdepslib.a $< $(LDFLAGS) -o $@
clean:
	rm -f compiler.o cdepslib.a compiler clib.o
