#!/usr/bin/env python3
import platform
from optparse import OptionParser
from src.buildchain.compiler import Compiler
from src.buildchain.intepreter import Intepreter
from src.ast.lexer import Lexer
from src.ast.parser import Parser
from src.buildchain.checker import TypeChecker
from src.std import create_ctx
from src.utils import printError
version = "0.01@test"



def main():
    parser = OptionParser()
    parser.add_option('-c', '--compile', dest='ftc', default=None, metavar='[filename]', help='To Compile file')    
    parser.add_option('-r', '--run', dest='ftr', default=None, metavar='[filename]', help='To Interprete file')    
    parser.add_option('-v', '--version', dest='showver', action="store_true", default=False, help='Show version')    
    (options, _) = parser.parse_args()
    if not (options.ftr or options.ftc or options.showver): print('Run flo -h for help')
    elif options.ftc:
        compile(options.ftc)
    elif options.ftr:
        run_file(options.ftr)
    elif options.showver:
        print(f"v{version}")

    if platform.system() == 'Windows':
        print("Press enter to continue")
        input()

def run(fn, code, Runner):
    # tokenize line
    lexer = Lexer(fn, code)
    tokens, error = lexer.tokenize()
    if error: printError(error)
    # Generate AST 
    parser = Parser(tokens)
    ast, error = parser.parse()
    if error: printError(error)
    # Static Check
    context = create_ctx(fn, 0)
    checker = TypeChecker(context)
    _, error = checker.visit(ast)
    if error: printError(error)
    # Inteprete AST
    context = create_ctx(fn, 1)
    runner = Runner(context)
    result = runner.execute(ast)
    return result

def run_file(fp: str):
    with open(fp, "r", encoding='utf-8') as f:
        _ = run(fp, f.read(), Intepreter)

    
def compile(fp: str):
    with open(fp, "r", encoding='utf-8') as f:
        _ = run(fp, f.read(), Compiler)

if __name__ == "__main__":
    main()
