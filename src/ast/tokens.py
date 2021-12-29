import string
from enum import Enum
from src.errors import Range

LETTERS = string.ascii_letters
DIGITS = '0123456789'

KEYWORDS = [
    'and',
    'or',
    'if',
    'else',
    'num',
    'bool',
    'str',
    'void',
    'for',
    'while',
    'fnc',
    'break',
    'continue',
    'return',
    'import',
    'from',
    'foreach',
    'in',
    'class',
    'pub',
    'priv',
    'as'
]
class TokType(Enum):
    COL = ':'
    SEMICOL = ';'
    COMMA = ','
    PLUS = '+'
    PLUS_PLUS = '++'
    MINUS = '-'
    MINUS_MINUS = '--'
    MULT = '*'
    DIV = '/'
    LPAR = '('
    RPAR = ')'
    MOD = '%'
    LBRACE = '{'
    RBRACE = '}'
    LBRACKET = '['
    RBRACKET = ']'
    NUM = 'number'
    LN = '\n'
    STR = 'string'
    POW = '^'
    QUES = '?'
    EQ = '='
    EEQ = '=='
    NEQ = '!='
    GT = '>'
    LT = '<'
    LTE = '<='
    GTE = '>='
    LEQ = '<='
    ARROW = '=>'
    EOF = 'EOF'
    NOT = '!'
    SL = '<<'
    SR = '>>'
    IDENTIFER = 'IDENTIFIER'
    KEYWORD = 'KEYWORD'


class Token:
    def __init__(self, _type: TokType, range: Range, _value: str =None  ):
        self.type = _type
        self.value = _value
        self.range = range
        

    def isKeyword(self, value):
        return self.type == TokType.KEYWORD and self.value == value
    
    def inKeywordList(self, list):
        found = False
        for  value in list:
            found = found or self.isKeyword(value)
        return found

    def __repr__(self):
        if self.value:
            return f'{self.value}'
        return f'{self.type._value_}'
