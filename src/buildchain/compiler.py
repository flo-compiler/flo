from src.ast.tokens import TokType
from src.buildchain import Visitor
from src.ast.nodes import *
from llvm.core import Module, Type, Builder, Constant, Function
from llvm.ee import GenericValue
from src.context import Context
from src.valtypes.checks import Types, arrayType, fncType
int_type   = Type.int()
float_type = Type.double()
void_type  = Type.void()
def tollType(type):
    if type == Types.NUMBER:
        return int_type
    elif type == Types.NULL:
        return void_type
    elif type == Types.STRING:
        return Type.struct([Type.pointer(int_type), int_type, int_type, int_type])
    elif isinstance(type, arrayType): # later work on static strings
        return Type.vector(tollType(type.elementType))

def func(name, module, rettype, argtypes):
    func_type   = Type.function(rettype, argtypes, False)
    lfunc       = Function.new(module, func_type, name)
    entry_block = lfunc.append_basic_block("entry")
    builder     = Builder.new(entry_block)
    return (lfunc, builder)

class Compiler(Visitor):
    def __init__(self, context: Context):
        super().__init__(context)
        self.context = context
        self.module = Module.new(context.display_name)
        func_type = Type.function(void_type, [], False)
        function = Function.new(self.module, func_type, "main")
        entry_block = function.append_basic_block("entry")
        builder = Builder.new(entry_block)
        self.exit_block = function.append_basic_block("exit")
        self.function = function
        self.builder = builder
    def visit(self, node: Node):
        return super().visit(node)
    def execute(self, node:Node):
        self.visit(node)
        self.builder.position_at_end(self.exit_block)
        self.builder.ret_void()
        print(self.module.to_native_assembly())

    def visitNumNode(self, node: NumNode):
        if isinstance(node.tok.value, int):
            return Constant.int(int_type, int(node.tok.value))
        else: 
            return Constant.real(float_type, float(node.tok.value))
    def visitNumOpNode(self, node: NumOpNode):
        a = self.visit(node.left_node)
        b = self.visit(node.right_node)
        if node.op.type ==TokType.PLUS:
            if a.type == float_type:
                return self.builder.fadd(a, b)
            else:
                return self.builder.add(a, b)
        elif node.op.type ==TokType.MULT:
            if a.type == float_type:
                return self.builder.fmul(a, b)
            else:
                return self.builder.mul(a, b)
        elif node.op.type == TokType.DIV:
            return self.builder.fdiv(a, b)
        elif node.op.type == TokType.MINUS:
            if a.type == float_type:
                return self.builder.fsub(a, b)
            else:
                return self.builder.sub(a, b)

    def visitStmtsNode(self, node: StmtsNode):
        for stmt in node.stmts:
            v = self.visit(stmt)
            print(v)


    def visitFncDefNode(self, node: FncDefNode):
        rettype = tollType(node.return_type)
        argtypes = []
        types = []
        for arg, type in node.args:
            types.append(tollType(type))
            argtypes.append(arg.value)
        func(node.var_name.value, self.module, rettype, argtypes)
        body = self.visit(node.body)

    def visitVarAssignNode(self, node: VarAssignNode):
        var_name = node.var_name.value
        value = self.visit(node.value)
        var = self.context.symbol_table.get(var_name)
        if var == None:
            ty = tollType(node.val_type) or value.type
            var = self.builder.alloca(ty, var_name)
        self.builder.store(value, var)
        self.context.symbol_table.set(var_name, var)
        return var

    def visitVarAccessNode(self, node: VarAccessNode):
        return self.context.symbol_table.get(node.var_name.value)
