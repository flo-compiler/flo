#!/usr/bin/env python
from genericpath import exists
from optparse import OptionParser
from compiler import Compiler
from lexer import Lexer
from parser import Parser
from analyzer import Analyzer
from errors import IOError
from builtIns import new_ctx

__version__ = "0.01@test"


def main():
    parser = OptionParser()
    parser.set_usage(" flo.py [options] [file.flo]")
    parser.remove_option("-h")
    parser.add_option("-h", "--help", action="help",
                      help="Show this help message.")
    parser.add_option(
        "-p",
        "--print_llvm",
        dest="print",
        action="store_true",
        help="Print generated llvm assembly.",
    )
    parser.add_option(
        "-o",
        dest="output_file",
        default="<file>",
        metavar="<file>",
        help="Place the output into <file>.",
    )
    parser.add_option(
        "--no-output",
        dest="no_output",
        action="store_true",
        help="Compile with no output.",
    )
    parser.add_option(
        "--opt-level",
        dest="opt_level",
        default=1,
        action="store",
        help="Specify the compiler's optimization level which is a value from 0-3.",
    )
    parser.add_option(
        "-e",
        "--execute",
        dest="execute",
        action="store_true",
        help="Execute file after compiling.",
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
    [file1] = files
    if not exists(file1):
        IOError(None, f"No such file or directory: '{file1}'").throw()
    compile(file1, options)


def compile(fn: str, options):
    f = open(fn, "r", encoding="utf-8")
    code = f.read()
    # Tokenize file
    lexer = Lexer(fn, code)
    tokens = lexer.tokenize()
    # Create Context
    context = new_ctx(fn)
    # Generate AST
    parser = Parser(tokens)
    ast = parser.parse()
    # Static Check and auto-casting by semantic analyzer
    analyzer = Analyzer(context)
    analyzer.analyze(ast)
    # Code-gen/execution
    compiler = Compiler(context)
    result = compiler.compile(ast, options)
    return result


if __name__ == "__main__":
    main()
