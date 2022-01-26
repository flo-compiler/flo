from llvmlite import ir

def floType(type, value):
    if type == None: type = value.type
    if isinstance(type, ir.IntType):
        return FloNum(value)
    elif isinstance(type, ir.PointerType) and isinstance(type.pointee.type, ir.IntType):
        return FloStr(value)
    else: raise Exception(f"Type Not handled {type}")


class FloNum:
    def __init__(self, value: int|float|ir.Constant, size=32):
        if isinstance(value, int):
            self.size = 32 if value < 2147483647 and value > -2147483647 else self.size
            self.value = ir.Constant(ir.IntType(self.size), int(value))
        elif isinstance(value, float):
            self.size = 64
            self.value = ir.Constant(ir.DoubleType(), float(value))
        else:
            self.value = value
            self.size = value.type.width
        self.i = 0
    @staticmethod
    def one(): return FloNum(ir.Constant(ir.IntType(32), 1), 32)
    @staticmethod
    def zero(): return FloNum(ir.Constant(ir.IntType(32), 0), 32)
    def incr(self):
        self.i+=1
        return self.i

    def toFloat(self, num1: ir.Constant, num2: ir.Constant):
            a = num1
            b = num2
            if isinstance(num1.type, ir.IntType):
                a = num1.sitofp(ir.DoubleType())
            if isinstance(num2.type, ir.IntType):
                b = num2.sitofp(ir.DoubleType())
            return a, b
    
    def toInt(self, num1: ir.Constant, num2: ir.Constant):
            a = num1
            b = num2
            if isinstance(num1.type, ir.DoubleType):
                a = num1.fptosi(ir.IntType(64))
            if isinstance(num2.type, ir.DoubleType):
                b = num2.fptosi(ir.IntType(64))
            return a, b

    def arithOp(self, op_fnc1, op_fnc2, num):
        a = self.value
        b = num.value
        if self.value.type != num.value.type:
            a, b = self.toFloat(self.value, num.value)
        if isinstance(self.value.type, ir.IntType):
            return op_fnc1(a, b)
        else:
            return op_fnc2(a, b)

    def add(self, builder: ir.IRBuilder, num):
        return FloNum(self.arithOp(builder.add, builder.fadd, num))

    def sub(self, builder: ir.IRBuilder, num):
        return FloNum(self.arithOp(builder.sub, builder.fsub, num))

    def mul(self, builder: ir.IRBuilder, num):
        return FloNum(self.arithOp(builder.mul, builder.fmul, num))

    def div(self, builder: ir.IRBuilder, num):
        return FloNum(self.arithOp(builder.fdiv, builder.fdiv, num))

    def mod(self, builder: ir.IRBuilder, num):
        a = self.value
        b = num.value
        if (a.type != b.type): a, b = self.toInt(a, b)
        return FloNum(builder.urem(a, b))

    def cmp(self, builder: ir.IRBuilder, op, num):
        if isinstance(self.value.type, ir.DoubleType) or isinstance(num.value.type, ir.DoubleType):
            a, b  = self.toFloat(self.value, num.value)
            return FloNum(builder.fcmp_ordered(op, a, b))
        return FloNum(builder.icmp_signed(op, self.value, num.value))
    
    def pow(self, builder: ir.IRBuilder, num):
        a = self.value
        b = num.value
        res = builder.alloca(ir.IntType(32), name="res")
        builder.store(FloNum.one(), res)
        base = builder.alloca(ir.IntType(32), name="base")
        builder.store(a, base)
        exp = builder.alloca(ir.IntType(32), name="exp")
        builder.store(b, exp)
        pow_entry_block = builder.append_basic_block(f"pow.entry{self.incr()}")
        builder.branch(pow_entry_block)
        builder.position_at_start(pow_entry_block)
        exp_value = builder.load(exp)
        with builder.if_then(
            builder.icmp_unsigned("!=", builder.and_(exp_value, FloNum.one()), FloNum.zero())
        ):
            base_value = builder.load(base)
            res_value = builder.load(res)
            builder.store(builder.mul(res_value, base_value), res)
        exp_value = builder.load(exp)
        builder.store(builder.lshr(exp_value, FloNum.one()), exp)
        exp_value = builder.load(exp)
        pow_exit_block = builder.append_basic_block(f"pow.exit{self.i}")
        with builder.if_then(builder.icmp_unsigned("==", exp_value, FloNum.zero())):
            builder.branch(pow_exit_block)
        base_value = builder.load(base)
        builder.store(builder.mul(base_value, base_value), base)
        builder.branch(pow_entry_block)
        builder.position_at_start(pow_exit_block)
        return FloNum(builder.load(res))
    
    def sl(self, builder: ir.IRBuilder, num):
        a = self.value
        b = num.value
        if isinstance(self.value.type, ir.DoubleType) or isinstance(num.value.type, ir.DoubleType):
            a, b = self.toInt(self.value, num.value)
        return FloNum(builder.shl(a, b))

    def sr(self, builder: ir.IRBuilder, num):
        a = self.value
        b = num.value
        if isinstance(self.value.type, ir.DoubleType) or isinstance(num.value.type, ir.DoubleType):
            a, b = self.toInt(self.value, num.value)
        return FloNum(builder.ashr(a, b))

    def or_(self, builder: ir.IRBuilder, num):
        a = self.value
        b = num.value
        if isinstance(self.value.type, ir.DoubleType) or isinstance(num.value.type, ir.DoubleType):
            a, b = self.toInt(self.value, num.value)
        return FloNum(builder.or_(a, b))

    def and_(self, builder: ir.IRBuilder, num):
        a = self.value
        b = num.value
        if isinstance(self.value.type, ir.DoubleType) or isinstance(num.value.type, ir.DoubleType):
            a, b = self.toInt(self.value, num.value)
        return FloNum(builder.and_(a, b))
        
    def xor(self, builder: ir.IRBuilder, num):
        a = self.value
        b = num.value
        if isinstance(self.value.type, ir.DoubleType) or isinstance(num.value.type, ir.DoubleType):
            a, b = self.toInt(self.value, num.value)
        return FloNum(builder.xor(a, b))
        

class FloStr:
    def __init__(self, value):
        if isinstance(value, str):
            encoded = (value+'\0').encode(encoding="utf-8", errors="xmlcharrefreplace")
            self.value = ir.Constant(ir.ArrayType(ir.IntType(8), len(encoded)), bytearray(encoded))
            self.size = len(value)
        else:
            self.value = value

class FloBool:
    def __init__ (self, value):
        self.value = value
    
    def cmp(self, op, builder: ir.IRBuilder, bool):
        return FloBool(builder.icmp_signed(op, self.value, bool.value))
    @staticmethod
    def true(): return FloBool(ir.Constant(ir.IntType(1), 1))
    @staticmethod
    def false(): return FloBool(ir.Constant(ir.IntType(1), 0))

    

class FloRef:
    def __init__(self, builder: ir.IRBuilder, value, name:str):
        self.builder = builder
        self.addr = self.builder.alloca(value.value.type, None, name)
        self.store(value)

    def load(self):
        
        return self.referee.__class__(self.builder.load(self.addr))
    
    def store(self, value):
        self.referee = value
        self.builder.store(value.value, self.addr)
        return value 