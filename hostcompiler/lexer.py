import codecs
from errors import Range, Position
from errors import ExpectedCharError, IllegalCharacterError
import string
from enum import Enum
from errors import Range

LETTERS = string.ascii_letters+"_"
BIN_DIGITS = "01"
OCT_DIGITS = BIN_DIGITS+"234567"
DEC_DIGITS = OCT_DIGITS+"89"
HEX_DIGITS = DEC_DIGITS+"ABCDEFabcdef"

KEYWORDS = [
    "and",
    "or",
    "xor",
    "const",
    "if",
    "else",
    "int",
    "float",
    "void",
    "for",
    "while",
    "fnc",
    "break",
    "private",
    "public",
    "protected",
    "continue",
    "return",
    "import",
    "let",
    "type",
    "in",
    "class",
    "enum",
    "new",
    "as",
    "is"
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
    CHAR = "char"
    POW = "^"
    QUES = "?"
    AMP = "&"
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
    DOT = "."
    DOT_DOT = ".."
    DOT_DOT_DOT = "..."
    IDENTIFER = "IDENTIFIER"
    MACRO_IDENTIFIER = "MACRO_IDENTIFER"
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
        line_type = 1 if self.current_char == "/" else 2
        while self.current_char != None:
            self.advance()
            if line_type == 1 and self.current_char == "\n":
                break
            elif line_type == 2:
                break_outer = False
                while self.current_char == "*":
                    self.advance()
                    if self.current_char == "/":
                        self.advance()
                        break_outer = True
                        break
                if break_outer:
                    break

    def tokenize(self):
        tokens = []
        while self.current_char != None:
            if self.current_char in " \t\n":
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
            elif self.current_char == TokType.DOT.value:
                tokens.append(make_dots(self))
            elif self.current_char in TokType._value2member_map_:
                tok = TokType._value2member_map_[self.current_char]
                tokens.append(Token(tok, Range(self.pos)))
                self.advance()
            # special cases so you need to make special characters
            elif self.current_char in LETTERS:
                tokens.append(make_identifier(self))
            elif self.current_char in DEC_DIGITS:
                tokens.append(make_number(self))
            elif self.current_char == "'":
                tok = make_char(self)
                tokens.append(tok)
            elif self.current_char == '"':
                tok = make_str(self)
                tokens.append(tok)
            elif self.current_char == "$":
                tokens.append(make_macro_identifer(self))
            else:
                pos_start = self.pos.copy()
                char = self.current_char
                self.advance()
                IllegalCharacterError(Range(pos_start, self.pos), char).throw()
        tokens.append(Token(TokType.EOF, Range(self.pos)))
        return tokens


def make_number(lexer: Lexer):
    number = ""
    pos_start = lexer.pos.copy()
    is_float = False
    base = 10
    BASE_CHARSET = DEC_DIGITS + "."
    if lexer.current_char == '0':
        number += lexer.current_char
        lexer.advance()
        if lexer.current_char == 'b':
            base = 2
            BASE_CHARSET = BIN_DIGITS
        elif lexer.current_char == 'o':
            base = 8
            BASE_CHARSET = OCT_DIGITS
        elif lexer.current_char == 'x':
            base = 16
            BASE_CHARSET = HEX_DIGITS
        if base != 10:
            lexer.advance()
    while lexer.current_char != None and lexer.current_char in BASE_CHARSET:
        if lexer.current_char == ".":
            if is_float:
                number = number[:-1]
                is_float = "." in number
                if not is_float:
                    lexer.pos.ind-=1
                break
            is_float = True
        number += lexer.current_char
        lexer.advance()
    if is_float:
        return Token(TokType.FLOAT, Range(pos_start, lexer.pos), float(number))
    else:
        return Token(TokType.INT, Range(pos_start, lexer.pos), int(number, base=base))


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
    LETTERS_DIGITS = LETTERS + DEC_DIGITS
    id_string = ""
    pos_start = lexer.pos.copy()
    while lexer.current_char != None and lexer.current_char in LETTERS_DIGITS:
        id_string += lexer.current_char
        lexer.advance()
    t_type = TokType.KEYWORD if id_string in KEYWORDS else TokType.IDENTIFER
    return Token(t_type, Range(pos_start, lexer.pos), id_string)

def make_macro_identifer(lexer: Lexer):
    DOLLAR_LETTERS_DIGITS = LETTERS + DEC_DIGITS + "$"
    id_string = ""
    pos_start = lexer.pos.copy()
    while lexer.current_char != None and lexer.current_char in DOLLAR_LETTERS_DIGITS:
        id_string += lexer.current_char
        lexer.advance()
    return Token(TokType.MACRO_IDENTIFIER, Range(pos_start, lexer.pos), id_string)

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


def make_dots(lexer: Lexer):
    pos_start = lexer.pos.copy()
    token = TokType.DOT
    lexer.advance()
    if lexer.current_char == '.':
        token = TokType.DOT_DOT
        lexer.advance()
        if lexer.current_char == '.':
            token = TokType.DOT_DOT_DOT
            lexer.advance()
    end_pos = lexer.pos.copy()
    return Token(token, Range(pos_start, end_pos))


def make_char(lexer: Lexer):
    pos_start = lexer.pos.copy()
    lexer.advance()
    char_val = lexer.current_char
    if char_val == "\\":
        lexer.advance()
        if lexer.current_char == "n":
            char_val = "\n"
        elif lexer.current_char == "a":
            char_val = "\a"
        elif lexer.current_char == "b":
            char_val = "\b"
        elif lexer.current_char == "t":
            char_val = "\t"
        elif lexer.current_char == "r":
            char_val = "\r"
        elif lexer.current_char == "f":
            char_val = "\f"
        elif lexer.current_char == "v":
            char_val = "\v"
        elif lexer.current_char == "'":
            char_val = "\'"
        elif lexer.current_char == "\"":
            char_val = "\""
        elif lexer.current_char == "\\":
            char_val = "\\"
        elif lexer.current_char == "0":
            char_val = "\0"
        else:
            IllegalCharacterError( Range(
                pos_start, lexer.pos), f"No character '\{lexer.current_char}'").throw()
    lexer.advance()
    if lexer.current_char != "'":
        ExpectedCharError(
            Range(
                pos_start, lexer.pos), f"No matching \"'\" in char"
        ).throw()
    lexer.advance()
    return Token(TokType.CHAR, Range(pos_start, lexer.pos), ord(char_val))


def make_str(lexer: Lexer):
    pos_start = lexer.pos.copy()
    str_val = ""
    escape_next = False
    lexer.advance()
    while lexer.current_char != None and (
        lexer.current_char != '"' or escape_next
    ):
        if lexer.current_char == "\\":
            escape_next = True
            str_val += lexer.current_char
        else:
            str_val += lexer.current_char
            escape_next = False
        lexer.advance()
    if lexer.current_char != '"':
        ExpectedCharError(
            Range(
                pos_start, lexer.pos), f"None matching '\"' in string"
        ).throw()
    lexer.advance()
    # Unstable code since codes.escape_decode is not a public python function and may be deprecated in the next future
    # Source from: https://stackoverflow.com/questions/4020539/process-escape-sequences-in-a-string-in-python
    return Token(TokType.STR, Range(pos_start, lexer.pos), codecs.escape_decode(bytes(str_val, "utf-8"))[0].decode("utf-8"))
