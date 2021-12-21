from os import error
from buildchain.BuildCache import BuildCache
from errors.rtError import RTError
from valtypes.array import Array
from valtypes.string import String
from valtypes.number import Number
from ast.nodes import *
from ast.visitor import Visitor
from buildchain.tokens import TokType
from utils.range import Range
from ast.nodes import *
from valtypes.valType import ValType
from stack.context import Context

class RTResult:
    def __init__(self, value: ValType=None, error: RTError=None):
        self.value = value
        self.error = error
        self.reset()
    def reset(self):
        self.func_return_value = None
        self.loop_should_continue = False
        self.loop_should_break = False
    def should_return(self):
        return self.func_return_value is not None
    def should_continue_break_or_return(self):
        return self.loop_should_continue or self.loop_should_break or self.should_return()

class Intepreter(Visitor):
    def __init__(self, context: Context):
        self.context = context
        self.originlSymbols = context.symbol_table.copy()
    def visit(self, node: Node)->RTResult:
        return super().visit(node)
        
    def visitNumNode(self, node: NumNode):
        return RTResult(Number(node.tok.value).set_ctx(self.context).set_range(node.range), None)
        
    def visitStrNode(self, node: StrNode):
        return RTResult(String(node.tok.value).set_ctx(self.context).set_range(node.range), None)

    def visitNumOpNode(self, node: NumOpNode):
        res = self.visit(node.left_node)
        left = res.value
        if res.error: return res
        res = self.visit(node.right_node)
        right = res.value
        if res.error : return res
        if node.op.type == TokType.PLUS:
            result, error = left.add(right)
        elif node.op.type == TokType.MINUS:
            result, error = left.sub(right)
        elif node.op.type == TokType.MULT:
            result, error = left.mul(right)
        elif node.op.type == TokType.DIV:
            result, error = left.div(right)
        elif node.op.type == TokType.POW:
            result, error = left.pow(right)
        elif node.op.type == TokType.MOD:
            result, error = left.mod(right)
        elif node.op.type == TokType.EEQ:
            result, error = left.comp_eq(right)
        elif node.op.type == TokType.LT:
            result, error = left.comp_lt(right)
        elif node.op.type == TokType.LTE:
            result, error = left.comp_lte(right)
        elif node.op.type == TokType.GT:
            result, error = left.comp_gt(right)
        elif node.op.type == TokType.NEQ:
            result, error = left.comp_neq(right)
        elif node.op.type == TokType.GTE:
            result, error = left.comp_gte(right)
        elif node.op.isKeyword('and'):
            result, error = left.l_and(right)
        elif node.op.isKeyword('or'):
            result, error = left.l_or(right)
        if error: return RTResult(None, RTError(node.range, error.msg))
        result.set_range(node.range)
        return RTResult(result, None)
        
    def visitUnaryNode(self, node: UnaryNode):
        result = self.visit(node.tok)
        if result.error: return result
        n = result.value
        if node.op.type == TokType.MINUS:
            result, error = n.mul(Number(-1))
            if error: return RTResult(None, error)
        elif node.op.type == TokType.NOT:
            result, error = n.l_not()
            if error: return RTResult(None, error)
        else:
            result = n
        return RTResult(result.set_range(node.range), error)

    def visitIncrDecrNode(self, node: IncrDecrNode):
        result = self.visit(node.identifier)
        if result.error: return result
        value = result.value
        incr = -1 if node.id.type == TokType.MINUS_MINUS else 1
        nValue, error = value.add(Number(incr))
        if error: return RTResult(None, error)
        nValue.set_range(node.range)
        self.context.symbol_table.set(node.identifier.var_name.value, nValue)
        return RTResult(nValue if node.ispre else value, None)

    def visitVarAccessNode(self, node: VarAccessNode):
        var_name = node.var_name.value
        value = self.context.symbol_table.get(var_name)
        value = value.set_range(node.range).set_ctx(self.context)
        return RTResult(value, None)

    def visitStmtsNode(self, node: StmtsNode):
        for expr in node.stmts:
            result = self.visit(expr)
            if result.error: return result
            if result.should_continue_break_or_return(): return result
        return RTResult()

    def visitVarAssignNode(self, node: VarAssignNode):
        var_name = node.var_name.value
        result = self.visit(node.value)
        value = result.value
        if result.error: return result
        self.context.symbol_table.set(var_name, value)
        return RTResult(value, None)

    def visitIfNode(self, node: IfNode):
        for cond, expr in node.cases:
            result = self.visit(cond)
            if result.error: return result
            cond_value = result.value
            if cond_value.isTrue():
                return self.visit(expr)
        if node.else_case:
            return self.visit(node.else_case)
        return RTResult()

    def visitForNode(self, node: ForNode):
        init = self.visit(node.init)
        if init.error: return init
        while True:
            result = self.visit(node.cond)
            if result.error: return result
            comp = result.value
            if not comp.isTrue(): break
            result = self.visit(node.stmt)
            if result.error: return result
            if result.should_return(): return result
            if result.loop_should_break: break
            result = self.visit(node.incr_decr)
            if result.error: return result
        return RTResult()
    
    def visitForEachNode(self, node: ForEachNode):
        id = node.identifier
        result = self.visit(node.iterator)
        if result.error: return result
        it = result.value
        for v in it.value:
            v = String(v) if type(v) == str else v
            self.context.symbol_table.set(id.value, v)
            result = self.visit(node.stmt)
            if result.error: return result
        self.context.symbol_table.set(id.value, None)
        return RTResult()

    def visitWhileNode(self, node: WhileNode):
        while True:
            result =  self.visit(node.cond)
            if result.error: return result
            comp = result.value
            if not comp.isTrue(): break
            result = self.visit(node.stmt)
            if result.error: return result
            if result.should_return(): return result
            if result.loop_should_break: break
        return RTResult()

    def visitFncDefNode(self, node: FncDefNode):
        from valtypes.func import Func
        fnc_name = node.var_name.value if node.var_name else None
        body = node.body
        args = [arg.value for (arg, _) in node.args]
        fnc = Func(fnc_name, body, args).set_ctx(self.context).set_range(body.range)
        if node.var_name:
            self.context.symbol_table.set(fnc_name, fnc)
        return RTResult(fnc, None)

    def visitReturnNode(self, node: ReturnNode):
        result = RTResult()
        result.func_return_value = ValType()
        if node.value:
            result = self.visit(node.value)
            if result.error: return result
            result.func_return_value = result.value
        return result

    def visitContinueNode(self, node: ContinueNode):
        result = RTResult()
        result.loop_should_continue = True
        return result

    def visitBreakNode(self, node: BreakNode):
        result = RTResult()
        result.loop_should_break = True
        return result

    def visitFncCallNode(self, node: FncCallNode):
        fnR = self.visit(node.name)
        if fnR.error: return fnR
        fn = fnR.value
        fn.set_range(node.range)
        args = []
        for arg in node.args:
            result = self.visit(arg)
            if result.error: return result
            res = result.value
            args.append(res)
        result, error = fn.execute(args)
        if error: return RTResult(None, error)
        return RTResult(result, None)
    
    def visitArrayNode(self, node:ArrayNode):
        elements = [] 
        for expr in node.elements:
            elem = self.visit(expr)
            if elem.error: return elem
            elements.append(elem.value)
        return RTResult(Array(elements).set_range(node.range).set_ctx(self.context), None)

    def visitArrayAccessNode(self, node: ArrayAccessNode):
        result = self.visit(node.name)
        arr = result.value
        if result.error: return result
        result = self.visit(node.index)
        if result.error: return result
        val, error = arr.getElement(result.value.value)
        if error: return RTResult(None, error)
        return RTResult(val, None)

    
    def visitArrayAssignNode(self, node: ArrayAssignNode):
        result = self.visit(node.array.index)
        if result.error: return result
        index = result.value
        result = self.visit(node.array.name)
        if result.error: return result
        arr = result.value
        result = self.visit(node.value)
        if result.error: return result
        val = result.value
        _, error = arr.setElement(index.value, val)
        if error: return RTResult(None, error)
        return RTResult(val, None)

    def visitImportNode(self, node: ImportNode):
        ast = BuildCache.module_asts.get(node.path.value)
        savedCtx = self.context
        self.context = Context(node.path.value)
        self.context.symbol_table = self.originlSymbols
        self.visit(ast)
        for identifier in node.ids:
            val = self.context.symbol_table.get(identifier.value)
            savedCtx.symbol_table.set(identifier.value, val)
        self.context = savedCtx
        return RTResult(None, None)