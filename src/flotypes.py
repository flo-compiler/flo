from context import Context
from llvmlite import ir


def floType(value, Type=None):
    if Type == None:
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
    else:
        return Type(value)


class FloInt:
    llvmtype = ir.IntType(32)

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
        return FloFloat(builder.fdiv(self.value, num.value))

    def mod(self, builder: ir.IRBuilder, num):
        return FloInt(builder.urem(self.value, num.value))

    def cmp(self, builder: ir.IRBuilder, op, num):
        if not isinstance(num, FloInt):
            return FloBool.false()
        return FloBool(builder.icmp_signed(op, self.value, num.value))

    def neg(self):
        self.value = self.value.neg()
        return self

    def pow(self, builder: ir.IRBuilder, num):
        res = FloRef(builder, FloInt.one(), "res")
        base = FloRef(builder, self, "base")
        exp = FloRef(builder, num, "exp")
        pow_entry_block = builder.append_basic_block(f"pow.entry{self.incr()}")
        builder.branch(pow_entry_block)
        builder.position_at_start(pow_entry_block)
        exp_value: FloInt = exp.load()
        with builder.if_then(
            exp_value.and_(builder, FloInt.one()).castTo(builder, FloBool).value
        ):
            base_value = base.load()
            res_value = res.load()
            res.store(res_value.mul(builder, base_value))
        exp.store(exp_value.sr(builder, FloInt.one()))
        exp_value = exp.load()
        pow_exit_block = builder.append_basic_block(f"pow.exit{self.i}")
        with builder.if_then(exp_value.cmp(builder, "==", FloInt.zero()).value):
            builder.branch(pow_exit_block)
        base_value = base.load()
        base.store(base_value.mul(builder, base_value))
        builder.branch(pow_entry_block)
        builder.position_at_start(pow_exit_block)
        ret = res.load()
        res.free()
        exp.free()
        base.free()
        return ret

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

    def __init__(self, value: float | ir.Constant):
        self.size = 64
        if isinstance(value, float):
            self.value = ir.Constant(ir.DoubleType(), float(value))
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

    def neg(self):
        self.value = self.value.fneg()
        return self

    def castTo(self, builder: ir.IRBuilder, type):
        if type == FloInt:
            return self.toInt(builder)
        elif type == FloBool:
            return self.cmp(builder, "!=", FloFloat.zero())
        else:
            raise Exception(f"Unhandled type cast: float to {type}")

    @staticmethod
    def zero():
        return FloFloat(0.0)

    @staticmethod
    def default_llvm_val():
        return FloFloat.zero().value


class FloStr:
    id = -1
    strs = {}
    llvmtype = ir.IntType(8).as_pointer()

    def __init__(self, value):
        # Check for already defined strings
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
        i8 = builder.load(builder.gep(self.value, [index.value], True))
        return FloChar(builder.zext(i8, FloChar.llvmtype))

    def incr(self):
        FloStr.id += 1
        return FloStr.id

    @staticmethod
    def default_llvm_val():
        return FloStr("").value


class FloBool:
    llvmtype = ir.IntType(1)

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

    @staticmethod
    def default_llvm_val(_):
        return FloBool.true().value

    @staticmethod
    def true():
        return FloBool(True)

    @staticmethod
    def false():
        return FloBool(False)


class FloChar:
    llvmtype = ir.IntType(8)

    def __init__(self, value):
        self.value = value


class FloRef:
    c_free_fnc = None

    def __init__(self, builder: ir.IRBuilder, value, name: str):
        self.builder = builder
        self.addr = self.builder.alloca(value.value.type, None, name)
        self.store(value)

    def load(self):
        return self.referee.__class__(self.builder.load(self.addr))

    def store(self, value):
        self.referee = value
        self.builder.store(value.value, self.addr)
        return value

    def free(self):
        free_arg_type = ir.PointerType(ir.IntType(8))
        if FloRef.c_free_fnc == None:
            cfn_ty = ir.FunctionType(FloVoid.llvmtype, [free_arg_type])
            FloRef.c_free_fnc = ir.Function(
                Context.current_llvm_module, cfn_ty, name="free"
            )
        self.builder.call(
            FloRef.c_free_fnc, [self.builder.bitcast(self.addr, free_arg_type)]
        )


class FloVoid:
    llvmtype = ir.VoidType()
