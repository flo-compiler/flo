from src.errors import RTError
class Value:
    def __init__(self):
        self.set_range()
        self.set_ctx()
        self.value: Value = None
    def illegalOp(self):
        return None, RTError(self.range, "Illegal operation")
    def add(self, _):
        return self.illegalOp()
    def sub(self, _):
        return self.illegalOp()
    def mul(self, _):
        return self.illegalOp()
    def div(self, _):
       return self.illegalOp()
    def pow(self, _):
       return self.illegalOp()
    def mod(self, _):
        return self.illegalOp()
    def comp_neq(self, _):
        return self.illegalOp()
    def comp_eq(self, _):
        return self.illegalOp()
    def comp_lt(self, _):
       return self.illegalOp()
    def comp_lte(self, _):
        return self.illegalOp()
    def comp_gt(self, _):
        return self.illegalOp()
    def comp_gte(self, _):
       return self.illegalOp()
    def l_and(self, _):
        return self.illegalOp()
    def l_or(self, _):
        return self.illegalOp()
    def l_not(self):
        return self.illegalOp()   
    def execute(self):
        return self.illegalOp()   
    def getElement(self, index):
        return self.illegalOp()
    def setElement(self, index, value):
        return self.illegalOp()
    def is_in(self, value):
        return self.illegalOp()
    def l_sl(self, value):
        return self.illegalOp()
    def l_sr(self, value):
        return self.illegalOp()
    def set_range(self, range=None):
        self.range = range
        return self
    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, self.__class__) and self.value == __o.value
    def copy(self):
        raise Exception('copy method not defined')
    
    def isTrue(self):
        return self.illegalOp()

    def set_ctx(self, context=None):
        self.context = context
        return self

    def __repr__(self):
           raise Exception('Not Implemented')
    def cast_to_type(self, type): 
            return self.illegalOp()