import builtIns
from context import Context
from llvmlite import ir


def llvmToFloType(value):
    llvm_type = value.type
    if isinstance(llvm_type, ir.IntType):
        return (
            FloBool(value)
            if llvm_type.width == FloBool.llvmtype.width
            else FloInt(value)
        )
    if isinstance(llvm_type, ir.DoubleType):
        return FloFloat(value)
    elif isinstance(llvm_type, ir.PointerType) and isinstance(
        llvm_type.pointee, ir.IntType
    ):
        return FloStr(value)
    elif isinstance(llvm_type, ir.VoidType):
        return FloVoid()
    else:
        raise Exception(f"Type Not handled {llvm_type}")


class FloInt:
    llvmtype = ir.IntType(32)
    print_fmt = "%li"
    bytes = 4

    def __init__(self, value: int | ir.Constant):
        self.size = FloInt.llvmtype.width
        if isinstance(value, int):
            self.value = ir.Constant(FloInt.llvmtype, int(value))
        else:
            self.value = value
        self.i = 0

    @staticmethod
    def one():
        return FloInt(ir.Constant(FloInt.llvmtype, 1))

    @staticmethod
    def zero():
        return FloInt(ir.Constant(FloInt.llvmtype, 0))

    @staticmethod
    def default_llvm_val():
        return FloInt.zero().value

    def string_repr_(self, _):
        return self.value

    def incr(self):
        self.i += 1
        return self.i

    def toFloat(self, builder: ir.IRBuilder):
        return FloFloat(builder.sitofp(self.value, FloFloat.llvmtype))

    def add(self, builder: ir.IRBuilder, num):
        return FloInt(builder.add(self.value, num.value))

    def sub(self, builder: ir.IRBuilder, num):
        return FloInt(builder.sub(self.value, num.value))

    def mul(self, builder: ir.IRBuilder, num):
        return FloInt(builder.mul(self.value, num.value))

    def div(self, builder: ir.IRBuilder, num):
        return FloFloat(builder.sdiv(self.value, num.value))

    def mod(self, builder: ir.IRBuilder, num):
        return FloInt(builder.srem(self.value, num.value))

    def cmp(self, builder: ir.IRBuilder, op, num):
        if not isinstance(num, FloInt):
            return FloBool.false()
        return FloBool(builder.icmp_signed(op, self.value, num.value))

    def neg(self):
        self.value = self.value.neg()
        return self

    def pow(self, builder: ir.IRBuilder, num):
        fv = self.castTo(builder, FloFloat).pow(
            builder, num.castTo(builder, FloFloat))
        return fv

    def sl(self, builder: ir.IRBuilder, num):
        return FloInt(builder.shl(self.value, num.value))

    def sr(self, builder: ir.IRBuilder, num):
        return FloInt(builder.ashr(self.value, num.value))

    def or_(self, builder: ir.IRBuilder, num):
        return FloInt(builder.or_(self.value, num.value))

    def and_(self, builder: ir.IRBuilder, num):
        return FloInt(builder.and_(self.value, num.value))

    def not_(self, builder: ir.IRBuilder):
        return FloInt(builder.not_(self.value))

    def xor(self, builder: ir.IRBuilder, num):
        return FloInt(builder.xor(self.value, num.value))

    def castTo(self, builder: ir.IRBuilder, type):
        if type == FloFloat:
            return self.toFloat(builder)
        elif type == FloBool:
            return self.cmp(builder, "!=", FloInt.zero())
        else:
            raise Exception(f"Unhandled type cast: int to {type}")


class FloFloat:
    bytes = 8
    llvmtype = ir.DoubleType()
    print_fmt = "%g"

    def __init__(self, value: float | ir.Constant):
        self.size = 64
        if isinstance(value, float):
            self.value = ir.Constant(ir.DoubleType(), value)
        else:
            self.value = value

    def toInt(self, builder: ir.IRBuilder):
        return FloInt(builder.fptosi(self.value, FloInt.llvmtype))

    def add(self, builder: ir.IRBuilder, num):
        return FloFloat(builder.fadd(self.value, num.value))

    def sub(self, builder: ir.IRBuilder, num):
        return FloFloat(builder.fsub(self.value, num.value))

    def mul(self, builder: ir.IRBuilder, num):
        return FloFloat(builder.fmul(self.value, num.value))

    def div(self, builder: ir.IRBuilder, num):
        return FloFloat(builder.fdiv(self.value, num.value))

    def cmp(self, builder: ir.IRBuilder, op, num):
        if not isinstance(num, FloFloat):
            return FloBool.false()
        return FloBool(builder.fcmp_ordered(op, self.value, num.value))

    def mod(self, builder: ir.IRBuilder, num):
        return FloFloat(builder.frem(self.value, num.value))

    def string_repr_(self, _):
        return self.value

    def pow(self, builder, num):
        v = builder.call(builtIns.get_instrinsic(
            "llvm.pow"), [self.value, num.value])
        return FloFloat(v)

    def neg(self):
        self.value = self.value.fneg()
        return self

    def castTo(self, builder: ir.IRBuilder, type):
        if type == FloInt:
            return self.toInt(builder)
        elif type == FloBool:
            return self.cmp(builder, "!=", FloFloat.zero())
        elif type == FloFloat:
            return self
        else:
            raise Exception(f"Unhandled type cast: float to {type}")

    @staticmethod
    def zero():
        return FloFloat(0.0)

    @staticmethod
    def one():
        return FloFloat(1.0)

    @staticmethod
    def default_llvm_val():
        return FloFloat.zero().value


class FloStr:
    id = -1
    strs = {}
    llvmtype = ir.IntType(8).as_pointer()
    print_fmt = "%s"
    bytes = 1

    def __init__(self, value, size=0):
        # Check for already defined strings
        self.size = size
        if FloStr.strs.get(str(value), None) != None:
            self.value = FloStr.strs[str(value)].value
            self.size = FloStr.strs[str(value)].size
        elif isinstance(value, str):
            encoded = (value + "\0").encode(
                encoding="utf-8", errors="xmlcharrefreplace"
            )
            str_val = ir.Constant(
                ir.ArrayType(ir.IntType(8), len(encoded)), bytearray(encoded)
            )
            self.size = len(value)
            str_ptr = ir.GlobalVariable(
                Context.current_llvm_module, str_val.type, f"str.{self.incr()}"
            )
            str_ptr.linkage = "private"
            str_ptr.global_constant = True
            str_ptr.unnamed_addr = True
            str_ptr.initializer = str_val
            self.value = str_ptr.bitcast(FloStr.llvmtype)
            FloStr.strs[value] = self
        else:
            self.value = value

    def getElement(self, builder: ir.IRBuilder, index: FloInt):
        val = builder.load(builder.gep(self.value, [index.value], True))
        char_ty = ir.IntType(8)
        arr_ty = ir.ArrayType(char_ty, 2)
        arr_ref = builder.alloca(arr_ty)
        ref_1 = builder.gep(
            arr_ref, [FloInt.zero().value, FloInt.zero().value])
        builder.store(val, ref_1)
        ref_2 = builder.gep(arr_ref, [FloInt.zero().value, FloInt.one().value])
        builder.store(ir.Constant(char_ty, 0), ref_2)
        return FloStr(ref_1, 1)

    def add(self, builder: ir.IRBuilder, str):
        arr_space = builder.alloca(ir.ArrayType(
            ir.IntType(8), self.size + str.size + 1))
        start_ptr = builder.gep(
            arr_space, [FloInt.zero().value, FloInt.zero().value])
        mid_ptr = builder.gep(start_ptr, [FloInt(self.size).value])
        builder.call(builtIns.get_instrinsic("llvm.memcpy"), [
                     start_ptr, self.value, FloInt(self.size).value, FloBool.false().value])
        builder.call(builtIns.get_instrinsic("llvm.memcpy"), [
                     mid_ptr, str.value, FloInt(str.size).value, FloBool.false().value])
        return FloStr(start_ptr, self.size+str.size)

    def incr(self):
        FloStr.id += 1
        return FloStr.id

    def string_repr_(self, _):
        return self.value

    @staticmethod
    def default_llvm_val():
        return FloStr("").value


class FloBool:
    llvmtype = ir.IntType(1)
    print_fmt = "%s"
    bytes = 1/8

    def __init__(self, value):
        if isinstance(value, bool):
            self.value = ir.Constant(FloBool.llvmtype, int(value))
        else:
            self.value = value

    def cmp(self, builder: ir.IRBuilder, op, bool):
        if not isinstance(bool, FloBool):
            return FloBool.false()
        return FloBool(builder.icmp_signed(op, self.value, bool.value))

    def not_(self, builder: ir.IRBuilder):
        return FloBool(builder.not_(self.value))

    def or_(self, builder: ir.IRBuilder, bool):
        return FloBool(builder.or_(self.value, bool.value))

    def and_(self, builder: ir.IRBuilder, bool):
        return FloBool(builder.and_(self.value, bool.value))

    def string_repr_(self, builder: ir.IRBuilder):
        return builder.select(self.value, FloStr("true").value, FloStr("false").value)

    @staticmethod
    def default_llvm_val(_):
        return FloBool.true().value

    @staticmethod
    def true():
        return FloBool(True)

    @staticmethod
    def false():
        return FloBool(False)


class FloArray:
    def __init__(self, builder: ir.IRBuilder, elms, size=0):
        self.size = size
        if isinstance(elms, list):
            self.elm_type = elms[0].__class__
            self.size = len(elms)
            self.type = ir.ArrayType(self.elm_type.llvmtype, self.size)
            arr_ptr = builder.alloca(self.type)
            for index in range(len(elms)):
                ptr = builder.gep(
                    arr_ptr, [FloInt.zero().value, FloInt(index).value], True)
                builder.store(elms[index].value, ptr)
            self.value = builder.bitcast(arr_ptr, self.elm_type.llvmtype.as_pointer())
        else:
            self.value = elms
            self.elm_type  = llvmToFloType(ir.Constant(elms.type.pointee, 0)).__class__

    def add(self, builder: ir.IRBuilder, arr):
        res_array_size = self.size + arr.size
        res_array_space = builder.alloca(ir.ArrayType(
            self.elm_type.llvmtype, res_array_size))
        memcpy_func = builtIns.get_instrinsic("llvm.memcpy")

        res_array_ptr = builder.bitcast(
            res_array_space, memcpy_func.args[0].type)
        arr1_ptr = builder.bitcast(self.value, memcpy_func.args[0].type)
        arr2_ptr = builder.bitcast(arr.value, memcpy_func.args[0].type)
        arr1_num_of_bytes = self.elm_type.bytes * self.size
        arr2_num_of_bytes = self.elm_type.bytes * arr.size
        zero = FloInt.zero().value
        arr1_pos_ptr = builder.gep(
            res_array_ptr, [zero])
        arr2_pos_ptr = builder.gep(
            res_array_ptr, [FloInt(arr1_num_of_bytes).value])
        builder.call(memcpy_func, [arr1_pos_ptr, arr1_ptr, FloInt(
            arr1_num_of_bytes).value, FloBool.false().value])
        builder.call(memcpy_func, [arr2_pos_ptr, arr2_ptr, FloInt(
            arr2_num_of_bytes).value, FloBool.false().value])
        res_array_space = builder.bitcast(res_array_space, self.elm_type.llvmtype.as_pointer())
        res_array = FloArray(builder, res_array_space, res_array_size)
        res_array.elm_type = self.elm_type
        return res_array

    def getElement(self, builder: ir.IRBuilder, index):
        ptr = builder.gep(self.value, [index.value], True)
        return self.elm_type(builder.load(ptr))

    def setElement(self, builder: ir.IRBuilder, index, value):
        ptr = builder.gep(self.value, [index.value], True)
        builder.store(value.value, ptr)
        return value

# TODO: Unecessary loads (re-load only when you have stored)


class FloRef:
    def __init__(self, builder: ir.IRBuilder, value, name: str):
        self.builder = builder
        self.addr = self.builder.alloca(value.value.type, None, name)
        self.store(value)

    def load(self):
        self.referee.value = self.builder.load(self.addr)
        return self.referee

    def store(self, value):
        self.referee = value
        self.builder.store(value.value, self.addr)
        return value


class FloVoid:
    llvmtype = ir.VoidType()
