from llvmlite import ir


class SymbolTable:
    def __init__(self, parent=None):
        self.symbols = {}
        self.parent = parent

    def get(self, name):
        value = self.symbols.get(name, None)
        if value == None and self.parent:
            return self.parent.get(name)
        return value

    def set(self, name, value):
        self.symbols[name] = value

    def delete(self, name):
        del self.symbols[name]

    def copy(self):
        tl = SymbolTable(self.parent)
        tl.symbols = self.symbols.copy()
        return tl


class Context:
    current_llvm_module: ir.Module = None

    def __init__(self, display_name, parent=None, parent_entry_pos=None):
        self.display_name = display_name
        self.parent = parent
        self.parent_entry_pos = parent_entry_pos
        self.symbol_table = SymbolTable()
