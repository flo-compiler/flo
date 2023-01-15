#!/usr/bin/env python3
import codecs
import pathlib
import re
import string
import struct
import sys
from ctypes import CFUNCTYPE, POINTER, c_char_p, c_int
from enum import Enum
from optparse import OptionParser
from os import _exit, path
from typing import Dict, List, Tuple, Union

from genericpath import exists
from llvmlite import binding as llvm, ir
from termcolor import colored


class Position:
    def __init__(self, ind, line, col, fn, txt):
        self.ind = ind
        self.line = line
        self.col = col
        self.fn = fn
        self.txt = txt

    def advance(self, currentChar=None):
        self.ind += 1
        if currentChar == "\n":
            self.line += 1
            self.col = 0
        else:
            self.col += 1

    def copy(self):
        return Position(self.ind, self.line, self.col, self.fn, self.txt)


class Range:
    def __init__(self, start: Position, end: Position = None):
        self.start = start.copy()
        if end is None:
            end = self.start.copy()
            end.advance()
            self.end = end
        else:
            self.end = end.copy()

    def copy(self):
        return Range(self.start, self.end)

    @staticmethod
    def merge(r1, r2):
        return Range(r1.start, r2.end)


class Error:
    def __init__(self, range: Range, name: str, msg: str):
        self.range = range
        self.name = name
        self.msg = msg

    def message(self):
        name = colored(f"[{self.name}]: ", "red", attrs=["bold"])
        msg = colored(f"{self.msg}\n", attrs=["bold"])
        trace = (
            f'File "{self.range.start.fn}", line {self.range.start.line+1}\n{string_with_arrows(self.range.start.txt, self.range.start, self.range.end)}'
            if self.range
            else ""
        )
        return name + msg + trace

    def throw(self):
        print(self.message())
        _exit(1)


class ExpectedCharError(Error):
    def __init__(self, range: Range, msg: str):
        super().__init__(range, "Expected character", msg)


class IllegalCharacterError(Error):
    def __init__(self, range: Range, char: str):
        super().__init__(range, "Illegal character", f"'{char}'")


class RTError(Error):
    def __init__(self, range: Range, msg: str):
        super().__init__(range, "Runtime Error", msg)


class SyntaxError(Error):
    def __init__(self, range: Range, char: str):
        super().__init__(range, "Syntax Error", char)


class TypeError(Error):
    def __init__(self, range: Range, message: str):
        super().__init__(range, "Type Error", message)


class GeneralError(Error):
    def __init__(self, range: Range, message: str):
        super().__init__(range, "Error", message)


class IOError(Error):
    def __init__(self, range: Range, message: str):
        super().__init__(range, "IO Error", message)


class NullError(Error):
    def __init__(self, range: Range, message: str):
        super().__init__(range, "Null pointer Error", message)


class NameError(Error):
    def __init__(self, range: Range, message: str):
        super().__init__(range, "Name Error", message)


class CompileError(Error):
    def __init__(self, message):
        super().__init__(None, "Compile Error", message)


def string_with_arrows(text, pos_start: Position, pos_end: Position):
    result = ""
    # Calculate indices
    idx_start = max(text.rfind("\n", 0, pos_start.ind), 0)
    idx_end = text.find("\n", idx_start + 1)
    if idx_end < 0:
        idx_end = len(text)

    # Generate each line
    line_count = pos_end.line - pos_start.line + 1
    for i in range(line_count):
        # Calculate line columns
        line = text[idx_start:idx_end]
        col_start = pos_start.col if i == 0 else 0
        col_end = pos_end.col if i == line_count - 1 else len(line) - 1

        # Append to result
        result += line + "\n"
        result += colored(
            " " * col_start + "^" * (col_end - col_start), "red", attrs=["bold"]
        )

        # Re-calculate indices
        idx_start = idx_end
        idx_end = text.find("\n", idx_start + 1)
        if idx_end < 0:
            idx_end = len(text)

    return result.replace("\t", "")


LETTERS = string.ascii_letters + "_"
BIN_DIGITS = "01"
OCT_DIGITS = BIN_DIGITS + "234567"
DEC_DIGITS = OCT_DIGITS + "89"
HEX_DIGITS = DEC_DIGITS + "ABCDEFabcdef"

KEYWORDS = [
    "and",
    "or",
    "xor",
    "const",
    "if",
    "else",
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
    "bool",
    "const",
    "int",
    "i4",
    "i8",
    "i16",
    "i32",
    "i64",
    "i128",
    "float",
    "f16",
    "f32",
    "f64",
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
    INT = "int"
    FLOAT = "float"
    CHAR = "char"
    STR = "str"
    RBRACKET = "]"
    LN = "\n"
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

    def tokenizeNext(self):
        if self.current_char == None:
            return None
        if self.current_char in " \t":
            self.advance()
            return self.tokenizeNext()
        elif self.current_char == "/":
            self.advance()
            if self.current_char == "/" or self.current_char == "*":
                self.skip_comment()
                return self.tokenizeNext()
            else:
                return Token(TokType.DIV, Range(self.pos))
        elif self.current_char == TokType.PLUS.value:
            return make_plus_plus(self)
        elif self.current_char == TokType.MINUS.value:
            return make_minus_minus(self)
        elif self.current_char == TokType.NOT.value:
            return make_neq(self)
        elif self.current_char == TokType.EQ.value:
            return make_eq(self)
        elif self.current_char == TokType.LT.value:
            return make_lte(self)
        elif self.current_char == TokType.GT.value:
            return make_gte(self)
        elif self.current_char == TokType.DOT.value:
            return make_dots(self)
        elif self.current_char in TokType._value2member_map_:
            tok = TokType._value2member_map_[self.current_char]
            pos = self.pos
            self.advance()
            return Token(tok, Range(pos))
        # special cases so you need to make special characters
        elif self.current_char in LETTERS:
            return make_identifier(self)
        elif self.current_char in DEC_DIGITS:
            return make_number(self)
        elif self.current_char == "'":
            return make_char(self)
        elif self.current_char == '"':
            return make_str(self)
        else:
            pos_start = self.pos.copy()
            char = self.current_char
            self.advance()
            IllegalCharacterError(Range(pos_start, self.pos), char).throw()

    def tokenize(self):
        tokens = []
        while self.current_char != None:
            token = self.tokenizeNext()
            if token != None:
                tokens.append(token)
        tokens.append(Token(TokType.EOF, Range(self.pos)))
        return tokens


def make_number(lexer: Lexer):
    number = ""
    pos_start = lexer.pos.copy()
    is_float = False
    base = 10
    BASE_CHARSET = DEC_DIGITS + "."
    if lexer.current_char == "0":
        number += lexer.current_char
        lexer.advance()
        if lexer.current_char == "b":
            base = 2
            BASE_CHARSET = BIN_DIGITS
        elif lexer.current_char == "o":
            base = 8
            BASE_CHARSET = OCT_DIGITS
        elif lexer.current_char == "x":
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
                    lexer.pos.ind -= 1
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
    if lexer.current_char == ".":
        token = TokType.DOT_DOT
        lexer.advance()
        if lexer.current_char == ".":
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
            char_val = "'"
        elif lexer.current_char == '"':
            char_val = '"'
        elif lexer.current_char == "\\":
            char_val = "\\"
        elif lexer.current_char == "0":
            char_val = "\0"
        else:
            IllegalCharacterError(
                Range(pos_start, lexer.pos), f"No character '\{lexer.current_char}'"
            ).throw()
    lexer.advance()
    if lexer.current_char != "'":
        ExpectedCharError(
            Range(pos_start, lexer.pos), f'No matching "\'" in char'
        ).throw()
    lexer.advance()
    return Token(TokType.CHAR, Range(pos_start, lexer.pos), ord(char_val))


class StrToken(Token):
    def __init__(self, range: Range, token_groups, _value: str = None):
        super().__init__(TokType.STR, range, _value)
        self.token_groups = token_groups


def make_str(lexer: Lexer):
    pos_start = lexer.pos.copy()
    str_val = ""
    escape_next = False
    token_groups = []
    lexer.advance()
    while lexer.current_char != None and (lexer.current_char != '"' or escape_next):
        if lexer.current_char == "\\":
            escape_next = True
            if (
                len(lexer.text) > lexer.pos.ind + 1
                and lexer.text[lexer.pos.ind + 1] != "$"
            ):
                str_val += lexer.current_char
            lexer.advance()
        elif not escape_next and lexer.current_char == "$":
            token_group = []
            str_val += lexer.current_char
            lexer.advance()
            if lexer.current_char == "(":
                lexer.advance()
                open_par_num = 0
                while lexer.current_char != None and (
                    lexer.current_char != ")" or open_par_num != 0
                ):
                    if lexer.current_char == "(":
                        open_par_num += 1
                    if lexer.current_char == ")":
                        open_par_num -= 1
                    next_tok = lexer.tokenizeNext()
                    if next_tok != None:
                        token_group.append(next_tok)
                lexer.advance()
            else:
                token_group.append(lexer.tokenizeNext())
            token_groups.append(token_group)
        else:
            str_val += lexer.current_char
            escape_next = False
            lexer.advance()
    if lexer.current_char != '"':
        ExpectedCharError(
            Range(pos_start, lexer.pos), f"None matching '\"' in string"
        ).throw()
    lexer.advance()
    # Unstable code since codes.escape_decode is not a public python function and may be deprecated in the next future
    # Source from: https://stackoverflow.com/questions/4020539/process-escape-sequences-in-a-string-in-python
    return StrToken(
        Range(pos_start, lexer.pos),
        token_groups,
        codecs.escape_decode(bytes(str_val, "utf-8"))[0].decode("utf-8"),
    )


machine_word_size = struct.calcsize("P") * 8
sizet_ty = ir.IntType(machine_word_size)
void_ty = ir.VoidType()
double_ty = ir.DoubleType()
byte_ty = ir.IntType(8)
byteptr_ty = byte_ty.as_pointer()
int32_ty = ir.IntType(32)
llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()
target_machine = llvm.Target.from_default_triple().create_target_machine()
target_data = target_machine.target_data


def get_instrinsic(name):
    m = Context.current_llvm_module
    if m.globals.get(name, None):
        return m.globals.get(name)
    elif name == "printf":
        return m.declare_intrinsic(
            "printf", (), ir.FunctionType(int32_ty, [byteptr_ty], var_arg=True)
        )
    elif name == "atoi":
        return m.declare_intrinsic("atoi", (), ir.FunctionType(int32_ty, [byteptr_ty]))
    elif name == "atof":
        return m.declare_intrinsic("atof", (), ir.FunctionType(double_ty, [byteptr_ty]))
    elif name == "pow":
        return m.declare_intrinsic("llvm.pow", [double_ty])
    elif name == "malloc":
        return m.declare_intrinsic(
            "malloc", (), ir.FunctionType(byteptr_ty, [sizet_ty])
        )
    elif name == "realloc":
        return m.declare_intrinsic(
            "realloc", (), ir.FunctionType(byteptr_ty, [byteptr_ty, sizet_ty])
        )
    elif name == "memcpy":
        return m.declare_intrinsic("llvm.memcpy", [byteptr_ty, byteptr_ty, sizet_ty])
    elif name == "memmove":
        return m.declare_intrinsic("llvm.memmove", [byteptr_ty, byteptr_ty, sizet_ty])
    elif name == "memset":
        return m.declare_intrinsic("llvm.memset", [byteptr_ty, sizet_ty])
    elif name == "va_start":
        return m.declare_intrinsic(
            "llvm.va_start", (), ir.FunctionType(void_ty, [byteptr_ty])
        )
    elif name == "va_end":
        return m.declare_intrinsic(
            "llvm.va_end", (), ir.FunctionType(void_ty, [byteptr_ty])
        )
    elif name == "free":
        return m.declare_intrinsic(
            "free", (), ir.FunctionType(ir.VoidType(), [byteptr_ty])
        )
    elif name == "memcmp":
        return m.declare_intrinsic(
            "memcmp", (), ir.FunctionType(sizet_ty, [byteptr_ty, byteptr_ty, sizet_ty])
        )
    elif name == "sprintf":
        return m.declare_intrinsic(
            "sprintf",
            (),
            ir.FunctionType(sizet_ty, [byteptr_ty, byteptr_ty], var_arg=True),
        )
    elif name == "snprintf":
        return m.declare_intrinsic(
            "snprintf",
            (),
            ir.FunctionType(sizet_ty, [byteptr_ty, sizet_ty, byteptr_ty], var_arg=True),
        )


def new_ctx(*args):
    filename = pathlib.Path(args[0]).name
    global_ctx = Context(*args)
    Context.current_llvm_module = ir.Module(name=filename)
    Context.current_llvm_module.triple = llvm.get_default_triple()
    Context.current_llvm_module.data_layout = str(target_data)
    return global_ctx


def create_array_buffer(builder: ir.IRBuilder, elems):
    elm_ty = elems[0].llvmtype
    mem = FloMem.halloc(builder, elm_ty, FloInt(len(elems)))
    for index, elem in enumerate(elems):
        mem.store_at_index(builder, elem, FloInt(index, 32))
    return mem


def strict_mem_compare(builder: ir.IRBuilder, op, mem1, mem2):
    my_int = FloInt(builder.ptrtoint(mem1.value, ir.IntType(32)), 32)
    other_int = FloInt(builder.ptrtoint(mem2.value, ir.IntType(32)), 32)
    return my_int.cmp(builder, op, other_int)


def is_string_object(type):
    return isinstance(type, FloObject) and type.referer.name == "string"


def str_to_int(builder: ir.IRBuilder, str_obj, bits):
    val = builder.call(get_instrinsic("atoi"), [str_obj.cval(builder)])
    return FloInt(val, 32).cast_to(builder, FloInt(None, bits))


def str_to_float(builder, str_obj, bits):
    val = builder.call(get_instrinsic("atof"), [str_obj.cval(builder)])
    return FloFloat(val, 64).cast_to(builder, FloFloat(None, bits))


def create_string_object(builder, args):
    str_class = FloClass.classes.get("string")
    return FloObject(str_class).construct(builder, args)


class FloType:
    llvmtype: ir.Type = None
    value: ir.Value

    def __init__(self, value) -> None:
        self.fmt = "%s"
        self.value = value

    def cast_to():
        raise Exception("undefined cast")

    @staticmethod
    def str():
        return "any"

    def store_value_to_ref(self, ref):
        if not ref.mem:
            ref.mem = FloMem.salloc(ref.builder, self.llvmtype, name=ref.name)
        ref.mem.store_at_index(ref.builder, self)

    def load_value_from_ref(self, ref):
        return self.__class__(ref.mem.load_at_index(ref.builder))

    def construct(self, builder: ir.IRBuilder, args):
        ptr = FloPointer(self)
        ptr.mem = FloMem.halloc(builder, self.llvmtype, args[0])
        return ptr

    def cval(self, _):
        return self.value


class FloNull(FloType):
    def __init__(self, base_type: FloType) -> None:
        if base_type:
            self.llvmtype = base_type.llvmtype
        self.base_type = base_type
        zero = ir.Constant(ir.IntType(32), 0)
        if isinstance(base_type, FloInt):
            self.floval = FloInt(0, base_type.bits)
        elif isinstance(base_type, FloFloat):
            self.floval = FloFloat(0.0, base_type.bits)
        elif (
            isinstance(base_type, FloPointer)
            or isinstance(base_type, FloObject)
            or isinstance(base_type, FloFunc)
            or isinstance(base_type, FloArray)
        ):
            self.floval = base_type.new_with_val(zero.inttoptr(base_type.llvmtype))
        else:
            print(base_type)

    def cast_to(self, builder: ir.IRBuilder, other_type):
        return self.floval.cast_to(builder, other_type)

    @property
    def value(self):
        return self.floval.value

    def store_value_to_ref(self, ref):
        return self.floval.store_value_to_ref(ref)

    def load_value_from_ref(self, ref):
        return self.floval.load_value_from_ref(ref)

    def __eq__(self, __o: object) -> bool:
        if self.floval:
            return self.floval.__eq__(__o)
        return False


class FloVoid(FloType):
    llvmtype = ir.VoidType()

    def to_string(builder):
        mem = FloConst.create_global_str("null")
        length = FloInt(4)
        return create_string_object(builder, [mem, length])

    def str(self) -> str:
        return "void"

    def cast_to(self, builder, new_ty):
        if is_string_object(new_ty):
            return self.to_string(builder)
        else:
            raise Exception("undefined case")

    def cval(self, _):
        return FloConst.create_global_str("null").value

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, FloVoid)


class FloConst:
    # TODO be careful with arrays and strings
    str_constants = {}

    def __init__(self, value) -> None:
        self.value = value

    def load(self, visitor):
        return visitor.visit(self.value)

    @staticmethod
    def create_global_str(value: str):
        if FloConst.str_constants.get(value) != None:
            str_ptr = FloConst.str_constants.get(value)
        else:
            encoded = (value + "\0").encode(
                encoding="utf-8", errors="xmlcharrefreplace"
            )
            byte_array = bytearray(encoded)
            str_val = ir.Constant(ir.ArrayType(byte_ty, len(byte_array)), byte_array)
            name = f"str.{len(FloConst.str_constants.keys())}"
            str_ptr = ir.GlobalVariable(Context.current_llvm_module, str_val.type, name)
            str_ptr.linkage = "private"
            str_ptr.global_constant = True
            str_ptr.unnamed_addr = True
            str_ptr.initializer = str_val
            str_ptr = str_ptr.bitcast(byteptr_ty)
            FloConst.str_constants[value] = str_ptr
        flo_ptr = FloMem(str_ptr)
        flo_ptr.is_constant = True
        return flo_ptr


class FloInt(FloType):
    def __init__(self, value: int, bits=machine_word_size):
        assert bits > 0 and bits < 128
        self.bits = bits
        if isinstance(value, int):
            self.value = ir.Constant(self.llvmtype, int(value))
        else:
            if isinstance(value, ir.Value):
                self.bits = value.type.width
            self.value = value

    def new_with_val(self, value):
        return FloInt(value, self.bits)

    @property
    def fmt(self):
        return "%s" if self.bits == 1 else "%d"

    def cval(self, builder):
        return self.value if self.bits != 1 else self.bool_value(builder)

    @property
    def llvmtype(self):
        return ir.IntType(self.bits)

    @property
    def is_constant(self):
        return isinstance(self.value, ir.Constant) and self.value.constant

    def add(self, builder: ir.IRBuilder, num):
        return FloInt(builder.add(self.value, num.value))

    def sub(self, builder: ir.IRBuilder, num):
        return FloInt(builder.sub(self.value, num.value))

    def mul(self, builder: ir.IRBuilder, num):
        return FloInt(builder.mul(self.value, num.value))

    def div(self, builder: ir.IRBuilder, num):
        return FloFloat(builder.sdiv(self.value, num.value))

    def mod(self, builder: ir.IRBuilder, num):
        return FloInt(builder.srem(self.value, num.value))

    def cmp(self, builder: ir.IRBuilder, op, num):
        if not isinstance(num, FloInt):
            return FloInt(0, 1)
        return FloInt(builder.icmp_signed(op, self.value, num.value), 1)

    def neg(self, builder: ir.IRBuilder):
        self.value = builder.neg(self.value)
        return self

    def pow(self, builder: ir.IRBuilder, num):
        fv = self.cast_to(builder, FloFloat).pow(
            builder, num.cast_to(builder, FloFloat)
        )
        return fv

    def sl(self, builder: ir.IRBuilder, num):
        return FloInt(builder.shl(self.value, num.value))

    def sr(self, builder: ir.IRBuilder, num):
        return FloInt(builder.ashr(self.value, num.value))

    def or_(self, builder: ir.IRBuilder, num):
        return FloInt(builder.or_(self.value, num.value))

    def and_(self, builder: ir.IRBuilder, num):
        return FloInt(builder.and_(self.value, num.value))

    def not_(self, builder: ir.IRBuilder):
        return FloInt(builder.not_(self.value))

    def xor(self, builder: ir.IRBuilder, num):
        return FloInt(builder.xor(self.value, num.value))

    def cast_to(self, builder: ir.IRBuilder, type):
        if isinstance(type, FloInt):
            return self.bitcast(builder, type.bits)
        elif isinstance(type, FloFloat):
            return FloFloat(builder.sitofp(self.value, type.llvmtype))
        elif is_string_object(type):
            return self.to_string(builder)
        else:
            raise Exception(f"Unhandled type cast: int to {type.str()}")

    def bitcast(self, builder: ir.IRBuilder, bits: int):
        llvmtype = ir.IntType(bits)
        if bits != self.bits:
            if self.is_constant:
                return FloInt(self.value.constant, bits)
            cast_fnc = builder.trunc if bits < self.bits else builder.zext
            return FloInt(cast_fnc(self.value, llvmtype), bits)
        else:
            return self

    def bool_value(self, builder: ir.IRBuilder):
        return builder.select(
            self.value,
            FloConst.create_global_str("true").value,
            FloConst.create_global_str("false").value,
        )

    def to_bool_string(self, builder: ir.IRBuilder):
        value = self.bool_value(builder)
        lenval = builder.select(self.value, FloInt(4).value, FloInt(5).value)
        mem = FloMem(value)
        return create_string_object(builder, [mem, FloInt(lenval)])

    def to_string(self, builder: ir.IRBuilder):
        if self.bits == 1:
            return self.to_bool_string(builder)
        sprintf = get_instrinsic("sprintf")
        str_buff = FloMem.halloc_size(builder, FloInt(10))
        fmt = FloConst.create_global_str(self.fmt)
        strlen = FloInt(builder.call(sprintf, [str_buff.value, fmt.value, self.value]))
        return create_string_object(builder, [str_buff, strlen])

    def str(self) -> str:
        if self.bits == 1:
            return "bool"
        elif self.bits == machine_word_size:
            return "int"
        else:
            return f"i{self.bits}"

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, FloNull):
            return __o == self
        return isinstance(__o, FloInt) and __o.bits == self.bits

    def new(self, value):
        return FloInt(value, self.bits)


class FloFloat(FloType):
    def __init__(self, value: Union[float, ir.Constant], bits=machine_word_size):
        assert bits == 16 or bits == 32 or bits == 64
        self.bits = bits
        self.fmt = "%.1lf"
        if isinstance(value, float):
            self.value = ir.Constant(self.llvmtype, value)
        else:
            self.value = value

    def new_with_val(self, value):
        return FloFloat(value, self.bits)

    def cval(self, _):
        return self.value

    def add(self, builder: ir.IRBuilder, num):
        return FloFloat(builder.fadd(self.value, num.value))

    def sub(self, builder: ir.IRBuilder, num):
        return FloFloat(builder.fsub(self.value, num.value))

    def mul(self, builder: ir.IRBuilder, num):
        return FloFloat(builder.fmul(self.value, num.value))

    def div(self, builder: ir.IRBuilder, num):
        return FloFloat(builder.fdiv(self.value, num.value))

    def cmp(self, builder: ir.IRBuilder, op, num):
        if not isinstance(num, FloFloat):
            return FloInt(0, 1)
        return FloInt(builder.fcmp_ordered(op, self.value, num.value), 1)

    def mod(self, builder: ir.IRBuilder, num):
        return FloFloat(builder.frem(self.value, num.value))

    def pow(self, builder: ir.IRBuilder, num):
        v = builder.call(get_instrinsic("pow"), [self.value, num.value])
        return FloFloat(v)

    def neg(self, builder: ir.IRBuilder):
        self.value = builder.fneg(self.value)
        return self

    def cast_to(self, builder: ir.IRBuilder, type):
        if isinstance(type, FloInt):
            return FloInt(builder.fptosi(self.value, type.llvmtype))
        if isinstance(type, FloFloat) and type.bits == self.bits:
            return self
        elif isinstance(type, FloFloat) and type.bits != self.bits:
            return FloFloat(builder.bitcast(self.value, type.llvmtype), type.bits)
        elif is_string_object(type):
            return self.to_string(builder)
        else:
            raise Exception(f"Unhandled type cast: float to {type.str()}")

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, FloNull):
            return __o == self
        return isinstance(__o, FloFloat) and __o.bits == self.bits

    def to_string(self, builder: ir.IRBuilder):
        sprintf = get_instrinsic("sprintf")
        str_buff = FloMem.halloc_size(builder, FloInt(1))
        fmt = FloConst.create_global_str(self.fmt)
        length = builder.call(sprintf, [str_buff.value, fmt.value, self.value])
        return create_string_object(builder, [str_buff, FloInt(length)])

    def new(self, value):
        return FloFloat(value, self.bits)

    def str(self) -> str:
        if self.bits == machine_word_size:
            return "float"
        else:
            return f"float{self.bits}"

    @property
    def is_constant(self):
        return isinstance(self.value, ir.Constant)

    @property
    def llvmtype(self):
        if self.bits == 16:
            return ir.HalfType()
        elif self.bits == 32:
            return ir.FloatType()
        else:
            return ir.DoubleType()


class FloMem:
    def __init__(self, value):
        assert not isinstance(value, FloMem)
        if value:
            assert isinstance(value.type, ir.PointerType) or isinstance(
                value.type, ir.ArrayType
            )
        self.is_constant = False
        self.value = value

    def get_pointer_at_index(self, builder: ir.IRBuilder, *indices: FloInt):
        if len(list(indices)) == 0:
            return self
        ir_indices = [index.value for index in indices]
        return FloMem(builder.gep(self.value, ir_indices, True))

    def store_at_index(self, builder: ir.IRBuilder, floval: FloType, *indices: FloInt):
        idx_ptr = self
        if indices:
            idx_ptr = self.get_pointer_at_index(builder, *indices)
        builder.store(floval.value, idx_ptr.value)

    def load_at_index(self, builder: ir.IRBuilder, *indices: FloInt):
        ptr = self
        if indices:
            ptr = self.get_pointer_at_index(builder, *indices)
        loaded_value = builder.load(ptr.value)
        if loaded_value.type.is_pointer or isinstance(loaded_value.type, ir.ArrayType):
            return FloMem(loaded_value)
        return loaded_value

    def compare(builder: ir.IRBuilder, mem1, mem2, size: FloInt):
        args = [mem1.value, mem2.value, size.value]
        return builder.call(get_instrinsic("memcmp"), args)

    def cmp(self, builder: ir.IRBuilder, mem2, size: FloInt):
        res = FloMem.compare(builder, self, mem2, size)
        return FloInt(res).cmp(builder, "==", FloInt(0))

    def copy_to(self, builder: ir.IRBuilder, dest, size: FloInt):
        args = [dest.value, self.value, size.value, FloInt(0, 1).value]
        builder.call(get_instrinsic("memcpy"), args)

    def free(self, builder: ir.IRBuilder):
        if FloMem.heap_allocations.get(self.uuid) != None:
            i8_ptr = builder.bitcast(self.value, byteptr_ty)
            builder.call(get_instrinsic("free"), [i8_ptr])

    @staticmethod
    def bitcast(builder: ir.IRBuilder, mem, ir_type: ir.Type):
        return FloMem(builder.bitcast(mem.value, ir_type))

    @staticmethod
    def halloc_size(builder: ir.IRBuilder, size: FloInt, name=""):
        malloc_fnc = get_instrinsic("malloc")
        return FloMem(builder.call(malloc_fnc, [size.value], name))

    @staticmethod
    def halloc(builder: ir.IRBuilder, ir_type: ir.Type, size: FloInt = None, name=""):
        abi_size = FloInt(ir_type.get_abi_size(target_data))
        if size:
            size = size.mul(builder, abi_size)
        else:
            size = abi_size
        mem_obj = FloMem.halloc_size(builder, size, name)
        return FloMem.bitcast(builder, mem_obj, ir_type.as_pointer())

    @staticmethod
    def salloc(builder: ir.IRBuilder, ir_type: ir.Type, size: FloInt = None, name=""):
        size_value = size.value if size else None
        ty_ptr = builder.alloca(ir_type, size=size_value, name=name)
        return FloMem(ty_ptr)

    @staticmethod
    def realloc(builder: ir.IRBuilder, mem, size: FloInt):
        realloc = get_instrinsic("realloc")
        size = size.mul(builder, FloInt(mem.value.type.get_abi_size(target_data)))
        old_mem = FloMem.bitcast(builder, mem, byteptr_ty).value
        new_mem = builder.call(realloc, [old_mem, size.value])
        return FloMem.bitcast(builder, FloMem(new_mem), mem.value.type)


class FloPointer(FloType):
    def __init__(self, flotype: FloType) -> None:
        self.is_constant = False
        self.elm_type = flotype
        self.mem = None
        self.methods = {}
        self.init_methods()
        self.fmt = "0x%X"

    def new_with_val(self, value):
        return self.new(FloMem(value))

    def init_methods(self):
        resize_call = lambda builder, args: self.new(
            FloMem.realloc(builder, self.mem, args[0])
        )
        resize_fnc = FloInlineFunc(resize_call, [FloInt(None)], self)
        copy_call = lambda builder, args: self.new(
            args[0].mem.copy_to(builder, self.mem, args[1])
        )
        copy_fnc = FloInlineFunc(copy_call, [self, FloInt(None)], self)
        cmp_call = lambda builder, args: FloInt(
            FloMem.compare(builder, self.mem, args[0].mem, args[1])
        )
        cmp_fnc = FloInlineFunc(cmp_call, [self, FloInt(None)], FloInt(None))
        self.methods["resize"] = resize_fnc
        self.methods["copy_from"] = copy_fnc
        self.methods["compare"] = cmp_fnc

    @property
    def value(self):
        return self.mem.value

    @value.setter
    def value(self, n_val):
        self.mem = FloMem(n_val)

    @property
    def llvmtype(self):
        return self.elm_type.llvmtype.as_pointer()

    def store_value_to_ref(self, ref):
        if not ref.mem:
            ref.mem = FloMem.salloc(ref.builder, self.llvmtype, name=ref.name)
        if self.mem:
            ref.mem.store_at_index(ref.builder, self)

    def load_value_from_ref(self, ref):
        return self.new(ref.mem.load_at_index(ref.builder))

    def new(self, mem):
        ptr = FloPointer(self.elm_type)
        ptr.mem = mem
        return ptr

    def get_element(self, builder: ir.IRBuilder, index: FloInt):
        mem = self.mem.get_pointer_at_index(builder, index)
        return self.elm_type.load_value_from_ref(
            FloRef(builder, self.elm_type, "", mem)
        )

    def add(self, builder: ir.IRBuilder, increment: FloInt):
        return self.new(self.mem.get_pointer_at_index(builder, increment))

    def sub(self, builder: ir.IRBuilder, increment: FloInt):
        return self.new(self.mem.get_pointer_at_index(builder, increment.neg(builder)))

    def set_element(self, builder: ir.IRBuilder, index: FloInt, value: FloType):
        self.mem.store_at_index(builder, value, index)
        return value

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, FloNull):
            return __o == self
        return isinstance(__o, FloPointer) and self.elm_type == __o.elm_type

    def get_pointer_at_index(self, builder: ir.IRBuilder, index: FloInt):
        return self.new(self.mem.get_pointer_at_index(builder, index))

    def cast_to(self, builder: ir.IRBuilder, type):
        if isinstance(type, FloObject):
            return type.new_with_val(
                FloMem.bitcast(builder, self.mem, type.llvmtype).value
            )
        if isinstance(type, FloFunc):
            return type.new_with_val(
                FloMem.bitcast(builder, self.mem, type.llvmtype).value
            )
        if not isinstance(type, FloPointer):
            raise Exception("Cannot cast")
        else:
            return FloPointer(type.elm_type).new(
                FloMem.bitcast(builder, self.mem, type.llvmtype)
            )

    def cmp(self, builder: ir.IRBuilder, op, other):
        return strict_mem_compare(builder, op, self.mem, other.floval.mem)

    def str(self):
        return f"{self.elm_type.str()}*"


class FloArray:
    def __init__(self, values, arr_len=None):
        self.mem = None
        if isinstance(values, list):
            self.is_constant = True
            self.elm_type = values[0] if len(values) > 0 else None
            self.is_constant = FloArray.is_constant(values)
            self.elems = values
            self.len = FloInt(len(values)) if arr_len == None else arr_len
        else:
            self.len: FloInt = arr_len
            self.elems = values
            self.is_constant = False

    def new_with_val(self, value):
        arr = FloArray(self.value, self.len)
        arr.value = value
        return arr

    @staticmethod
    def is_constant(values):
        for v in values:
            if not v.is_constant:
                return False
        return True

    def cmp(self, builder, op, other):
        if isinstance(other, FloArray):
            # TODO:
            return FloInt(0, 1)
        else:
            return FloInt(0, 1)

    @property
    def value(self):
        if self.mem:
            return self.mem.value
        if self.elems:
            return ir.Constant(self.llvmtype.pointee, [elm.value for elm in self.elems])
        return None

    @value.setter
    def value(self, new_value):
        assert new_value
        self.mem = FloMem(new_value)

    def get_index(self, idx: FloInt):
        return (
            [FloInt(0, idx.bits), idx]
            if not self.mem or isinstance(self.mem.value.type, ir.ArrayType)
            else [idx]
        )

    def store_value_to_ref(self, ref):
        builder: ir.IRBuilder = ref.builder
        if not ref.mem and not self.mem:
            if self.len.is_constant:
                ty = ir.ArrayType(self.elm_type.llvmtype, self.len.value.constant)
                ref.mem = FloMem.salloc(builder, ty, name=ref.name)
            else:
                # call stacksave and stackrestore at the end of function call.
                self.mem = FloMem.salloc(
                    builder, self.llvmtype.pointee, self.len, ref.name
                )
        if self.is_constant and self.len.is_constant and self.value:
            ref.mem.store_at_index(builder, FloType(self.value), FloInt(0))
        elif self.elems and len(self.elems) > 0:
            next_idx = self.get_index(FloInt(0, 32))
            tmp_mem = self.mem or ref.mem
            for floval in self.elems:
                tmp_mem = tmp_mem.get_pointer_at_index(builder, *next_idx)
                next_idx = [FloInt(1, 32)]
                floval.store_value_to_ref(FloRef(builder, floval, "", tmp_mem))

    @property
    def llvmtype(self):
        return self.elm_type.llvmtype.as_pointer()

    def load_value_from_ref(self, ref):
        loaded_array = FloArray(self.elems, self.len)
        if ref.mem:
            if ref.mem.value.type.pointee.is_pointer:
                loaded_array.mem = ref.mem.load_at_index(ref.builder, FloInt(0, 32))
            else:
                loaded_array.mem = ref.mem.get_pointer_at_index(
                    ref.builder, *self.get_index(FloInt(0, 32))
                )
        elif not ref.mem:
            loaded_array.mem = self.mem
        loaded_array.elm_type = self.elm_type
        return loaded_array

    def get_element(self, builder: ir.IRBuilder, index: FloInt):
        value = self.mem.get_pointer_at_index(builder, *self.get_index(index))
        return self.elm_type.load_value_from_ref(
            FloRef(builder, self.elm_type, "", value)
        )

    def set_element(self, builder: ir.IRBuilder, index, value):
        self.mem.store_at_index(builder, value, *self.get_index(index))
        return value

    def get_pointer_at_index(self, builder: ir.IRBuilder, index):
        mem = self.mem.get_pointer_at_index(builder, *self.get_index(index))
        return FloPointer(self.elm_type).new(mem)

    def str(self) -> str:
        return f"{self.elm_type.str()}[]"

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, FloNull):
            return __o == self
        return isinstance(__o, FloArray) and self.elm_type == __o.elm_type


class FloRef:
    def __init__(self, builder: ir.IRBuilder, referee: FloType, name="", mem=None):
        self.builder = builder
        self.name = name
        self.mem = mem
        if not mem:
            self.store(referee)
        self.referee = referee

    def load(self):
        return self.referee.load_value_from_ref(self)

    def store(self, referee: FloType):
        referee.store_value_to_ref(self)


class FloFunc(FloType):
    defined_methods = {}

    def get_llvm_type(self):
        arg_types = [arg_ty.llvmtype for arg_ty in self.arg_types]
        if self.var_args:
            arg_types.append(FloInt.llvmtype)
        return ir.FunctionType(
            self.return_type.llvmtype, arg_types, var_arg=self.var_args
        )

    def cval(self, builder):
        return FloConst.create_global_str(self.str()).value

    def new_with_val(self, value):
        fnc = FloFunc(self.arg_types, self.return_type, self.name)
        fnc.value = value
        return fnc

    def __init__(self, arg_types: List, return_type, name, var_args=False):
        self.fmt = "%s"
        self.return_type = return_type
        self.var_args = False
        if var_args:
            self.var_arg_ty = arg_types.pop()
            self.var_args = True
        self.arg_types = arg_types
        if name:
            self.context = None
            current_module = Context.current_llvm_module
            self.value = ir.Function(current_module, self.get_llvm_type(), name)
            fn_entry_block = self.value.append_basic_block()
            self.builder = ir.IRBuilder(fn_entry_block)

    @staticmethod
    def declare(arg_types: List, return_type, name, var_args=False):
        n_arg_types = [arg_ty.llvmtype for arg_ty in arg_types]
        fn_ty = ir.FunctionType(return_type.llvmtype, n_arg_types, var_arg=var_args)
        val = Context.current_llvm_module.declare_intrinsic(name, (), fn_ty)
        new_fnc = FloFunc(arg_types, return_type, None)
        new_fnc.value = val
        return new_fnc

    def call(self, builder: ir.IRBuilder, args):
        passed_args = [arg.value for arg in args]
        rt_value = builder.call(self.value, passed_args)
        if isinstance(self.return_type, FloVoid):
            return FloVoid(rt_value)
        return self.return_type.new_with_val(rt_value)

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, FloNull):
            return __o == self
        if not isinstance(__o, FloFunc):
            return False
        if self.return_type != __o.return_type:
            return False
        if len(self.arg_types) != len(__o.arg_types):
            return False
        for argty1, argty2 in zip(self.arg_types, __o.arg_types):
            if argty1 != argty2:
                return False
        return True

    def get_local_ctx(self, parent_ctx, arg_names: List[str]):
        self.arg_names = arg_names
        local_ctx = parent_ctx.create_child(self.value.name)
        for arg_name, arg_type, arg_value in zip(
            arg_names, self.arg_types, self.value.args
        ):
            if isinstance(arg_type, FloFunc):
                arg_type = FloFunc(
                    arg_type.arg_types, arg_type.return_type, None, arg_type.var_args
                )
            arg_type.value = arg_value
            local_ctx.set(arg_name, FloRef(self.builder, arg_type, arg_name))
        self.context = local_ctx
        return local_ctx

    def ret(self, value):
        if isinstance(value, FloVoid):
            self.builder.ret_void()
        else:
            self.builder.ret(value.value)

    @property
    def llvmtype(self):
        return self.get_llvm_type().as_pointer()

    def load_value_from_ref(self, ref):
        loaded_func = FloFunc(self.arg_types, self.return_type, None, self.var_args)
        loaded_func.value = ref.mem.load_at_index(ref.builder).value
        return loaded_func

    def str(self) -> str:
        arg_list = ", ".join([arg.str() for arg in self.arg_types])
        return f"({arg_list}) => {self.return_type.str()}"

    def cmp(self, builder: ir.IRBuilder, op, other):
        if op in ("==", "!="):
            if isinstance(other, FloFunc):
                return strict_mem_compare(
                    builder, op, FloMem(self.value), FloMem(other.value)
                )
            elif isinstance(other, FloNull):
                return strict_mem_compare(
                    builder, op, FloMem(self.value), FloMem(other.floval.value)
                )
        return FloInt(0, 1)


vtable_offset = 1


class FloClass:
    classes = {}

    def __init__(self, name, parent=None, init_body=True) -> None:
        self.name = name
        self.methods: dict[str, FloMethod] = {}
        self.properties: dict[str, FloType] = {}
        self.static_members = {}
        self.value = ir.global_context.get_identified_type(name)
        self.constructor = None
        self.vtable_ty = None
        self.vtable_data = None
        self.parent = parent
        if parent:
            self.properties.update(parent.properties)
            if init_body:
                self.methods.update(self.parent.methods)
        if init_body:
            FloClass.classes[name] = self

    def get_method(self, method_name: str):
        current = self
        while current.methods.get(method_name) == None and current.parent:
            current = current.parent
        return current.methods.get(method_name)

    def add_method(self, fnc: FloFunc, name=""):
        # prepend this in args
        if not isinstance(fnc, FloMethod):
            assert isinstance(fnc, FloFunc)
            self.static_members[name] = fnc
            return
        assert fnc.value
        if fnc.value.name == self.name + "_constructor":
            self.constructor = fnc
        else:
            self.methods[fnc.original_name] = fnc

    def add_property(self, name, value):
        self.properties[name] = value

    @property
    def llvmtype(self):
        return self.value.as_pointer()

    def init_value(self):
        self.vtable_ty = ir.global_context.get_identified_type(f"{self.name}_vtable_ty")
        vtable_tys = [method.llvmtype for method in self.methods.values()]
        self.vtable_ty.set_body(*vtable_tys)
        fields = [value.llvmtype for value in self.properties.values()]
        fields.insert(0, self.vtable_ty.as_pointer())
        self.value.set_body(*fields)
        self.vtable_data = ir.GlobalVariable(
            Context.current_llvm_module, self.vtable_ty, f"{self.name}_vtable_data"
        )
        self.vtable_data.initializer = ir.Constant(
            self.vtable_ty, [func.value for func in self.methods.values()]
        )

    def constant_init(self, builder: ir.IRBuilder, args):
        # TODO: Decide when to allocate on the heap
        ptr_value = FloMem.halloc(builder, self.value)
        is_constant = FloArray.is_constant(args)
        if is_constant:
            constant = ir.Constant(
                self.value, [self.vtable_data] + [arg.value for arg in args]
            )
            ptr_value.store_at_index(builder, FloType(constant))
        else:
            self.set_vtable_data(builder, ptr_value)
            for index, arg in enumerate(args):
                ptr_value.store_at_index(
                    builder, arg, FloInt(0, 32), FloInt(index + vtable_offset, 32)
                )
        obj = FloObject(self)
        obj.mem = ptr_value
        return obj

    def set_vtable_data(self, builder: ir.IRBuilder, mem: FloMem):
        mem.store_at_index(
            builder, FloType(self.vtable_data), FloInt(0, 32), FloInt(0, 32)
        )

    def has_parent(self, other):
        current = self
        while current.parent:
            if current.parent.name == other.name:
                return True
            current = current.parent
        return False


class FloMethod(FloFunc):
    def __init__(
        self,
        arg_types: List,
        return_type,
        name,
        var_args=False,
        class_: FloClass = None,
    ):
        if name:
            if class_:
                self.original_name = name
                name = class_.name + "_" + name
                arg_types.insert(0, FloObject(class_))
                self.class_ = class_
            self.current_object = None
        else:
            self.value = var_args
            var_args = None
        super().__init__(arg_types, return_type, name, var_args)

    @staticmethod
    def declare(arg_types: List, return_type, name, var_args, class_):
        n_arg_types = [FloObject(class_).llvmtype] + [
            arg_ty.llvmtype for arg_ty in arg_types
        ]
        name = class_.name + "_" + name
        fn_ty = ir.FunctionType(return_type.llvmtype, n_arg_types, var_arg=var_args)
        val = Context.current_llvm_module.declare_intrinsic(name, (), fn_ty)
        new_fnc = FloMethod(arg_types, return_type, None, val, class_)
        return new_fnc

    def call(self, builder: ir.IRBuilder, args):
        return super().call(builder, [self.current_object] + args)

    def get_local_ctx(self, parent_ctx, arg_names: List[str]):
        local_ctx = super().get_local_ctx(parent_ctx, ["this"] + arg_names)
        if self.class_ and self.class_.parent:
            parent_constructor = self.class_.parent.constructor
            if parent_constructor:
                parent_constructor.current_object = (
                    local_ctx.get("this")
                    .load()
                    .cast_to(self.builder, FloObject(self.class_.parent))
                )
                local_ctx.set("super", parent_constructor)
        return local_ctx

    def load_value_from_ref(self, ref):
        loaded_func = FloMethod(
            self.arg_types,
            self.return_type,
            None,
            ref.mem.load_at_index(ref.builder).value,
            None,
        )
        loaded_func.current_object = self.current_object
        return loaded_func


class FloObject(FloType):
    def __init__(self, referer: FloClass) -> None:
        self.fmt = "%s"
        self.referer = referer
        self.is_constant = False
        self.mem = None
        assert referer
        if not isinstance(referer.value, str):
            self.llvmtype = referer.value.as_pointer()

    def new_with_val(self, value):
        obj = FloObject(self.referer)
        obj.mem = FloMem(value)
        return obj

    def store_value_to_ref(self, ref):
        if not ref.mem:
            ref.mem = FloMem.salloc(ref.builder, self.llvmtype, name=ref.name)
        if self.mem:
            ref.mem.store_at_index(ref.builder, self)

    def load_value_from_ref(self, ref):
        loaded_object = FloObject(self.referer)
        loaded_object.mem = ref.mem.load_at_index(ref.builder)
        return loaded_object

    def in_(self, builder: ir.IRBuilder, member):
        in_method = self.get_method("__in__", builder)
        return in_method.call(builder, [member])

    @property
    def value(self):
        return self.mem.value

    @value.setter
    def value(self, n_val):
        self.mem = FloMem(n_val)

    def get_property_mem(self, builder: ir.IRBuilder, name):
        property_index = list(self.referer.properties.keys()).index(name)
        return self.mem.get_pointer_at_index(
            builder, FloInt(0, 32), FloInt(property_index + vtable_offset, 32)
        )

    def get_property(self, builder: ir.IRBuilder, name):
        try:
            mem = self.get_property_mem(builder, name)
        except Exception:
            return self.get_method(name, builder)
        property_value: FloType = self.referer.properties.get(name)
        return property_value.load_value_from_ref(
            FloRef(builder, property_value, "", mem)
        )

    def get_method(self, name, builder: ir.IRBuilder) -> Union[FloMethod, None]:
        assert isinstance(self.referer, FloClass)
        method_index = -1
        current = self.referer
        while current:
            method = current.methods.get(name)
            if method != None:
                method_index = list(self.referer.methods.keys()).index(name)
                break
            else:
                current = current.parent
        method_value: FloType = self.referer.methods.get(name)
        if method_value == None:
            # 1: Find where this goes wrong
            self.referer = FloClass.classes.get(self.referer.name)
            current = self.referer
            method_value = current.methods.get(name)
            if method_value == None:
                return None
            # 1: Fix it.
            method_index = list(current.methods.keys()).index(name)
        if list(current.methods.keys())[0] == "constructor":
            method_index -= 1
        vtable_ptr = self.mem.load_at_index(builder, FloInt(0, 32), FloInt(0, 32))
        method_mem = vtable_ptr.get_pointer_at_index(
            builder, FloInt(0, 32), FloInt(method_index, 32)
        )
        flomethod = method_value.load_value_from_ref(
            FloRef(builder, method_value, "", method_mem)
        )
        flomethod.current_object = (
            self.cast_to(builder, FloObject(current))
            if self.referer != current
            else self
        )
        return flomethod

    def sl(self, builder: ir.IRBuilder, other: FloType):
        return self.get_method("__sl__", builder).call(builder, [other])

    def set_property(self, builder: ir.IRBuilder, name: str, value: FloType):
        property_index = list(self.referer.properties.keys()).index(name)
        mem = self.mem.get_pointer_at_index(
            builder, FloInt(0, 32), FloInt(property_index + vtable_offset, 32)
        )
        value.store_value_to_ref(FloRef(builder, value, "", mem))
        return value

    def construct(self, builder: ir.IRBuilder, args):
        self.mem = FloMem.halloc(builder, self.referer.value)
        self.referer.set_vtable_data(builder, self.mem)
        if self.referer.constructor:
            self.referer.constructor.current_object = self
            self.referer.constructor.call(builder, args)
        return self

    def str(self) -> str:
        return (
            self.referer.name
            if isinstance(self.referer, FloClass)
            else self.referer.value
        )

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FloNull):
            return other == self
        if not other:
            return False
        if not isinstance(other, FloObject):
            return False
        self_classname = self.referer.name
        other_classname = other.referer.name
        return self_classname == other_classname

    def add(self, builder: ir.IRBuilder, other):
        method = self.get_method("__add__", builder)
        return method.call(builder, [other])

    def cmp(self, builder: ir.IRBuilder, op, other):
        should_not = op == "!="
        if isinstance(other, FloNull):
            return strict_mem_compare(builder, op, self.mem, other.floval.mem)
        if not isinstance(other, FloObject):
            return FloInt(0, 1)
        if op == "==" or op == "!=":
            eq_method = self.get_method("__eq__", builder)
            other_object: FloObject = other
            if eq_method:
                if len(eq_method.arg_types) > 0 and other_object.referer.has_parent(
                    eq_method.arg_types[0].referer
                ):
                    other_object = other_object.cast_to(builder, eq_method.arg_types[0])
                value = eq_method.call(builder, [other_object])
            else:
                return strict_mem_compare(builder, op, self.mem, other_object.mem)
            return value.not_(builder) if should_not else value

    def get_cast_method(self, type, builder):
        name = "__as_" + type.str() + "__"
        return self.get_method(name, builder)

    def cast_to(self, builder: ir.IRBuilder, type):
        if is_string_object(type):
            if is_string_object(self):
                return self
            if self.get_method("__as_string__", builder) == None:
                string = f"@{self.referer.name}"
                return create_string_object(
                    builder, [FloConst.create_global_str(string), FloInt(len(string))]
                )
        elif is_string_object(self):
            if isinstance(type, FloInt):
                return str_to_int(builder, self, type.bits)
            elif isinstance(type, FloFloat):
                return str_to_float(builder, self, type.bits)
        if isinstance(type, FloObject):
            # if(self.referer.has_parent(type.referer)): (Possibly unsafe with check on this line)
            casted_mem = FloMem.bitcast(builder, self.mem, type.llvmtype)
            newObj = FloObject(type.referer)
            newObj.mem = casted_mem
            return newObj
        method: FloMethod = self.get_cast_method(type, builder)
        if method != None:
            return method.call(builder, [])
        else:
            raise Exception("Cannot cast")

    def cval(self, builder: ir.IRBuilder):
        v = (
            self.cast_to(builder, FloObject(FloClass.classes.get("string")))
            .get_method("to_cstring", builder)
            .call(builder, [])
            .value
        )
        return v


class FloGeneric(FloObject):
    def __init__(self, referer: FloClass, constraints: List[FloType]) -> None:
        if isinstance(referer, Token):
            self.name = referer.value
        else:
            self.name = referer.name
        self.constraints = constraints
        super().__init__(referer)

    def str(self):
        if isinstance(self.referer, FloClass):
            return self.referer.name
        return (
            self.name
            + "<"
            + ", ".join([constraint.str() for constraint in self.constraints])
            + ">"
        )


class FloEnum(FloType):
    def __init__(self, elements: List[str]):
        self.elements = elements
        self.global_offset = 0

    def get_property(self, name: str) -> FloInt:
        index = self.elements.index(name) + self.global_offset
        return FloInt(index)

    def str(self):
        return "Enum"


class FloInlineFunc(FloFunc):
    def __init__(self, call, arg_types, return_type, var_args=False, defaults=[]):
        self.arg_types = arg_types
        self.name = ""
        self.return_type = return_type
        self.var_args = var_args
        self.defaults = defaults
        self.call_method = call

    def call(self, *kargs):
        assert self.call_method
        returned = self.call_method(*kargs)
        if returned != None:
            return returned
        else:
            return FloVoid(None)


class SymbolTable:
    def __init__(self):
        self.symbols = {}

    def get(self, name):
        return self.symbols.get(name, None)

    def set(self, name, value):
        self.symbols[name] = value

    def delete(self, name):
        del self.symbols[name]


class Context:
    current_llvm_module: ir.Module = None

    def __init__(self, display_name, parent=None):
        self.display_name = display_name
        if parent:
            assert parent.display_name != self.display_name
        self.parent: Context = parent
        self.symbol_table = SymbolTable()

    def copy(self):
        cp_ctx = Context(self.display_name)
        cp_ctx.symbol_table = self.symbol_table.copy()
        return cp_ctx

    def get(self, name):
        value = self.symbol_table.get(name)
        if value == None and self.parent:
            return self.parent.get(name)
        return value

    def set(self, name, value):
        self.symbol_table.set(name, value)

    def create_child(self, name):
        return Context(name, self)

    def get_values(self):
        return list(self.symbol_table.symbols.values())

    def delete(self, name):
        self.symbol_table.delete(name)

    def get_symbols(self):
        symbols = []
        current = self
        while current != None:
            symbols += list(current.symbol_table.symbols.keys())
            current = current.parent
        return symbols


class Visitor:
    def __init__(self, context: Context):
        self.context = context

    def visit(self, node):
        return node.accept(self)

    def visitIntNode(self, node):
        pass

    def visitFloatNode(self, node):
        pass

    def visitStrNode(self, node):
        pass

    def visitNumOpNode(self, node):
        pass

    def visitUnaryNode(self, node):
        pass

    def visitIncrDecrNode(self, node):
        pass

    def visitTernaryNode(self, node):
        pass

    def visitVarAccessNode(self, node):
        pass

    def visitStmtsNode(self, node):
        pass

    def visitMacroDeclarationNode(self, node):
        pass

    def visitVarDeclarationNode(self, node):
        pass

    def visitClassDeclarationNode(self, node):
        pass

    def visitGenericClassNode(self, node):
        pass

    def visitVarAssignNode(self, node):
        pass

    def visitIfNode(self, node):
        pass

    def visitForNode(self, node):
        pass

    def visitForEachNode(self, node):
        pass

    def visitWhileNode(self, node):
        pass

    def visitFncNode(self, node):
        pass

    def visitFncDefNode(self, node):
        pass

    def visitReturnNode(self, node):
        pass

    def visitContinueNode(self, node):
        pass

    def visitBreakNode(self, node):
        pass

    def visitFncCallNode(self, node):
        pass

    def visitPropertyAccessNode(self, node):
        pass

    def visitPropertyAssignNode(self, node):
        pass

    def visitMethodDeclarationNode(self, node):
        pass

    def visitPropertyDeclarationNode(self, node):
        pass

    def visitTypeNode(self, node):
        pass

    def visitTypeAliasNode(self, node):
        pass

    def visitArrayNode(self, node):
        pass

    def visitArrayAccessNode(self, node):
        pass

    def visitArrayAssignNode(self, node):
        pass

    def visitNewMemNode(self, node):
        pass

    def visitContinueNode(self, node):
        pass

    def visitImportNode(self, node):
        pass

    def visitCharNode(self, node):
        pass

    def visitEnumDeclarationNode(self, node):
        pass

    def visitRangeNode(self, node):
        pass


class Node:
    def __init__(self, range: Range):
        self.range = range
        self.expects = None

    def accept(self, _: Visitor):
        pass


class VarAccessNode(Node):
    def __init__(self, var_name: Token, range: Range):
        self.var_name = var_name
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitVarAccessNode(self)


class ArrayAccessNode(Node):
    def __init__(self, name: VarAccessNode, index: Node, range: Range):
        self.name = name
        self.index = index
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitArrayAccessNode(self)


class ArrayAssignNode(Node):
    def __init__(self, array: ArrayAccessNode, value: Node, range: Range):
        self.array = array
        self.value = value
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitArrayAssignNode(self)


class ArrayNode(Node):
    def __init__(self, elements: List[Node], range: Range):
        self.elements = elements
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitArrayNode(self)


class BreakNode(Node):
    def __init__(self, range: Range):
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitBreakNode(self)


class TernaryNode(Node):
    def __init__(self, cond: Node, is_true: Node, is_false: Node, range: Range):
        self.cond = cond
        self.is_true = is_true
        self.is_false = is_false
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitTernaryNode(self)


class TypeNode(Node):
    def __init__(self, type, range: Range):
        self.type = type
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitTypeNode(self)


class TypeAliasNode(Node):
    def __init__(self, identifier: Token, type: TypeNode, range: Range):
        self.identifier = identifier
        self.type = type
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitTypeAliasNode(self)


class VarAssignNode(Node):
    def __init__(self, var_name: Token, value: Node, range: Range):
        self.var_name = var_name
        self.value = value
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitVarAssignNode(self)


class StmtsNode(Node):
    def __init__(self, stmts: List[Node], range: Range):
        self.stmts = stmts
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitStmtsNode(self)


class ClassDeclarationNode(Node):
    def __init__(self, name: Token, parent: TypeNode, body: StmtsNode, range: Range):
        self.name = name
        self.parent = parent
        self.body = body
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitClassDeclarationNode(self)


class GenericClassNode(Node):
    def __init__(
        self,
        generic_constraints: List[Token],
        class_declaration: ClassDeclarationNode,
        range: Range,
    ):
        self.generic_constraints = generic_constraints
        self.class_declaration = class_declaration
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitGenericClassNode(self)


class MacroDeclarationNode(Node):
    def __init__(self, macro_name: Token, value: Node, range: Range):
        self.macro_name = macro_name
        self.value = value
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitMacroDeclarationNode(self)


class VarDeclarationNode(Node):
    def __init__(self, var_name: Token, type: TypeNode, value: Node, range: Range):
        self.var_name = var_name
        self.type = type
        self.value = value
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitVarDeclarationNode(self)


class ContinueNode(Node):
    def __init__(self, range: Range):
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitContinueNode(self)


class PropertyAccessNode(Node):
    def __init__(self, expr: Node, property: Token, range: Range):
        self.expr = expr
        self.property = property
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitPropertyAccessNode(self)


class FncCallNode(Node):
    def __init__(
        self,
        name: Union[VarAccessNode, PropertyAccessNode],
        args: List[Node],
        range: Range,
    ):
        self.name = name
        self.args = args
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitFncCallNode(self)


class PropertyAssignNode(Node):
    def __init__(self, expr: PropertyAccessNode, value: Node, range: Range):
        self.expr = expr
        self.value = value
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitPropertyAssignNode(self)


class FncNode(Node):
    def __init__(
        self,
        args: List[Tuple[Token, TypeNode, Node]],
        body: StmtsNode,
        is_variadic: bool,
        range: Range,
        return_type: TypeNode = None,
    ):
        self.args = args
        self.body = body
        super().__init__(range)
        self.is_variadic = is_variadic
        self.return_type = return_type

    def accept(self, visitor: Visitor):
        return visitor.visitFncNode(self)


class RangeNode(Node):
    def __init__(self, start: Node, end: Node, range: Range):
        self.start = start
        self.end = end
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitRangeNode(self)


class PropertyDeclarationNode(Node):
    def __init__(
        self, access_modifier: Token, property_name: Token, type: TypeNode, range: Range
    ):
        self.access_modifier = access_modifier
        self.property_name = property_name
        self.type = type
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitPropertyDeclarationNode(self)


class MethodDeclarationNode(Node):
    def __init__(
        self,
        access_modifier: Token,
        is_static: bool,
        method_name: Token,
        method_body: FncNode,
        range: Range,
    ):
        self.access_modifier = access_modifier
        self.is_static = is_static
        self.method_name = method_name
        self.method_body = method_body
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitMethodDeclarationNode(self)


class FncDefNode(Node):
    def __init__(self, func_name: Token, func_body: FncNode, range: Range):
        self.func_name = func_name
        self.func_body = func_body
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitFncDefNode(self)


class ForNode(Node):
    def __init__(self, init: Node, cond: Node, incr_decr: Node, stmt: StmtsNode, range):
        self.init = init
        self.cond = cond
        self.incr_decr = incr_decr
        self.stmt = stmt
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitForNode(self)


class ForEachNode(Node):
    def __init__(self, identifier: Token, iterator: Node, stmt: StmtsNode, range):
        self.identifier = identifier
        self.iterator = iterator
        self.stmt = stmt
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitForEachNode(self)


class IfNode(Node):
    def __init__(
        self, cases: List[Tuple[Node, StmtsNode]], else_case: StmtsNode, range: Range
    ) -> None:
        self.cases = cases
        self.else_case = else_case
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitIfNode(self)


class IncrDecrNode(Node):
    def __init__(
        self,
        id: Token,
        identifier: Union[VarAccessNode, ArrayAccessNode, PropertyAccessNode],
        ispre: bool,
        range: Range,
    ):
        self.id = id
        self.identifier = identifier
        self.ispre = ispre
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitIncrDecrNode(self)


class ImportNode(Node):
    def __init__(self, ids: List[Token], path: Token, range: Range):
        self.ids = ids
        self.path = path
        super().__init__(range)
        self.resolved_as = []

    def accept(self, visitor: Visitor):
        return visitor.visitImportNode(self)


class IntNode(Node):
    def __init__(self, tok: Token, range: Range):
        self.tok = tok
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitIntNode(self)


class CharNode(Node):
    def __init__(self, tok: Token, range: Range):
        self.tok = tok
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitCharNode(self)


class FloatNode(Node):
    def __init__(self, tok: Token, range: Range):
        self.tok = tok
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitFloatNode(self)


class NumOpNode(Node):
    def __init__(self, left_node: Node, op_tok: Token, right_node: Node, range: Range):
        self.left_node = left_node
        self.op = op_tok
        self.right_node = right_node
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitNumOpNode(self)


class ReturnNode(Node):
    def __init__(self, value: Node, range: Range):
        self.value = value
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitReturnNode(self)


class NewMemNode(Node):
    def __init__(self, type: TypeNode, args: List[Node], range: Range):
        self.type = type
        self.args = args
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitNewMemNode(self)


class StrNode(Node):
    def __init__(self, tok: Token, nodes: List[Node], range: Range):
        self.tok = tok
        self.nodes = nodes
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitStrNode(self)


class UnaryNode(Node):
    def __init__(self, op: Token, value: Node, range):
        self.op = op
        self.value = value
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitUnaryNode(self)


class WhileNode(Node):
    def __init__(self, cond: Node, stmt: StmtsNode, range: Range):
        self.cond = cond
        self.stmt = stmt
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitWhileNode(self)


class EnumDeclarationNode(Node):
    def __init__(self, name: Token, tokens: List[Token], range: Range):
        self.name = name
        self.tokens = tokens
        super().__init__(range)

    def accept(self, visitor: Visitor):
        return visitor.visitEnumDeclarationNode(self)


def str_to_flotype(str):
    if str == "int":
        return FloInt(None)
    if str == "float":
        return FloFloat(None)
    elif str == "void":
        return FloVoid(None)


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.current_tok = None
        self.current_i = -1
        self.advance()

    def advance(self):
        self.current_i += 1
        if self.current_i < len(self.tokens):
            self.current_tok = self.tokens[self.current_i]
        else:
            self.current_tok = self.tokens[-1]

    def peek(self):
        return self.tokens[
            self.current_i + 1 if self.current_i < len(self.tokens) else self.current_i
        ]

    def parse(self):
        res = self.stmts()
        if self.current_tok.type != TokType.EOF:
            SyntaxError(
                self.current_tok.range,
                f"Unexpected '{self.current_tok.type.value}', Expected '+', '-', '*' '/', '^' or an identifier",
            ).throw()
        return res

    def skip_new_lines(self) -> None:
        while self.current_tok.type == TokType.LN:
            self.advance()

    def stmts(self):
        stmts = []
        range_start = self.current_tok.range
        self.skip_new_lines()
        while (
            self.current_tok.type != TokType.RBRACE
            and self.current_tok.type != TokType.EOF
        ):
            stmt = self.stmt()
            stmts.append(stmt)
            self.skip_new_lines()
        return StmtsNode(stmts, Range.merge(range_start, self.current_tok.range))

    def block(self):
        self.skip_new_lines()
        if self.current_tok.type != TokType.LBRACE:
            return self.expression()
        self.advance()
        if self.current_tok.type == TokType.RBRACE:
            self.advance()
            return []
        stmts = self.expressions()
        if self.current_tok.type != TokType.RBRACE:
            SyntaxError(self.current_tok.range, "Expected '}'").throw()
        self.advance()
        return stmts

    def stmt(self):
        self.skip_new_lines()
        tok = self.current_tok
        if tok.isKeyword("import"):
            return self.import_stmt()
        if tok.isKeyword("const"):
            return self.macro_declaration()
        if tok.isKeyword("type"):
            return self.type_alias()
        if tok.isKeyword("class"):
            return self.class_declaration()
        if tok.isKeyword("enum"):
            return self.enum_declaration()
        elif tok.isKeyword("fnc"):
            return self.fnc_def_stmt()
        else:
            SyntaxError(tok.range, f"Unexpected '{tok.value}'").throw()

    def expressions(self):
        expressions = []
        range_start = self.current_tok.range
        self.skip_new_lines()
        while (
            self.current_tok.type != TokType.RBRACE
            and self.current_tok.type != TokType.EOF
        ):
            stmt = self.expression()
            expressions.append(stmt)
            self.skip_new_lines()
        return StmtsNode(expressions, Range.merge(range_start, self.current_tok.range))

    def expression(self):
        tok = self.current_tok
        if tok.isKeyword("if"):
            return self.if_stmt()
        elif tok.isKeyword("for"):
            return self.for_stmt()
        elif tok.isKeyword("while"):
            return self.while_stmt()
        elif tok.inKeywordList(("return", "continue", "break")):
            return self.change_flow_stmt()
        elif tok.isKeyword("let"):
            return self.var_declaration()
        return self.expr()

    def import_stmt(self):
        range_start = self.current_tok.range
        self.advance()
        ids = []
        path = ""
        if self.current_tok.type == TokType.IDENTIFER:
            ids = self.identifier_list()
            if not self.current_tok.isKeyword("in"):
                SyntaxError(self.current_tok.range, "Expected keyword 'in'").throw()
            self.advance()
        if self.current_tok.type != TokType.STR:
            SyntaxError(self.current_tok.range, "Expected a string").throw()
        path = self.current_tok
        self.advance()
        return ImportNode(ids, path, Range.merge(range_start, path.range))

    def if_stmt(self) -> IfNode:
        range_start = self.current_tok.range
        self.advance()
        cases = []
        else_case = None
        cond = self.expr()
        stmts = self.block()
        self.skip_new_lines()
        cases.append((cond, stmts))
        if self.current_tok.isKeyword("else"):
            self.advance()
            if self.current_tok.isKeyword("if"):
                resCases = self.if_stmt()
                cases += resCases.cases
                else_case = resCases.else_case
            else:
                stmts = self.block()
                else_case = stmts
        range_end = (else_case or cases[len(cases) - 1][0]).range
        return IfNode(cases, else_case, Range.merge(range_start, range_end))

    def macro_declaration(self) -> MacroDeclarationNode:
        range_start = self.current_tok.range
        self.advance()
        name_tok = self.current_tok
        self.advance()
        if self.current_tok.type != TokType.EQ:
            SyntaxError(self.current_tok.range, "Expected '='").throw()
        self.advance()
        value_node = self.expr()
        node_range = Range.merge(range_start, self.current_tok.range)
        return MacroDeclarationNode(name_tok, value_node, node_range)

    def var_declaration(self) -> VarDeclarationNode:
        self.advance()
        range_start = self.current_tok.range
        type = None
        if self.current_tok.type != TokType.IDENTIFER:
            SyntaxError(range_start, "Expected and identifier").throw()
        name_tok = self.current_tok
        self.advance()
        if self.current_tok.type == TokType.COL:
            self.advance()
            type = self.composite_type()
        if self.current_tok.type == TokType.EQ:
            self.advance()
            value_node = self.expr()
            node_range = Range.merge(range_start, self.current_tok.range)
        else:
            value_node = None
            node_range = Range.merge(range_start, self.current_tok.range)
        return VarDeclarationNode(name_tok, type, value_node, node_range)

    def type_alias(self):
        range_start = self.current_tok.range
        self.advance()
        identifier = self.current_tok
        self.advance()
        if self.current_tok.type != TokType.EQ:
            SyntaxError(self.current_tok.range, "Expected =").throw()
        self.advance()
        type = self.composite_type()
        node_range = Range.merge(range_start, type.range)
        return TypeAliasNode(identifier, type, node_range)

    def generic_constraint(self):
        tok = self.current_tok
        if tok.type != TokType.IDENTIFER:
            SyntaxError(tok.range, "Expected an identifer").throw()
        self.advance()
        return tok

    def generic_constraints(self):
        constraints = [self.generic_constraint()]
        while self.current_tok.type == TokType.COMMA:
            self.advance()
            constraints.append(self.generic_constraint())
        return constraints

    def class_declaration(self) -> Union[ClassDeclarationNode, GenericClassNode]:
        self.advance()
        range_start = self.current_tok.range
        if self.current_tok.type != TokType.IDENTIFER:
            SyntaxError(range_start, "Expected and identifier").throw()
        name = self.current_tok
        self.advance()
        constraints = None
        if self.current_tok.type == TokType.LT:
            self.advance()
            constraints = self.generic_constraints()
            if self.current_tok.type != TokType.GT:
                SyntaxError(self.current_tok.range, "Expected a '>'").throw()
            self.advance()
        parent = None
        if self.current_tok.type == TokType.LPAR:
            self.advance()
            parent = self.prim_type()
            if self.current_tok.type != TokType.RPAR:
                SyntaxError(self.current_tok.range, "Expected a matching ')'").throw()
            self.advance()
        class_body = self.class_block()
        node_range = Range.merge(range_start, self.current_tok.range)
        node = ClassDeclarationNode(name, parent, class_body, node_range)
        if constraints != None:
            node = GenericClassNode(constraints, node, node_range)
        return node

    def class_block(self):
        self.skip_new_lines()
        if self.current_tok.type != TokType.LBRACE:
            SyntaxError(self.current_tok.range, "Expected '{'").throw()
        self.advance()
        statements = []
        range_start = self.current_tok.range
        while self.current_tok.type != TokType.RBRACE:
            self.skip_new_lines()
            statements.append(self.class_stmt())
            self.skip_new_lines()
        if self.current_tok.type != TokType.RBRACE:
            SyntaxError(self.current_tok.range, "Expected '}'").throw()
        node_range = Range.merge(range_start, self.current_tok.range)
        self.advance()
        return StmtsNode(statements, node_range)

    def class_stmt(self):
        access_modifier = None
        if self.current_tok.inKeywordList(["public", "private", "protected"]):
            access_modifier = self.current_tok
            self.advance()
        if self.current_tok.type != TokType.IDENTIFER:
            SyntaxError(self.current_tok.range, "Expected an Identifer").throw()
        name = self.current_tok
        self.advance()
        if self.current_tok.type == TokType.COL:
            self.advance()
            property_type = self.composite_type()
            node_range = Range.merge(name.range, property_type.range)
            return PropertyDeclarationNode(
                access_modifier, name, property_type, node_range
            )
        elif self.current_tok.type == TokType.LPAR:
            is_static = True
            next_token = self.peek()
            if next_token.type == TokType.IDENTIFER and next_token.value == "this":
                self.advance()
                if self.peek().type == TokType.COMMA:
                    self.advance()
                is_static = False
            method_body = self.function_body()
            node_range = Range.merge(name.range, method_body.range)
            return MethodDeclarationNode(
                access_modifier, is_static, name, method_body, node_range
            )
        else:
            SyntaxError(
                self.current_tok.range,
                "Expected a property declaration or a method declaration",
            ).throw()

    def enum_declaration(self) -> EnumDeclarationNode:
        self.advance()
        range_start = self.current_tok.range
        token_list = []
        if self.current_tok.type != TokType.IDENTIFER:
            SyntaxError(self.current_tok.range, "Expected an Identifier").throw()
        name = self.current_tok
        self.advance()
        if self.current_tok.type != TokType.LBRACE:
            SyntaxError(self.current_tok.range, "Expected '{'").throw()
        self.advance()
        self.skip_new_lines()
        while self.current_tok.type == TokType.IDENTIFER:
            token_list.append(self.current_tok)
            self.advance()
            self.skip_new_lines()
        if self.current_tok.type != TokType.RBRACE:
            SyntaxError(self.current_tok.range, "Expected '}'").throw()
        self.advance()
        node_range = Range.merge(range_start, self.current_tok.range)
        return EnumDeclarationNode(name, token_list, node_range)

    def for_stmt(self) -> ForNode:
        self.advance()
        init = None
        range_start = self.current_tok.range
        if self.current_tok.isKeyword("let"):
            init = self.var_declaration()
        else:
            init = self.expr()
        if self.current_tok.isKeyword("in"):
            self.advance()
            it = self.expr()
            stmts = self.block()
            return ForEachNode(
                init, it, stmts, Range.merge(range_start, self.current_tok.range)
            )
        if self.current_tok.type != TokType.SEMICOL:
            SyntaxError(self.current_tok.range, "Expected ';'").throw()
        self.advance()
        cond = self.expr()
        if self.current_tok.type != TokType.SEMICOL:
            SyntaxError(self.current_tok.range, "Expected ';'").throw()
        self.advance()
        incr_decr = self.expr()
        stmts = self.block()
        return ForNode(
            init, cond, incr_decr, stmts, Range.merge(range_start, stmts.range)
        )

    def while_stmt(self):
        self.advance()
        cond = self.expr()
        stmts = self.block()
        return WhileNode(cond, stmts, Range.merge(cond.range, stmts.range))

    def fnc_def_stmt(self):
        self.advance()
        range_start = self.current_tok.range
        if self.current_tok.type != TokType.IDENTIFER:
            SyntaxError(self.current_tok.range, "Expected Identifier").throw()
        var_name = self.current_tok
        self.advance()
        if self.current_tok.type != TokType.LPAR:
            SyntaxError(self.current_tok.range, "Expected '('").throw()
        function_body = self.function_body()
        return FncDefNode(
            var_name, function_body, Range.merge(range_start, function_body.range)
        )

    def function_body(self):
        self.advance()
        range_start = self.current_tok.range
        args, is_var_arg = self.arg_list()
        if self.current_tok.type != TokType.RPAR:
            SyntaxError(self.current_tok.range, "Expected ')'").throw()
        self.advance()
        return_type = None
        if self.current_tok.type == TokType.COL:
            self.advance()
            return_type = self.composite_type()
        body = None
        if self.current_tok.type == TokType.LBRACE:
            body = self.block()
        return FncNode(
            args,
            body,
            is_var_arg,
            Range.merge(range_start, self.current_tok.range),
            return_type,
        )

    def identifier_list(self):
        args = []
        if (
            self.current_tok.type == TokType.IDENTIFER
            or self.current_tok.type == TokType.MACRO_IDENTIFIER
        ):
            id = self.current_tok
            self.advance()
            args.append(id)
            while self.current_tok.type == TokType.COMMA:
                self.advance()
                if (
                    self.current_tok.type != TokType.IDENTIFER
                    and self.current_tok.type != TokType.MACRO_IDENTIFIER
                ):
                    SyntaxError(
                        self.current_tok.range, "Expected an Identifier"
                    ).throw()
                args.append(self.current_tok)
                self.advance()
        return args

    def arg_item(self):
        id = self.current_tok
        default_val = None
        self.advance()
        if self.current_tok.type == TokType.EQ:
            self.advance()
            default_val = self.expr()
            return (id, None, default_val)
        if self.current_tok.type != TokType.COL:
            SyntaxError(id.range, "Expected ':' or '=' after identifier").throw()
        self.advance()
        type_id = self.composite_type()
        if self.current_tok.type == TokType.EQ:
            self.advance()
            default_val = self.expr()
        return (id, type_id, default_val)

    def arg_list(self):
        args = []
        is_var_arg = False
        if self.current_tok.type == TokType.DOT_DOT_DOT:
            is_var_arg = True
            self.advance()
        if self.current_tok.type == TokType.IDENTIFER:
            args.append(self.arg_item())
            while self.current_tok.type == TokType.COMMA and not is_var_arg:
                self.advance()
                if self.current_tok.type == TokType.DOT_DOT_DOT:
                    is_var_arg = True
                    self.advance()
                if self.current_tok.type != TokType.IDENTIFER:
                    SyntaxError(
                        self.current_tok.range, "Expected an Identifier"
                    ).throw()
                args.append(self.arg_item())
        return args, is_var_arg

    def change_flow_stmt(self):
        range_start = self.current_tok.range
        if self.current_tok.isKeyword("return"):
            self.advance()
            expr = None
            if self.current_tok.type not in (TokType.LN, TokType.EOF, TokType.RBRACE):
                expr = self.expr()

            range = (
                range_start if expr is None else Range.merge(range_start, expr.range)
            )
            return ReturnNode(expr, range)
        elif self.current_tok.isKeyword("continue"):
            self.advance()
            return ContinueNode(range_start)
        elif self.current_tok.isKeyword("break"):
            self.advance()
            return BreakNode(range_start)

    def expr(self):
        return self.num_op(
            self.ternary_expr,
            ((TokType.KEYWORD, "as"), (TokType.KEYWORD, "is")),
            self.composite_type,
        )

    def ternary_expr(self):
        cond = self.bit_expr()
        if self.current_tok.type != TokType.QUES:
            return cond
        self.advance()
        true_expr = self.expr()
        if self.current_tok.type != TokType.COL:
            SyntaxError(self.current_tok.range, f"Expected ':' but").throw()
        self.advance()
        false_expr = self.expr()
        return TernaryNode(
            cond, true_expr, false_expr, Range.merge(cond.range, false_expr.range)
        )

    def bit_expr(self):
        return self.num_op(
            self.comp_expr,
            (
                (TokType.KEYWORD, "and"),
                (TokType.KEYWORD, "or"),
                (TokType.KEYWORD, "xor"),
                (TokType.KEYWORD, "in"),
                TokType.SL,
                TokType.SR,
            ),
        )

    def comp_expr(self):
        if self.current_tok.type == TokType.NOT:
            tok = self.current_tok
            self.advance()
            expr = self.comp_expr()
            return UnaryNode(tok, expr, Range.merge(tok.range, expr.range))
        return self.num_op(
            self.arith_expr,
            (
                TokType.NEQ,
                TokType.EEQ,
                TokType.LT,
                TokType.LEQ,
                TokType.GT,
                TokType.GTE,
            ),
        )

    def arith_expr(self):
        return self.num_op(self.range_expr, (TokType.PLUS, TokType.MINUS))

    def range_expr(self):
        node = None
        if self.current_tok.type != TokType.DOT_DOT:
            node = self.arith_expr1()
            start_range = node.range
        else:
            start_range = self.current_tok.range
        if self.current_tok.type == TokType.DOT_DOT:
            self.advance()
            end = self.arith_expr1()
            node = RangeNode(node, end, Range.merge(start_range, end.range))
        return node

    def arith_expr1(self):
        return self.num_op(
            self.unary_expr, (TokType.MULT, TokType.DIV, TokType.MOD, TokType.POW)
        )

    def unary_expr(self):
        tok = self.current_tok
        if tok.type in (TokType.PLUS, TokType.MINUS, TokType.AMP):
            self.advance()
            f = self.unary_expr()
            return UnaryNode(tok, f, Range.merge(tok.range, f.range))
        elif tok.type in (TokType.PLUS_PLUS, TokType.MINUS_MINUS):
            self.advance()
            f = self.unary_expr()
            return IncrDecrNode(
                tok, f, True, Range.merge(tok.range, self.current_tok.range)
            )
        elif tok.isKeyword("new"):
            return self.new_memexpr()
        return self.unary_expr1()

    def new_memexpr(self):
        tok = self.current_tok
        self.advance()
        type = self.composite_type()
        args = []
        end_range = self.current_tok.range
        if self.current_tok.type != TokType.LPAR:
            SyntaxError(self.current_tok.range, "Expected (").throw()
        self.advance()
        if self.current_tok.type != TokType.RPAR:
            args = self.expr_list()
        if self.current_tok.type != TokType.RPAR:
            SyntaxError(self.current_tok.range, "Expected )").throw()
        end_range = self.current_tok.range
        self.advance()
        node_range = Range.merge(tok.range, end_range)
        return NewMemNode(type, args, node_range)

    def unary_expr1(self):
        node = self.expr_value_op()
        if self.current_tok.type in (TokType.PLUS_PLUS, TokType.MINUS_MINUS) and (
            isinstance(node, VarAccessNode)
            or isinstance(node, ArrayAccessNode)
            or isinstance(node, PropertyAccessNode)
        ):
            tok = self.current_tok
            self.advance()
            return IncrDecrNode(
                tok, node, False, Range.merge(tok.range, self.current_tok.range)
            )
        return node

    def expr_list(self):
        args = []
        expr = self.expr()
        args.append(expr)
        while self.current_tok.type == TokType.COMMA:
            self.advance()
            expr = self.expr()
            args.append(expr)
        return args

    def assign_part(self, node: Node):
        self.advance()
        value = self.expr()
        node_range = Range.merge(node.range, value.range)
        if isinstance(node, VarAccessNode):
            return VarAssignNode(node.var_name, value, node_range)
        if isinstance(node, ArrayAccessNode):
            return ArrayAssignNode(node, value, node_range)
        elif isinstance(node, PropertyAccessNode):
            return PropertyAssignNode(node, value, node_range)
        else:
            SyntaxError(
                node.range, "Unexpected expression expected identifier or array"
            ).throw()

    def expr_value_op(self):
        range_start = self.current_tok.range
        node = self.expr_value()
        while (
            self.current_tok.type == TokType.LBRACKET
            or self.current_tok.type == TokType.LPAR
            or self.current_tok.type == TokType.DOT
        ):
            if self.current_tok.type == TokType.DOT:
                node = self.property_access(node)
            elif self.current_tok.type == TokType.LBRACKET:
                self.advance()
                expr = self.expr()
                if self.current_tok.type != TokType.RBRACKET:
                    SyntaxError(self.current_tok.range, "Expected ']'").throw()
                end_range = self.current_tok.range
                self.advance()
                node = ArrayAccessNode(node, expr, Range.merge(node.range, end_range))

            elif self.current_tok.type == TokType.LPAR:
                self.advance()
                args = []
                if self.current_tok.type != TokType.RPAR:
                    args = self.expr_list()

                if self.current_tok.type != TokType.RPAR:
                    SyntaxError(self.current_tok.range, "Expected ')'").throw()
                end_range = self.current_tok.range
                self.advance()
                node = FncCallNode(node, args, Range.merge(node.range, end_range))
        if self.current_tok.type == TokType.EQ:
            return self.assign_part(node)
        node.range = Range.merge(range_start, node.range)
        return node

    def expr_value(self):
        tok = self.current_tok
        if tok.type == TokType.INT:
            self.advance()
            return IntNode(tok, tok.range)
        if tok.type == TokType.FLOAT:
            self.advance()
            return FloatNode(tok, tok.range)
        if tok.type == TokType.CHAR:
            self.advance()
            return CharNode(tok, tok.range)
        elif tok.type == TokType.STR:
            self.advance()
            nodes = []
            for group in tok.token_groups:
                tmp_parser = Parser(group)
                nodes.append(tmp_parser.expr())
            return StrNode(tok, nodes, tok.range)
        elif tok.type == TokType.IDENTIFER:
            self.advance()
            return VarAccessNode(tok, tok.range)
        elif tok.type == TokType.LPAR:
            self.advance()
            exp = self.expr()
            if self.current_tok.type == TokType.RPAR:
                self.advance()
                return exp
            SyntaxError(self.current_tok.range, "Expected ')'").throw()
        elif tok.type == TokType.LBRACKET:
            self.advance()
            list = []
            if self.current_tok.type != TokType.RBRACKET:
                list = self.expr_list()

                if self.current_tok.type != TokType.RBRACKET:
                    SyntaxError(self.current_tok.range, "Expected ']'").throw()
            end_range = self.current_tok.range
            self.advance()
            return ArrayNode(list, Range.merge(tok.range, end_range))
        SyntaxError(tok.range, f"Expected an expression value before '{tok}'").throw()

    def property_access(self, expr):
        self.advance()
        ident = self.current_tok
        node_range = ident.range
        expr = PropertyAccessNode(expr, ident, node_range)
        if ident.type != TokType.IDENTIFER:
            SyntaxError(node_range, "Expected an Identifier").throw()
        self.advance()
        return expr

    def prim_type(self):
        tok = self.current_tok
        self.advance()
        if tok.isKeyword("bool"):
            type = FloInt(None, 1)
            return TypeNode(type, tok.range)
        elif tok.isKeyword("int"):
            type = FloInt(None)
            return TypeNode(type, tok.range)
        elif tok.isKeyword("i4"):
            type = FloInt(None, 4)
            return TypeNode(type, tok.range)
        elif tok.isKeyword("i8"):
            type = FloInt(None, 8)
            return TypeNode(type, tok.range)
        elif tok.isKeyword("i16"):
            type = FloInt(None, 16)
            return TypeNode(type, tok.range)
        elif tok.isKeyword("i32"):
            type = FloInt(None, 32)
            return TypeNode(type, tok.range)
        elif tok.isKeyword("i64"):
            type = FloInt(None, 64)
            return TypeNode(type, tok.range)
        elif tok.isKeyword("i128"):
            type = FloInt(None, 128)
            return TypeNode(type, tok.range)
        elif tok.isKeyword("float"):
            type = FloFloat(None)
            return TypeNode(type, tok.range)
        elif tok.isKeyword("f16"):
            type = FloFloat(None, 16)
            return TypeNode(type, tok.range)
        elif tok.isKeyword("f32"):
            type = FloFloat(None, 32)
            return TypeNode(type, tok.range)
        elif tok.isKeyword("f64"):
            type = FloFloat(None, 64)
            return TypeNode(type, tok.range)
        elif tok.type == TokType.IDENTIFER:
            type = FloObject(tok)
            if self.current_tok.type == TokType.LT:
                self.advance()
                arg_list = self.type_list()
                type = FloGeneric(tok, arg_list)
                if (
                    self.current_tok.type != TokType.GT
                    and self.current_tok.type != TokType.SR
                ):
                    SyntaxError(self.current_tok.range, "Expected '>'").throw()
                if self.current_tok.type == TokType.GT:
                    self.advance()
                else:
                    self.current_tok.type = TokType.GT
            return TypeNode(type, tok.range)

    def type_list(self):
        types = [self.composite_type()]
        while self.current_tok.type == TokType.COMMA:
            self.advance()
            types.append(self.composite_type())
        return types

    def fnc_type(self):
        range_start = self.current_tok.range
        self.advance()
        arg_types = []
        if self.current_tok.type != TokType.RPAR:
            arg_types = self.type_list()
            if self.current_tok.type != TokType.RPAR:
                SyntaxError(self.current_tok.range, "Expected ')'").throw()
        self.advance()
        if self.current_tok.type != TokType.ARROW:
            SyntaxError(self.current_tok.range, "Expected '=>'").throw()
        self.advance()
        type = FloInlineFunc(None, arg_types, self.composite_type())
        return TypeNode(type, Range.merge(range_start, type.return_type.range))

    def composite_type(self):
        tok = self.current_tok
        type = None
        if (
            tok.inKeywordList(
                (
                    "int",
                    "i4",
                    "i8",
                    "i16",
                    "i32",
                    "i64",
                    "i128",
                    "float",
                    "f16",
                    "f32",
                    "f64",
                    "bool",
                )
            )
            or tok.type == TokType.IDENTIFER
            or tok.type == TokType.LBRACE
        ):
            type = self.prim_type()
        elif tok.type == TokType.LPAR:
            return self.fnc_type()
        while (
            self.current_tok.type == TokType.MULT
            or self.current_tok.type == TokType.LBRACKET
        ):
            if self.current_tok.type == TokType.MULT:
                end_range = self.current_tok.range
                self.advance()
                type = TypeNode(FloPointer(type), Range.merge(type.range, end_range))
            else:
                self.advance()
                if self.current_tok.type == TokType.RBRACKET:
                    end_range = self.current_tok.range
                    self.advance()
                    type = TypeNode(
                        FloGeneric(Token(TokType.IDENTIFER, None, "Array"), [type]),
                        Range.merge(type.range, end_range),
                    )
                    continue
                size = self.expr()
                if self.current_tok.type != TokType.RBRACKET:
                    if self.current_tok.type != TokType.RBRACKET:
                        SyntaxError(self.current_tok.range, "Expected ']'").throw()
                end_range = self.current_tok.range
                self.advance()
                arr_ty = FloArray(None, size)
                arr_ty.elm_type = type
                type = TypeNode(arr_ty, Range.merge(type.range, end_range))
        if type:
            return type
        else:
            SyntaxError(tok.range, "Expected type definition").throw()

    def num_op(self, func_a, toks, func_b=None):
        if func_b == None:
            func_b = func_a
        left_node = func_a()
        while (
            self.current_tok.type in toks
            or (self.current_tok.type, self.current_tok.value) in toks
        ):
            op_tok = self.current_tok
            self.advance()
            if self.current_tok.type == TokType.EQ:
                assign_node = self.assign_part(left_node)
                node_range = Range.merge(left_node.range, assign_node.range)
                num_op_node = NumOpNode(
                    left_node, op_tok, assign_node.value, assign_node.value.range
                )
                assign_node.value = num_op_node
                assign_node.range = node_range
                return assign_node
            else:
                right_node = func_b()
                left_node = NumOpNode(
                    left_node,
                    op_tok,
                    right_node,
                    Range.merge(left_node.range, right_node.range),
                )
        return left_node


cached_files = {}


def get_ast_from_file(filename, range=None):
    if not path.isfile(filename):
        IOError(range, f"File '{filename}' does not exist").throw()
    cache_value = cached_files.get(filename)
    if cache_value != None:
        return cache_value
    with open(filename, "r") as file:
        src_code = file.read()
        lexer = Lexer(filename, src_code)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        cached_files[filename] = ast
        return ast


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return path.join(sys._MEIPASS, relative_path)
    return path.join(
        path.abspath(pathlib.Path(__file__).parent.resolve()), relative_path
    )


class NodesFindResult:
    def __init__(self, resolved: List[Node], unresolved: List[str]):
        self.resolved = resolved
        self.unresolved = unresolved


class BlockTy(Enum):
    class_ = "class"
    func = "function"


class Block:
    def __init__(self, name: str, ty: BlockTy):
        self.name = name
        self.type = ty


class NodeFinder(Visitor):
    def __init__(self, context: Context):
        super().__init__(context)
        self.block_in = None
        self.dependency_map: dict[str, List[str]] = {}

    @staticmethod
    def get_abs_path(m_path, current_file):
        abs_path = ""
        if m_path[:5] == "@flo/":
            stddir = resource_path("flolib/packages")
            abs_path = path.join(stddir, m_path[5:])
        else:
            abs_path = path.join(path.dirname(current_file), m_path)
        if path.isdir(abs_path):
            abs_path += "/" + abs_path.split("/")[-1]
        if abs_path.split(".")[-1] != "flo":
            abs_path += ".flo"
        return abs_path

    def resolve_dependencies(self, names: List[str], ignore: List[str]):
        unresolved = []
        resolved_nodes = []
        for name in names:
            if name in ignore:
                continue
            resolved_node = self.context.get(name)
            if resolved_node == None:
                unresolved.append(name)
            else:
                dependencies_for_name = self.dependency_map.get(name)
                if dependencies_for_name != None and len(dependencies_for_name) != 0:
                    dependency_nodes, unresolved_names = self.resolve_dependencies(
                        dependencies_for_name, ignore
                    )
                    resolved_nodes += dependency_nodes
                    unresolved += unresolved_names
                ignore.append(name)
                resolved_nodes.append(resolved_node)
        return resolved_nodes, unresolved

    def find(
        self,
        names_to_find: List[str],
        resolved_names: List[str],
        range: Range,
        imported_modules=[],
    ):
        module_path = NodeFinder.get_abs_path(self.context.display_name, range.start.fn)
        self.imported_modules = imported_modules + [range.start.fn, module_path]
        self.module_path = module_path
        ast = get_ast_from_file(self.module_path, range)
        if len(names_to_find) == 0:
            return NodesFindResult([ast], [])
        self.ignore = resolved_names
        self.visit(ast)
        resolved_nodes, unresolved_names = self.resolve_dependencies(
            names_to_find, resolved_names
        )
        not_found_names = list(
            filter(lambda name: name in names_to_find, unresolved_names)
        )
        if len(not_found_names) > 0:
            NameError(
                range,
                f"Could not find {', '.join(not_found_names)} in {self.context.display_name}",
            ).throw()
        return NodesFindResult(resolved_nodes, not_found_names)

    def visitNumOpNode(self, node: NumOpNode):
        self.visit(node.left_node)
        self.visit(node.right_node)

    def visitStmtsNode(self, node: StmtsNode):
        for stmt in node.stmts:
            self.visit(stmt)

    def visitFncNode(self, node: FncNode):
        for (_, ty, defval) in node.args:
            if ty:
                self.visit(ty)
            if defval:
                self.visit(defval)
        if node.body:
            self.visit(node.body)
        if node.return_type:
            self.visit(node.return_type)

    def visitFncDefNode(self, node: FncDefNode):
        fnc_name = node.func_name.value
        if fnc_name in self.ignore:
            return
        self.context.set(fnc_name, node)
        self.context = self.context.create_child(fnc_name)
        self.local_vars = []
        self.dependency_map[fnc_name] = []
        self.block_in = Block(fnc_name, BlockTy.func)
        self.visit(node.func_body)
        self.context = self.context.parent
        self.local_vars = []
        self.block_in = None

    def visitMethodDeclarationNode(self, node: MethodDeclarationNode):
        self.visit(node.method_body)

    def visitPropertyDeclarationNode(self, node: PropertyDeclarationNode):
        self.visit(node.type)

    def visitVarAssignNode(self, node: VarAssignNode):
        var_name = node.var_name.value
        if var_name in self.ignore:
            return
        self.context.set(var_name, node)
        if self.block_in and self.block_in.type == BlockTy.func:
            self.local_vars.append(var_name)
        self.visit(node.value)

    def visitVarDeclaration(self, node: VarDeclarationNode):
        var_name = node.var_name.value
        if node.value:
            self.visit(node.value)
        if node.type:
            self.visit(node.type)
        if var_name in self.ignore:
            return
        self.context.set(var_name, node)
        if self.block_in and self.block_in.type == BlockTy.func:
            self.local_vars.append(var_name)

    def visitArrayAssignNode(self, node: ArrayAssignNode):
        if node.value:
            self.visit(node.value)

    def visitPropertyAssignNode(self, node: PropertyAssignNode):
        if node.value:
            self.visit(node.value)

    def visitVarAccessNode(self, node: VarAccessNode):
        var_name = node.var_name.value
        if var_name in self.ignore:
            return
        if self.block_in and var_name not in self.local_vars:
            self.dependency_map.get(self.block_in.name).append(var_name)

    def visitFncCallNode(self, node: FncCallNode):
        self.visit(node.name)
        for arg in node.args:
            self.visit(arg)

    def visitMacroDeclarationNode(self, node: MacroDeclarationNode):
        macro_name = node.macro_name.value
        if macro_name in self.ignore:
            return
        self.context.set(macro_name, node)
        self.visit(node.value)

    def visitForEachNode(self, node: ForEachNode):
        self.visit(node.stmt)

    def visitForNode(self, node: ForNode):
        self.visit(node.stmt)

    def visitWhileNode(self, node: WhileNode):
        self.visit(node.stmt)

    def visitReturnNode(self, node: ReturnNode):
        if node.value:
            self.visit(node.value)

    def visitNewMemNode(self, node: NewMemNode):
        self.visit(node.type)
        if node.args:
            for arg in node.args:
                self.visit(arg)

    def visitIfNode(self, node: IfNode):
        for cond, case in node.cases:
            self.visit(cond)
            self.visit(case)
        if node.else_case:
            self.visit(node.else_case)

    def visitTernaryNode(self, node: TernaryNode):
        self.visit(node.cond)
        self.visit(node.is_true)
        self.visit(node.is_false)

    def visitEnumDeclarationNode(self, node: EnumDeclarationNode):
        enum_name = node.name.value
        if enum_name in self.ignore:
            return
        self.context.set(enum_name, node)

    def visitTypeNode(self, node: TypeNode):
        if isinstance(node.type, FloObject):
            if isinstance(node.type, FloGeneric):
                class_name = node.type.name
            else:
                class_name = node.type.referer.value
            if self.block_in != None and self.block_in.name != class_name:
                self.dependency_map.get(self.block_in.name).append(class_name)

        if isinstance(node.type, FloPointer) or isinstance(node.type, FloArray):
            if isinstance(node.type.elm_type, TypeNode):
                self.visit(node.type.elm_type)
        if isinstance(node.type, FloInlineFunc):
            for arg in node.type.arg_types:
                if isinstance(arg, TypeNode):
                    self.visit(arg)

    def visitTypeAliasNode(self, node: TypeAliasNode):
        type_name = node.identifier.value
        if type_name in self.ignore:
            return
        self.visit(node.type)
        self.context.set(type_name, node)

    def visitGenericClassNode(self, node: GenericClassNode):
        self.visit(node.class_declaration)

    def visitClassDeclarationNode(self, node: ClassDeclarationNode):
        class_name = node.name.value
        if class_name in self.ignore:
            return
        if node.parent:
            self.visit(node.parent)
        self.context.set(class_name, node)
        self.context = self.context.create_child(class_name)
        self.block_in = Block(class_name, BlockTy.class_)
        self.dependency_map[class_name] = []
        self.local_vars = []
        self.visit(node.body)
        self.context = self.context.parent
        self.local_vars = []
        self.block_in = None

    def visitImportNode(self, node: ImportNode):
        symbols_to_import = filter(
            lambda name: name not in self.ignore, [id.value for id in node.ids]
        )
        ctx = self.context.create_child(node.path.value)
        if (
            NodeFinder.get_abs_path(node.path.value, node.range.start.fn)
            in self.imported_modules
            or node.path.value in self.imported_modules
        ):
            return
        node_finder = NodeFinder(ctx)
        result = node_finder.find(
            list(symbols_to_import),
            self.context.get_symbols(),
            node.range,
            self.imported_modules,
        )
        for resolved_node in result.resolved:
            self.visit(resolved_node)


class FncDescriptor:
    def __init__(self, rtype: FloType, arg_names: List[str]):
        self.rtype = rtype
        self.arg_names = arg_names


class Block:
    @staticmethod
    def loop():
        return Block("loop")

    @staticmethod
    def class_():
        return Block("class")

    @staticmethod
    def fnc(func: FncDescriptor):
        return Block("function", func)

    @staticmethod
    def stmt():
        return Block("stmt")

    @staticmethod
    def if_():
        return Block("if")

    def else_():
        return Block("else")

    def __init__(self, name, fn: FncDescriptor = None):
        self.name = name
        self.fn_within = fn
        self.always_returns = False
        self.parent_blocks = []
        self.last_if_always_returns = False

    def can_continue(self):
        return self.is_in_block("loop")

    def can_break(self):
        return self.can_continue()

    def is_in_block(self, name):
        for (p_name, _, _) in self.parent_blocks:
            if p_name == name:
                return True
        return False

    def get_parent_fnc_ty(self):
        return self.fn_within.rtype

    def can_return(self):
        return self.fn_within != None

    def can_return_value(self, value):
        return value == self.fn_within.rtype

    def return_value(self, _):
        if self.name == "stmt":
            self.always_returns = True
        if self.is_in_block("else") and self.last_if_always_returns:
            self.always_returns = True
        else:
            self.always_returns = True

    def append_block(self, block):
        new_rt_state = self.always_returns
        if block.name == "function":
            new_rt_state = block.always_returns
        if block.name == "if":
            self.last_if_always_returns = False
        fn_state = block.fn_within or self.fn_within
        self.parent_blocks.append((self.name, self.fn_within, self.always_returns))
        (self.name, self.fn_within, self.always_returns) = (
            block.name,
            fn_state,
            new_rt_state,
        )

    def pop_block(self):
        if self.is_in_block("if") and self.always_returns:
            self.last_if_always_returns = True
        new_state = self.parent_blocks.pop()
        (self.name, self.fn_within, _) = new_state
        if new_state[0] != "function":
            self.always_returns = new_state[2]


class Analyzer(Visitor):
    comparason_ops = (
        TokType.EEQ,
        TokType.NEQ,
        TokType.GT,
        TokType.LT,
        TokType.GTE,
        TokType.LTE,
        TokType.NEQ,
    )
    arithmetic_ops_1 = (
        TokType.PLUS,
        TokType.MINUS,
        TokType.MULT,
        TokType.DIV,
        TokType.POW,
        TokType.MOD,
    )
    bit_operators = (TokType.SL, TokType.SR)

    def __init__(self, context: Context):
        self.context = Context(context.display_name + "_typecheck", context)
        self.constants = context.get_symbols()
        self.constants.append("null")
        self.constants.append("true")
        self.constants.append("false")
        self.class_within: str = None
        self.current_block = Block.stmt()
        self.imported_module_names = []  # denotes full imported module
        self.types_aliases = {}
        self.generic_aliases = {}
        self.generics: Dict[str, GenericClassNode] = {}

    def visit(self, node: Node):
        return super().visit(node)

    def analyze(self, entry_node: Node):
        self.include_builtins(entry_node)
        self.visit(entry_node)

    def include_builtins(self, node: StmtsNode):
        mpath = resource_path("flolib/builtins.flo")
        ast = get_ast_from_file(mpath, None)
        node.stmts = ast.stmts + node.stmts

    def visitIntNode(self, node: IntNode):
        if node.expects:
            if isinstance(node.expects, FloInt):
                return FloInt(None, node.expects.bits)
        return FloInt(None)

    def visitFloatNode(self, _: FloatNode):
        return FloFloat(None)

    def visitCharNode(self, _: CharNode):
        return FloInt(None, 8)

    def visitStrNode(self, node: StrNode):
        for arg_node in node.nodes:
            self.visit(arg_node)
        if node.expects == FloPointer(FloInt(None, 8)):
            return node.expects
        return FloObject(self.context.get("string"))

    def cast(self, node: Node, type):
        return NumOpNode(
            node,
            Token(TokType.KEYWORD, node.range, "as"),
            TypeNode(type, node.range),
            node.range,
        )

    def isNumeric(self, *types):
        isNum = True
        for type in types:
            isNum = isNum and isinstance(type, FloInt) or isinstance(type, FloFloat)
        return isNum

    def visitNumOpNode(self, node: NumOpNode):
        node.left_node.expects = node.expects
        left = self.visit(node.left_node)
        node.right_node.expects = left
        right = self.visit(node.right_node)
        if isinstance(left, FloInt) and isinstance(right, FloInt) and left != right:
            if isinstance(node.left_node, IntNode) or isinstance(
                node.left_node, UnaryNode
            ):
                node.left_node.expects = right
            elif isinstance(node.right_node, IntNode) or isinstance(
                node.right_node, UnaryNode
            ):
                node.right_node.expects = left
            left = self.visit(node.left_node)
            right = self.visit(node.right_node)
        if not isinstance(node.right_node, TypeNode):
            if left != right and isinstance(left, FloInt) and isinstance(right, FloInt):
                node.left_node = self.cast(
                    node.left_node, FloInt(None, max(left.bits, right.bits))
                )
                node.right_node = self.cast(
                    node.right_node, FloInt(None, max(left.bits, right.bits))
                )
            if (
                left != right
                and isinstance(left, FloFloat)
                and isinstance(right, FloFloat)
            ):
                node.left_node = self.cast(
                    node.left_node, FloFloat(None, max(left.bits, right.bits))
                )
                node.right_node = self.cast(
                    node.right_node, FloFloat(None, max(left.bits, right.bits))
                )
        if node.op.type in self.arithmetic_ops_1:
            if isinstance(left, FloFloat) and isinstance(right, FloInt):
                node.right_node = self.cast(node.right_node, left)
                return FloFloat(0)
            if isinstance(left, FloInt) and isinstance(right, FloFloat):
                node.left_node = self.cast(node.left_node, right)
                return FloFloat(0)
            if isinstance(left, FloInt) and isinstance(right, FloInt):
                # TODO: Check sizes and choose the biggest and cast the smallest
                return left
            if isinstance(left, FloFloat) and isinstance(right, FloFloat):
                # TODO: Check sizes and choose the biggest and cast the smallest
                return right
            if isinstance(left, FloPointer) and isinstance(right, FloInt):
                return left
            # TODO: Other object types arithmetic operators/operator overloading.
            if node.op.type == TokType.PLUS and isinstance(left, FloObject):
                add_method = left.referer.get_method("__add__")
                if add_method != None:
                    return self.check_fnc_call(add_method, [node.right_node], node)

        elif (
            node.op.type in self.bit_operators
            or node.op.isKeyword("xor")
            or node.op.isKeyword("or")
            or node.op.isKeyword("and")
        ):
            if isinstance(left, FloObject):
                sl = left.referer.get_method("__sl__")
                if sl:
                    return self.check_fnc_call(sl, [node.right_node], node)
            if self.isNumeric(left, right):
                if isinstance(left, FloFloat):
                    node.left_node = self.cast(node.left_node, right)
                    return right
                if isinstance(right, FloFloat):
                    node.right_node = self.cast(node.right_node, left)
                    return left
                if isinstance(left, FloInt) and isinstance(right, FloInt):
                    # TODO: Check sizes and choose the biggest and cast the smallest
                    return left
                # TODO: Object types bitwise
        elif node.op.type in Analyzer.comparason_ops or node.op.isKeyword("is"):
            if node.op.type in Analyzer.comparason_ops:
                if left == FloFloat and right == FloInt:
                    node.right_node = self.cast(node.right_node, left)
                if left == FloInt and right == FloFloat:
                    node.left_node = self.cast(node.left_node, left)
            return FloInt(None, 1)
        elif node.op.isKeyword("in"):
            if isinstance(right, FloObject):
                in_method = right.referer.get_method("__in__")
                if in_method:
                    return self.check_fnc_call(in_method, [node.left_node], node)
        elif node.op.isKeyword("as"):
            if left == right:
                node = node.left_node
            return right
        TypeError(
            node.range,
            f"Illegal operation {node.op} between types '{left.str()}' and '{right.str()}'",
        ).throw()

    def visitUnaryNode(self, node: UnaryNode):
        node.value.expects = node.expects
        type = self.visit(node.value)
        if node.op.type == TokType.AMP:
            return FloPointer(type)
        if type != FloInt(None, 1) and (not self.isNumeric(type)):
            TypeError(
                node.value.range,
                f"Expected type of '{FloInt(None, 1).str()}', '{FloFloat.str()}' or '{FloFloat.str()}' but got '{type.str()}'",
            ).throw()
        if node.op.type == TokType.MINUS and (not self.isNumeric(type)):
            TypeError(
                node.value.range,
                f"Illegal negative {type.str()}",
            ).throw()
        if node.op.type == TokType.NOT:
            if isinstance(type, FloFloat):
                node.value = self.cast(node.value, FloInt(None, 1))
            if self.isNumeric(type):
                return type
            else:
                # TODO: Object types
                TypeError(
                    node.value.range,
                    f"Illegal not on {type.str()}",
                ).throw()
        else:
            return type

    def visitIncrDecrNode(self, node: IncrDecrNode):
        action = "decrement" if node.id.type == TokType.MINUS_MINUS else "increment"
        if not (
            isinstance(node.identifier, ArrayAccessNode)
            or isinstance(node.identifier, VarAccessNode)
            or isinstance(node.identifier, PropertyAccessNode)
        ):
            SyntaxError(
                node.identifier.range, f"Illegal {action} on non-identifier"
            ).throw()
        type = self.visit(node.identifier)
        if self.isNumeric(type) or isinstance(type, FloPointer):
            return type
        else:
            TypeError(
                node.range, f"Illegal {action} operation on type '{type.str()}'"
            ).throw()

    def visitVarAccessNode(self, node: VarAccessNode):
        var_name = node.var_name.value
        if var_name == "true":
            return FloInt(1, 1)
        elif var_name == "false":
            return FloInt(0, 1)
        elif var_name == "null":
            if node.expects == None:
                TypeError(node.range, "Null without type hint context").throw()
            return FloNull(node.expects)
        value = self.context.get(var_name)
        if value == None:
            NameError(node.var_name.range, f"'{var_name}' is not defined").throw()
        return value

    def visitStmtsNode(self, node: StmtsNode):
        self.current_block.append_block(Block.stmt())
        for i, expr in enumerate(node.stmts):
            self.visit(expr)
            if self.current_block.always_returns:
                node.stmts = node.stmts[: i + 1]
                break
        self.current_block.pop_block()

    def visitMacroDeclarationNode(self, node: MacroDeclarationNode):
        const_name = node.macro_name.value
        value = self.visit(node.value)
        self.context.set(const_name, value)
        self.constants.append(const_name)

    def visitEnumDeclarationNode(self, node: EnumDeclarationNode):
        enum_name = node.name.value
        self.context.set(enum_name, FloEnum([token.value for token in node.tokens]))

    def check_inheritance(self, parent, child, node: Node):
        if parent == child:
            return None
        if not isinstance(child, FloObject):
            return None
        if child.referer.has_parent(parent.referer):
            node.value = self.cast(node.value, parent)
            return parent

    def check_value_assignment(self, defined_var_value, var_value, node):
        if isinstance(defined_var_value, FloObject) and node.value:
            c = self.check_inheritance(defined_var_value, var_value, node)
            if c:
                return c
        if var_value != defined_var_value:
            TypeError(
                node.range,
                f"Illegal assignment of type {var_value.str()} to {defined_var_value.str()}",
            ).throw()
        return defined_var_value

    def visitVarAssignNode(self, node: VarAssignNode):
        var_name = node.var_name.value
        if var_name in self.constants:
            TypeError(
                node.var_name.range, f"changing constant's {var_name} value"
            ).throw()
        defined_var_value = self.context.get(var_name)
        if defined_var_value == None:
            GeneralError(
                node.range, f"Illegal assignment to undeclared variable '{var_name}'"
            ).throw()
        node.value.expects = defined_var_value
        var_value = self.visit(node.value)
        return self.check_value_assignment(defined_var_value, var_value, node)

    def visitVarDeclarationNode(self, node: VarDeclarationNode):
        var_name = node.var_name.value
        if self.context.get(var_name) != None:
            GeneralError(
                node.range, f"Illegal redeclaration of variable '{var_name}'"
            ).throw()
        expected_ty = None
        if node.type:
            expected_ty = self.visit(node.type)
            if node.value:
                node.value.expects = expected_ty
            else:
                if isinstance(expected_ty, FloObject):
                    self.check_constructor_call(expected_ty, [], node)
        if node.value:
            var_value = self.visit(node.value)
            if not expected_ty:
                expected_ty = var_value
            self.check_value_assignment(expected_ty, var_value, node)
        if expected_ty == None:
            TypeError(
                node.var_name.range, f"Cannot declare variable {var_name} without type"
            ).throw()
        self.context.set(var_name, expected_ty)

    def condition_check(self, cond_node: Node):
        cond_type = self.visit(cond_node)
        if cond_type == None:
            return cond_node
        if self.isNumeric(cond_type):
            cond_node = self.cast(cond_node, FloInt(None, 1))
        else:
            TypeError(
                cond_node.range,
                f"Expected type numeric but got type '{cond_type.str()}'",
            ).throw()
        return cond_node

    def visitIfNode(self, node: IfNode):
        for i, (cond, expr) in enumerate(node.cases):
            self.current_block.append_block(Block.if_())
            node.cases[i] = (self.condition_check(cond), expr)
            self.visit(expr)
            self.current_block.pop_block()
        if node.else_case:
            self.current_block.append_block(Block.else_())
            self.visit(node.else_case)
            self.current_block.pop_block()

    def visitTernaryNode(self, node: TernaryNode):
        self.condition_check(node.cond)
        node.is_true.expects = node.expects
        is_true = self.visit(node.is_true)
        node.is_false.expects = is_true
        is_false = self.visit(node.is_false)
        if is_true != is_false:
            if isinstance(is_true, FloObject) and isinstance(is_false, FloObject):
                var = VarAssignNode(None, node.is_false, None)
                c = self.check_inheritance(is_true, is_false, var)
                if c:
                    node.is_false = var.value
                    return c
            TypeError(
                node.is_false.range,
                f"Expected type {is_true.str()} from first case but got type {is_false.str()}",
            ).throw()
        return is_true

    def visitForNode(self, node: ForNode):
        self.current_block.append_block(Block.loop())
        self.visit(node.init)
        node.cond = self.condition_check(node.cond)
        self.visit(node.stmt)
        self.visit(node.incr_decr)
        self.current_block.pop_block()

    def visitForEachNode(self, node: ForEachNode):
        self.current_block.append_block(Block.loop())
        it = self.visit(node.iterator)
        # TODO: Handle iteration
        if not (isinstance(it, FloArray) or isinstance(it, FloObject)):
            TypeError(
                node.iterator.range,
                f"Expected iterable but got type '{it.str()}'",
            ).throw()
        type = it.elm_type
        self.context.set(node.identifier.value, type)
        self.visit(node.stmt)
        self.current_block.pop_block()
        self.context.set(node.identifier.value, None)

    def visitWhileNode(self, node: WhileNode):
        self.current_block.append_block(Block.loop())
        node.cond = self.condition_check(node.cond)
        self.visit(node.stmt)
        self.current_block.pop_block()

    def visitFncNode(self, node: FncNode):
        if node.return_type:
            rt_type = self.visit(node.return_type)
        else:
            node.return_type = TypeNode(FloVoid(None), node.range)
            rt_type = FloVoid(None)
        arg_types = []
        default_args = []
        arg_names = []
        # TODO: Need for better functions
        for i, (arg_name_tok, type_node, default_value_node) in enumerate(node.args):
            default_value = None
            arg_type = None
            if type_node:
                arg_type = self.visit(type_node)
            if default_value_node:
                default_value = self.visit(default_value_node)
            arg_name = arg_name_tok.value
            if arg_type and default_value:
                if arg_type != default_value:
                    TypeError(
                        node.range,
                        f"Type mismatch between {arg_type.str()} and ${default_value.str()}",
                    )
            elif arg_type == None and default_value:
                arg_type = default_value
                node.args[i] = (
                    arg_name_tok,
                    TypeNode(default_value, (type_node or default_value_node).range),
                    default_value_node,
                )
            if arg_name in arg_names:
                NameError(
                    node.args[i][0].range,
                    f"Parameter '{arg_name}' defined twice in function parameters",
                ).throw()
            else:
                arg_names.append(arg_name)
                arg_types.append(arg_type)
                default_args.append(default_value_node)
        fnc_type = FloInlineFunc(
            None, arg_types, rt_type, node.is_variadic, default_args
        )
        fnc_type.arg_names = arg_names
        return fnc_type

    def evaluate_function_body(self, fnc_type: FloInlineFunc, node: FncNode):
        for arg_name, arg_type in zip(fnc_type.arg_names, fnc_type.arg_types):
            self.context.set(arg_name, arg_type)

        if node.is_variadic:
            var_arr = FloArray(None)
            var_arr.elm_type = fnc_type.arg_types[-1]
            self.context.set(fnc_type.arg_names[-1], var_arr)

        fn_descriptor = FncDescriptor(fnc_type.return_type, fnc_type.arg_names)
        self.current_block.append_block(Block.fnc(fn_descriptor))
        if node.body:
            self.visit(node.body)
            if not self.current_block.always_returns:
                if fnc_type.return_type == FloVoid(None):
                    node.body.stmts.append(ReturnNode(None, node.range))
                else:
                    GeneralError(
                        node.return_type.range,
                        "Function missing ending return statement",
                    ).throw()
        self.current_block.pop_block()
        self.context = self.context.parent

    def visitFncDefNode(self, node: FncDefNode):
        fnc_name = node.func_name.value
        fnc_type = self.visit(node.func_body)
        if self.context.get(fnc_name) != None:
            NameError(
                node.func_name.range,
                f"{fnc_name} is already defined",
            ).throw()
        self.context.set(fnc_name, fnc_type)
        self.context = self.context.create_child(fnc_name)
        self.evaluate_function_body(fnc_type, node.func_body)

    def visitMethodDeclarationNode(self, node: MethodDeclarationNode):
        assert self.class_within
        # TODO: think about access
        method_name = node.method_name.value
        method_ty = self.class_within.methods.get(method_name)
        assert method_ty
        self.context = self.context.create_child(method_name)
        self.context.set("this", FloObject(self.class_within))
        if method_name == "constructor":
            self.class_within.constructor = method_ty
        else:
            if self.class_within.parent:
                expected_ty = self.class_within.parent.get_method(method_name)
                if expected_ty and expected_ty != method_ty:
                    TypeError(
                        node.method_name.range,
                        f"Method '{method_name}' in type '{self.class_within.name}' is not assignable to the same method in base type '{self.class_within.parent.name}'."
                        + "\n\t\t\t\t"
                        + f"Type '{method_ty.str()}' is not assignable to type '{expected_ty.str()}'.\n",
                    ).throw()
            self.class_within.methods[method_name] = method_ty
        self.evaluate_function_body(method_ty, node.method_body)

    def visitPropertyDeclarationNode(self, node: PropertyDeclarationNode):
        assert self.class_within != None
        property_name = node.property_name.value
        property_ty = self.visit(node.type)
        if self.class_within.parent:
            expected_ty = self.class_within.parent.properties.get(property_name)
            if expected_ty and expected_ty != property_ty:
                TypeError(
                    node.property_name.range,
                    f"Property '{property_name}' in type '{self.class_within.name}' is not assignable to the same property in base type '{self.class_within.parent.name}'."
                    + "\n\t\t\t\t"
                    + f"Type '{property_ty.str()}' is not assignable to type '{expected_ty.str()}'.\n",
                ).throw()
        self.class_within.properties[property_name] = property_ty

    def visitReturnNode(self, node: ReturnNode):
        if not self.current_block.can_return():
            SyntaxError(node.range, "Illegal return outside a function").throw()
        if node.value:
            node.value.expects = self.current_block.get_parent_fnc_ty()
            val = self.visit(node.value)
        else:
            val = FloVoid(None)

        if isinstance(val, FloObject) and isinstance(
            self.current_block.fn_within.rtype, FloObject
        ):
            if val.referer.has_parent(self.current_block.fn_within.rtype.referer):
                node.value = self.cast(node.value, self.current_block.fn_within.rtype)
                val = self.current_block.fn_within.rtype
        if not self.current_block.can_return_value(val):
            TypeError(
                node.range,
                f"Expected return type of '{self.current_block.get_parent_fnc_ty().str()}' but got '{val.str()}'",
            ).throw()
        else:
            self.current_block.return_value(val)

    def visitContinueNode(self, node: ContinueNode):
        if not self.current_block.can_continue():
            SyntaxError(node.range, "Illegal continue outside of a loop").throw()

    def visitBreakNode(self, node: BreakNode):
        if not self.current_block.can_break():
            SyntaxError(node.range, "Illegal break outside of a loop").throw()

    def visitFncCallNode(self, node: FncCallNode):
        fn = self.visit(node.name)
        if not isinstance(fn, FloInlineFunc):
            TypeError(node.range, f"{node.name} is not a function").throw()
        return self.check_fnc_call(fn, node.args, node)

    def check_fnc_call(self, fn, args, node):
        # Replacing missing args with defaults
        for i, _ in enumerate(fn.arg_types):
            if i == len(args) and fn.defaults[i] != None:
                args.append(fn.defaults[i])
            elif i >= len(args):
                break
            elif args[i] == None and fn.defaults[i] != None:
                args[i] = fn.defaults[i]
        # Checking for varargs and alignings
        fn_args = fn.arg_types.copy()
        if fn.var_args:
            last_arg = fn_args.pop()
            fn_args += [last_arg] * (len(args) - len(fn_args))
        if len(args) != len(fn_args):
            TypeError(
                node.range,
                f"Expected {len(fn.arg_types)} arguments, but got {len(args)}",
            ).throw()
        for i, (node_arg, fn_arg_ty) in enumerate(zip(args, fn_args)):
            node_arg.expects = fn_arg_ty
            passed_arg_ty = self.visit(node_arg)
            c = None
            if (
                isinstance(passed_arg_ty, FloObject)
                and fn_arg_ty != FloType
                and isinstance(fn_arg_ty, FloObject)
            ):
                c = self.check_inheritance(
                    fn_arg_ty, passed_arg_ty, VarAssignNode(None, node_arg, None)
                )
                if c:
                    args[i] = self.cast(node_arg, fn_arg_ty)
            if passed_arg_ty != fn_arg_ty and fn_arg_ty != FloType and c == None:
                TypeError(
                    node_arg.range,
                    f"Expected type '{fn_arg_ty.str()}' but got '{passed_arg_ty.str()}'",
                ).throw()
            if isinstance(fn_arg_ty, FloInlineFunc) and isinstance(
                node_arg, PropertyAccessNode
            ):
                GeneralError(
                    node_arg.range,
                    "Cannot decouple method from object to pass as argument.",
                ).throw()
        return fn.return_type

    def get_object_class(self, node_type, node):
        class_name = node_type.referer.value
        class_ = self.context.get(class_name)
        if class_ == None or not (
            isinstance(class_, FloClass) or isinstance(class_, FloEnum)
        ):
            if self.class_within == None or (class_name != self.class_within.name):
                NameError(node.range, f"type {class_name} not defined").throw()
            else:
                class_ = self.class_within
        return class_

    def init_generic(self, generic: FloGeneric, node):
        # if it has it's referer is a token
        if isinstance(generic.referer, FloClass):
            return
        generic_name = generic.referer.value
        if self.context.get(generic_name) != None:
            return
        generic_node = self.generics.get(generic.name)
        if generic_node == None:
            NameError(node.range, f"'{generic.name}' type not defined").throw()
        generic_node.class_declaration.name.value = generic_name
        type_aliases = self.generic_aliases.copy()
        for key_tok, type_arg in zip(
            generic_node.generic_constraints, generic.constraints
        ):
            self.generic_aliases[key_tok.value] = type_arg
        self.visit(generic_node.class_declaration)
        generic_node.class_declaration.name.value = generic.name
        self.generic_aliases = type_aliases

    def visitTypeNode(self, node: TypeNode):
        node_type = node.type
        if isinstance(node_type, FloGeneric):
            generic = FloGeneric(
                Token(
                    node_type.referer.type,
                    node_type.referer.range,
                    node_type.referer.value,
                ),
                [],
            )
            for constraint in node.type.constraints:
                if isinstance(constraint, TypeNode):
                    generic.constraints.append(self.visit(constraint))
                generic.referer.value = generic.str()
            self.init_generic(generic, node)
            node_type = generic
        if isinstance(node_type, FloObject):
            if isinstance(node_type.referer, FloClass):
                return node_type
            alias = self.types_aliases.get(node_type.referer.value)
            if alias:
                if isinstance(alias, TypeNode):
                    aliased = self.visit(alias)
                    node.type = aliased
                    return aliased
            alias = self.generic_aliases.get(node_type.referer.value)
            if alias:
                return alias
            class_ = self.get_object_class(node_type, node)
            if isinstance(node_type, FloGeneric):
                return FloGeneric(class_, node_type.constraints)
            elif isinstance(class_, FloEnum):
                return FloInt(None)
            else:
                return FloObject(class_)
        elif isinstance(node_type, FloPointer) or isinstance(node_type, FloArray):
            if isinstance(node_type.elm_type, TypeNode):
                mm = node_type.__class__(None)
                mm.elm_type = self.visit(node_type.elm_type)
                node_type = mm
            if isinstance(node_type, FloArray) and isinstance(node_type.len, TypeNode):
                nn = FloArray(None, self.visit(node_type.len))
                nn.elm_type = node_type.elm_type
                if not isinstance(nn.len, FloInt):
                    TypeError(node.type.len.range, "Expected an int").throw()
                return nn
        elif isinstance(node_type, FloInlineFunc):
            fnc_ty = FloInlineFunc(
                None, [], None, node_type.var_args, node_type.defaults
            )
            for arg_ty in node_type.arg_types:
                fnc_ty.arg_types.append(self.visit(arg_ty))
            fnc_ty.return_type = self.visit(node_type.return_type)
            return fnc_ty
        return node_type

    def visitArrayNode(self, node: ArrayNode):
        if len(node.elements) == 0:
            return node.expects
        expected_type = self.visit(node.elements[0])
        expected_elm_ty = None
        if node.expects:
            if isinstance(node.expects, FloGeneric):
                if (
                    node.expects.name == "Array"
                    and node.expects.constraints[0] == expected_type
                ):
                    return node.expects
                else:
                    gen_name = "Array<" + expected_type.str() + ">"
                    if node.expects.str() == gen_name:
                        return node.expects
                    TypeError(
                        node.range,
                        f"Expected '{node.expects.str()}' but got '{gen_name}'",
                    ).throw()
            elif isinstance(node.expects, FloArray):
                expected_elm_ty = node.expects.elm_type
                expected_type = expected_elm_ty
        for elem in node.elements:
            elem.expects = expected_elm_ty
            type = self.visit(elem)
            if type != expected_type:
                TypeError(
                    elem.range,
                    f"Expected array to be of type '{expected_type.str()}' because of first element but got '{type.str()}'",
                ).throw()
        arr = FloArray(None, len(node.elements))
        arr.elm_type = expected_type
        return arr

    def check_subscribable(
        self, collection, index, node: PropertyAccessNode, set_value=None
    ):
        method_name = "__getitem__" if set_value == None else "__setitem__"
        fnc: FloInlineFunc = collection.referer.get_method(method_name)
        if fnc == None:
            TypeError(
                node.name.range,
                f"{collection.referer.name} object has no method {method_name}",
            ).throw()
        if index != fnc.arg_types[0]:
            TypeError(
                node.index.range,
                f"{collection.referer.name} object expects type {fnc.arg_types[0].str()} as index",
            ).throw()
        if set_value:
            if set_value != fnc.arg_types[1]:
                TypeError(
                    node.index.range,
                    f"{collection.referer.name} object expects type {fnc.arg_types[1].str()} for index assignment",
                ).throw()
        return fnc.return_type

    def visitRangeNode(self, node: RangeNode):
        if node.start:
            start = self.visit(node.start)
        else:
            start = FloInt(0)
        end = self.visit(node.end)
        if not (isinstance(start, FloInt)):
            TypeError(
                node.start.range, f"Excpected an 'int' but got a {start.str()}"
            ).throw()
        if not (isinstance(end, FloInt)):
            TypeError(
                node.end.range, f"Excpected an 'int' but got a {end.str()}"
            ).throw()
        return FloObject(self.context.get("Range"))

    def visitArrayAccessNode(self, node: ArrayAccessNode):
        collection = self.visit(node.name)
        index = self.visit(node.index)
        if isinstance(collection, FloArray) or isinstance(collection, FloPointer):
            if not self.isNumeric(index):
                TypeError(
                    node.index.range,
                    f"Expected key to be of type 'int' but got '{index.str()}'",
                ).throw()
            return collection.elm_type
        elif isinstance(collection, FloObject):
            return self.check_subscribable(collection, index, node)
        else:
            TypeError(
                node.name.range,
                f"Expected array, pointer or object but got '{collection.str()}'",
            ).throw()

    def visitArrayAssignNode(self, node: ArrayAssignNode):
        arr: FloArray = self.visit(node.array)
        node.value.expects = arr
        value = self.visit(node.value)
        if isinstance(arr, FloObject):
            index = self.visit(node.array.index)
            obj = self.visit(node.array.name)
            if isinstance(obj, FloArray) or isinstance(obj, FloPointer):
                obj = arr
            else:
                return self.check_subscribable(obj, index, node.array, value)
        if arr != value:
            TypeError(
                node.range,
                f"Expected assigned value to be of type '{arr.str()}' but got '{value.str()}'",
            ).throw()
        return value

    def declare_class(self, class_ob: FloClass, node: StmtsNode):
        for stmt in node.stmts:
            if isinstance(stmt, MethodDeclarationNode):
                method_name = stmt.method_name.value
                if class_ob.methods.get(method_name) != None:
                    NameError(
                        stmt.method_name.range,
                        f"{method_name} is already defined in class {class_ob.name}",
                    ).throw()
                class_ob.methods[method_name] = self.visit(stmt.method_body)

    def visitClassDeclarationNode(self, node: ClassDeclarationNode):
        self.current_block.append_block(Block.class_())
        class_name = node.name.value
        parent = None
        prev_super = self.context.get("super")
        if node.parent:
            parent_type = self.visit(node.parent)
            self.context.set("super", parent_type.referer.constructor)
            if not isinstance(parent_type, FloObject):
                TypeError(
                    node.name.range,
                    f"Type '{parent_type.str()}' cannot be base type of class '{class_name}'.",
                ).throw()
            else:
                parent = parent_type.referer
        class_ob = FloClass(class_name, parent, False)
        self.context.set(class_name, class_ob)
        self.declare_class(class_ob, node.body)
        prev_class = self.class_within
        self.class_within = class_ob
        self.constants.append(class_name)
        self.visit(node.body)
        self.class_within = prev_class
        self.context.set("super", prev_super)
        self.current_block.pop_block()

    def visitGenericClassNode(self, node: GenericClassNode):
        self.generics[node.class_declaration.name.value] = node

    def visitTypeAliasNode(self, node: TypeAliasNode):
        self.types_aliases[node.identifier.value] = node.type

    def visitPropertyAccessNode(self, node: PropertyAccessNode):
        root = self.visit(node.expr)
        property_name = node.property.value
        if isinstance(root, FloEnum):
            try:
                return root.get_property(property_name)
            except:
                NameError(
                    node.property.range,
                    f"property '{property_name}' is not defined on enum '{node.expr.var_name.value}'",
                ).throw()
        if isinstance(root, FloPointer):
            method = root.methods.get(property_name)
            if method == None:
                GeneralError(
                    node.property.range, f"{property_name} not defined on pointer"
                ).throw()
            return method
        if isinstance(root, FloClass):
            value = root.properties.get(property_name)
            if value == None:
                value = root.get_method(property_name)
            if value == None:
                GeneralError(
                    node.property.range,
                    f"{property_name} not defined as static member of class {root.name}",
                ).throw()
            return value
        if not isinstance(root, FloObject):
            TypeError(node.expr.range, "Expected an object").throw()
        value = root.referer.properties.get(property_name)
        if value == None:
            value = root.referer.get_method(property_name)
        if value == None:
            GeneralError(
                node.property.range,
                f"{property_name} not defined on {root.referer.name} object",
            ).throw()
        return value

    def visitPropertyAssignNode(self, node: PropertyAssignNode):
        expr = self.visit(node.expr)
        node.value.expects = expr
        value = self.visit(node.value)
        if isinstance(expr, FloObject) and isinstance(value, FloObject):
            c = self.check_inheritance(expr, value, node)
            if c:
                return c
        if expr != value:
            TypeError(
                node.range, f"Expected type {expr.str()} but got type {value.str()}"
            ).throw()
        return value

    def check_constructor_call(self, object, args, node):
        if object.referer.constructor:
            self.check_fnc_call(object.referer.constructor, args, node)

    def visitNewMemNode(self, node: NewMemNode):
        typeval = self.visit(node.type)
        if isinstance(typeval, FloObject):
            self.check_constructor_call(typeval, node.args or [], node)
            return typeval
        else:
            if not isinstance(typeval, FloPointer):
                TypeError(
                    node.type.range, "Type can only be an object or a pointer"
                ).throw()
            if len(node.args) != 1:
                TypeError(
                    node.range,
                    f"Expected 1 argument for new call but got {len(node.args)}",
                ).throw()
            return FloPointer(typeval.elm_type)

    def visitImportNode(self, node: ImportNode):
        # TODO: Needs work using NodeFinder.get_abs_path twice
        relative_path = node.path.value
        names_to_find = [id.value for id in node.ids]
        importer = NodeFinder(Context(relative_path))
        mpath = NodeFinder.get_abs_path(relative_path, node.range.start.fn)
        if mpath in self.imported_module_names:
            return
        if len(names_to_find) == 0:
            self.imported_module_names.append(mpath)
        names_to_ignore = self.context.get_symbols()
        find_result = importer.find(names_to_find, names_to_ignore, node.range)
        node.resolved_as = find_result.resolved
        for res_node in find_result.resolved:
            self.visit(res_node)


saved_labels = []


def save_labels(*args):
    saved_labels.append(list(args))


def pop_labels():
    return saved_labels.pop()


class Compiler(Visitor):
    def __init__(self, context: Context):
        self.context = context
        self.module = Context.current_llvm_module
        self.builder: ir.IRBuilder = None
        self.ret = None
        self.break_block = None
        self.current_fnc_return_ty = None
        self.continue_block = None
        self.class_within = None
        self.generics: Dict[str, GenericClassNode] = {}
        self.generic_aliases = {}

    def visit(self, node: Node):
        return super().visit(node)

    def compile(self, node: Node, options):
        FloEnum.start = 0
        self.visit(node)
        llvm.initialize_native_asmparser()
        basename = pathlib.Path(self.context.display_name).stem
        try:
            llvm_module = llvm.parse_assembly(str(self.module))
            llvm_module.verify()
        except RuntimeError as e:
            with open(f"{basename}.ll", "w") as file:
                file.write(str(self.module))
            exit(e)

        # Passes
        pass_manager_builder = llvm.create_pass_manager_builder()
        pass_manager_builder.opt_level = int(options.opt_level)
        pass_manager = llvm.create_module_pass_manager()
        pass_manager_builder.populate(pass_manager)
        pass_manager.run(llvm_module)
        basename = options.output_file.replace("<file>", basename)
        if options.emit:
            with open(f"{basename}.ll", "w") as object:
                object.write(str(llvm_module).replace("<string>", self.module.name))
            object.close()
        # Write executable
        if options.output_file != "<file>":
            with open(f"{basename}", "wb") as object:
                object.write(target_machine.emit_object(llvm_module))
                object.close()
        else:
            # Execute code
            if self.context.get("main") == None:
                CompileError("No main method to execute").throw()
            backing_mod = llvm.parse_assembly("")
            with llvm.create_mcjit_compiler(backing_mod, target_machine) as engine:
                engine.add_module(llvm_module)
                engine.finalize_object()
                engine.run_static_constructors()
                cfptr = engine.get_function_address("main")
                cfn = CFUNCTYPE(c_int, c_int, POINTER(c_char_p))(cfptr)
                args = [bytes(arg, encoding="utf-8") for arg in options.args]
                args_array = (c_char_p * (len(args) + 1))()
                args_array[:-1] = args
                cfn(len(args), args_array)

        # subprocess.run(["clang", f"{basename}.o", "-o" f"{basename}"])

    def visitIntNode(self, node: IntNode):
        if node.expects:
            if isinstance(node.expects, FloInt):
                return FloInt(node.tok.value, node.expects.bits)
        return FloInt(node.tok.value)

    def visitFloatNode(self, node: FloatNode):
        return FloFloat(node.tok.value)

    def visitCharNode(self, node: CharNode):
        if node.expects:
            if isinstance(node.expects, FloInt):
                return FloInt(node.tok.value, node.expects.bits)
        return FloInt(node.tok.value, 8)

    def visitStrNode(self, node: StrNode):
        str_val = node.tok.value
        values = []
        str_len = None
        for node_args in node.nodes:
            val = self.visit(node_args)
            values.append(val)
            str_val = str_val.replace("$", val.fmt, 1)
        fmt = FloConst.create_global_str(str_val)
        if len(values) > 0:
            sprintf = get_instrinsic("sprintf")
            snprintf = get_instrinsic("snprintf")
            passed_args = [arg.cval(self.builder) for arg in values]
            i8_ty = ir.IntType(8)
            i8_ptr_ty = ir.PointerType(i8_ty)
            str_len = FloInt(
                self.builder.call(
                    snprintf,
                    [
                        self.builder.inttoptr(FloInt(0).value, i8_ptr_ty),
                        FloInt(0).value,
                        fmt.value,
                    ]
                    + passed_args,
                )
            )
            str_buff = FloMem.halloc(
                self.builder, i8_ty, str_len.add(self.builder, FloInt(1))
            )
            self.builder.call(sprintf, [str_buff.value, fmt.value] + passed_args)
        else:
            str_buff = fmt
            str_len = FloInt(len(str_val.encode("utf-8")))
        if isinstance(node.expects, FloPointer):
            return node.expects.new_with_val(fmt.value)
        string_class = FloClass.classes.get("string")
        return string_class.constant_init(self.builder, [str_buff, str_len, str_len])

    def visitNumOpNode(self, node: NumOpNode):
        a = self.visit(node.left_node)
        b = self.visit(node.right_node)
        if node.op.type == TokType.PLUS:
            return a.add(self.builder, b)
        elif node.op.type == TokType.MINUS:
            return a.sub(self.builder, b)
        elif node.op.type == TokType.MULT:
            return a.mul(self.builder, b)
        elif node.op.type == TokType.DIV:
            return a.div(self.builder, b)
        elif node.op.type == TokType.MOD:
            return a.mod(self.builder, b)
        elif node.op.type == TokType.POW:
            return a.pow(self.builder, b)
        elif (
            node.op.type == TokType.EEQ
            or node.op.type == TokType.NEQ
            or node.op.type == TokType.GT
            or node.op.type == TokType.LT
            or node.op.type == TokType.LT
            or node.op.type == TokType.LTE
            or node.op.type == TokType.GTE
            or node.op.type == TokType.LEQ
        ):
            return a.cmp(self.builder, node.op.type._value_, b)
        elif node.op.type == TokType.SL:
            return a.sl(self.builder, b)
        elif node.op.type == TokType.SR:
            return a.sr(self.builder, b)
        elif node.op.isKeyword("or"):
            return a.or_(self.builder, b)
        elif node.op.isKeyword("and"):
            return a.and_(self.builder, b)
        elif node.op.isKeyword("xor"):
            return a.xor(self.builder, b)
        elif node.op.isKeyword("in"):
            return b.in_(self.builder, a)
        elif node.op.isKeyword("as"):
            try:
                return a.cast_to(self.builder, b)
            except Exception as e:
                TypeError(node.range, f"Cannot cast {a.str()} to {b.str()}").throw()
        elif node.op.isKeyword("is"):
            return FloInt(isinstance(a, b), 1)

    def visitStmtsNode(self, node: StmtsNode):
        for stmt in node.stmts:
            self.visit(stmt)

    def init_generic(self, generic: FloGeneric):
        previous_aliases = self.generic_aliases.copy()
        generic_name = generic.str()
        if FloClass.classes.get(generic_name):
            return
        generic_node = self.generics.get(generic.name)
        for key_tok, ty in zip(generic_node.generic_constraints, generic.constraints):
            self.generic_aliases[key_tok.value] = ty
        generic_node.class_declaration.name.value = generic_name
        self.visit(generic_node.class_declaration)
        self.generic_aliases = previous_aliases

    def visitTypeNode(self, node: TypeNode):
        type_ = node.type
        if isinstance(type_, FloFunc):
            type_.arg_types = [
                self.visit(ty) if isinstance(ty, TypeNode) else ty
                for ty in type_.arg_types
            ]
            if isinstance(type_.return_type, TypeNode):
                type_.return_type = self.visit(type_.return_type)
        elif isinstance(type_, FloGeneric):
            if isinstance(type_.referer, Token):
                gen = FloGeneric(
                    Token(type_.referer.type, type_.referer.range, type_.referer.value),
                    [],
                )
            else:
                if FloClass.classes.get(type_.referer.name) == None:
                    gen = FloGeneric(
                        Token(TokType.IDENTIFER, None, type_.referer.name), []
                    )
                    type_.constraints = [
                        TypeNode(constraint, None) for constraint in type_.constraints
                    ]
                else:
                    return type_
            for constraint in type_.constraints:
                res = self.visit(constraint)
                gen.constraints.append(res)
            type_ = gen
            type_.name = re.sub(r"(\<)+(.+?)(\>)+", "", type_.name)
            self.init_generic(type_)
            type_.referer.value = gen.str()
        if isinstance(type_, FloObject):
            alias = self.generic_aliases.get(type_.referer.value)
            if alias:
                return alias
            # Why?
            classname = (
                type_.referer.value
                if isinstance(type_.referer, Token)
                else type_.referer.name
            )
            if isinstance(self.context.get(classname), FloEnum):
                return FloInt(None)
            associated_class = FloClass.classes.get(classname)
            if isinstance(type_, FloGeneric):
                return FloGeneric(associated_class, type_.constraints)
            if associated_class == None:
                associated_class = FloClass(classname, None)
            return FloObject(associated_class)
        elif isinstance(type_, FloArray) or isinstance(type_, FloPointer):
            if isinstance(type_.elm_type, Node):
                if isinstance(type_, FloArray):
                    mm = FloArray(type_.elems, type_.len)
                else:
                    mm = FloPointer(None)
                mm.elm_type = self.visit(type_.elm_type)
                type_ = mm
            if isinstance(type_, FloArray):
                if isinstance(type_.len, Node):
                    type_.len = self.visit(type_.len)
                self.visit(TypeNode(type_.elm_type, None))
        return type_

    def visitFncNode(self, node: FncNode):
        arg_types = []
        arg_names = []
        rtype = self.visit(node.return_type)
        for arg_name, arg_type, _ in node.args:
            arg_names.append(arg_name.value)
            arg_types.append(self.visit(arg_type))
        return arg_types, arg_names, rtype

    def evaluate_function_body(self, fn, arg_names, node: StmtsNode):
        outer_ret = self.ret
        outer_builder = self.builder
        self.ret = fn.ret
        if node:
            self.context = fn.get_local_ctx(self.context, arg_names)
            self.builder = fn.builder
            self.visit(node)
            self.context = self.context.parent
            self.builder = outer_builder
        self.ret = outer_ret

    def visitFncDefNode(self, node: FncDefNode):
        fn_name = node.func_name.value
        arg_types, arg_names, rtype = self.visit(node.func_body)
        self.current_fnc_return_ty = rtype
        if node.func_body.body:
            fn = FloFunc(arg_types, rtype, fn_name, node.func_body.is_variadic)
        else:
            fn = FloFunc.declare(arg_types, rtype, fn_name, node.func_body.is_variadic)
        self.context.set(fn_name, fn)
        self.evaluate_function_body(fn, arg_names, node.func_body.body)

    def visitMethodDeclarationNode(self, node: MethodDeclarationNode):
        method_name = node.method_name.value
        if method_name == "constructor":
            fn = self.class_within.constructor
        else:
            fn = self.class_within.get_method(method_name)
            if fn == None:
                fn = self.class_within.static_members.get(method_name)
        assert fn
        _, arg_names, rt = self.visit(node.method_body)
        self.current_fnc_return_ty = rt
        self.evaluate_function_body(fn, arg_names, node.method_body.body)

    def visitUnaryNode(self, node: UnaryNode):
        if node.op.type == TokType.AMP:
            if isinstance(node.value, ArrayAccessNode):
                array: FloArray = self.visit(node.value.name)
                index = self.visit(node.value.index)
                return array.get_pointer_at_index(self.builder, index)
            if isinstance(node.value, PropertyAccessNode):
                object: FloObject = self.visit(node.value.expr)
                return object.get_property_mem(self.builder, node.value.property.value)
            var_name = node.value.var_name.value
            var: FloRef = self.context.get(var_name)
            return FloPointer(var.referee).new(var.mem)
        value = self.visit(node.value)
        if node.op.type == TokType.MINUS:
            return value.neg(self.builder)
        elif node.op.type == TokType.NOT:
            return value.not_(self.builder)
        else:
            return value

    def visitMacroDeclarationNode(self, node: MacroDeclarationNode):
        macro_name = node.macro_name.value
        const_val = FloConst(node.value)
        self.context.set(macro_name, const_val)

    def visitVarAssignNode(self, node: VarAssignNode):
        var_name = node.var_name.value
        value = self.visit(node.value)
        ref = self.context.get(var_name)
        ref.store(value)
        return value

    def visitVarDeclarationNode(self, node: VarDeclarationNode):
        var_name = node.var_name.value
        ty = None
        if node.type:
            ty = self.visit(node.type)

        if node.value:
            if ty != None:
                node.value.expects = ty
            value = self.visit(node.value)
        else:
            if isinstance(ty, FloObject):
                llvm_val = self.builder.alloca(ty.llvmtype)
                value = ty.new_with_val(llvm_val)
                value.construct(self.builder, [])
            else:
                value = ty
        ref = FloRef(self.builder, value, var_name)
        self.context.set(var_name, ref)

    def visitPropertyDeclarationNode(self, node: PropertyDeclarationNode):
        pass

    def visitVarAccessNode(self, node: VarAccessNode):
        var_name = node.var_name.value
        if var_name == "true":
            return FloInt(1, 1)
        elif var_name == "false":
            return FloInt(0, 1)
        elif var_name == "null":
            ty = node.expects
            if isinstance(ty, FloObject):
                try:
                    ty.referer = FloClass.classes[ty.referer.name]
                except:
                    pass
            return FloNull(ty)
        ref = self.context.get(var_name)
        if isinstance(ref, FloRef):
            return ref.load()
        elif isinstance(ref, FloConst):
            return ref.load(self)
        return ref

    def visitIfNode(self, node: IfNode):
        def ifCodeGen(cases: List[Tuple[Node, Node]], else_case):
            (comp, do) = cases.pop(0)
            cond = self.visit(comp)
            end_here = len(cases) == 0
            # Guard
            if end_here and else_case == None:
                with self.builder.if_then(cond.value):
                    self.visit(do)
                    return
            # Recursion
            with self.builder.if_else(cond.value) as (then, _else):
                with then:
                    self.visit(do)
                with _else:
                    if end_here:
                        self.visit(else_case)
                    else:
                        ifCodeGen(cases, else_case)

        ifCodeGen(node.cases.copy(), node.else_case)

    def visitTernaryNode(self, node: TernaryNode):
        true_block = self.builder.append_basic_block("true_block")
        false_block = self.builder.append_basic_block("false_block")
        end = self.builder.append_basic_block("end")
        cond = self.visit(node.cond)
        self.builder.cbranch(cond.value, true_block, false_block)
        self.builder.position_at_start(true_block)
        is_true = self.visit(node.is_true)
        self.builder.branch(end)
        self.builder.position_at_start(false_block)
        is_false = self.visit(node.is_false)
        self.builder.branch(end)
        self.builder.position_at_start(end)
        phi_node = self.builder.phi(is_true.llvmtype)
        phi_node.add_incoming(is_true.value, true_block)
        phi_node.add_incoming(is_false.value, false_block)
        return is_true.new_with_val(phi_node)

    def visitForNode(self, node: ForNode):
        for_entry_block = self.builder.append_basic_block(f"for.entry")
        self.builder.branch(for_entry_block)
        self.builder.position_at_start(for_entry_block)
        self.visit(node.init)
        for_cond_block = self.builder.append_basic_block(f"for.cond")
        for_body_block = self.builder.append_basic_block(f"for.body")
        for_incr_block = self.builder.append_basic_block(f"for.incr")
        for_end_block = self.builder.append_basic_block(f"for.end")
        save_labels(self.break_block, self.continue_block)
        self.break_block = for_end_block
        self.continue_block = for_incr_block
        self.builder.branch(for_cond_block)
        self.builder.position_at_start(for_cond_block)
        cond = self.visit(node.cond)
        self.builder.cbranch(cond.value, for_body_block, for_end_block)
        self.builder.position_at_start(for_body_block)
        self.visit(node.stmt)
        self.builder.branch(for_incr_block)
        self.builder.position_at_start(for_incr_block)
        self.visit(node.incr_decr)
        self.builder.branch(for_cond_block)
        [self.break_block, self.continue_block] = pop_labels()
        self.builder.position_at_start(for_end_block)

    def visitWhileNode(self, node: WhileNode):
        while_entry_block = self.builder.append_basic_block(f"while.entry")
        while_exit_block = self.builder.append_basic_block(f"while.exit")
        save_labels(self.break_block, self.continue_block)
        self.break_block = while_exit_block
        self.continue_block = while_entry_block
        cond = self.visit(node.cond)
        self.builder.cbranch(cond.value, while_entry_block, while_exit_block)
        self.builder.position_at_start(while_entry_block)
        self.visit(node.stmt)
        cond = self.visit(node.cond)
        self.builder.cbranch(cond.value, while_entry_block, while_exit_block)
        [self.break_block, self.continue_block] = pop_labels()
        self.builder.position_at_start(while_exit_block)

    def visitFncCallNode(self, node: FncCallNode):
        fnc = self.visit(node.name)
        args = [self.visit(arg) for arg in node.args]
        return fnc.call(self.builder, args)

    def visitReturnNode(self, node: ReturnNode):
        if node.value == None:
            return self.ret(FloVoid(None))
        node.value.expects = self.current_fnc_return_ty
        val = self.visit(node.value)
        if isinstance(val, FloVoid) or val == None:
            return self.ret(FloVoid(None))
        return self.ret(val)

    def visitBreakNode(self, _: BreakNode):
        self.builder.branch(self.break_block)

    def visitContinueNode(self, _: ContinueNode):
        self.builder.branch(self.continue_block)

    def visitIncrDecrNode(self, node: IncrDecrNode):
        value = self.visit(node.identifier)
        incr = (
            FloInt(-1, value.bits)
            if node.id.type == TokType.MINUS_MINUS
            else FloInt(1, value.bits)
        )
        nValue = value.add(self.builder, incr)
        if isinstance(node.identifier, VarAccessNode):
            ref: FloRef = self.context.get(node.identifier.var_name.value)
            ref.store(ref.load().add(self.builder, incr))
            self.context.set(node.identifier.var_name.value, ref)
        elif isinstance(node.identifier, ArrayAccessNode):
            index = self.visit(node.identifier.index)
            array = self.visit(node.identifier.name)
            array.set_element(self.builder, index, nValue)
        elif isinstance(node.identifier, PropertyAccessNode):
            root: FloObject = self.visit(node.identifier.expr)
            root.set_property(self.builder, node.identifier.property.value, nValue)
        return nValue if node.ispre else value

    def visitArrayAccessNode(self, node: ArrayAccessNode):
        index = self.visit(node.index)
        value = self.visit(node.name)
        if isinstance(value, FloObject):
            return value.get_property(self.builder, "__getitem__").call(
                self.builder, [index]
            )
        return value.get_element(self.builder, index)

    def visitArrayNode(self, node: ArrayNode):
        elems = [self.visit(elm_node) for elm_node in node.elements]
        if isinstance(node.expects, FloGeneric):
            array_class: FloClass = FloClass.classes.get(node.expects.str())
            if array_class == None:
                node.expects.name = re.sub(r"(\<)+(.+?)(\>)+", "", node.expects.str())
                self.init_generic(node.expects)
                array_class: FloClass = FloClass.classes.get(node.expects.str())
            length = FloInt(len(elems))
            llvm_ty = node.expects.constraints[0].llvmtype
            size = llvm_ty.get_abi_size(target_data) * len(elems)
            if len(elems) > 0:
                pointer = create_array_buffer(self.builder, elems)
            else:
                llvm_ty = node.expects.constraints[0].llvmtype
                size = llvm_ty.get_abi_size(target_data)
                length = FloInt(0)
                pointer = FloMem.halloc(self.builder, llvm_ty, FloInt(size))
            return array_class.constant_init(
                self.builder, [pointer, length, FloInt(size)]
            )
        else:
            size = FloInt(len(elems))
            if node.expects and node.expects.len and len(elems) == 0:
                size = node.expects.len
            array = FloArray(elems, size)
            array.elm_type = (
                node.expects.elm_type if array.elm_type == None else array.elm_type
            )
            return array

    def declare_class(self, class_obj, node: ClassDeclarationNode):
        for stmt in node.body.stmts:
            if isinstance(stmt, MethodDeclarationNode):
                method_name = stmt.method_name.value
                arg_types, _, rtype = self.visit(stmt.method_body)
                if stmt.is_static:
                    fn = FloFunc(
                        arg_types,
                        rtype,
                        class_obj.name + "_" + method_name,
                        stmt.method_body.is_variadic,
                    )
                elif stmt.method_body.body:
                    fn = FloMethod(
                        arg_types,
                        rtype,
                        method_name,
                        stmt.method_body.is_variadic,
                        class_obj,
                    )
                class_obj.add_method(fn, method_name)
            else:
                property_name = stmt.property_name.value
                property_type = self.visit(stmt.type)
                class_obj.add_property(property_name, property_type)
        if len(node.body.stmts) > 0:
            class_obj.init_value()

    def visitClassDeclarationNode(self, node: ClassDeclarationNode):
        class_name = node.name.value
        parent = None
        if node.parent:
            parent = self.visit(node.parent).referer
        class_obj = FloClass(class_name, parent)
        previous_class = self.class_within
        self.context.set(class_name, class_obj)
        self.declare_class(class_obj, node)
        self.class_within = class_obj
        self.visit(node.body)
        self.class_within = previous_class

    def visitGenericClassNode(self, node: GenericClassNode):
        self.generics[node.class_declaration.name.value] = node

    def visitRangeNode(self, node: RangeNode):
        if node.start:
            start = self.visit(node.start)
        else:
            start = FloInt(0)
        end = self.visit(node.end)
        range_class = FloClass.classes.get("Range")
        return range_class.constant_init(self.builder, [start, end])

    def visitPropertyAccessNode(self, node: PropertyAccessNode):
        root = self.visit(node.expr)
        property_name = node.property.value
        if isinstance(root, FloEnum):
            return root.get_property(property_name)
        if isinstance(root, FloClass):
            return root.static_members.get(property_name)
        if isinstance(root, FloPointer):
            return root.methods.get(property_name)
        return root.get_property(self.builder, property_name)

    def visitEnumDeclarationNode(self, node: EnumDeclarationNode):
        enum_name = node.name.value
        self.context.set(enum_name, FloEnum([token.value for token in node.tokens]))

    def visitPropertyAssignNode(self, node: PropertyAssignNode):
        root = self.visit(node.expr.expr)
        value = self.visit(node.value)
        if not isinstance(root, FloObject):
            TypeError(
                node.range,
                f"Can't set attribute {node.expr.property.value} of type {root.str()}",
            ).throw()
        root.set_property(self.builder, node.expr.property.value, value)

    def visitNewMemNode(self, node: NewMemNode):
        typeval = self.visit(node.type)
        if isinstance(typeval, FloObject):
            args = [self.visit(arg) for arg in node.args]
            return typeval.construct(self.builder, args)
        else:
            len = self.visit(node.args[0])
            mem = FloMem.halloc(self.builder, typeval.elm_type.llvmtype, size=len)
            return FloPointer.new(FloPointer(typeval.elm_type), mem)

    def visitArrayAssignNode(self, node: ArrayAssignNode):
        index = self.visit(node.array.index)
        array = self.visit(node.array.name)
        if isinstance(array, FloPointer):
            if isinstance(array.elm_type, FloGeneric):
                node.value.expects = array.elm_type
        value = self.visit(node.value)
        if isinstance(array, FloObject):
            return array.get_property(self.builder, "__setitem__").call(
                self.builder, [index, value]
            )
        return array.set_element(self.builder, index, value)

    def visitImportNode(self, node: ImportNode):
        for imported_node in node.resolved_as:
            self.visit(imported_node)


__version__ = "0.01@test"


def main():
    parser = OptionParser()
    parser.set_usage(" flo.py [options] [file.flo]")
    parser.remove_option("-h")
    parser.add_option("-h", "--help", action="help", help="Show this help message.")
    parser.add_option(
        "-l",
        "--emit-llvm",
        dest="emit",
        action="store_true",
        help="Emit generated llvm assembly.",
    )
    parser.add_option(
        "-o",
        dest="output_file",
        default="<file>",
        metavar="<file>",
        help="Place the output into <file>.",
    )
    parser.add_option(
        "-O",
        dest="opt_level",
        default=0,
        action="store",
        help="Specify the compiler's optimization level which is a value from 0-3.",
    )
    parser.add_option(
        "-v",
        "--version",
        dest="show_version",
        action="store_true",
        help="Show version.",
    )
    (options, files) = parser.parse_args()
    if options.show_version:
        return print(f"v{__version__}")
    if len(files) == 0 or not files[0]:
        IOError(None, "No input file specified.").throw()
    [file1, *_] = files
    if not exists(file1):
        IOError(None, f"No such file or directory: '{file1}'").throw()
    options.args = files
    compile(file1, options)


def compile(fn: str, options):
    context = new_ctx(fn)
    ast = get_ast_from_file(fn)
    # Static Check and auto-casting by semantic analyzer
    analyzer = Analyzer(context)
    analyzer.analyze(ast)
    # Code-gen/execution
    compiler = Compiler(context)
    result = compiler.compile(ast, options)
    return result


if __name__ == "__main__":
    main()
