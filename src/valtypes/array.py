from typing import List, Union
from src.buildchain import checker
from src.valtypes import Value, string, boolean, number
from src.errors import RTError
class Array(Value):
    def __init__(self, value:List[Value]):
        super().__init__()
        self.value = value
        self.length = len(value)
    def add(self, other: Value):
        if (type(other) == Array):
            return Array(self.value + other.value).set_ctx(self.context), None
        return self.illegalOp()

    def l_sl(self, other: Value):
        self.value.append(other)
        self.length+=1
        return self, None

    def l_sr(self, other: Value):
        self.value.pop(other.value)
        self.length-=1
        return self, None

    def mul(self, num):
        if(type(num) == number.Number):
            if isinstance(self.value[0], Array):
                arr = []
                for _ in range(num.value):
                    arr+=([el.copy() for el in self.value])
                return Array(arr).set_ctx(self.comp_neq), None
            return Array(self.value * num.value).set_ctx(self.context), None
        return self.illegalOp()
    
    def comp_eq(self, other: Value):
        if(type(other) == Array):
            return boolean.Boolean(int(self.value == other.value)).set_ctx(self.context), None
        return boolean.Boolean(0), None
        
    def comp_neq(self, other: Value):
        if(type(other) == Array):
            return boolean.Boolean(int(self.value != other.value)).set_ctx(self.context), None
        return boolean.Boolean(0), None
        
    def getElement(self, index: Union[int, float]):
        index = int(index)
        if(index < 0 or index >= self.length):
            return None, RTError( self.range, f'Index out of range, index {index} on array of length {self.length}')
        return self.value[index], None
    
    def setElement(self, index, value: Union[int, float]):
        index = int(index)
        if(index < 0 or index >= self.length):
            return None, RTError( self.range, f'Index out of range, index {index} on array of length {self.length}')
        self.value[index] = value
        return self, None

    def is_in(self, value: Value):
        return boolean.Boolean(value in self.value), None

    def copy(self):
        cp = [el.copy() for el in self.value]
        cp = Array(cp)
        cp.set_ctx(self.context)
        cp.set_range(self.range)
        return cp
    def cast_to_type(self, type):
        if isinstance(type, checker.arrayType):
            rt = []
            for el in self.value:
                nel, error = el.cast_to_type(type.elementType)
                if error: return None, error
                rt.append(nel)
            return Array(rt), None
        elif type == checker.Types.STRING:
            res = ""
            for el in self.value:
                nel, error = el.cast_to_type(type)
                if error: return None, error
                res+=nel.value
            return string.String(res), None
        return self.illegalOp()
        
    def __repr__(self):
        return f'{self.value}'
