
CC=clang
CFLAGS=-g `llvm-config --cflags`
SHAREDFLAGS=-shared
LD=clang++
LDFLAGS=`llvm-config --cxxflags --ldflags --libs --system-libs`

all: flo

flo: libllvm.a
	hostcompiler/flo.py compiler/llvm/bindings_test.flo -o $@
	$(LD) flo.o libllvm.a $< $(LDFLAGS) -o $@

flollvm.o:
	$(CC) -c compiler/llvm/bindings/c-deps.c -o $@

libllvm.a: flollvm.o
	ar rc $@ flollvm.o
	
clean:
	rm -f *.o flo *.a *.ll
