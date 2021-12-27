import os
from typing import List
from buildchain import BuildCache
from buildchain import Visitor
from context import Context, SymbolTable
from errors import Error, TypeError, SyntaxError
from ast.tokens import TokType
from ast.lexer import Lexer
from ast.parser import Parser
from ast.nodes import *
from valtypes.checks import *

class TypeChecker(Visitor):
    def __init__(self, context: Context):
        self.context = context
        self.reserved = context.symbol_table.symbols.copy()
        self.funcStack: List[fncType] = []
        self.inLoop = [False]
        self.shoudlReturn = False
    def visit(self, node: Node)->Tuple[Types, Error]:
        return super().visit(node)

    def visitNumNode(self, node: NumNode)->Tuple[Types, Error]:
        return Types.NUMBER, None
        
    def visitStrNode(self, node: StrNode)->Tuple[Types, Error]:
        return Types.STRING, None

    def visitNumOpNode(self, node: NumOpNode)->Tuple[Types, Error]:
        left, error = self.visit(node.left_node)
        if error: return None, error
        right, error = self.visit(node.right_node)
        if error: return None, error
        if node.op.type in (TokType.PLUS, TokType.MINUS, TokType.MULT, TokType.DIV, TokType.MOD, TokType.POW, TokType.SL, TokType.SR):
            if left == Types.NUMBER and right == left:
                return Types.NUMBER, None
            elif left == Types.STRING and right == Types.STRING and node.op.type == TokType.PLUS:
                return Types.STRING, None
            elif ((isinstance(left, arrayType) and right == Types.NUMBER) or (isinstance(right, arrayType) and left == Types.NUMBER)) and node.op.type == TokType.MULT:
                return left, None
            elif (isinstance(left, arrayType) and left == right ) and node.op.type == TokType.PLUS:
                return left, None
            elif  node.op.type == TokType.SL or node.op.type == TokType.SR:
                if right != Types.NUMBER and left == Types.NUMBER:
                    return None, TypeError(node.right_node.range, f"Expected type '{typeToStr(Types.NUMBER)}' but got type '{typeToStr(right)}' on bit shift")
                if isinstance(left, arrayType) and left.elementType != right:                    
                    return None, TypeError(node.right_node.range, f"Expected type '{typeToStr(left.elementType)}' but got type '{typeToStr(right)}' on append")
                if isinstance(left, arrayType) or left == Types.NUMBER:
                    return left, None
            elif left == Types.NUMBER and right == Types.STRING or right == Types.NUMBER and left == Types.STRING and node.op.type in (TokType.PLUS, TokType.MULT):
                return Types.STRING, None
        elif  node.op.type in (TokType.EEQ, TokType.NEQ, TokType.GT, TokType.LT, TokType.GTE, TokType.LTE, TokType.NEQ):
            if left == right and left == Types.NUMBER or left == Types.BOOL: 
                return Types.BOOL, None
            elif left == right and left == Types.STRING and node.op.type == TokType.EEQ:
                return Types.BOOL, None
            elif left == right and left == Types.STRING and node.op.type == TokType.NEQ:
                return Types.BOOL, None
            elif left == Types.BOOL and right == Types.NUMBER or left == Types.BOOL and right == Types.NUMBER:
                return Types.BOOL, None
        elif node.op.isKeyword('or') or node.op.isKeyword('and'):
            if left == right == Types.NUMBER:
                return Types.NUMBER, None
            elif left == right == Types.BOOL:
                return Types.BOOL, None
        elif node.op.isKeyword('in'):
            if isinstance(right, arrayType):
                return Types.BOOL, None
            elif right == Types.STRING:
                return Types.BOOL, None
            else:
                return None, TypeError(node.right_node.range, f"Illegal operation in on type '{typeToStr(right)}' expected type 'str' or 'array'")
        return None, TypeError(node.range, f"Illegal operation {node.op} between types '{typeToStr(left)}' and '{typeToStr(right)}'")
        
    def visitUnaryNode(self, node: UnaryNode)->Tuple[Types, Error]:
        type, error = self.visit(node.tok)
        if error: return None, error
        if node.op.type == TokType.MINUS and type == Types.NUMBER:
            return Types.NUMBER, None
        elif node.op.type == TokType.NOT:
            if type == Types.BOOL:
                return Types.BOOL, None
            elif type == Types.NUMBER:
                return Types.NUMBER, None
        else:
            return type, None

    def visitIncrDecrNode(self, node: IncrDecrNode)->Tuple[Types, Error]:
        action = "decrement" if node.id.type == TokType.MINUS_MINUS else "increment"
        if not (isinstance(node.identifier, ArrayAccessNode) or isinstance(node.identifier, VarAccessNode)):
            return None, SyntaxError(node.identifier.range, f"Variable is required for {action}")
        value, error = self.visit(node.identifier)
        if error: return None, error
        if value == Types.NUMBER:
            return Types.NUMBER, None
        else:
            return None, TypeError(node.range, f"Illegal {action} operation on type '{typeToStr(value)}'")

    def visitVarAccessNode(self, node: VarAccessNode)->Tuple[Types, Error]:
        var_name = node.var_name.value
        value = self.context.symbol_table.get(var_name)
        if value == None:
            return None, Error(
                node.var_name.range,
                None,
                f"'{var_name}' is not defined"
            )
        return value, None

    def visitStmtsNode(self, node: StmtsNode)->Tuple[Types, Error]:
        rt = Types.NULL
        for expr in node.stmts:
            s = self.visit(expr)
            e, error = s
            if error: return None, error
            if self.shoudlReturn:
                self.shoudlReturn = False
                rt = e
        return rt, None

    def visitVarAssignNode(self, node: VarAssignNode)->Tuple[Types, Error]:
        var_name = node.var_name.value
        if var_name.isupper() and self.context.symbol_table.get(var_name)!= None:
            return None, Error(
                node.range,
                None,
                f"Cannot change value of the constant {var_name}"
            )
        if var_name in self.reserved.keys():
            return None, Error(
                node.var_name.range,
                None,
                f"{var_name} is a reserved constant"
            )
        expected_type = node.val_type or self.context.symbol_table.get(var_name) or Types.NULL
        type, error = self.visit(node.value)
        if type == Types.ANY and expected_type == Types.NULL:
            return None, TypeError(node.range, f"Type cannot be infered be sure to add a type on variable assignment")
        elif expected_type != Types.NULL and type == Types.ANY:
            type = expected_type
        if error: return None, error
        if type == expected_type or expected_type == Types.NULL:
            self.context.symbol_table.set(var_name, type)
            return type, None
        else:
            return None, TypeError(node.range, f"Assigning '{typeToStr(type)}' to type '{typeToStr(expected_type)}'")

    def visitIfNode(self, node: IfNode)->Tuple[Types, Error]: 
        for cond, expr in node.cases:
            cond_type, error = self.visit(cond)
            if error: return None, error
            if not (cond_type == Types.NUMBER or cond_type == Types.BOOL):
                return None, TypeError(cond.range, f"Expected type 'num' or 'bool' but got type '{typeToStr(cond_type)}'")
            else:
                self.shoudlReturn = False
                _, error = self.visit(expr)
                if error: return None, error
        if node.else_case:
            _, error = self.visit(node.else_case)
            if error: return None, error
        return _ if self.shoudlReturn else Types.NULL, None

    def visitForNode(self, node: ForNode)->Tuple[Types, Error]:
        _, error = self.visit(node.init)
        if error: return None, error
        cond_type, error = self.visit(node.cond)
        if error: return None, error
        if not (cond_type == Types.NUMBER or cond_type == Types.BOOL):
            return None, TypeError(node.cond.range, f"Expected type 'num' or 'bool' but got type '{cond_type}'")
        index = len(self.inLoop)
        self.inLoop.append(True)
        _, error = self.visit(node.stmt)
        if error: return None, error
        self.inLoop.pop(index)
        _, error = self.visit(node.incr_decr)
        if error: return None, error
        return Types.NULL, None
    
    def visitForEachNode(self, node: ForEachNode):
        it, error = self.visit(node.iterator)
        if error: return None, error
        if (not isinstance(it, arrayType)) and (it != Types.STRING) and (not isinstance(it, dictType)):
            return None, TypeError(node.iterator.range, f"Expected type of 'str', dict or 'array' but got type '{typeToStr(it)}'")
        index = len(self.inLoop)
        self.inLoop.append(True)
        type = Types.STRING if it == Types.STRING or isinstance(it, dictType) else it.elementType
        self.context.symbol_table.set(node.identifier.value, type)
        _, error = self.visit(node.stmt)
        if error: return None, error
        self.context.symbol_table.set(node.identifier.value, None)
        self.inLoop.pop(index)
        return Types.NULL, None

    def visitWhileNode(self, node: WhileNode)->Tuple[Types, Error]: 
        cond_type, error =  self.visit(node.cond)   
        if error: return None, error
        if not (cond_type == Types.NUMBER or cond_type == Types.BOOL):
            return None, TypeError(node.cond.range, f"Expected type 'num' or 'bool' but got type '{cond_type}'")
        index = len(self.inLoop)
        self.inLoop.append(True)
        _, error = self.visit(node.stmt)
        self.inLoop.pop(index)
        if error: return None, error
        return Types.NULL, None

    def visitFncDefNode(self, node: FncDefNode)->Tuple[Types, Error]:
        fnc_name = node.var_name.value
        if fnc_name in self.reserved.keys():
            return None, Error(
                node.var_name.range,
                None,
                f"{fnc_name} is a reserved constant"
            )
        fnc_type = node.return_type
        if fnc_type == None:
            return None, TypeError(node.var_name.range, f"No return type for function '{fnc_name}'")
        args = []
        count = {}
        savedTbl = self.context.symbol_table.copy()
        for arg, type in node.args:
            if count.get(arg.value, None) != None:
                return None, Error(arg.range, None, f"parameter '{arg.value}' defined twice in function parameters")
            elif type == None:
                return None, TypeError(arg.range, f"parameter '{arg.value}' has an unknown type")
            elif arg.value == fnc_name:
                return None, Error(arg.range, None, f"parameter '{arg.value}' has same name as function")
            else:
                count[arg.value] = 1
                self.context.symbol_table.set(arg.value, type)
                args.append(type)
        rtype = fncType(fnc_type, args)
        self.context.symbol_table.set(fnc_name, rtype)
        self.funcStack.append(fnc_type)
        bodyType, error = self.visit(node.body)
        self.funcStack.pop()
        self.context.symbol_table = savedTbl
        if error: return None, error
        if bodyType != fnc_type:
            return None, TypeError(node.range, f"Expected return type of '{typeToStr(fnc_type)}' but got '{typeToStr(bodyType)}'")
        if fnc_name:
            self.context.symbol_table.set(fnc_name, rtype)
        return rtype, None

    def visitReturnNode(self, node: ReturnNode)->Tuple[Types, Error]:
        self.shoudlReturn = True
        if len(self.funcStack) == 0:
            return None, Error(node.range, None, 'Illegal return outside a function')
        if node.value:
            val, error = self.visit(node.value)
            if error: return None, error
            rt = self.funcStack[-1]
            if rt == val:
                return val, None
            else:
                return None, TypeError(node.range, f"Expected return type of '{typeToStr(rt)}' but got '{typeToStr(val)}'")
        else:
            return Types.NULL, None

    def visitContinueNode(self, node: ContinueNode)->Tuple[Types, Error]: 
        if not self.inLoop[-1]:
            return None, Error(node.range, None, 'Illegal continue outside of a loop')
        return Types.NULL, None

    def visitBreakNode(self, node: BreakNode)->Tuple[Types, Error]:
        if not self.inLoop[-1]:
            return None, Error(node.range, None, 'Illegal break outside of a loop')
        return Types.NULL, None

    def visitFncCallNode(self, node: FncCallNode)->Tuple[Types, Error]:
        fn, error = self.visit(node.name)
        if error: return None, error
        if not isinstance(fn, fncType):
            return None, Error(node.range, None, f'{node.name.var_name.value} is not a function')
        if len(fn.argTypes) != len(node.args):
            return None, Error(node.range, None, f'Expected {len(fn.argTypes)} arguments, but got {len(node.args)}')
        for i in range(len(node.args)):
            argType, error = self.visit(node.args[i])
            if error: return None, error
            if argType != fn.argTypes[i] and not fn.argTypes[i] == Types.ANY and not argType == Types.ANY:
                return None, TypeError(node.args[i].range, f"Expected type '{typeToStr(fn.argTypes[i])}' but got '{typeToStr(argType)}'")
        return fn.returnType, None

    def visitTypeNode(node: TypeNode):
        return node.type, None
    
    def visitArrayNode(self, node: ArrayNode):
        if len(node.elements) == 0: return Types.ANY, None
        expected_type, error = self.visit(node.elements[0])
        if error: return None, error
        for elem in node.elements[1:]:
            type, error = self.visit(elem)
            if error: return None, error
            if type != expected_type:
                return None, TypeError(elem.range, f"Expected array to be of type '{typeToStr(expected_type)}' because of first element but got '{typeToStr(type)}'")
        return arrayType(expected_type), None

    def visitArrayAccessNode(self, node: ArrayAccessNode): 
        arr, error = self.visit(node.name)
        if error: return None, error
        isDict = False
        if isinstance(arr, dictType): isDict = True  
        elif not isinstance(arr, arrayType) and arr != Types.STRING:
            return None, TypeError(node.name.range, f"Expected array or string but got '{typeToStr(arr)}'")
        index, error = self.visit(node.index)
        if error: return None, error
        if index != Types.NUMBER and not isDict:
            return None, TypeError(node.index.range, f"Expected index to be of type 'num' but got '{typeToStr(index)}'")
        elif isDict and index != Types.STRING:
            return None, TypeError(node.index.range, f"Expected key to be of type 'str' but got '{typeToStr(index)}'")
        if isinstance(arr, arrayType) or isDict:
            return arr.elementType, None
        else:
            return Types.STRING, None

    def visitArrayAssignNode(self, node: ArrayAssignNode):
        arr, error = self.visit(node.array)
        if error: return None, error
        value, error = self.visit(node.value)
        if error: return None, error
        if arr != value: return None, TypeError(node.range, f"Expected assigned value to be of type '{typeToStr(arr)}' but got '{typeToStr(value)}'")
        return arr, None

    def visitImportNode(self, node: ImportNode)->Tuple[Types, Error]:
        path = os.path.join(os.path.dirname(self.context.display_name), node.path.value)
        identifiers = node.ids
        if not os.path.isfile(path):
            return None, Error(node.path.range, None, f"File '{node.path.value}' does not exist")
        with open(path, 'r') as f:
            code = f.read()
            lexer = Lexer(path, code)
            tokens, error = lexer.tokenize()
            if error: return None, error
            parser = Parser(tokens)
            ast, error =  parser.parse()
            if error: return None, error
            BuildCache.module_asts[node.path.value] = ast
            savedCtx = self.context
            ctx = Context(path)
            ctx.symbol_table = SymbolTable()
            ctx.symbol_table.symbols = self.reserved.copy()
            self.context = ctx
            _, error = self.visit(ast)
            if error: return None, error
            if node.all:
                savedCtx.symbol_table.symbols.update(self.context.symbol_table.symbols)
            else:
                for identifier in identifiers:
                    val = self.context.symbol_table.get(identifier.value)
                    if val != None:
                        savedCtx.symbol_table.set(identifier.value, val)
                    else:
                        return None, Error(identifier.range, "Error", f"Cannot find identifier {identifier.value} in module {path}")
            self.context = savedCtx
        return Types.NULL, None
    
    def visitDictNode(self, node: DictNode):
        if len(node.values) == 0: return Types.ANY, None
        expectedType, error = self.visit(node.values[0][1])
        if error: return None, error
        for (key, value) in node.values:
            ktype, error = self.visit(key)
            if error: return None, error
            if ktype != Types.STRING:
                return None, TypeError(key.range, "Expected type of 'str'")
            vtype, error = self.visit(value)
            if error: return None, error
            if vtype != expectedType:
                return None, TypeError(value.range, f"Expected type of '{typeToStr(expectedType)}' because of type of first element")
        return dictType(expectedType), None

    def visitTypeCastNode(self, node: TypeCastNode):
        val, error = self.visit(node.value)
        if error: return None, error
        if val == Types.STRING:
            if node.type == Types.NUMBER:
                return Types.NUMBER, None
            elif node.type == Types.BOOL:
                return Types.BOOL, None
            elif isinstance(node.type, arrayType):
                if node.type.elementType == Types.STRING:
                    return node.type, None
        elif val == Types.NUMBER:
            if node.type == Types.STRING:
                return Types.STRING, None
            elif node.type == Types.BOOL:
                return Types.BOOL, None
        elif val == Types.BOOL:
            if node.type == Types.NUMBER:
                return Types.NUMBER, None
        elif isinstance(val, arrayType):
            if node.type == Types.STRING:
                return Types.STRING, None
            if isinstance(node.type, arrayType):
                if node.type.elementType == Types.NUMBER and val.elementType == Types.STRING:
                    return arrayType(Types.NUMBER), None
                elif node.type.elementType == Types.BOOL and val.elementType == Types.STRING:
                    return arrayType(Types.BOOL), None
                elif node.type.elementType == Types.STRING and val.elementType == Types.NUMBER:
                    return arrayType(Types.STRING), None
                elif node.type.elementType == Types.NUMBER and val.elementType == Types.BOOL:
                    return arrayType(Types.NUMBER), None
                elif node.type.elementType == Types.BOOL and val.elementType == Types.NUMBER:
                    return arrayType(Types.BOOL), None
        return None, TypeError(node.range, f"Cannot cast {typeToStr(val)} to {typeToStr(node.type)}")
                
                
            
