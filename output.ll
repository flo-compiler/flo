; ModuleID = 'examples/vm/main.flo'
source_filename = "examples/vm/main.flo"

%StackVM = type <{ ptr, i64, i64, ptr, i64, i64, i1 }>

@VTableStackVM = internal global <{ ptr, ptr }> <{ ptr @StackVM_run, ptr @StackVM_loadProgram }>
@vmBuffer = internal global [1000 x i64] zeroinitializer
@0 = private unnamed_addr constant [11 x i8] c"push (%d)\0A\00", align 1
@1 = private unnamed_addr constant [7 x i8] c"halt!\0A\00", align 1
@2 = private unnamed_addr constant [5 x i8] c"add\0A\00", align 1
@3 = private unnamed_addr constant [5 x i8] c"sub\0A\00", align 1
@4 = private unnamed_addr constant [5 x i8] c"mul\0A\00", align 1
@5 = private unnamed_addr constant [5 x i8] c"div\0A\00", align 1
@6 = private unnamed_addr constant [12 x i8] c"output: %x\0A\00", align 1

define i64 @main() local_unnamed_addr {
  %prog = alloca [10 x i64], align 8
  store i64 3000, ptr %prog, align 8
  %.fca.1.gep = getelementptr inbounds [10 x i64], ptr %prog, i64 0, i64 1
  store i64 800, ptr %.fca.1.gep, align 8
  %.fca.2.gep = getelementptr inbounds [10 x i64], ptr %prog, i64 0, i64 2
  store i64 1073741825, ptr %.fca.2.gep, align 8
  %.fca.3.gep = getelementptr inbounds [10 x i64], ptr %prog, i64 0, i64 3
  store i64 100, ptr %.fca.3.gep, align 8
  %.fca.4.gep = getelementptr inbounds [10 x i64], ptr %prog, i64 0, i64 4
  store i64 1073741825, ptr %.fca.4.gep, align 8
  %.fca.5.gep = getelementptr inbounds [10 x i64], ptr %prog, i64 0, i64 5
  store i64 29, ptr %.fca.5.gep, align 8
  %.fca.6.gep = getelementptr inbounds [10 x i64], ptr %prog, i64 0, i64 6
  store i64 1073741826, ptr %.fca.6.gep, align 8
  %.fca.7.gep = getelementptr inbounds [10 x i64], ptr %prog, i64 0, i64 7
  store i64 16, ptr %.fca.7.gep, align 8
  %.fca.8.gep = getelementptr inbounds [10 x i64], ptr %prog, i64 0, i64 8
  store i64 1073741827, ptr %.fca.8.gep, align 8
  %.fca.9.gep = getelementptr inbounds [10 x i64], ptr %prog, i64 0, i64 9
  store i64 1073741824, ptr %.fca.9.gep, align 8
  %1 = alloca %StackVM, align 8
  store ptr @VTableStackVM, ptr %1, align 8
  %memberidx.i = getelementptr inbounds %StackVM, ptr %1, i64 0, i32 1
  store i64 10, ptr %memberidx.i, align 8
  %memberidx1.i = getelementptr inbounds %StackVM, ptr %1, i64 0, i32 2
  store i64 0, ptr %memberidx1.i, align 8
  %memberidx2.i = getelementptr inbounds %StackVM, ptr %1, i64 0, i32 4
  store i64 0, ptr %memberidx2.i, align 8
  %memberidx3.i = getelementptr inbounds %StackVM, ptr %1, i64 0, i32 3
  store ptr @vmBuffer, ptr %memberidx3.i, align 8
  %memberidx4.i = getelementptr inbounds %StackVM, ptr %1, i64 0, i32 5
  store i64 0, ptr %memberidx4.i, align 8
  %memberidx5.i = getelementptr inbounds %StackVM, ptr %1, i64 0, i32 6
  store i1 true, ptr %memberidx5.i, align 8
  %2 = load ptr, ptr getelementptr inbounds (<{ ptr, ptr }>, ptr @VTableStackVM, i64 0, i32 1), align 8
  call void %2(ptr nonnull %1, ptr nonnull %prog, i64 10)
  %3 = load ptr, ptr %1, align 8
  %4 = load ptr, ptr %3, align 8
  call void %4(ptr nonnull %1)
  ret i64 0
}

define internal void @StackVM_run(ptr nocapture %0) {
  %memberidx = getelementptr inbounds %StackVM, ptr %0, i64 0, i32 1
  %2 = load i64, ptr %memberidx, align 4
  %3 = add i64 %2, -1
  store i64 %3, ptr %memberidx, align 4
  %memberidx2 = getelementptr inbounds %StackVM, ptr %0, i64 0, i32 6
  %4 = load i1, ptr %memberidx2, align 1
  br i1 %4, label %while.entry.preheader, label %while.end

while.entry.preheader:                            ; preds = %1
  %memberidx.i15 = getelementptr inbounds %StackVM, ptr %0, i64 0, i32 4
  %memberidx2.i16 = getelementptr inbounds %StackVM, ptr %0, i64 0, i32 3
  %memberidx3.i = getelementptr inbounds %StackVM, ptr %0, i64 0, i32 5
  %memberidx46.i.i = getelementptr inbounds %StackVM, ptr %0, i64 0, i32 2
  %memberidx32.i.i = getelementptr inbounds %StackVM, ptr %0, i64 0, i32 2
  %memberidx18.i.i = getelementptr inbounds %StackVM, ptr %0, i64 0, i32 2
  %memberidx5.i.i = getelementptr inbounds %StackVM, ptr %0, i64 0, i32 2
  %memberidx2.i = getelementptr inbounds %StackVM, ptr %0, i64 0, i32 2
  br label %while.entry

while.entry:                                      ; preds = %while.entry.preheader, %StackVM_execute.exit
  %5 = load i64, ptr %memberidx, align 4
  %6 = add i64 %5, 1
  store i64 %6, ptr %memberidx, align 4
  %7 = load ptr, ptr %memberidx2.i16, align 8
  %ptridx.i17 = getelementptr inbounds i64, ptr %7, i64 %6
  %8 = load i64, ptr %ptridx.i17, align 4
  %9 = lshr i64 %8, 30
  %10 = and i64 %9, 3
  store i64 %10, ptr %memberidx.i15, align 4
  %11 = load i64, ptr %ptridx.i17, align 4
  %12 = and i64 %11, 1073741823
  store i64 %12, ptr %memberidx3.i, align 4
  %13 = and i64 %8, 1073741824
  %14 = icmp eq i64 %13, 0
  br i1 %14, label %if.entry.i, label %else.i

if.entry.i:                                       ; preds = %while.entry
  %15 = load i64, ptr %memberidx2.i, align 4
  %16 = add i64 %15, 1
  store i64 %16, ptr %memberidx2.i, align 4
  %17 = trunc i64 %12 to i32
  %18 = call i32 @printf(ptr nonnull @0, i32 %17)
  %19 = load i64, ptr %memberidx2.i, align 4
  %20 = load ptr, ptr %memberidx2.i16, align 8
  %ptridx.i = getelementptr inbounds i64, ptr %20, i64 %19
  %21 = load i64, ptr %memberidx3.i, align 4
  store i64 %21, ptr %ptridx.i, align 4
  br label %StackVM_execute.exit

else.i:                                           ; preds = %while.entry
  %trunc = trunc i64 %11 to i30
  switch i30 %trunc, label %StackVM_execute.exit [
    i30 0, label %if.entry.i.i
    i30 1, label %if.entry2.i.i
    i30 2, label %if.entry15.i.i
    i30 3, label %if.entry29.i.i
    i30 4, label %if.entry43.i.i
  ]

if.entry.i.i:                                     ; preds = %else.i
  %22 = call i32 @printf(ptr nonnull @1, i32 0)
  store i1 false, ptr %memberidx2, align 1
  br label %StackVM_execute.exit

if.entry2.i.i:                                    ; preds = %else.i
  %23 = call i32 @printf(ptr nonnull @2, i32 0)
  %24 = load i64, ptr %memberidx5.i.i, align 4
  %25 = add i64 %24, -1
  %26 = load ptr, ptr %memberidx2.i16, align 8
  %ptridx.i.i = getelementptr inbounds i64, ptr %26, i64 %25
  %27 = load i64, ptr %ptridx.i.i, align 4
  %ptridx12.i.i = getelementptr inbounds i64, ptr %26, i64 %24
  %28 = load i64, ptr %ptridx12.i.i, align 4
  %29 = add i64 %28, %27
  store i64 %29, ptr %ptridx.i.i, align 4
  %30 = load i64, ptr %memberidx5.i.i, align 4
  %31 = add i64 %30, -1
  store i64 %31, ptr %memberidx5.i.i, align 4
  br label %StackVM_execute.exit

if.entry15.i.i:                                   ; preds = %else.i
  %32 = call i32 @printf(ptr nonnull @3, i32 0)
  %33 = load i64, ptr %memberidx18.i.i, align 4
  %34 = add i64 %33, -1
  %35 = load ptr, ptr %memberidx2.i16, align 8
  %ptridx20.i.i = getelementptr inbounds i64, ptr %35, i64 %34
  %36 = load i64, ptr %ptridx20.i.i, align 4
  %ptridx26.i.i = getelementptr inbounds i64, ptr %35, i64 %33
  %37 = load i64, ptr %ptridx26.i.i, align 4
  %38 = sub i64 %36, %37
  store i64 %38, ptr %ptridx20.i.i, align 4
  %39 = load i64, ptr %memberidx18.i.i, align 4
  %40 = add i64 %39, -1
  store i64 %40, ptr %memberidx18.i.i, align 4
  br label %StackVM_execute.exit

if.entry29.i.i:                                   ; preds = %else.i
  %41 = call i32 @printf(ptr nonnull @4, i32 0)
  %42 = load i64, ptr %memberidx32.i.i, align 4
  %43 = add i64 %42, -1
  %44 = load ptr, ptr %memberidx2.i16, align 8
  %ptridx34.i.i = getelementptr inbounds i64, ptr %44, i64 %43
  %45 = load i64, ptr %ptridx34.i.i, align 4
  %ptridx40.i.i = getelementptr inbounds i64, ptr %44, i64 %42
  %46 = load i64, ptr %ptridx40.i.i, align 4
  %47 = mul i64 %46, %45
  store i64 %47, ptr %ptridx34.i.i, align 4
  %48 = load i64, ptr %memberidx32.i.i, align 4
  %49 = add i64 %48, -1
  store i64 %49, ptr %memberidx32.i.i, align 4
  br label %StackVM_execute.exit

if.entry43.i.i:                                   ; preds = %else.i
  %50 = call i32 @printf(ptr nonnull @5, i32 0)
  %51 = load i64, ptr %memberidx46.i.i, align 4
  %52 = add i64 %51, -1
  %53 = load ptr, ptr %memberidx2.i16, align 8
  %ptridx48.i.i = getelementptr inbounds i64, ptr %53, i64 %52
  %54 = load i64, ptr %ptridx48.i.i, align 4
  %ptridx54.i.i = getelementptr inbounds i64, ptr %53, i64 %51
  %55 = load i64, ptr %ptridx54.i.i, align 4
  %56 = sdiv i64 %54, %55
  store i64 %56, ptr %ptridx48.i.i, align 4
  %57 = load i64, ptr %memberidx46.i.i, align 4
  %58 = add i64 %57, -1
  store i64 %58, ptr %memberidx46.i.i, align 4
  br label %StackVM_execute.exit

StackVM_execute.exit:                             ; preds = %if.entry.i.i, %if.entry2.i.i, %if.entry15.i.i, %if.entry29.i.i, %if.entry43.i.i, %else.i, %if.entry.i
  %59 = load i1, ptr %memberidx2, align 1
  br i1 %59, label %while.entry, label %while.end

while.end:                                        ; preds = %StackVM_execute.exit, %1
  %memberidx4 = getelementptr inbounds %StackVM, ptr %0, i64 0, i32 2
  %60 = load i64, ptr %memberidx4, align 4
  %memberidx5 = getelementptr inbounds %StackVM, ptr %0, i64 0, i32 3
  %61 = load ptr, ptr %memberidx5, align 8
  %ptridx = getelementptr inbounds i64, ptr %61, i64 %60
  %62 = load i64, ptr %ptridx, align 4
  %63 = trunc i64 %62 to i32
  %64 = call i32 @printf(ptr nonnull @6, i32 %63)
  ret void
}

; Function Attrs: mustprogress nofree nosync nounwind willreturn
define internal void @StackVM_loadProgram(ptr nocapture readonly %0, ptr nocapture readonly %1, i64 %2) #0 {
  %memberidx = getelementptr inbounds %StackVM, ptr %0, i64 0, i32 3
  %4 = load ptr, ptr %memberidx, align 8
  %5 = shl i64 %2, 3
  call void @llvm.memcpy.p0.p0.i64(ptr align 8 %4, ptr align 8 %1, i64 %5, i1 false)
  ret void
}

declare i32 @printf(ptr, i32) local_unnamed_addr

; Function Attrs: argmemonly mustprogress nocallback nofree nounwind willreturn
declare void @llvm.memcpy.p0.p0.i64(ptr noalias nocapture writeonly, ptr noalias nocapture readonly, i64, i1 immarg) #1

attributes #0 = { mustprogress nofree nosync nounwind willreturn }
attributes #1 = { argmemonly mustprogress nocallback nofree nounwind willreturn }
