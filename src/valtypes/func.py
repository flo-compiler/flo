import os
from stack.context import Context
from stack.symbolTable import SymbolTable
from valtypes.array import Array
from valtypes.number import Number
from valtypes.string import String
from valtypes.valType import ValType
from buildchain.intepreter import Intepreter

class FuncType(ValType):
    def __init__(self, name):
        super().__init__()
        self.name = name or 'anonymous'
    def create_ctx(self):
        cont = Context(self.name, self.context, self.range.start)
        cont.symbol_table = SymbolTable(cont.parent.symbol_table)
        return cont
       
    def check_populate_args(self, arg_names, args, cont: Context): 
        for i in range(len(args)):
            arg_name = arg_names[i]
            arg_val = args[i]
            arg_val.set_ctx(cont)
            cont.symbol_table.set(arg_name, arg_val)
        return None
    def execute()->None: None, None
    def __repr__(self):
        return f"<fnc {self.name}>"

class Func(FuncType):
    def __init__(self, name , body, args):
        super().__init__(name)
        self.body = body
        self.args = args

    def execute(self, args):
        cont = self.create_ctx()
        it = Intepreter(cont)
        error = self.check_populate_args(self.args, args, cont)
        if error: return None, error
        result = it.visit(self.body)
        if result.error: return None, result.error
        return result.func_return_value if result.func_return_value != None else result.value, None

    def copy(self):
        cp = Func(self.name, self.body, self.args)
        cp.set_ctx(self.context)
        cp.set_range(self.range)
        return cp
        

class BuiltinFunc(FuncType):
    def __init__(self, name):
        super().__init__(name)
    def execute(self, args):
        cont = self.create_ctx()
        method = getattr(self, f'exec_{self.name}', self.no_exec)
        error = self.check_populate_args(method.args, args, cont)
        if error: return None, error
        val, error = method(cont)
        if error: return error
        return val, None
    
    def no_exec(self, ctx):
        raise Exception(f'No built-in function ${self.name}')
    
    def copy(self):
        cp = BuiltinFunc(self.name)
        cp.set_ctx(self.context)
        cp.set_range(self.range)
        return cp

    def exec_print(self, ctx: Context):
        val = ctx.symbol_table.get('value')
        print(str(val), end='')
        return None, None
    exec_print.args = ["value"]

    def exec_println(self, ctx: Context):
        val = ctx.symbol_table.get('value')
        print(str(val))
        return None, None
    exec_println.args = ["value"]

    def exec_input(self, ctx: Context):
        val = input()
        try:
            if '.' in val:
                val = float(val)
            else:
                val = int(val)
            return Number(val), None
        except:
            return String(val), None
    exec_input.args = []

    def exec_len(self, ctx: Context):
        val = ctx.symbol_table.get('value')
        return Number(len(val.value)), None
    exec_len.args = ["value"]
    
    def exec_split(self, ctx: Context):
        val = ctx.symbol_table.get('value')
        seperator = ctx.symbol_table.get('seperator')
        list = val.value.split(seperator.value)
        for i in range(len(list)):
            list[i] = String(list[i])
            list[i].set_range(val.range)
        return Array(list), None
    exec_split.args = ["value", "seperator"]

    def exec_readFile(self, ctx: Context):
        fn = ctx.symbol_table.get('path')
        path = os.path.join(os.path.dirname(ctx.parent.display_name), fn.value)
        with open(path, "r", encoding='utf-8') as f:
            return String(f.read()), None
    exec_readFile.args = ["path"]

    def exec_toNum(self, ctx: Context):
        fn = ctx.symbol_table.get('string')
        return Number(int(fn.value)), None
    exec_toNum.args = ["string"]

BuiltinFunc.print = BuiltinFunc('print')
BuiltinFunc.println = BuiltinFunc('println')
BuiltinFunc.input = BuiltinFunc('input')
BuiltinFunc.len = BuiltinFunc('len')
BuiltinFunc.split = BuiltinFunc('split')
BuiltinFunc.readFile = BuiltinFunc('readFile')
BuiltinFunc.toNum = BuiltinFunc('toNum')