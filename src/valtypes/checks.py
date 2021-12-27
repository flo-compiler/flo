from enum import Enum

class fncType:
    def __init__(self, returnType, argTypes):
        self.returnType = returnType
        self.argTypes = argTypes
    def __eq__(self, o: object) -> bool:
        if isinstance(o, fncType):
            if len(self.argTypes) != len(o.argTypes): return False
            for i in range(len(o.argTypes)):
                if self.argTypes[i] != o.argTypes[i]: return False
        else:
            return False

class arrayType:
    def __init__(self, elementType):
        self.elementType = elementType
    def __eq__(self, o: object) -> bool:
        if isinstance(o, arrayType):
            return self.elementType == o.elementType
        return False
class dictType:
    def __init__(self, elementType):
        self.elementType = elementType
    def __eq__(self, o: object) -> bool:
        if isinstance(o, dictType):
            return self.elementType == o.elementType
        return False
        
class objectType:
    def __init__(self, fields):
        self.fields = fields

class Types(Enum):
    NUMBER = 1
    STRING = 2
    BOOL = 3
    NULL = 4
    ANY = 5


def typeToStr(type):
    if type == Types.NUMBER:
        return 'num'
    elif type == Types.STRING:
        return 'str'
    elif type == Types.BOOL:
        return 'bool'
    elif type == Types.NULL:
        return 'void'
    elif isinstance(type, fncType):
        return f'{ "<T>" if Types.ANY in type.argTypes else "" }({", ".join([typeToStr(t) for t in type.argTypes])}) => {typeToStr(type.returnType)}'
    elif isinstance(type, arrayType):
        return f'[{typeToStr(type.elementType)}]'
    elif isinstance(type, dictType):
        return "{"+f'{typeToStr(type.elementType)}'+"}"
    else: return "T"

def strToType(str):
    if str == 'num':
        return Types.NUMBER
    elif str == 'str':
        return Types.STRING
    elif str == 'bool':
        return Types.BOOL
    elif str == 'void':
        return Types.NULL
