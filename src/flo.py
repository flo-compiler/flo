#!/usr/bin/env python3
import sys
from context import SymbolTable, Context
from ast.lexer import Lexer
from ast.parser import Parser
from buildchain.checker import TypeChecker, Types, arrayType, fncType
from buildchain.intepreter import Intepreter
from valtypes.boolean import Boolean
from valtypes.func import BuiltinFunc

global_symbol_table = SymbolTable()
global_symbol_table.set('true', Boolean(1))
global_symbol_table.set('false', Boolean(0))

global_symbol_table.set('print', BuiltinFunc.print)
global_symbol_table.set('println', BuiltinFunc.println)
global_symbol_table.set('input', BuiltinFunc.input)
global_symbol_table.set('len', BuiltinFunc.len)
global_symbol_table.set('split', BuiltinFunc.split)
global_symbol_table.set('readFile', BuiltinFunc.readFile)

global_types_symbol_table = SymbolTable()
global_types_symbol_table.set('true', Types.BOOL)
global_types_symbol_table.set('false', Types.BOOL)
global_types_symbol_table.set('print', fncType(Types.NULL, [Types.ANY]))
global_types_symbol_table.set('println', fncType(Types.NULL, [Types.ANY]))
global_types_symbol_table.set('len', fncType(Types.NUMBER, [Types.ANY]))
global_types_symbol_table.set('input', fncType(Types.STRING, []))
global_types_symbol_table.set('split', fncType(arrayType(Types.STRING), [Types.STRING, Types.STRING]))
global_types_symbol_table.set('readFile', fncType(Types.STRING, [Types.STRING]))


def main():    
    args = sys.argv[1:]
    if len(args) > 0:
        if '-c' in args:
            if len(args) < 2: 
                print('please specify filename to compile')
                return
            compile(args[1])
        else:
            run_file(args[0])

def run(fn, code):
    # tokenize line
    lexer = Lexer(fn, code)
    tokens, error = lexer.tokenize()
    if error: return tokens, error
    # Generate AST 
    parser = Parser(tokens)
    ast, error = parser.parse()
    if error: return None, error
    # Static Check
    context = Context(fn or '<exec>')
    context.symbol_table = global_types_symbol_table
    checker = TypeChecker(context)
    _, error = checker.visit(ast)
    if error: return None, error
    # Inteprete AST
    context = Context(fn or '<exec>')
    context.symbol_table = global_symbol_table
    intepreter = Intepreter(context)
    result = intepreter.visit(ast)
    if result.error: return None, result.error
    return result.value, None

def run_file(fp: str):
    with open(fp, "r", encoding='utf-8') as f:
        _, error = run(fp, f.read())
        if error: print(error.message())
    

def compile(fp): pass

if __name__ == "__main__":
    main()
        