
CC=clang
CFLAGS=-g `llvm-config --cflags`
SHAREDFLAGS=-shared
LD=clang++
LDFLAGS=`llvm-config --cxxflags --ldflags --libs --system-libs`

all: flo

flo: libllvm.a flo.o
	$(LD) flo.o libllvm.a $< $(LDFLAGS) -o $@

flo.o: compiler/*.flo
	hostcompiler/flo.py --opt-level=3 compiler/main.flo -o flo

flollvm.o: compiler/llvm/bindings/c-deps.c
	$(CC) -c compiler/llvm/bindings/c-deps.c -o $@

libllvm.a: flollvm.o
	ar rc $@ flollvm.o
	
clean:
	rm -f *.o flo *.a *.ll
