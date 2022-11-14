; ModuleID = 'src/runtime/runtime-src.flo'
source_filename = "src/runtime/runtime-src.flo"

%string = type <{ ptr, ptr, i64, i64 }>

@VTablestring = global <{ ptr, ptr, ptr, ptr, ptr, ptr, ptr, ptr, ptr, ptr, ptr }> <{ ptr @string___add__, ptr @string_add_byte, ptr @string___getitem__, ptr @string___eq__, ptr @string_find, ptr @string___in__, ptr @string_substring, ptr @string_get_byte, ptr @string_get_bytes, ptr @string_replace, ptr @string_to_cstring }>
@VTableRange = global <{ ptr }> <{ ptr @Range___in__ }>

define ptr @string___add__(ptr %0, ptr %1) {
  %memberidx = getelementptr inbounds ptr, ptr %0, i64 2
  %3 = load i64, ptr %memberidx, align 4
  %memberidx1 = getelementptr inbounds ptr, ptr %1, i64 2
  %4 = load i64, ptr %memberidx1, align 4
  %5 = add i64 %3, %4
  %6 = tail call ptr @malloc(i32 ptrtoint (ptr getelementptr (i8, ptr null, i32 1) to i32))
  %memberidx2 = getelementptr inbounds ptr, ptr %0, i64 1
  %7 = load ptr, ptr %memberidx2, align 8
  %8 = load i64, ptr %memberidx, align 4
  %9 = call i64 @memcpy(ptr %6, ptr %7, i64 %8)
  %10 = load i64, ptr %memberidx, align 4
  %11 = getelementptr inbounds ptr, ptr %6, i64 %10
  %memberidx5 = getelementptr inbounds ptr, ptr %1, i64 1
  %12 = load ptr, ptr %memberidx5, align 8
  %13 = load i64, ptr %memberidx1, align 4
  %14 = add i64 %13, 1
  %15 = call i64 @memcpy(ptr %11, ptr %12, i64 %14)
  %16 = tail call ptr @malloc(i32 ptrtoint (ptr getelementptr (%string, ptr null, i32 1) to i32))
  call void @string_constructor(ptr %16, ptr %6, i64 %5)
  ret ptr %16
}

define void @string_add_byte(ptr %0, i8 %1) {
  %memberidx = getelementptr inbounds ptr, ptr %0, i64 2
  %3 = load i64, ptr %memberidx, align 4
  %4 = add i64 %3, 1
  %memberidx1 = getelementptr inbounds ptr, ptr %0, i64 3
  %5 = load i64, ptr %memberidx1, align 4
  %6 = icmp sge i64 %4, %5
  br i1 %6, label %if.entry, label %ifend

if.entry:                                         ; preds = %2
  %7 = mul i64 %5, 2
  store i64 %7, ptr %memberidx1, align 4
  %memberidx4 = getelementptr inbounds ptr, ptr %0, i64 1
  %8 = load ptr, ptr %memberidx4, align 8
  %9 = call ptr @realloc(ptr %8, i64 %7)
  store ptr %9, ptr %memberidx4, align 8
  br label %ifend

ifend:                                            ; preds = %2, %if.entry
  %10 = load i64, ptr %memberidx, align 4
  %memberidx8 = getelementptr inbounds ptr, ptr %0, i64 1
  %11 = load ptr, ptr %memberidx8, align 8
  %ptridx = getelementptr inbounds ptr, ptr %11, i64 %10
  store i8 %1, ptr %ptridx, align 1
  %12 = load i64, ptr %memberidx, align 4
  %13 = add i64 %12, 1
  store i64 %13, ptr %memberidx, align 4
  ret void
}

define ptr @string___getitem__(ptr %0, i64 %1) {
  %3 = tail call ptr @malloc(i32 ptrtoint (ptr getelementptr (i8, ptr null, i32 1) to i32))
  %memberidx = getelementptr inbounds ptr, ptr %0, i64 1
  %4 = load ptr, ptr %memberidx, align 8
  %ptridx1 = getelementptr inbounds ptr, ptr %4, i64 %1
  %5 = load i8, ptr %ptridx1, align 1
  store i8 %5, ptr %3, align 1
  %ptridx2 = getelementptr inbounds ptr, ptr %3, i64 1
  store i8 0, ptr %ptridx2, align 1
  %6 = tail call ptr @malloc(i32 ptrtoint (ptr getelementptr (%string, ptr null, i32 1) to i32))
  call void @string_constructor(ptr %6, ptr %3, i64 2)
  ret ptr %6
}

define i1 @string___eq__(ptr %0, ptr %1) {
  %memberidx = getelementptr inbounds ptr, ptr %0, i64 2
  %3 = load i64, ptr %memberidx, align 4
  %memberidx1 = getelementptr inbounds ptr, ptr %1, i64 2
  %4 = icmp ne i64 %3, 0
  br i1 %4, label %common.ret, label %ifend

common.ret:                                       ; preds = %2, %ifend
  %common.ret.op = phi i1 [ %8, %ifend ], [ false, %2 ]
  ret i1 %common.ret.op

ifend:                                            ; preds = %2
  %memberidx2 = getelementptr inbounds ptr, ptr %0, i64 1
  %5 = load ptr, ptr %memberidx2, align 8
  %memberidx3 = getelementptr inbounds ptr, ptr %1, i64 1
  %6 = load ptr, ptr %memberidx3, align 8
  %7 = call i64 @memcmp(ptr %5, ptr %6, i64 %3)
  %8 = icmp eq i64 %7, 0
  br label %common.ret
}

define i64 @string_find(ptr %0, ptr %1) {
for.entry:
  br label %for.cond

for.cond:                                         ; preds = %ifend, %for.entry
  %i.0 = phi i64 [ 0, %for.entry ], [ %13, %ifend ]
  %memberidx = getelementptr inbounds ptr, ptr %0, i64 2
  %2 = load i64, ptr %memberidx, align 4
  %3 = icmp slt i64 %i.0, %2
  br i1 %3, label %for.body, label %common.ret

for.body:                                         ; preds = %for.cond
  %memberidx1 = getelementptr inbounds ptr, ptr %1, i64 1
  %4 = load ptr, ptr %memberidx1, align 8
  %5 = load i8, ptr %4, align 1
  %memberidx2 = getelementptr inbounds ptr, ptr %0, i64 1
  %6 = load ptr, ptr %memberidx2, align 8
  %ptridx3 = getelementptr inbounds ptr, ptr %6, i64 %i.0
  %7 = load i8, ptr %ptridx3, align 1
  %8 = icmp eq i8 %5, %7
  br i1 %8, label %if.entry, label %ifend

common.ret:                                       ; preds = %while.entry, %for.cond, %if.entry12
  %common.ret.op = phi i64 [ %i.0, %if.entry12 ], [ -1, %for.cond ], [ -1, %while.entry ]
  ret i64 %common.ret.op

if.entry:                                         ; preds = %for.body
  %x = alloca i64, align 8
  %memberidx4 = getelementptr inbounds ptr, ptr %1, i64 2
  %9 = load i64, ptr %memberidx4, align 4
  %10 = sub i64 %9, 1
  store i64 %10, ptr %x, align 4
  %matches = alloca i1, align 1
  store i1 true, ptr %matches, align 1
  %11 = load i64, ptr %x, align 4
  %12 = icmp sgt i64 %11, 0
  br i1 %12, label %while.entry, label %while.end

ifend:                                            ; preds = %while.end, %for.body
  %13 = add i64 %i.0, 1
  br label %for.cond

while.entry:                                      ; preds = %ifend11, %if.entry
  %14 = load i64, ptr %x, align 4
  %15 = load ptr, ptr %memberidx1, align 8
  %ptridx6 = getelementptr inbounds ptr, ptr %15, i64 %14
  %16 = load i8, ptr %ptridx6, align 1
  %17 = add i64 %14, %i.0
  %18 = load ptr, ptr %memberidx2, align 8
  %ptridx8 = getelementptr inbounds ptr, ptr %18, i64 %17
  %19 = icmp ne i8 %16, 0
  br i1 %19, label %common.ret, label %ifend11

while.end:                                        ; preds = %ifend11, %if.entry
  %20 = load i1, ptr %matches, align 1
  br i1 %20, label %if.entry12, label %ifend

ifend11:                                          ; preds = %while.entry
  %21 = add i64 %14, -1
  store i64 %21, ptr %x, align 4
  %22 = icmp sgt i64 %21, 0
  br i1 %22, label %while.entry, label %while.end

if.entry12:                                       ; preds = %while.end
  br label %common.ret
}

define i1 @string___in__(ptr %0, ptr %1) {
  %3 = load ptr, ptr %0, align 8
  %memberidx = getelementptr inbounds ptr, ptr %3, i64 4
  %4 = load ptr, ptr %memberidx, align 8
  %5 = call i64 %4(ptr %0, ptr %1)
  %6 = icmp ne i64 %5, 0
  ret i1 %6
}

define ptr @string_substring(ptr %0, i64 %1, i64 %2) {
  %4 = tail call ptr @malloc(i32 ptrtoint (ptr getelementptr (%string, ptr null, i32 1) to i32))
  %memberidx = getelementptr inbounds ptr, ptr %0, i64 1
  %5 = load ptr, ptr %memberidx, align 8
  %6 = getelementptr inbounds ptr, ptr %5, i64 %1
  call void @string_constructor(ptr %4, ptr %6, i64 %2)
  ret ptr %4
}

define i8 @string_get_byte(ptr %0, i64 %1) {
  %memberidx = getelementptr inbounds ptr, ptr %0, i64 1
  %3 = load ptr, ptr %memberidx, align 8
  %ptridx = getelementptr inbounds ptr, ptr %3, i64 %1
  %4 = load i8, ptr %ptridx, align 1
  ret i8 %4
}

define ptr @string_get_bytes(ptr %0) {
  %memberidx = getelementptr inbounds ptr, ptr %0, i64 1
  %2 = load ptr, ptr %memberidx, align 8
  ret ptr %2
}

define ptr @string_replace(ptr %0, ptr %1, ptr %2) {
  %4 = load ptr, ptr %0, align 8
  %memberidx = getelementptr inbounds ptr, ptr %4, i64 4
  %5 = load ptr, ptr %memberidx, align 8
  %6 = call i64 %5(ptr %0, ptr %1)
  %7 = icmp sgt i64 %6, 0
  br i1 %7, label %if.entry, label %ifend

common.ret:                                       ; preds = %ifend, %if.entry
  %common.ret.op = phi ptr [ %31, %if.entry ], [ %0, %ifend ]
  ret ptr %common.ret.op

if.entry:                                         ; preds = %3
  %new_length = alloca i64, align 8
  %memberidx1 = getelementptr inbounds ptr, ptr %0, i64 2
  %8 = load i64, ptr %memberidx1, align 4
  %memberidx2 = getelementptr inbounds ptr, ptr %1, i64 2
  %9 = load i64, ptr %memberidx2, align 4
  %memberidx3 = getelementptr inbounds ptr, ptr %2, i64 2
  %10 = load i64, ptr %memberidx3, align 4
  %11 = add i64 %9, %10
  %12 = sub i64 %8, %11
  store i64 %12, ptr %new_length, align 4
  %new_buffer = alloca ptr, align 8
  %13 = tail call ptr @malloc(i32 ptrtoint (ptr getelementptr (i8, ptr null, i32 1) to i32))
  store ptr %13, ptr %new_buffer, align 8
  %memberidx4 = getelementptr inbounds ptr, ptr %0, i64 1
  %14 = load ptr, ptr %memberidx4, align 8
  %15 = call i64 @memcpy(ptr %13, ptr %14, i64 %6)
  %16 = load ptr, ptr %new_buffer, align 8
  %17 = getelementptr inbounds ptr, ptr %16, i64 %6
  %memberidx5 = getelementptr inbounds ptr, ptr %2, i64 1
  %18 = load ptr, ptr %memberidx5, align 8
  %19 = load i64, ptr %memberidx3, align 4
  %20 = call i64 @memcpy(ptr %17, ptr %18, i64 %19)
  %21 = load ptr, ptr %new_buffer, align 8
  %22 = load i64, ptr %memberidx3, align 4
  %23 = add i64 %6, %22
  %24 = getelementptr inbounds ptr, ptr %21, i64 %23
  %25 = load ptr, ptr %memberidx4, align 8
  %26 = add i64 %6, 1
  %27 = getelementptr inbounds ptr, ptr %25, i64 %26
  %28 = load i64, ptr %memberidx1, align 4
  %29 = sub i64 %28, %6
  %30 = call i64 @memcpy(ptr %24, ptr %27, i64 %29)
  %31 = tail call ptr @malloc(i32 ptrtoint (ptr getelementptr (%string, ptr null, i32 1) to i32))
  %32 = load ptr, ptr %new_buffer, align 8
  %33 = load i64, ptr %new_length, align 4
  call void @string_constructor(ptr %31, ptr %32, i64 %33)
  br label %common.ret

ifend:                                            ; preds = %3
  br label %common.ret
}

define ptr @string_to_cstring(ptr %0) {
  %2 = tail call ptr @malloc(i32 ptrtoint (ptr getelementptr (i8, ptr null, i32 1) to i32))
  %memberidx = getelementptr inbounds ptr, ptr %0, i64 1
  %3 = load ptr, ptr %memberidx, align 8
  %memberidx1 = getelementptr inbounds ptr, ptr %0, i64 2
  %4 = load i64, ptr %memberidx1, align 4
  %5 = call i64 @memcpy(ptr %2, ptr %3, i64 %4)
  %6 = load i64, ptr %memberidx1, align 4
  %ptridx = getelementptr inbounds ptr, ptr %2, i64 %6
  store i8 0, ptr %ptridx, align 1
  ret ptr %2
}

define void @string_constructor(ptr %0, ptr %1, i64 %2) {
  store ptr @VTablestring, ptr %0, align 8
  %memberidx = getelementptr inbounds ptr, ptr %0, i64 1
  store ptr %1, ptr %memberidx, align 8
  %memberidx1 = getelementptr inbounds ptr, ptr %0, i64 2
  store i64 %2, ptr %memberidx1, align 4
  %memberidx2 = getelementptr inbounds ptr, ptr %0, i64 3
  store i64 %2, ptr %memberidx2, align 4
  ret void
}

define i1 @Range___in__(ptr %0, i64 %1) {
  %memberidx = getelementptr inbounds ptr, ptr %0, i64 1
  %3 = load i64, ptr %memberidx, align 4
  %4 = icmp sge i64 %1, %3
  %memberidx1 = getelementptr inbounds ptr, ptr %0, i64 2
  %5 = load i64, ptr %memberidx1, align 4
  %6 = icmp slt i64 %1, %5
  %7 = and i1 %4, %6
  ret i1 %7
}

define void @Range_constructor(ptr %0, i64 %1, i64 %2) {
  store ptr @VTableRange, ptr %0, align 8
  %memberidx = getelementptr inbounds ptr, ptr %0, i64 1
  store i64 %1, ptr %memberidx, align 4
  %memberidx1 = getelementptr inbounds ptr, ptr %0, i64 2
  store i64 %2, ptr %memberidx1, align 4
  ret void
}

declare i64 @memcmp(ptr %0, ptr %1, i64 %2)

declare i64 @memcpy(ptr %0, ptr %1, i64 %2)

declare void @memset(ptr %0, i64 %1, i64 %2)

declare ptr @realloc(ptr %0, i64 %1)

declare noalias ptr @malloc(i32 %0)

!llvm.dbg.cu = !{!0}

!0 = distinct !DICompileUnit(language: DW_LANG_C, file: !1, producer: "Flo Compiler", isOptimized: false, runtimeVersion: 0, emissionKind: FullDebug, splitDebugInlining: false, debugInfoForProfiling: true, sysroot: ".")
!1 = !DIFile(filename: "src/runtime/runtime-src.flo", directory: ".")
