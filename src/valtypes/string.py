from valtypes.boolean import Boolean
from valtypes.valType import ValType
from errors.rtError import RTError

class String(ValType):
    def __init__(self, value):
        super().__init__()
        self.value = value
    def add(self, stri):
        from valtypes.number import Number
        if (type(stri) == String):
            return String(self.value + stri.value).set_ctx(self.context), None
        elif (type(stri) == Number):
            return String(self.value + str(stri.value)).set_ctx(self.context), None
        return self.illegalOp()

    def mul(self, num):
        from valtypes.number import Number
        if(type(num) == Number):
            return String(self.value * num.value).set_ctx(self.context), None
        return self.illegalOp()
    
    def comp_eq(self, str):
        if(type(str) == String):
            return Boolean(int(self.value == str.value)).set_ctx(self.context), None
        return Boolean(0), None
        
    def comp_neq(self, str):
        if(type(str) == String):
            return Boolean(int(self.value != str.value)).set_ctx(self.context), None
        return Boolean(0), None

    def getElement(self, index):
        index = int(index)
        if(index < 0 or index >= len(self.value)):
            return None, RTError(self.range, f'Index out of range, index {index} on string of length {len(self.value)}')
        return String(self.value[index]), None

    def copy(self):
        cp = String(self.value)
        cp.set_ctx(self.context)
        cp.set_range(self.range)
        return cp
    
    
    def __repr__(self):
        return f'{self.value}'
