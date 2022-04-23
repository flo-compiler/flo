from os import path
from lexer import Lexer
from parser import Parser
from errors import IOError
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