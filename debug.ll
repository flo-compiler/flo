; ModuleID = "./examples/fnc.flo"
target triple = "unknown-unknown-unknown"
target datalayout = ""

%"struct.str" = type {i8*, i32}
%"struct.arr" = type {i8*, i32, i32}
define void @"main"()
{
.2:
  %".3" = mul i32 4, 10
  %".4" = call i8* @"malloc"(i32 %".3")
  %".5" = bitcast i8* %".4" to i32*
  %".6" = getelementptr inbounds i32, i32* %".5", i32 0
  store i32 1, i32* %".6"
  %".8" = getelementptr inbounds i32, i32* %".5", i32 1
  store i32 2, i32* %".8"
  %".10" = getelementptr inbounds i32, i32* %".5", i32 2
  store i32 3, i32* %".10"
  %".12" = getelementptr inbounds i32, i32* %".5", i32 3
  store i32 4, i32* %".12"
  %".14" = getelementptr inbounds i32, i32* %".5", i32 4
  store i32 5, i32* %".14"
  %".16" = call %"struct.arr"* @"struct.arr.new"(i8* %".4", i32 5, i32 10)
  %"original" = alloca %"struct.arr"*
  store %"struct.arr"* %".16", %"struct.arr"** %"original"
  %".18" = load %"struct.arr"*, %"struct.arr"** %"original"
  %".19" = call %"struct.arr"* @"map"(%"struct.arr"* %".18", i32 (i32)* @"double")
  %"doubled" = alloca %"struct.arr"*
  store %"struct.arr"* %".19", %"struct.arr"** %"doubled"
  %".21" = load %"struct.arr"*, %"struct.arr"** %"doubled"
  %".22" = call i32 (...) @"printf"(i8* bitcast ([2 x i8]* @"str.0" to i8*))
  %".23" = getelementptr %"struct.arr", %"struct.arr"* %".21", i32 0, i32 1
  %".24" = load i32, i32* %".23"
  %".25" = sub i32 %".24", 1
  br label %"foreach.entry"
foreach.entry:
  %".27" = alloca i32
  store i32 0, i32* %".27"
  br label %"foreach.loop"
foreach.loop:
  %".30" = load i32, i32* %".27"
  %".31" = add i32 %".30", 1
  store i32 %".31", i32* %".27"
  %".33" = icmp slt i32 %".31", %".25"
  %".34" = getelementptr %"struct.arr", %"struct.arr"* %".21", i32 0, i32 0
  %".35" = load i8*, i8** %".34"
  %".36" = bitcast i8* %".35" to i32*
  %".37" = getelementptr inbounds i32, i32* %".36", i32 %".30"
  %".38" = load i32, i32* %".37"
  %".39" = call i32 (...) @"printf"(i8* bitcast ([3 x i8]* @"str.1" to i8*), i32 %".38")
  %".40" = call i32 (...) @"printf"(i8* bitcast ([3 x i8]* @"str.2" to i8*))
  br i1 %".33", label %"foreach.loop", label %"foreach.exit"
foreach.exit:
  %".42" = getelementptr %"struct.arr", %"struct.arr"* %".21", i32 0, i32 0
  %".43" = load i8*, i8** %".42"
  %".44" = bitcast i8* %".43" to i32*
  %".45" = getelementptr inbounds i32, i32* %".44", i32 %".25"
  %".46" = load i32, i32* %".45"
  %".47" = call i32 (...) @"printf"(i8* bitcast ([3 x i8]* @"str.1" to i8*), i32 %".46")
  %".48" = call i32 (...) @"printf"(i8* bitcast ([2 x i8]* @"str.3" to i8*))
  %".49" = call i32 (...) @"printf"(i8* bitcast ([2 x i8]* @"str.4" to i8*))
  %".50" = load %"struct.arr"*, %"struct.arr"** %"original"
  %".51" = call i32 (...) @"printf"(i8* bitcast ([2 x i8]* @"str.0" to i8*))
  %".52" = getelementptr %"struct.arr", %"struct.arr"* %".50", i32 0, i32 1
  %".53" = load i32, i32* %".52"
  %".54" = sub i32 %".53", 1
  br label %"foreach.entry.1"
foreach.entry.1:
  %".56" = alloca i32
  store i32 0, i32* %".56"
  br label %"foreach.loop.1"
foreach.loop.1:
  %".59" = load i32, i32* %".56"
  %".60" = add i32 %".59", 1
  store i32 %".60", i32* %".56"
  %".62" = icmp slt i32 %".60", %".54"
  %".63" = getelementptr %"struct.arr", %"struct.arr"* %".50", i32 0, i32 0
  %".64" = load i8*, i8** %".63"
  %".65" = bitcast i8* %".64" to i32*
  %".66" = getelementptr inbounds i32, i32* %".65", i32 %".59"
  %".67" = load i32, i32* %".66"
  %".68" = call i32 (...) @"printf"(i8* bitcast ([3 x i8]* @"str.1" to i8*), i32 %".67")
  %".69" = call i32 (...) @"printf"(i8* bitcast ([3 x i8]* @"str.2" to i8*))
  br i1 %".62", label %"foreach.loop.1", label %"foreach.exit.1"
foreach.exit.1:
  %".71" = getelementptr %"struct.arr", %"struct.arr"* %".50", i32 0, i32 0
  %".72" = load i8*, i8** %".71"
  %".73" = bitcast i8* %".72" to i32*
  %".74" = getelementptr inbounds i32, i32* %".73", i32 %".54"
  %".75" = load i32, i32* %".74"
  %".76" = call i32 (...) @"printf"(i8* bitcast ([3 x i8]* @"str.1" to i8*), i32 %".75")
  %".77" = call i32 (...) @"printf"(i8* bitcast ([2 x i8]* @"str.3" to i8*))
  %".78" = call i32 (...) @"printf"(i8* bitcast ([2 x i8]* @"str.4" to i8*))
  ret void
}

define %"struct.arr"* @"map"(%"struct.arr"* %".1", i32 (i32)* %".2")
{
.4:
  %"array" = alloca %"struct.arr"*
  store %"struct.arr"* %".1", %"struct.arr"** %"array"
  %"func" = alloca i32 (i32)*
  store i32 (i32)* %".2", i32 (i32)** %"func"
  %".7" = load i32 (i32)*, i32 (i32)** %"func"
  %".8" = load %"struct.arr"*, %"struct.arr"** %"array"
  %".9" = getelementptr %"struct.arr", %"struct.arr"* %".8", i32 0, i32 0
  %".10" = load i8*, i8** %".9"
  %".11" = bitcast i8* %".10" to i32*
  %".12" = getelementptr inbounds i32, i32* %".11", i32 0
  %".13" = load i32, i32* %".12"
  %".14" = call i32 %".7"(i32 %".13")
  %".15" = mul i32 4, 2
  %".16" = call i8* @"malloc"(i32 %".15")
  %".17" = bitcast i8* %".16" to i32*
  %".18" = getelementptr inbounds i32, i32* %".17", i32 0
  store i32 %".14", i32* %".18"
  %".20" = call %"struct.arr"* @"struct.arr.new"(i8* %".16", i32 1, i32 2)
  %"arr" = alloca %"struct.arr"*
  store %"struct.arr"* %".20", %"struct.arr"** %"arr"
  br label %"for.entry"
for.entry:
  %"i" = alloca i32
  store i32 1, i32* %"i"
  br label %"for.cond"
for.cond:
  %".25" = load i32, i32* %"i"
  %".26" = load %"struct.arr"*, %"struct.arr"** %"array"
  %".27" = getelementptr %"struct.arr", %"struct.arr"* %".26", i32 0, i32 1
  %".28" = load i32, i32* %".27"
  %".29" = icmp slt i32 %".25", %".28"
  br i1 %".29", label %"for.body", label %"for.end"
for.body:
  %".31" = load %"struct.arr"*, %"struct.arr"** %"arr"
  %".32" = load i32 (i32)*, i32 (i32)** %"func"
  %".33" = load i32, i32* %"i"
  %".34" = load %"struct.arr"*, %"struct.arr"** %"array"
  %".35" = getelementptr %"struct.arr", %"struct.arr"* %".34", i32 0, i32 0
  %".36" = load i8*, i8** %".35"
  %".37" = bitcast i8* %".36" to i32*
  %".38" = getelementptr inbounds i32, i32* %".37", i32 %".33"
  %".39" = load i32, i32* %".38"
  %".40" = call i32 %".32"(i32 %".39")
  %".41" = getelementptr %"struct.arr", %"struct.arr"* %".31", i32 0, i32 1
  %".42" = getelementptr %"struct.arr", %"struct.arr"* %".31", i32 0, i32 1
  %".43" = load i32, i32* %".42"
  %".44" = getelementptr %"struct.arr", %"struct.arr"* %".31", i32 0, i32 2
  %".45" = load i32, i32* %".44"
  %".46" = icmp eq i32 %".43", %".45"
  br i1 %".46", label %"for.body.if", label %"for.body.endif"
for.incr:
  %".68" = load i32, i32* %"i"
  %".69" = add i32 %".68", 1
  %".70" = load i32, i32* %"i"
  %".71" = add i32 %".70", 1
  store i32 %".71", i32* %"i"
  br label %"for.cond"
for.end:
  %".74" = load %"struct.arr"*, %"struct.arr"** %"arr"
  %".75" = bitcast %"struct.arr"* %".34" to i8*
  %".76" = getelementptr %"struct.arr", %"struct.arr"* %".34", i32 0, i32 0
  %".77" = load i8*, i8** %".76"
  call void @"free"(i8* %".77")
  call void @"free"(i8* %".75")
  ret %"struct.arr"* %".74"
for.body.if:
  %".48" = getelementptr %"struct.arr", %"struct.arr"* %".31", i32 0, i32 2
  %".49" = load i32, i32* %".48"
  %".50" = mul i32 %".49", 2
  %".51" = getelementptr %"struct.arr", %"struct.arr"* %".31", i32 0, i32 0
  %".52" = load i8*, i8** %".51"
  %".53" = mul i32 %".50", 4
  %".54" = call i8* @"realloc"(i8* %".52", i32 %".53")
  %".55" = getelementptr %"struct.arr", %"struct.arr"* %".31", i32 0, i32 0
  store i8* %".54", i8** %".55"
  %".57" = getelementptr %"struct.arr", %"struct.arr"* %".31", i32 0, i32 2
  store i32 %".50", i32* %".57"
  br label %"for.body.endif"
for.body.endif:
  %".60" = getelementptr %"struct.arr", %"struct.arr"* %".31", i32 0, i32 0
  %".61" = load i8*, i8** %".60"
  %".62" = bitcast i8* %".61" to i32*
  %".63" = getelementptr inbounds i32, i32* %".62", i32 %".43"
  store i32 %".40", i32* %".63"
  %".65" = add i32 %".43", 1
  store i32 %".65", i32* %".41"
  br label %"for.incr"
}

declare i8* @"malloc"(i32 %".1")

define %"struct.arr"* @"struct.arr.new"(i8* %".1", i32 %".2", i32 %".3")
{
.5:
  %".6" = call i8* @"malloc"(i32 16)
  %".7" = bitcast i8* %".6" to %"struct.arr"*
  %".8" = getelementptr %"struct.arr", %"struct.arr"* %".7", i32 0, i32 0
  %".9" = getelementptr %"struct.arr", %"struct.arr"* %".7", i32 0, i32 1
  %".10" = getelementptr %"struct.arr", %"struct.arr"* %".7", i32 0, i32 2
  store i32 %".2", i32* %".9"
  store i32 %".3", i32* %".10"
  store i8* %".1", i8** %".8"
  ret %"struct.arr"* %".7"
}

declare i8* @"realloc"(i8* %".1", i32 %".2")

declare void @"free"(i8* %".1")

define i32 @"double"(i32 %".1")
{
.3:
  %"x" = alloca i32
  store i32 %".1", i32* %"x"
  %".5" = load i32, i32* %"x"
  %".6" = mul i32 %".5", 2
  ret i32 %".6"
}

@"str.0" = private unnamed_addr constant [2 x i8] c"[\00"
declare i32 @"printf"(...)

@"str.1" = private unnamed_addr constant [3 x i8] c"%d\00"
@"str.2" = private unnamed_addr constant [3 x i8] c", \00"
@"str.3" = private unnamed_addr constant [2 x i8] c"]\00"
@"str.4" = private unnamed_addr constant [2 x i8] c"\0a\00"