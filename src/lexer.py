import codecs
from errors import Range, Position
from errors import ExpectedCharError, IllegalCharacterError
import string
from enum import Enum
from errors import Range

LETTERS = string.ascii_letters
DIGITS = "0123456789"

KEYWORDS = [
    "and",
    "or",
    "xor",
    "if",
    "else",
    "int",
    "float",
    "bool",
    "str",
    "void",
    "for",
    "while",
    "fnc",
    "break",
    "continue",
    "return",
    "import",
    "from",
    "foreach",
    "in",
    "class",
    "pub",
    "priv",
    "as",
    "is",
    "inline"
]


class TokType(Enum):
    COL = ":"
    SEMICOL = ";"
    COMMA = ","
    PLUS = "+"
    PLUS_PLUS = "++"
    MINUS = "-"
    MINUS_MINUS = "--"
    MULT = "*"
    DIV = "/"
    LPAR = "("
    RPAR = ")"
    MOD = "%"
    LBRACE = "{"
    RBRACE = "}"
    LBRACKET = "["
    RBRACKET = "]"
    INT = "int"
    FLOAT = "float"
    LN = "\n"
    STR = "string"
    POW = "^"
    QUES = "?"
    EQ = "="
    EEQ = "=="
    NEQ = "!="
    GT = ">"
    LT = "<"
    LTE = "<="
    GTE = ">="
    LEQ = "<="
    ARROW = "=>"
    EOF = "EOF"
    NOT = "!"
    SL = "<<"
    SR = ">>"
    IDENTIFER = "IDENTIFIER"
    KEYWORD = "KEYWORD"


class Token:
    def __init__(self, _type: TokType, range: Range, _value: str = None):
        self.type = _type
        self.value = _value
        self.range = range

    def isKeyword(self, value):
        return self.type == TokType.KEYWORD and self.value == value

    def inKeywordList(self, list):
        found = False
        for value in list:
            found = found or self.isKeyword(value)
        return found

    def __repr__(self):
        if self.value:
            return f"{self.value}"
        return f"{self.type._value_}"


class Lexer:
    def __init__(self, fn, text):
        self.fn = fn
        self.text = text
        self.pos = Position(-1, 0, -1, fn, text)
        self.current_char = None
        self.advance()

    def advance(self):
        self.pos.advance(self.current_char)
        if self.pos.ind < len(self.text):
            self.current_char = self.text[self.pos.ind]
        else:
            self.current_char = None

    def skip_comment(self):
        single_line = True if self.current_char == "/" else False
        double_line = True if self.current_char == "*" else False
        while single_line and self.current_char != "\n" and self.current_char != None:
            self.advance()
        close_comment = False
        while double_line and not close_comment and self.current_char != None:
            self.advance()
            if self.current_char == "*":
                self.advance()
                if self.current_char == "/":
                    close_comment = True
        self.advance()

    def tokenize(self):
        tokens = []
        while self.current_char != None:
            if self.current_char in " \t":
                self.advance()
            elif self.current_char == "/":
                self.advance()
                if self.current_char == "/" or self.current_char == "*":
                    self.skip_comment()
                else:
                    tokens.append(Token(TokType.DIV, Range(self.pos)))
            elif self.current_char == TokType.PLUS.value:
                tok = make_plus_plus(self)
                tokens.append(tok)
            elif self.current_char == TokType.MINUS.value:
                tok = make_minus_minus(self)
                tokens.append(tok)
            elif self.current_char == TokType.NOT.value:
                tok = make_neq(self)
                tokens.append(tok)
            elif self.current_char == TokType.EQ.value:
                tokens.append(make_eq(self))
            elif self.current_char == TokType.LT.value:
                tokens.append(make_lte(self))
            elif self.current_char == TokType.GT.value:
                tokens.append(make_gte(self))
            elif self.current_char in TokType._value2member_map_:
                tok = TokType._value2member_map_[self.current_char]
                tokens.append(Token(tok, Range(self.pos)))
                self.advance()
            # special cases so you need to make special characters
            elif self.current_char in LETTERS:
                tokens.append(make_identifier(self))
            elif self.current_char in DIGITS:
                tokens.append(makeNumber(self))
            elif self.current_char == '"' or self.current_char == "'":
                tok = make_str(self)
                tokens.append(tok)
            else:
                pos_start = self.pos.copy()
                char = self.current_char
                self.advance()
                IllegalCharacterError(Range(pos_start, self.pos), char).throw()
        tokens.append(Token(TokType.EOF, Range(self.pos)))
        return tokens


def makeNumber(lexer: Lexer):
    DIGITS_DOT = DIGITS + "."
    number = ""
    pos_start = lexer.pos.copy()
    isFloat = False
    while lexer.current_char != None and lexer.current_char in DIGITS_DOT:
        if lexer.current_char == ".":
            if isFloat:
                break
            isFloat = True
        number += lexer.current_char
        lexer.advance()
    if isFloat:
        return Token(TokType.FLOAT, Range(pos_start, lexer.pos), float(number))
    else:
        return Token(TokType.INT, Range(pos_start, lexer.pos), int(number))


def make_plus_plus(lexer: Lexer):
    pos_start = lexer.pos.copy()
    lexer.advance()
    if lexer.current_char == TokType.PLUS.value:
        lexer.advance()
        return Token(TokType.PLUS_PLUS, Range(pos_start, lexer.pos))
    else:
        return Token(TokType.PLUS, Range(pos_start))


def make_minus_minus(lexer: Lexer):
    pos_start = lexer.pos.copy()
    lexer.advance()
    if lexer.current_char == TokType.MINUS.value:
        lexer.advance()
        return Token(TokType.MINUS_MINUS, Range(pos_start, lexer.pos))
    else:
        return Token(TokType.MINUS, Range(pos_start))


def make_identifier(lexer: Lexer):
    LETTERS_DIGITS = LETTERS + "_" + DIGITS
    id_string = ""
    pos_start = lexer.pos.copy()
    while lexer.current_char != None and lexer.current_char in LETTERS_DIGITS:
        id_string += lexer.current_char
        lexer.advance()
    t_type = TokType.KEYWORD if id_string in KEYWORDS else TokType.IDENTIFER
    return Token(t_type, Range(pos_start, lexer.pos), id_string)


def make_neq(lexer: Lexer):
    pos_start = lexer.pos.copy()
    lexer.advance()
    if lexer.current_char == "=":
        lexer.advance()
        return Token(TokType.NEQ, Range(pos_start, lexer.pos))
    else:
        return Token(TokType.NOT, Range(pos_start))


def make_eq(lexer: Lexer):
    pos_start = lexer.pos.copy()
    lexer.advance()
    if lexer.current_char == "=":
        lexer.advance()
        return Token(TokType.EEQ, Range(pos_start, lexer.pos))
    elif lexer.current_char == ">":
        lexer.advance()
        return Token(TokType.ARROW, Range(pos_start, lexer.pos))

    return Token(TokType.EQ, Range(pos_start))


def make_lte(lexer: Lexer):
    pos_start = lexer.pos.copy()
    lexer.advance()
    if lexer.current_char == "=":
        lexer.advance()
        return Token(TokType.LEQ, Range(pos_start, lexer.pos))
    elif lexer.current_char == "<":
        lexer.advance()
        return Token(TokType.SL, Range(pos_start, lexer.pos))
    return Token(TokType.LT, Range(pos_start))


def make_gte(lexer: Lexer):
    pos_start = lexer.pos.copy()
    lexer.advance()
    if lexer.current_char == "=":
        lexer.advance()
        return Token(TokType.GTE, Range(pos_start, lexer.pos))
    elif lexer.current_char == ">":
        lexer.advance()
        return Token(TokType.SR, Range(pos_start, lexer.pos))
    return Token(TokType.GT, Range(pos_start))


def make_str(lexer: Lexer):
    pos_start = lexer.pos.copy()
    str_val = ""
    escape_next = False
    quote_char = lexer.current_char
    lexer.advance()
    while lexer.current_char != None and (
        lexer.current_char != quote_char or escape_next
    ):
        if lexer.current_char == "\\":
            escape_next = True
            str_val += lexer.current_char
        else:
            str_val += lexer.current_char
            escape_next = False
        lexer.advance()
    if lexer.current_char != quote_char:
        ExpectedCharError(
            Range(
                pos_start, lexer.pos), f"None matching '{quote_char}' in string"
        ).throw()
    lexer.advance()
    # Unstable code since codes.escape_decode is not a public python function and may be deprecated in the next future
    # Source from: https://stackoverflow.com/questions/4020539/process-escape-sequences-in-a-string-in-python
    return Token(TokType.STR, Range(pos_start, lexer.pos), codecs.escape_decode(bytes(str_val, "utf-8"))[0].decode("utf-8"))
