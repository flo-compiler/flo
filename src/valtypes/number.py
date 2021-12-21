
from errors.rtError import RTError
from utils.range import Range
from valtypes.array import Array
from valtypes.boolean import Boolean
from valtypes.valType import ValType
from valtypes.string import String



class Number(ValType):
    def __init__(self, value):
        super().__init__()
        self.value = value
    def add(self, num):
        if(type(num) == Number):
            return Number(self.value + num.value), None
        elif (type(num) == String):
            return String(str(self.value) + num.value), None
        return self.illegalOp()
    def sub(self, num):
        if(type(num) == Number):
            return Number(self.value - num.value), None
        return self.illegalOp()
    def mul(self, num):
        if(type(num) == Number):
            return Number(self.value * num.value), None
        elif(type(num) == Array):
            return Array(self.value * num.value), None
        return self.illegalOp()
    def div(self, num):
        if(type(num) == Number):
            if(num.value == 0): return None, RTError(Range.merge(self.range, num.range), "Division by zero")
            return Number(self.value / num.value), None
        return self.illegalOp()
    def pow(self, num):
        if(type(num) == Number):
            return Number(pow(self.value, num.value)), None
    def mod(self, num):
        if(type(num) == Number):
            res = self.value%num.value
            intres = int(res)
            return Number(res if intres!= res else intres), None
        return self.illegalOp()
    def comp_neq(self, num):
        if(type(num) == Number):
            return Boolean(int(self.value != num.value)).set_ctx(self.context), None
        return self.illegalOp()
    
    def comp_eq(self, num):
        if(type(num) == Number):
            return Boolean(int(self.value == num.value)).set_ctx(self.context), None
        return self.illegalOp()

    def comp_lt(self, num):
        if(type(num) == Number):
            return Boolean(int(self.value < num.value)).set_ctx(self.context), None
        return self.illegalOp()
    def comp_lte(self, num):
        if(type(num) == Number):
            return Boolean(int(self.value <= num.value)).set_ctx(self.context), None
    def comp_gt(self, num):
        if(type(num) == Number):
            return Boolean(int(self.value > num.value)).set_ctx(self.context), None
        return self.illegalOp()
    def comp_gte(self, num):
        if(type(num) == Number):
            return Boolean(int(self.value >= num.value)).set_ctx(self.context), None
        return self.illegalOp()
    def l_and(self, num):
        if(type(num) == Number):
            return Boolean(int(self.value and num.value)).set_ctx(self.context), None
        return self.illegalOp()
    def l_or(self, num):
        if(type(num) == Number):
            return Boolean(int(self.value or num.value)).set_ctx(self.context), None
        return self.illegalOp()
    def l_not(self):
        return Boolean(int(not self.value)).set_ctx(self.context), None
                
    def copy(self):
        cp = Number(self.value)
        cp.set_range(self.range)
        cp.set_ctx(self.context)
        return cp
    
    def isTrue(self):
        return Boolean(self.value).isTrue()

    def __repr__(self):
        return f'{self.value}'
