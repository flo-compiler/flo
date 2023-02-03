; ModuleID = 'examples/test.flo'
source_filename = "examples/test.flo"

define i64 @main() {
  %1 = call i64 @add(i64 1, i64 -1)
  ret i64 %1
}

define i64 @add(i64 %0, i64 %1) {
  %x = alloca i64, align 8
  store i64 %0, ptr %x, align 4
  %y = alloca i64, align 8
  store i64 %1, ptr %y, align 4
  %3 = load i64, ptr %x, align 4
  %4 = load i64, ptr %y, align 4
  %5 = add i64 %3, %4
  ret i64 %5
}

define i64 @add.1(i64 %0, i64 %1) {
  %x = alloca i64, align 8
  store i64 %0, ptr %x, align 4
  %y = alloca i64, align 8
  store i64 %1, ptr %y, align 4
  %3 = load i64, ptr %x, align 4
  %4 = load i64, ptr %y, align 4
  %5 = sub i64 %3, %4
  ret i64 %5
}
