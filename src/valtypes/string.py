
from errors import RTError
from buildchain.checker import Types, arrayType
from valtypes import Value, array, number
from valtypes.boolean import Boolean

class String(Value):
    def __init__(self, value):
        super().__init__()
        self.value = value
    def add(self, stri: Value):
        if (type(stri) == String):
            return String(self.value + stri.value).set_ctx(self.context), None
        elif (type(stri) == number.Number):
            return String(self.value + str(stri.value)).set_ctx(self.context), None
        return self.illegalOp()

    def mul(self, num):
        if(type(num) == number.Number):
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
        return String(self.value[index]).set_ctx(self.context), None

    def is_in(self, value: Value):
        return Boolean(value.value in self.value).set_ctx(self.context), None

    def cast_to_type(self, type):
        if type == Types.BOOL:
            return Boolean(len(self.value)).set_ctx(self.context), None
        elif type == Types.NUMBER:
            try:
                if '.' in self.value:
                    v = float(self.value)
                else:
                    v = int(self.value)
                return number.Number(v).set_ctx(self.context), None
            except:
                return None, RTError(self.range, f"Cannot convert string '{self.value}' to num")
        elif isinstance(type, arrayType) and type.elementType == Types.STRING:
            arr = []
            rg = self.range.copy()
            rg.end.col = rg.start.col+1 
            rg.end.ind = rg.start.ind+1
            for char in self.value:
                rg.start.advance()
                rg.end.advance()
                arr.append(String(char).set_ctx(self.context).set_range(rg))
            return array.Array(arr).set_ctx(self.context), None
        elif type == Types.STRING:
            return self, None
        return self.illegalOp()

    def copy(self):
        cp = String(self.value)
        cp.set_ctx(self.context)
        cp.set_range(self.range)
        return cp
    
    
    def __repr__(self):
        return f'{self.value}'
