from errors.rtError import RTError
class ValType:
    def __init__(self):
        self.set_range()
        self.set_ctx()
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
    def set_range(self, range=None):
        self.range = range
        return self
    
    def copy(self):
        raise Exception('copy method not defined')
    
    def isTrue(self):
        return self.illegalOp()

    def set_ctx(self, context=None):
        self.context = context
        return self

    def __repr__(self):
           raise Exception('Not Implemented')
