# Hopefully the executable can stay under 1.2MB
start=`date +%s`
./src/flo.py compiler/flo.flo --opt-level=3
end=`date +%s`
# Linking
clang++ -c -fPIC compiler/codegen/llvm/cpp_api.cc -o cpp_api.o
clang++ flo.o cpp_api.o -o flo
# Cleaning
rm flo.o
rm cpp_api.so
# Status Message
echo "Compiled Flo Compiler!"
# Stats
runtime=$(($end - $start))
echo "Compile time: "$runtime"s"

echo "File size:"
du -sh flo