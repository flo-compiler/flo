from valtypes.valType import ValType


class Boolean(ValType):
    def __init__(self, value):
        super().__init__()
        self.value = (0 if value == 0 else 1)

    def l_and(self, stri):
        from valtypes.string import String
        from valtypes.number import Number
        if (type(stri) == Boolean):
            return Boolean(self.value and stri.value).set_ctx(self.context), None
        if (type(stri) == String):
            return Boolean(self.value + len(stri.value)).set_ctx(self.context), None
        elif (type(stri) == Number):
            return Boolean(self.value + str(stri.value)).set_ctx(self.context), None
        return self, None

    def l_or(self, num):
        from valtypes.number import Number
        if(type(num) == Boolean):
            return Boolean(self.value and num.value).set_ctx(self.context), None
        if(type(num) == Number):
            return Boolean(self.value * num.value).set_ctx(self.context), None
        return self, None


    def l_not(self):
        return Boolean(int (not self.value)), None

    def comp_eq(self, other):
        if (type(other) == Boolean):
            return Boolean(self.value == other.value).set_ctx(self.context), None
        return Boolean(0), None

    def isTrue(self):
        return self.value != 0
    
    def copy(self):
        cp = Boolean(self.value)
        cp.set_ctx(self.context)
        cp.set_range(self.range)
        return cp
        
    def __repr__(self):
        val = ('false' if self.value == 0 else 'true')
        return f'{val}'
