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
        raise Exception(f"Type Not handled {type}")

class FloInt:
    llvmtype = ir.IntType(32)
    pow_fnc = None
    print_fmt = "%li"
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
        fv = self.castTo(builder, FloFloat).pow(builder, num.castTo(builder, FloFloat))
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
    llvmtype = ir.DoubleType()
    pow_fnc = None
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
        if FloFloat.pow_fnc == None:
            FloFloat.pow_fnc = Context.current_llvm_module.declare_intrinsic("llvm.pow", [FloFloat.llvmtype])
        v = builder.call(FloFloat.pow_fnc, [self.value, num.value])
        return FloFloat(v)

    def neg(self):
        self.value = self.value.fneg()
        return self

    def castTo(self, builder: ir.IRBuilder, type):
        if type == FloInt:
            return self.toInt(builder)
        elif type == FloBool:
            return self.cmp(builder, "!=", FloFloat.zero())
        elif type == FloFloat: return self
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
    asprintf = None

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
        ref = builder.alloca(ir.IntType(8))
        builder.store(val, ref)
        return FloStr(ref, 1)

    def add(self, builder: ir.IRBuilder, str):
        if FloStr.asprintf == None:
            cfn_ty = ir.FunctionType(
                FloInt.llvmtype,
                [FloStr.llvmtype.as_pointer(), FloStr.llvmtype],
                var_arg=True,
            )
            FloStr.asprintf = Context.current_llvm_module.declare_intrinsic("asprintf", [], cfn_ty)
        resStr = builder.alloca(FloStr.llvmtype)
        builder.call(
            FloStr.asprintf,
            [resStr, FloStr("%s%s").value, self.value, str.value],
        )
        return FloStr(builder.load(resStr), self.size+str.size)

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
    concat_intr = None
    def __init__(self, builder, elms):
        if isinstance(elms, list):
            arr_ty = ir.ArrayType(elms[0].llvmtype, len(elms))
            val = ir.Constant(arr_ty, [elm.value for elm in elms])
            ptr = builder.alloca(arr_ty)
            builder.store(val, ptr)
            self.value = builder.bitcast(ptr, elms[0].llvmtype.as_pointer())
        else:
            self.value = elms

    def getElement(self, builder: ir.IRBuilder, index):
        ptr = builder.gep(self.value, [index.value], True)
        return llvmToFloType(builder.load(ptr))

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
