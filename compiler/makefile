
CC=clang
CFLAGS=-g `llvm-config --cflags`
SHAREDFLAGS=-shared -undefined dynamic_lookup
LD=clang++
LDFLAGS=`llvm-config --cxxflags --ldflags --libs core executionengine mcjit interpreter analysis native bitwriter --system-libs`
compiler:
	../src/flo.py codegen/llvm/llvm.flo -o compiler
	$(CC) $< $(CFLAGS) $(SHAREDFLAGS) -o cdepslib.so codegen/llvm/bindings/c-deps.c
	$(LD) compiler.o $< $(LDFLAGS) -o $@ cdepslib.so
clean:
	rm -f compiler.o cdepslib.so compiler
