; ModuleID = './tests/classes/class-inheritance.flo'
source_filename = "./tests/classes/class-inheritance.flo"

%Person = type <{ ptr, i64 }>
%PersonWithFavColor = type <{ ptr, i64, ptr }>

@Person_MAXAGE = global i64 90
@VTablePerson = global <{ ptr, ptr }> <{ ptr @Person_getAge, ptr @Person_setAge }>
@VTablePersonWithFavColor = global <{ ptr, ptr, ptr, ptr }> <{ ptr @Person_getAge, ptr @Person_setAge, ptr @PersonWithFavColor_setFavColor, ptr @PersonWithFavColor_getFavColor }>

define i64 @Person_max(i64 %0, i64 %1) {
end:
  %2 = icmp sgt i64 %0, %1
  %ternary = select i1 %2, i64 %0, i64 %1
  ret i64 %ternary
}

define i64 @Person_getAge(ptr %0) {
  %memberidx = getelementptr inbounds ptr, ptr %0, i64 1
  %2 = load i64, ptr %memberidx, align 4
  ret i64 %2
}

define void @Person_setAge(ptr %0, i64 %1) {
  %memberidx = getelementptr inbounds ptr, ptr %0, i64 1
  store i64 %1, ptr %memberidx, align 4
  ret void
}

define void @Person_constructor(ptr %0, i64 %1) {
  store ptr @VTablePerson, ptr %0, align 8
  %3 = load ptr, ptr getelementptr inbounds (<{ ptr, ptr }>, ptr @VTablePerson, i64 0, i32 1), align 8
  call void %3(ptr %0, i64 %1)
  ret void
}

define i64 @PersonWithFavColor_min(i64 %0, i64 %1) {
end:
  %2 = icmp sgt i64 %0, %1
  %ternary = select i1 %2, i64 %1, i64 %0
  ret i64 %ternary
}

define void @PersonWithFavColor_setFavColor(ptr %0, ptr %1) {
  %memberidx = getelementptr inbounds ptr, ptr %0, i64 2
  store ptr %1, ptr %memberidx, align 8
  ret void
}

define ptr @PersonWithFavColor_getFavColor(ptr %0) {
  %memberidx = getelementptr inbounds ptr, ptr %0, i64 2
  %2 = load ptr, ptr %memberidx, align 8
  ret ptr %2
}

define void @PersonWithFavColor_constructor(ptr %0, i64 %1) {
  store ptr @VTablePersonWithFavColor, ptr %0, align 8
  %3 = load ptr, ptr getelementptr inbounds (<{ ptr, ptr, ptr, ptr }>, ptr @VTablePersonWithFavColor, i64 0, i32 1), align 8
  call void %3(ptr %0, i64 %1)
  ret void
}

define i64 @main() {
  %1 = alloca %Person, align 8
  call void @Person_constructor(ptr %1, i64 54)
  %2 = alloca %PersonWithFavColor, align 8
  call void @PersonWithFavColor_constructor(ptr %2, i64 100)
  %3 = alloca %PersonWithFavColor, align 8
  call void @PersonWithFavColor_constructor(ptr %3, i64 11)
  %4 = load ptr, ptr %1, align 8
  %5 = load ptr, ptr %4, align 8
  %6 = call i64 %5(ptr %1)
  %7 = load ptr, ptr %3, align 8
  %8 = load ptr, ptr %7, align 8
  %9 = call i64 %8(ptr %3)
  %10 = call i64 @PersonWithFavColor_min(i64 %6, i64 %9)
  ret i64 %10
}

!llvm.dbg.cu = !{!0}

!0 = distinct !DICompileUnit(language: DW_LANG_C, file: !1, producer: "Flo Compiler", isOptimized: false, runtimeVersion: 0, emissionKind: FullDebug, splitDebugInlining: false, debugInfoForProfiling: true, sysroot: ".")
!1 = !DIFile(filename: "./tests/classes/class-inheritance.flo", directory: ".")
flo: malloc.c:2379: sysmalloc: Assertion `(old_top == initial_top (av) && old_size == 0) || ((unsigned long) (old_size) >= MINSIZE && prev_inuse (old_top) && ((unsigned long) old_end & (pagesize - 1)) == 0)' failed.
