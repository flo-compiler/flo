# from itypes.boolean import Boolean
# from itypes.func import BuiltinFunc
from analyzer import Types, arrayType, fncType
from context import SymbolTable, Context

global_symbol_table = SymbolTable()
# global_symbol_table.set('true', Boolean(1))
# global_symbol_table.set('false', Boolean(0))

# global_symbol_table.set('print', BuiltinFunc.print)
# global_symbol_table.set('println', BuiltinFunc.println)
# global_symbol_table.set('input', BuiltinFunc.input)
# global_symbol_table.set('len', BuiltinFunc.len)
# global_symbol_table.set('split', BuiltinFunc.split)
# global_symbol_table.set('readFile', BuiltinFunc.readFile)

global_types_symbol_table = SymbolTable()
global_types_symbol_table.set('true', Types.BOOL)
global_types_symbol_table.set('false', Types.BOOL)
global_types_symbol_table.set('print', fncType(Types.VOID, [Types.ANY]))
global_types_symbol_table.set('println', fncType(Types.VOID, [Types.ANY]))
global_types_symbol_table.set('len', fncType(Types.NUMBER, [Types.ANY]))
global_types_symbol_table.set('input', fncType(Types.STRING, []))
global_types_symbol_table.set('split', fncType(arrayType(Types.STRING), [Types.STRING, Types.STRING]))
global_types_symbol_table.set('readFile', fncType(Types.STRING, [Types.STRING]))


def create_ctx(fn:str, type: int = 0)->Context:
    context = Context(fn or '<exec>')
    if type == 0:
        context.symbol_table = global_types_symbol_table
    else:
        context.symbol_table = global_symbol_table
    return context