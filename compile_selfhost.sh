start=`date +%s`
./src/flo.py selfhost/flo.flo --opt-level=3
gcc flo.o -o flo
rm flo.o
end=`date +%s`
echo "Compiled Flo Compiler!"
runtime=$(($end - $start))
echo "Compile time: "$runtime"s"

echo "File size:"
du -sh flo