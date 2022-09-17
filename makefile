
CC=clang
CFLAGS=-g `llvm-config --cflags`
SHAREDFLAGS=-shared
LD=clang++
LDFLAGS=`llvm-config --cxxflags --ldflags --libs core executionengine mcjit interpreter analysis native bitwriter --system-libs`

flo:
	hostcompiler/flo.py compiler/flo.flo -o flo
	$(CC) -c llvm/bindings/c-deps.c -o clib.o && llvm-ar rc cdepslib.a clib.o
	$(LD) flo.o cdepslib.a $< $(LDFLAGS) -o flo
clean:
	rm -f flo.o flo cdepslib.a clib.o
