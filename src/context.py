from llvmlite import ir

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
            symbols+=list(current.symbol_table.symbols.keys())
            current = current.parent
        return symbols