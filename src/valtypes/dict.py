from valtypes.boolean import Boolean
from valtypes.number import Number
from valtypes import Value
class Dict(Value):
    def __init__(self, value: dict[str, Value]):
        super().__init__()
        self.value = value

    def comp_eq(self, other):
        if(type(other) == Dict):
            return Boolean(int(self.value == other.value)).set_ctx(self.context), None
        return Boolean(0), None
        
    def comp_neq(self, other):
        if(type(other) == Dict):
            return Boolean(int(self.value != other.value)).set_ctx(self.context), None
        return Boolean(0), None
        
    def getElement(self, index):
        v = self.value.get(index, None)
        if v == None: return Number(0).set_ctx(self.context), None
        return v, None
    
    def setElement(self, index, value):
        self.value[index] = value
        return self, None
        
    def __repr__(self):
        return f'{self.value}'
