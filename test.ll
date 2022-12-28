; ModuleID = 'examples/test.flo'
source_filename = "examples/test.flo"

%string = type <{ ptr, ptr, i64, i64 }>

@0 = private unnamed_addr constant [3 x i8] c"%s\00", align 1
@STDOUT = constant i64 1
@VTablestring = global <{ ptr, ptr, ptr, ptr, ptr, ptr, ptr, ptr, ptr, ptr, ptr, ptr, ptr }> <{ ptr @string___add__, ptr @string___adda__, ptr @string___getitem__, ptr @string___eq__, ptr @string_find, ptr @string___in__, ptr @string_substring, ptr @string_get_byte, ptr @string_get_bytes, ptr @string_replace, ptr @string_to_cstring, ptr @string_ends_with, ptr @string_starts_with }>
@VTableStringBuilder = global <{ ptr, ptr, ptr, ptr }> <{ ptr @StringBuilder_add_bytes_length, ptr @StringBuilder_append_string, ptr @StringBuilder_add_byte, ptr @StringBuilder_get_string }>
@VTableRange = global <{ ptr }> <{ ptr @Range___in__ }>
@1 = private unnamed_addr constant [2 x i8] c"\0A\00", align 1

define i64 @main() {
  %1 = call i64 (ptr, i64, ptr, ...) @snprintf(ptr null, i64 0, ptr @0, [5 x i8] c"true\00")
  %2 = trunc i64 %1 to i32
  %mallocsize = mul i32 %2, ptrtoint (ptr getelementptr (i8, ptr null, i32 1) to i32)
  %3 = tail call ptr @malloc(i32 %mallocsize)
  %4 = call i64 (ptr, ptr, ...) @sprintf(ptr %3, ptr @0, [5 x i8] c"true\00")
  %5 = tail call ptr @malloc(i32 ptrtoint (ptr getelementptr (ptr, ptr null, i32 1) to i32))
  call void @string_constructor(ptr %5, ptr %3, i64 %1)
  call void @println(ptr %5)
  ret i64 0
}

declare i64 @snprintf(ptr %0, i64 %1, ptr %2, ...)

declare noalias ptr @malloc(i32 %0)

declare i64 @sprintf(ptr %0, ptr %1, ...)

define ptr @string___add__(ptr %0, ptr %1) {
  %this = alloca ptr, align 8
  store ptr %0, ptr %this, align 8
  %data = alloca ptr, align 8
  store ptr %1, ptr %data, align 8
  %new_str_len = alloca i64, align 8
  %3 = load ptr, ptr %this, align 8
  %memberidx = getelementptr inbounds ptr, ptr %3, i64 2
  %4 = load i64, ptr %memberidx, align 4
  %5 = load ptr, ptr %data, align 8
  %memberidx1 = getelementptr inbounds ptr, ptr %5, i64 2
  %6 = load i64, ptr %memberidx1, align 4
  %7 = add i64 %4, %6
  store i64 %7, ptr %new_str_len, align 4
  %new_buffer = alloca ptr, align 8
  %8 = load i64, ptr %new_str_len, align 4
  %9 = trunc i64 %8 to i32
  %mallocsize = mul i32 %9, ptrtoint (ptr getelementptr (i8, ptr null, i32 1) to i32)
  %10 = tail call ptr @malloc(i32 %mallocsize)
  store ptr %10, ptr %new_buffer, align 8
  %11 = load ptr, ptr %new_buffer, align 8
  %12 = load ptr, ptr %this, align 8
  %memberidx2 = getelementptr inbounds ptr, ptr %12, i64 1
  %13 = load ptr, ptr %memberidx2, align 8
  %14 = load ptr, ptr %this, align 8
  %memberidx3 = getelementptr inbounds ptr, ptr %14, i64 2
  %15 = load i64, ptr %memberidx3, align 4
  %16 = call i64 @memcpy(ptr %11, ptr %13, i64 %15)
  %trailing_buffer = alloca ptr, align 8
  %17 = load ptr, ptr %new_buffer, align 8
  %18 = load ptr, ptr %this, align 8
  %memberidx4 = getelementptr inbounds ptr, ptr %18, i64 2
  %19 = load i64, ptr %memberidx4, align 4
  %20 = getelementptr inbounds ptr, ptr %17, i64 %19
  store ptr %20, ptr %trailing_buffer, align 8
  %21 = load ptr, ptr %trailing_buffer, align 8
  %22 = load ptr, ptr %data, align 8
  %memberidx5 = getelementptr inbounds ptr, ptr %22, i64 1
  %23 = load ptr, ptr %memberidx5, align 8
  %24 = load ptr, ptr %data, align 8
  %memberidx6 = getelementptr inbounds ptr, ptr %24, i64 2
  %25 = load i64, ptr %memberidx6, align 4
  %26 = call i64 @memcpy(ptr %21, ptr %23, i64 %25)
  %27 = tail call ptr @malloc(i32 ptrtoint (ptr getelementptr (%string, ptr null, i32 1) to i32))
  %28 = load ptr, ptr %new_buffer, align 8
  %29 = load i64, ptr %new_str_len, align 4
  call void @string_constructor(ptr %27, ptr %28, i64 %29)
  ret ptr %27
}

define ptr @string___adda__(ptr %0, ptr %1) {
  %this = alloca ptr, align 8
  store ptr %0, ptr %this, align 8
  %other = alloca ptr, align 8
  store ptr %1, ptr %other, align 8
  %3 = load ptr, ptr %this, align 8
  %memberidx = getelementptr inbounds ptr, ptr %3, i64 1
  %4 = load ptr, ptr %this, align 8
  %memberidx1 = getelementptr inbounds ptr, ptr %4, i64 1
  %5 = load ptr, ptr %memberidx1, align 8
  %6 = load ptr, ptr %this, align 8
  %memberidx2 = getelementptr inbounds ptr, ptr %6, i64 2
  %7 = load i64, ptr %memberidx2, align 4
  %8 = load ptr, ptr %other, align 8
  %memberidx3 = getelementptr inbounds ptr, ptr %8, i64 2
  %9 = load i64, ptr %memberidx3, align 4
  %10 = add i64 %7, %9
  %11 = mul i64 %10, ptrtoint (ptr getelementptr (i8, ptr null, i32 1) to i64)
  %12 = call ptr @realloc(ptr %5, i64 %11)
  store ptr %12, ptr %memberidx, align 8
  %13 = load ptr, ptr %this, align 8
  %memberidx4 = getelementptr inbounds ptr, ptr %13, i64 1
  %14 = load ptr, ptr %memberidx4, align 8
  %15 = load ptr, ptr %this, align 8
  %memberidx5 = getelementptr inbounds ptr, ptr %15, i64 2
  %16 = load i64, ptr %memberidx5, align 4
  %17 = getelementptr inbounds ptr, ptr %14, i64 %16
  %18 = load ptr, ptr %other, align 8
  %memberidx6 = getelementptr inbounds ptr, ptr %18, i64 1
  %19 = load ptr, ptr %memberidx6, align 8
  %20 = load ptr, ptr %other, align 8
  %memberidx7 = getelementptr inbounds ptr, ptr %20, i64 2
  %21 = load i64, ptr %memberidx7, align 4
  %22 = call i64 @memcpy(ptr %17, ptr %19, i64 %21)
  %23 = load ptr, ptr %this, align 8
  ret ptr %23
}

define ptr @string___getitem__(ptr %0, i64 %1) {
  %this = alloca ptr, align 8
  store ptr %0, ptr %this, align 8
  %index = alloca i64, align 8
  store i64 %1, ptr %index, align 4
  %new_buffer = alloca ptr, align 8
  %3 = trunc i64 2 to i32
  %mallocsize = mul i32 %3, ptrtoint (ptr getelementptr (i8, ptr null, i32 1) to i32)
  %4 = tail call ptr @malloc(i32 %mallocsize)
  store ptr %4, ptr %new_buffer, align 8
  %5 = load ptr, ptr %new_buffer, align 8
  %ptridx = getelementptr inbounds ptr, ptr %5, i64 0
  %6 = load i64, ptr %index, align 4
  %7 = load ptr, ptr %this, align 8
  %memberidx = getelementptr inbounds ptr, ptr %7, i64 1
  %8 = load ptr, ptr %memberidx, align 8
  %ptridx1 = getelementptr inbounds ptr, ptr %8, i64 %6
  %9 = load i8, ptr %ptridx1, align 1
  store i8 %9, ptr %ptridx, align 1
  %10 = load ptr, ptr %new_buffer, align 8
  %ptridx2 = getelementptr inbounds ptr, ptr %10, i64 1
  store i8 0, ptr %ptridx2, align 1
  %11 = tail call ptr @malloc(i32 ptrtoint (ptr getelementptr (%string, ptr null, i32 1) to i32))
  %12 = load ptr, ptr %new_buffer, align 8
  call void @string_constructor(ptr %11, ptr %12, i64 2)
  ret ptr %11
}

define i1 @string___eq__(ptr %0, ptr %1) {
  %this = alloca ptr, align 8
  store ptr %0, ptr %this, align 8
  %other = alloca ptr, align 8
  store ptr %1, ptr %other, align 8
  %3 = load ptr, ptr %this, align 8
  %memberidx = getelementptr inbounds ptr, ptr %3, i64 2
  %4 = load i64, ptr %memberidx, align 4
  %5 = load ptr, ptr %other, align 8
  %memberidx1 = getelementptr inbounds ptr, ptr %5, i64 2
  %6 = load i64, ptr %memberidx1, align 4
  %7 = icmp ne i64 %4, 0
  br i1 %7, label %if.entry, label %else

if.entry:                                         ; preds = %2
  ret i1 false

else:                                             ; preds = %2
  br label %ifend

ifend:                                            ; preds = %else
  %8 = load ptr, ptr %this, align 8
  %memberidx2 = getelementptr inbounds ptr, ptr %8, i64 1
  %9 = load ptr, ptr %memberidx2, align 8
  %10 = load ptr, ptr %other, align 8
  %memberidx3 = getelementptr inbounds ptr, ptr %10, i64 1
  %11 = load ptr, ptr %memberidx3, align 8
  %12 = load ptr, ptr %this, align 8
  %memberidx4 = getelementptr inbounds ptr, ptr %12, i64 2
  %13 = load i64, ptr %memberidx4, align 4
  %14 = call i64 @memcmp(ptr %9, ptr %11, i64 %13)
  %15 = icmp eq i64 %14, 0
  ret i1 %15
}

define i64 @string_find(ptr %0, ptr %1, i64 %2) {
  %this = alloca ptr, align 8
  store ptr %0, ptr %this, align 8
  %search = alloca ptr, align 8
  store ptr %1, ptr %search, align 8
  %start = alloca i64, align 8
  store i64 %2, ptr %start, align 4
  br label %for.entry

for.entry:                                        ; preds = %3
  %i = alloca i64, align 8
  %4 = load i64, ptr %start, align 4
  store i64 %4, ptr %i, align 4
  br label %for.cond

for.cond:                                         ; preds = %for.incr, %for.entry
  %5 = load i64, ptr %i, align 4
  %6 = load ptr, ptr %this, align 8
  %memberidx = getelementptr inbounds ptr, ptr %6, i64 2
  %7 = load i64, ptr %memberidx, align 4
  %8 = icmp slt i64 %5, %7
  br i1 %8, label %for.body, label %for.end

for.body:                                         ; preds = %for.cond
  %9 = load ptr, ptr %search, align 8
  %memberidx1 = getelementptr inbounds ptr, ptr %9, i64 1
  %10 = load ptr, ptr %memberidx1, align 8
  %ptridx = getelementptr inbounds ptr, ptr %10, i64 0
  %11 = load i8, ptr %ptridx, align 1
  %12 = load i64, ptr %i, align 4
  %13 = load ptr, ptr %this, align 8
  %memberidx2 = getelementptr inbounds ptr, ptr %13, i64 1
  %14 = load ptr, ptr %memberidx2, align 8
  %ptridx3 = getelementptr inbounds ptr, ptr %14, i64 %12
  %15 = load i8, ptr %ptridx3, align 1
  %16 = icmp eq i8 %11, %15
  br i1 %16, label %if.entry, label %else

for.incr:                                         ; preds = %ifend
  %17 = load i64, ptr %i, align 4
  %18 = add i64 %17, 1
  store i64 %18, ptr %i, align 4
  br label %for.cond

for.end:                                          ; preds = %for.cond
  ret i64 -1

if.entry:                                         ; preds = %for.body
  %x = alloca i64, align 8
  %19 = load ptr, ptr %search, align 8
  %memberidx4 = getelementptr inbounds ptr, ptr %19, i64 2
  %20 = load i64, ptr %memberidx4, align 4
  %21 = sub i64 %20, 1
  store i64 %21, ptr %x, align 4
  %matches = alloca i1, align 1
  store i1 true, ptr %matches, align 1
  %22 = load i64, ptr %x, align 4
  %23 = icmp sgt i64 %22, 0
  br i1 %23, label %while.entry, label %while.end

else:                                             ; preds = %for.body
  br label %ifend

ifend:                                            ; preds = %else, %ifend14
  br label %for.incr

while.entry:                                      ; preds = %ifend11, %if.entry
  %24 = load i64, ptr %x, align 4
  %25 = load ptr, ptr %search, align 8
  %memberidx5 = getelementptr inbounds ptr, ptr %25, i64 1
  %26 = load ptr, ptr %memberidx5, align 8
  %ptridx6 = getelementptr inbounds ptr, ptr %26, i64 %24
  %27 = load i8, ptr %ptridx6, align 1
  %28 = load i64, ptr %x, align 4
  %29 = load i64, ptr %i, align 4
  %30 = add i64 %28, %29
  %31 = load ptr, ptr %this, align 8
  %memberidx7 = getelementptr inbounds ptr, ptr %31, i64 1
  %32 = load ptr, ptr %memberidx7, align 8
  %ptridx8 = getelementptr inbounds ptr, ptr %32, i64 %30
  %33 = load i8, ptr %ptridx8, align 1
  %34 = icmp ne i8 %27, 0
  br i1 %34, label %if.entry9, label %else10

while.end:                                        ; preds = %ifend11, %if.entry
  %35 = load i1, ptr %matches, align 1
  br i1 %35, label %if.entry12, label %else13

if.entry9:                                        ; preds = %while.entry
  ret i64 -1

else10:                                           ; preds = %while.entry
  br label %ifend11

ifend11:                                          ; preds = %else10
  %36 = load i64, ptr %x, align 4
  %37 = add i64 %36, -1
  store i64 %37, ptr %x, align 4
  %38 = load i64, ptr %x, align 4
  %39 = icmp sgt i64 %38, 0
  br i1 %39, label %while.entry, label %while.end

if.entry12:                                       ; preds = %while.end
  %40 = load i64, ptr %i, align 4
  ret i64 %40

else13:                                           ; preds = %while.end
  br label %ifend14

ifend14:                                          ; preds = %else13
  br label %ifend
}

define i1 @string___in__(ptr %0, ptr %1) {
  %this = alloca ptr, align 8
  store ptr %0, ptr %this, align 8
  %other = alloca ptr, align 8
  store ptr %1, ptr %other, align 8
  %3 = load ptr, ptr %this, align 8
  %4 = getelementptr inbounds ptr, ptr %3, i64 0
  %5 = load ptr, ptr %4, align 8
  %memberidx = getelementptr inbounds ptr, ptr %5, i64 4
  %6 = load ptr, ptr %memberidx, align 8
  %7 = load ptr, ptr %other, align 8
  %8 = call i64 %6(ptr %3, ptr %7, i64 0)
  %9 = icmp ne i64 %8, 0
  ret i1 %9
}

define ptr @string_substring(ptr %0, i64 %1, i64 %2) {
  %this = alloca ptr, align 8
  store ptr %0, ptr %this, align 8
  %start = alloca i64, align 8
  store i64 %1, ptr %start, align 4
  %length = alloca i64, align 8
  store i64 %2, ptr %length, align 4
  %4 = tail call ptr @malloc(i32 ptrtoint (ptr getelementptr (%string, ptr null, i32 1) to i32))
  %5 = load ptr, ptr %this, align 8
  %memberidx = getelementptr inbounds ptr, ptr %5, i64 1
  %6 = load ptr, ptr %memberidx, align 8
  %7 = load i64, ptr %start, align 4
  %8 = getelementptr inbounds ptr, ptr %6, i64 %7
  %9 = load i64, ptr %length, align 4
  call void @string_constructor(ptr %4, ptr %8, i64 %9)
  ret ptr %4
}

define i8 @string_get_byte(ptr %0, i64 %1) {
  %this = alloca ptr, align 8
  store ptr %0, ptr %this, align 8
  %index = alloca i64, align 8
  store i64 %1, ptr %index, align 4
  %3 = load i64, ptr %index, align 4
  %4 = load ptr, ptr %this, align 8
  %memberidx = getelementptr inbounds ptr, ptr %4, i64 1
  %5 = load ptr, ptr %memberidx, align 8
  %ptridx = getelementptr inbounds ptr, ptr %5, i64 %3
  %6 = load i8, ptr %ptridx, align 1
  ret i8 %6
}

define ptr @string_get_bytes(ptr %0) {
  %this = alloca ptr, align 8
  store ptr %0, ptr %this, align 8
  %2 = load ptr, ptr %this, align 8
  %memberidx = getelementptr inbounds ptr, ptr %2, i64 1
  %3 = load ptr, ptr %memberidx, align 8
  ret ptr %3
}

define ptr @string_replace(ptr %0, ptr %1, ptr %2) {
  %this = alloca ptr, align 8
  store ptr %0, ptr %this, align 8
  %val = alloca ptr, align 8
  store ptr %1, ptr %val, align 8
  %repl = alloca ptr, align 8
  store ptr %2, ptr %repl, align 8
  %idx = alloca i64, align 8
  %4 = load ptr, ptr %this, align 8
  %5 = getelementptr inbounds ptr, ptr %4, i64 0
  %6 = load ptr, ptr %5, align 8
  %memberidx = getelementptr inbounds ptr, ptr %6, i64 4
  %7 = load ptr, ptr %memberidx, align 8
  %8 = load ptr, ptr %val, align 8
  %9 = call i64 %7(ptr %4, ptr %8, i64 0)
  store i64 %9, ptr %idx, align 4
  %10 = load i64, ptr %idx, align 4
  %11 = icmp sge i64 %10, 0
  br i1 %11, label %if.entry, label %else

if.entry:                                         ; preds = %3
  %nlen = alloca i64, align 8
  %12 = load ptr, ptr %this, align 8
  %memberidx1 = getelementptr inbounds ptr, ptr %12, i64 2
  %13 = load i64, ptr %memberidx1, align 4
  %14 = load ptr, ptr %val, align 8
  %memberidx2 = getelementptr inbounds ptr, ptr %14, i64 2
  %15 = load i64, ptr %memberidx2, align 4
  %16 = load ptr, ptr %repl, align 8
  %memberidx3 = getelementptr inbounds ptr, ptr %16, i64 2
  %17 = load i64, ptr %memberidx3, align 4
  %18 = add i64 %15, %17
  %19 = sub i64 %13, %18
  store i64 %19, ptr %nlen, align 4
  %nbuff = alloca ptr, align 8
  %20 = load i64, ptr %nlen, align 4
  %21 = trunc i64 %20 to i32
  %mallocsize = mul i32 %21, ptrtoint (ptr getelementptr (i8, ptr null, i32 1) to i32)
  %22 = tail call ptr @malloc(i32 %mallocsize)
  store ptr %22, ptr %nbuff, align 8
  %23 = load ptr, ptr %nbuff, align 8
  %24 = load ptr, ptr %this, align 8
  %memberidx4 = getelementptr inbounds ptr, ptr %24, i64 1
  %25 = load ptr, ptr %memberidx4, align 8
  %26 = load i64, ptr %idx, align 4
  %27 = call i64 @memcpy(ptr %23, ptr %25, i64 %26)
  %wbuff = alloca ptr, align 8
  %28 = load ptr, ptr %nbuff, align 8
  %29 = load i64, ptr %idx, align 4
  %30 = getelementptr inbounds ptr, ptr %28, i64 %29
  store ptr %30, ptr %wbuff, align 8
  %31 = load ptr, ptr %wbuff, align 8
  %32 = load ptr, ptr %repl, align 8
  %memberidx5 = getelementptr inbounds ptr, ptr %32, i64 1
  %33 = load ptr, ptr %memberidx5, align 8
  %34 = load ptr, ptr %repl, align 8
  %memberidx6 = getelementptr inbounds ptr, ptr %34, i64 2
  %35 = load i64, ptr %memberidx6, align 4
  %36 = call i64 @memcpy(ptr %31, ptr %33, i64 %35)
  %37 = load ptr, ptr %wbuff, align 8
  %38 = load ptr, ptr %repl, align 8
  %memberidx7 = getelementptr inbounds ptr, ptr %38, i64 2
  %39 = load i64, ptr %memberidx7, align 4
  %40 = getelementptr inbounds ptr, ptr %37, i64 %39
  store ptr %40, ptr %wbuff, align 8
  %41 = load ptr, ptr %wbuff, align 8
  %42 = load ptr, ptr %this, align 8
  %memberidx8 = getelementptr inbounds ptr, ptr %42, i64 1
  %43 = load ptr, ptr %memberidx8, align 8
  %44 = load i64, ptr %idx, align 4
  %45 = load ptr, ptr %val, align 8
  %memberidx9 = getelementptr inbounds ptr, ptr %45, i64 2
  %46 = load i64, ptr %memberidx9, align 4
  %47 = add i64 %44, %46
  %48 = getelementptr inbounds ptr, ptr %43, i64 %47
  %49 = load ptr, ptr %this, align 8
  %memberidx10 = getelementptr inbounds ptr, ptr %49, i64 2
  %50 = load i64, ptr %memberidx10, align 4
  %51 = load ptr, ptr %val, align 8
  %memberidx11 = getelementptr inbounds ptr, ptr %51, i64 2
  %52 = load i64, ptr %memberidx11, align 4
  %53 = sub i64 %50, %52
  %54 = call i64 @memcpy(ptr %41, ptr %48, i64 %53)
  %55 = tail call ptr @malloc(i32 ptrtoint (ptr getelementptr (%string, ptr null, i32 1) to i32))
  %56 = load ptr, ptr %nbuff, align 8
  %57 = load i64, ptr %nlen, align 4
  call void @string_constructor(ptr %55, ptr %56, i64 %57)
  ret ptr %55

else:                                             ; preds = %3
  br label %ifend

ifend:                                            ; preds = %else
  %58 = load ptr, ptr %this, align 8
  ret ptr %58
}

define ptr @string_to_cstring(ptr %0) {
  %this = alloca ptr, align 8
  store ptr %0, ptr %this, align 8
  %c_string = alloca ptr, align 8
  %2 = load ptr, ptr %this, align 8
  %memberidx = getelementptr inbounds ptr, ptr %2, i64 2
  %3 = load i64, ptr %memberidx, align 4
  %4 = add i64 %3, 1
  %5 = trunc i64 %4 to i32
  %mallocsize = mul i32 %5, ptrtoint (ptr getelementptr (i8, ptr null, i32 1) to i32)
  %6 = tail call ptr @malloc(i32 %mallocsize)
  store ptr %6, ptr %c_string, align 8
  %7 = load ptr, ptr %c_string, align 8
  %8 = load ptr, ptr %this, align 8
  %memberidx1 = getelementptr inbounds ptr, ptr %8, i64 1
  %9 = load ptr, ptr %memberidx1, align 8
  %10 = load ptr, ptr %this, align 8
  %memberidx2 = getelementptr inbounds ptr, ptr %10, i64 2
  %11 = load i64, ptr %memberidx2, align 4
  %12 = call i64 @memcpy(ptr %7, ptr %9, i64 %11)
  %13 = load ptr, ptr %this, align 8
  %memberidx3 = getelementptr inbounds ptr, ptr %13, i64 2
  %14 = load i64, ptr %memberidx3, align 4
  %15 = load ptr, ptr %c_string, align 8
  %ptridx = getelementptr inbounds ptr, ptr %15, i64 %14
  store i8 0, ptr %ptridx, align 1
  %16 = load ptr, ptr %c_string, align 8
  ret ptr %16
}

define i1 @string_ends_with(ptr %0, ptr %1) {
  %this = alloca ptr, align 8
  store ptr %0, ptr %this, align 8
  %suffix = alloca ptr, align 8
  store ptr %1, ptr %suffix, align 8
  %3 = load ptr, ptr %this, align 8
  %memberidx = getelementptr inbounds ptr, ptr %3, i64 2
  %4 = load i64, ptr %memberidx, align 4
  %5 = load ptr, ptr %suffix, align 8
  %memberidx1 = getelementptr inbounds ptr, ptr %5, i64 2
  %6 = load i64, ptr %memberidx1, align 4
  %7 = icmp slt i64 %4, %6
  br i1 %7, label %if.entry, label %else

if.entry:                                         ; preds = %2
  ret i1 false

else:                                             ; preds = %2
  br label %ifend

ifend:                                            ; preds = %else
  %end_buff = alloca ptr, align 8
  %8 = load ptr, ptr %this, align 8
  %memberidx2 = getelementptr inbounds ptr, ptr %8, i64 1
  %9 = load ptr, ptr %memberidx2, align 8
  %10 = load ptr, ptr %this, align 8
  %memberidx3 = getelementptr inbounds ptr, ptr %10, i64 2
  %11 = load i64, ptr %memberidx3, align 4
  %12 = load ptr, ptr %suffix, align 8
  %memberidx4 = getelementptr inbounds ptr, ptr %12, i64 2
  %13 = load i64, ptr %memberidx4, align 4
  %14 = sub i64 %11, %13
  %15 = getelementptr inbounds ptr, ptr %9, i64 %14
  store ptr %15, ptr %end_buff, align 8
  %16 = load ptr, ptr %end_buff, align 8
  %17 = load ptr, ptr %suffix, align 8
  %memberidx5 = getelementptr inbounds ptr, ptr %17, i64 1
  %18 = load ptr, ptr %memberidx5, align 8
  %19 = load ptr, ptr %suffix, align 8
  %memberidx6 = getelementptr inbounds ptr, ptr %19, i64 2
  %20 = load i64, ptr %memberidx6, align 4
  %21 = call i64 @memcmp(ptr %16, ptr %18, i64 %20)
  %22 = icmp eq i64 %21, 0
  ret i1 %22
}

define i1 @string_starts_with(ptr %0, ptr %1) {
  %this = alloca ptr, align 8
  store ptr %0, ptr %this, align 8
  %preffix = alloca ptr, align 8
  store ptr %1, ptr %preffix, align 8
  %3 = load ptr, ptr %this, align 8
  %memberidx = getelementptr inbounds ptr, ptr %3, i64 2
  %4 = load i64, ptr %memberidx, align 4
  %5 = load ptr, ptr %preffix, align 8
  %memberidx1 = getelementptr inbounds ptr, ptr %5, i64 2
  %6 = load i64, ptr %memberidx1, align 4
  %7 = icmp slt i64 %4, %6
  br i1 %7, label %if.entry, label %else

if.entry:                                         ; preds = %2
  ret i1 false

else:                                             ; preds = %2
  br label %ifend

ifend:                                            ; preds = %else
  %8 = load ptr, ptr %this, align 8
  %memberidx2 = getelementptr inbounds ptr, ptr %8, i64 1
  %9 = load ptr, ptr %memberidx2, align 8
  %10 = load ptr, ptr %preffix, align 8
  %memberidx3 = getelementptr inbounds ptr, ptr %10, i64 1
  %11 = load ptr, ptr %memberidx3, align 8
  %12 = load ptr, ptr %preffix, align 8
  %memberidx4 = getelementptr inbounds ptr, ptr %12, i64 2
  %13 = load i64, ptr %memberidx4, align 4
  %14 = call i64 @memcmp(ptr %9, ptr %11, i64 %13)
  %15 = icmp eq i64 %14, 0
  ret i1 %15
}

declare i64 @memcmp(ptr %0, ptr %1, i64 %2)

declare i64 @memcpy(ptr %0, ptr %1, i64 %2)

define void @string_constructor(ptr %0, ptr %1, i64 %2) {
  %this = alloca ptr, align 8
  store ptr %0, ptr %this, align 8
  %4 = getelementptr inbounds ptr, ptr %0, i64 0
  store ptr @VTablestring, ptr %4, align 8
  %data = alloca ptr, align 8
  store ptr %1, ptr %data, align 8
  %len = alloca i64, align 8
  store i64 %2, ptr %len, align 4
  %5 = load ptr, ptr %this, align 8
  %memberidx = getelementptr inbounds ptr, ptr %5, i64 1
  %6 = load ptr, ptr %data, align 8
  store ptr %6, ptr %memberidx, align 8
  %7 = load ptr, ptr %this, align 8
  %memberidx1 = getelementptr inbounds ptr, ptr %7, i64 2
  %8 = load i64, ptr %len, align 4
  store i64 %8, ptr %memberidx1, align 4
  %9 = load ptr, ptr %this, align 8
  %memberidx2 = getelementptr inbounds ptr, ptr %9, i64 3
  %10 = load i64, ptr %len, align 4
  store i64 %10, ptr %memberidx2, align 4
  ret void
}

declare ptr @realloc(ptr %0, i64 %1)

define void @StringBuilder_add_bytes_length(ptr %0, ptr %1, i64 %2) {
  %this = alloca ptr, align 8
  store ptr %0, ptr %this, align 8
  %bytes = alloca ptr, align 8
  store ptr %1, ptr %bytes, align 8
  %length = alloca i64, align 8
  store i64 %2, ptr %length, align 4
  %4 = load ptr, ptr %this, align 8
  %memberidx = getelementptr inbounds ptr, ptr %4, i64 2
  %5 = load i64, ptr %memberidx, align 4
  %6 = load ptr, ptr %this, align 8
  %memberidx1 = getelementptr inbounds ptr, ptr %6, i64 4
  %7 = load i64, ptr %memberidx1, align 4
  %8 = sub i64 %5, %7
  %9 = load i64, ptr %length, align 4
  %10 = icmp sle i64 %8, %9
  br i1 %10, label %if.entry, label %else

if.entry:                                         ; preds = %3
  %11 = load ptr, ptr %this, align 8
  call void @StringBuilder_resize(ptr %11)
  br label %ifend

else:                                             ; preds = %3
  br label %ifend

ifend:                                            ; preds = %else, %if.entry
  %12 = load ptr, ptr %this, align 8
  %memberidx2 = getelementptr inbounds ptr, ptr %12, i64 3
  %13 = load ptr, ptr %memberidx2, align 8
  %14 = load ptr, ptr %bytes, align 8
  %15 = load i64, ptr %length, align 4
  %16 = call i64 @memcpy(ptr %13, ptr %14, i64 %15)
  %17 = load ptr, ptr %this, align 8
  %memberidx3 = getelementptr inbounds ptr, ptr %17, i64 3
  %18 = load ptr, ptr %this, align 8
  %memberidx4 = getelementptr inbounds ptr, ptr %18, i64 3
  %19 = load ptr, ptr %memberidx4, align 8
  %20 = load i64, ptr %length, align 4
  %21 = getelementptr inbounds ptr, ptr %19, i64 %20
  store ptr %21, ptr %memberidx3, align 8
  %22 = load ptr, ptr %this, align 8
  %memberidx5 = getelementptr inbounds ptr, ptr %22, i64 4
  %23 = load ptr, ptr %this, align 8
  %memberidx6 = getelementptr inbounds ptr, ptr %23, i64 4
  %24 = load i64, ptr %memberidx6, align 4
  %25 = load i64, ptr %length, align 4
  %26 = add i64 %24, %25
  store i64 %26, ptr %memberidx5, align 4
  ret void
}

define void @StringBuilder_append_string(ptr %0, ptr %1) {
  %this = alloca ptr, align 8
  store ptr %0, ptr %this, align 8
  %str = alloca ptr, align 8
  store ptr %1, ptr %str, align 8
  %3 = load ptr, ptr %this, align 8
  %4 = getelementptr inbounds ptr, ptr %3, i64 0
  %5 = load ptr, ptr %4, align 8
  %memberidx = getelementptr inbounds ptr, ptr %5, i64 0
  %6 = load ptr, ptr %memberidx, align 8
  %7 = load ptr, ptr %str, align 8
  %8 = getelementptr inbounds ptr, ptr %7, i64 0
  %9 = load ptr, ptr %8, align 8
  %memberidx1 = getelementptr inbounds ptr, ptr %9, i64 8
  %10 = load ptr, ptr %memberidx1, align 8
  %11 = call ptr %10(ptr %7)
  %12 = load ptr, ptr %str, align 8
  %memberidx2 = getelementptr inbounds ptr, ptr %12, i64 2
  %13 = load i64, ptr %memberidx2, align 4
  call void %6(ptr %3, ptr %11, i64 %13)
  ret void
}

define void @StringBuilder_add_byte(ptr %0, i8 %1) {
  %this = alloca ptr, align 8
  store ptr %0, ptr %this, align 8
  %byte = alloca i8, align 1
  store i8 %1, ptr %byte, align 1
  %3 = load ptr, ptr %this, align 8
  %memberidx = getelementptr inbounds ptr, ptr %3, i64 2
  %4 = load i64, ptr %memberidx, align 4
  %5 = load ptr, ptr %this, align 8
  %memberidx1 = getelementptr inbounds ptr, ptr %5, i64 4
  %6 = load i64, ptr %memberidx1, align 4
  %7 = sub i64 %4, %6
  %8 = icmp sle i64 %7, 1
  br i1 %8, label %if.entry, label %else

if.entry:                                         ; preds = %2
  %9 = load ptr, ptr %this, align 8
  call void @StringBuilder_resize(ptr %9)
  br label %ifend

else:                                             ; preds = %2
  br label %ifend

ifend:                                            ; preds = %else, %if.entry
  %10 = load ptr, ptr %this, align 8
  %memberidx2 = getelementptr inbounds ptr, ptr %10, i64 3
  %11 = load ptr, ptr %memberidx2, align 8
  %ptridx = getelementptr inbounds ptr, ptr %11, i64 0
  %12 = load i8, ptr %byte, align 1
  store i8 %12, ptr %ptridx, align 1
  %13 = load ptr, ptr %this, align 8
  %memberidx3 = getelementptr inbounds ptr, ptr %13, i64 3
  %14 = load ptr, ptr %this, align 8
  %memberidx4 = getelementptr inbounds ptr, ptr %14, i64 3
  %15 = load ptr, ptr %memberidx4, align 8
  %16 = getelementptr inbounds ptr, ptr %15, i64 1
  store ptr %16, ptr %memberidx3, align 8
  %17 = load ptr, ptr %this, align 8
  %memberidx5 = getelementptr inbounds ptr, ptr %17, i64 4
  %18 = load ptr, ptr %this, align 8
  %memberidx6 = getelementptr inbounds ptr, ptr %18, i64 4
  %19 = load i64, ptr %memberidx6, align 4
  %20 = add i64 %19, 1
  store i64 %20, ptr %memberidx5, align 4
  ret void
}

define ptr @StringBuilder_get_string(ptr %0) {
  %this = alloca ptr, align 8
  store ptr %0, ptr %this, align 8
  %2 = tail call ptr @malloc(i32 ptrtoint (ptr getelementptr (%string, ptr null, i32 1) to i32))
  %3 = load ptr, ptr %this, align 8
  %memberidx = getelementptr inbounds ptr, ptr %3, i64 1
  %4 = load ptr, ptr %memberidx, align 8
  %5 = load ptr, ptr %this, align 8
  %memberidx1 = getelementptr inbounds ptr, ptr %5, i64 4
  %6 = load i64, ptr %memberidx1, align 4
  call void @string_constructor(ptr %2, ptr %4, i64 %6)
  ret ptr %2
}

define void @StringBuilder_resize(ptr %0) {
  %this = alloca ptr, align 8
  store ptr %0, ptr %this, align 8
  %2 = load ptr, ptr %this, align 8
  %memberidx = getelementptr inbounds ptr, ptr %2, i64 2
  %3 = load ptr, ptr %this, align 8
  %memberidx1 = getelementptr inbounds ptr, ptr %3, i64 2
  %4 = load i64, ptr %memberidx1, align 4
  %5 = mul i64 %4, 2
  store i64 %5, ptr %memberidx, align 4
  %6 = load ptr, ptr %this, align 8
  %memberidx2 = getelementptr inbounds ptr, ptr %6, i64 1
  %7 = load ptr, ptr %this, align 8
  %memberidx3 = getelementptr inbounds ptr, ptr %7, i64 1
  %8 = load ptr, ptr %memberidx3, align 8
  %9 = load ptr, ptr %this, align 8
  %memberidx4 = getelementptr inbounds ptr, ptr %9, i64 2
  %10 = load i64, ptr %memberidx4, align 4
  %11 = mul i64 %10, ptrtoint (ptr getelementptr (i8, ptr null, i32 1) to i64)
  %12 = call ptr @realloc(ptr %8, i64 %11)
  store ptr %12, ptr %memberidx2, align 8
  %13 = load ptr, ptr %this, align 8
  %memberidx5 = getelementptr inbounds ptr, ptr %13, i64 3
  %14 = load ptr, ptr %this, align 8
  %memberidx6 = getelementptr inbounds ptr, ptr %14, i64 1
  %15 = load ptr, ptr %memberidx6, align 8
  %16 = load ptr, ptr %this, align 8
  %memberidx7 = getelementptr inbounds ptr, ptr %16, i64 4
  %17 = load i64, ptr %memberidx7, align 4
  %18 = getelementptr inbounds ptr, ptr %15, i64 %17
  store ptr %18, ptr %memberidx5, align 8
  ret void
}

define i1 @Range___in__(ptr %0, i64 %1) {
  %this = alloca ptr, align 8
  store ptr %0, ptr %this, align 8
  %num = alloca i64, align 8
  store i64 %1, ptr %num, align 4
  %3 = load i64, ptr %num, align 4
  %4 = load ptr, ptr %this, align 8
  %memberidx = getelementptr inbounds ptr, ptr %4, i64 1
  %5 = load i64, ptr %memberidx, align 4
  %6 = icmp sge i64 %3, %5
  %7 = load i64, ptr %num, align 4
  %8 = load ptr, ptr %this, align 8
  %memberidx1 = getelementptr inbounds ptr, ptr %8, i64 2
  %9 = load i64, ptr %memberidx1, align 4
  %10 = icmp slt i64 %7, %9
  %11 = and i1 %6, %10
  ret i1 %11
}

define ptr @string_from_cstring(ptr %0) {
  %str = alloca ptr, align 8
  store ptr %0, ptr %str, align 8
  %len = alloca i64, align 8
  %2 = load ptr, ptr %str, align 8
  %3 = call i64 @strlen(ptr %2)
  store i64 %3, ptr %len, align 4
  %buf = alloca ptr, align 8
  %4 = load i64, ptr %len, align 4
  %5 = trunc i64 %4 to i32
  %mallocsize = mul i32 %5, ptrtoint (ptr getelementptr (i8, ptr null, i32 1) to i32)
  %6 = tail call ptr @malloc(i32 %mallocsize)
  store ptr %6, ptr %buf, align 8
  %7 = load ptr, ptr %buf, align 8
  %8 = load ptr, ptr %str, align 8
  %9 = load i64, ptr %len, align 4
  %10 = call i64 @memcpy(ptr %7, ptr %8, i64 %9)
  %11 = tail call ptr @malloc(i32 ptrtoint (ptr getelementptr (%string, ptr null, i32 1) to i32))
  %12 = load ptr, ptr %buf, align 8
  %13 = load i64, ptr %len, align 4
  call void @string_constructor(ptr %11, ptr %12, i64 %13)
  ret ptr %11
}

declare i64 @strlen(ptr %0)

define void @StringBuilder_constructor(ptr %0, i64 %1) {
  %this = alloca ptr, align 8
  store ptr %0, ptr %this, align 8
  %3 = getelementptr inbounds ptr, ptr %0, i64 0
  store ptr @VTableStringBuilder, ptr %3, align 8
  %size = alloca i64, align 8
  store i64 %1, ptr %size, align 4
  %4 = load ptr, ptr %this, align 8
  %memberidx = getelementptr inbounds ptr, ptr %4, i64 2
  %5 = load i64, ptr %size, align 4
  store i64 %5, ptr %memberidx, align 4
  %6 = load ptr, ptr %this, align 8
  %memberidx1 = getelementptr inbounds ptr, ptr %6, i64 1
  %7 = load ptr, ptr %this, align 8
  %memberidx2 = getelementptr inbounds ptr, ptr %7, i64 2
  %8 = load i64, ptr %memberidx2, align 4
  %9 = trunc i64 %8 to i32
  %mallocsize = mul i32 %9, ptrtoint (ptr getelementptr (i8, ptr null, i32 1) to i32)
  %10 = tail call ptr @malloc(i32 %mallocsize)
  store ptr %10, ptr %memberidx1, align 8
  %11 = load ptr, ptr %this, align 8
  %memberidx3 = getelementptr inbounds ptr, ptr %11, i64 3
  %12 = load ptr, ptr %this, align 8
  %memberidx4 = getelementptr inbounds ptr, ptr %12, i64 1
  %13 = load ptr, ptr %memberidx4, align 8
  store ptr %13, ptr %memberidx3, align 8
  %14 = load ptr, ptr %this, align 8
  %memberidx5 = getelementptr inbounds ptr, ptr %14, i64 4
  store i64 0, ptr %memberidx5, align 4
  ret void
}

define void @Range_constructor(ptr %0, i64 %1, i64 %2) {
  %this = alloca ptr, align 8
  store ptr %0, ptr %this, align 8
  %4 = getelementptr inbounds ptr, ptr %0, i64 0
  store ptr @VTableRange, ptr %4, align 8
  %start = alloca i64, align 8
  store i64 %1, ptr %start, align 4
  %end = alloca i64, align 8
  store i64 %2, ptr %end, align 4
  %5 = load ptr, ptr %this, align 8
  %memberidx = getelementptr inbounds ptr, ptr %5, i64 1
  %6 = load i64, ptr %start, align 4
  store i64 %6, ptr %memberidx, align 4
  %7 = load ptr, ptr %this, align 8
  %memberidx1 = getelementptr inbounds ptr, ptr %7, i64 2
  %8 = load i64, ptr %end, align 4
  store i64 %8, ptr %memberidx1, align 4
  ret void
}

define void @print(ptr %0) {
  %str = alloca ptr, align 8
  store ptr %0, ptr %str, align 8
  %2 = load i64, ptr @STDOUT, align 4
  %3 = load ptr, ptr %str, align 8
  %4 = getelementptr inbounds ptr, ptr %3, i64 0
  %5 = load ptr, ptr %4, align 8
  %memberidx = getelementptr inbounds ptr, ptr %5, i64 8
  %6 = load ptr, ptr %memberidx, align 8
  %7 = call ptr %6(ptr %3)
  %8 = load ptr, ptr %str, align 8
  %memberidx1 = getelementptr inbounds ptr, ptr %8, i64 2
  %9 = load i64, ptr %memberidx1, align 4
  call void @write(i64 %2, ptr %7, i64 %9)
  ret void
}

declare void @write(i64 %0, ptr %1, i64 %2)

define void @println(ptr %0) {
  %str = alloca ptr, align 8
  store ptr %0, ptr %str, align 8
  %2 = load ptr, ptr %str, align 8
  call void @print(ptr %2)
  %3 = load i64, ptr @STDOUT, align 4
  call void @write(i64 %3, ptr @1, i64 1)
  ret void
}

!llvm.dbg.cu = !{!0, !2}

!0 = distinct !DICompileUnit(language: DW_LANG_C, file: !1, producer: "Flo Compiler", isOptimized: false, runtimeVersion: 0, emissionKind: FullDebug, splitDebugInlining: false, debugInfoForProfiling: true, sysroot: ".")
!1 = !DIFile(filename: "examples/test.flo", directory: ".")
!2 = distinct !DICompileUnit(language: DW_LANG_C, file: !3, producer: "Flo Compiler", isOptimized: false, runtimeVersion: 0, emissionKind: FullDebug, splitDebugInlining: false, debugInfoForProfiling: true, sysroot: ".")
!3 = !DIFile(filename: "./flolib/builtins.flo", directory: ".")
