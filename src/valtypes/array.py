from typing import List
from valtypes.boolean import Boolean
from valtypes.valType import ValType
from errors.rtError import RTError
class Array(ValType):
    def __init__(self, value:List[ValType]):
        super().__init__()
        self.value = value
        self.length = len(value)
    def add(self, other):
        if (type(other) == Array):
            return Array(self.value + other.value).set_ctx(self.context), None
        return self.illegalOp()

    def mul(self, num):
        from valtypes.number import Number
        if(type(num) == Number):
            if isinstance(self.value[0], Array):
                arr = []
                for _ in range(num.value):
                    arr+=([el.copy() for el in self.value])
                return Array(arr).set_ctx(self.comp_neq), None
            return Array(self.value * num.value).set_ctx(self.context), None
        return self.illegalOp()
    
    def comp_eq(self, other):
        if(type(other) == Array):
            return Boolean(int(self.value == other.value)).set_ctx(self.context), None
        return Boolean(0), None
        
    def comp_neq(self, other):
        if(type(other) == Array):
            return Boolean(int(self.value != other.value)).set_ctx(self.context), None
        return Boolean(0), None
        
    def getElement(self, index):
        index = int(index)
        if(index < 0 or index >= self.length):
            return None, RTError( self.range, f'Index out of range, index {index} on array of length {self.length}')
        return self.value[index], None
    
    def setElement(self, index, value):
        index = int(index)
        if(index < 0 or index >= self.length):
            return None, RTError( self.range, f'Index out of range, index {index} on array of length {self.length}')
        self.value[index] = value
        return self, None

    def copy(self):
        cp = [el.copy() for el in self.value]
        cp = Array(cp)
        cp.set_ctx(self.context)
        cp.set_range(self.range)
        return cp
        
    def __repr__(self):
        return f'{self.value}'
