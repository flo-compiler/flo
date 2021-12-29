from src.valtypes import Value


class Boolean(Value):
    def __init__(self, value):
        super().__init__()
        self.value = (0 if value == 0 else 1)

    def l_and(self, stri):
        if (type(stri) == Boolean):
            return Boolean(self.value and stri.value).set_ctx(self.context), None
        return self.illegalOp()

    def l_or(self, num):
        if(type(num) == Boolean):
            return Boolean(self.value or num.value).set_ctx(self.context), None
        return self.illegalOp()


    def l_not(self):
        return Boolean(int (not self.value)), None

    def comp_eq(self, other):
        if (type(other) == Boolean):
            return Boolean(self.value == other.value).set_ctx(self.context), None
        return Boolean(0), None

    def isTrue(self):
        return self.value != 0
    
    def cast_to_type(self, type):
        from buildchain.checker import Types
        from valtypes.number import Number
        from valtypes.string import String
        if type == Types.NUMBER:
            return Number(self.value).set_ctx(self.context), None
        elif type == Types.STRING:
            return String(self.__repr__()).set_ctx(self.context), None
        elif type == Types.BOOL:
            return self, None
        return self.illegalOp()

    def copy(self):
        cp = Boolean(self.value)
        cp.set_ctx(self.context)
        cp.set_range(self.range)
        return cp
        
    def __repr__(self):
        val = ('false' if self.value == 0 else 'true')
        return f'{val}'
