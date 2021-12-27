from buildchain import Visitor
from context import Context
class Compiler(Visitor):
    def __init__(self, context: Context):
        super().__init__(context)