from os import path
from typing import List
from context import Context, SymbolTable
from errors import Error, TypeError, SyntaxError, NameError, IOError
from lexer import TokType
from lexer import Lexer
from parser import Parser
from interfaces.astree import *
from itypes import *


class BuildCache:
    module_asts = {}


class Analyzer(Visitor):
    def __init__(self, context: Context):
        self.context = context
        self.reserved = context.symbol_table.symbols.copy()
        self.funcStack: List[fncType] = []
        self.inLoop = [False]
        self.shoudlReturn = False

    def visit(self, node: Node) -> Tuple[Types, Error]:
        return super().visit(node)

    def visitNumNode(self, _: NumNode) -> Tuple[Types, Error]:
        return Types.NUMBER

    def visitStrNode(self, _: StrNode) -> Tuple[Types, Error]:
        return Types.STRING

    def visitNumOpNode(self, node: NumOpNode) -> Tuple[Types, Error]:
        left = self.visit(node.left_node)
        right = self.visit(node.right_node)
        if node.op.type in (
            TokType.PLUS,
            TokType.MINUS,
            TokType.MULT,
            TokType.DIV,
            TokType.MOD,
            TokType.POW,
            TokType.SL,
            TokType.SR,
        ):
            if left == Types.NUMBER and right == left:
                return Types.NUMBER
            elif (
                left == Types.STRING
                and right == Types.STRING
                and node.op.type == TokType.PLUS
            ):
                return Types.STRING
            elif (
                (isinstance(left, arrayType) and right == Types.NUMBER)
                or (isinstance(right, arrayType) and left == Types.NUMBER)
            ) and node.op.type == TokType.MULT:
                return left
            elif (
                isinstance(left, arrayType) and left == right
            ) and node.op.type == TokType.PLUS:
                return left
            elif node.op.type == TokType.SL or node.op.type == TokType.SR:
                if right != Types.NUMBER and left == Types.NUMBER:
                    TypeError(
                        node.right_node.range,
                        f"Expected type '{typeToStr(Types.NUMBER)}' but got type '{typeToStr(right)}' on bit shift",
                    ).throw()
                if isinstance(left, arrayType) and left.elementType != right:
                    TypeError(
                        node.right_node.range,
                        f"Expected type '{typeToStr(left.elementType)}' but got type '{typeToStr(right)}' on append",
                    ).throw()
                if isinstance(left, arrayType) or left == Types.NUMBER:
                    return left
            elif (
                left == Types.NUMBER
                and right == Types.STRING
                or right == Types.NUMBER
                and left == Types.STRING
                and node.op.type in (TokType.PLUS, TokType.MULT)
            ):
                return Types.STRING
        elif node.op.type in (
            TokType.EEQ,
            TokType.NEQ,
            TokType.GT,
            TokType.LT,
            TokType.GTE,
            TokType.LTE,
            TokType.NEQ,
        ):
            if left == right and left == Types.NUMBER or left == Types.BOOL:
                return Types.BOOL
            elif left == right and left == Types.STRING and node.op.type == TokType.EEQ:
                return Types.BOOL
            elif left == right and left == Types.STRING and node.op.type == TokType.NEQ:
                return Types.BOOL
            elif (
                left == Types.BOOL
                and right == Types.NUMBER
                or left == Types.BOOL
                and right == Types.NUMBER
            ):
                return Types.BOOL
        elif (
            node.op.isKeyword("or")
            or node.op.isKeyword("and")
            or node.op.isKeyword("xor")
        ):
            if left == right == Types.NUMBER:
                return Types.NUMBER
            elif left == right == Types.BOOL:
                return Types.BOOL
        elif node.op.isKeyword("in"):
            if isinstance(right, arrayType) or right == Types.STRING:
                return Types.BOOL
            else:
                TypeError(
                    node.right_node.range,
                    f"Illegal operation in on type '{typeToStr(right)}' expected type 'str' or 'array'",
                ).throw()
        elif node.op.isKeyword("as"):
            return self.checkisCastable(left, right, node.range)
        elif node.op.isKeyword("is"):
            return Types.BOOL
        TypeError(
            node.range,
            f"Illegal operation {node.op} between types '{typeToStr(left)}' and '{typeToStr(right)}'",
        ).throw()

    def visitUnaryNode(self, node: UnaryNode) -> Tuple[Types, Error]:
        type = self.visit(node.tok)
        if node.op.type == TokType.MINUS and type == Types.NUMBER:
            return Types.NUMBER
        elif node.op.type == TokType.NOT:
            if type == Types.BOOL:
                return Types.BOOL
            elif type == Types.NUMBER:
                return Types.NUMBER
        else:
            return type

    def visitIncrDecrNode(self, node: IncrDecrNode) -> Tuple[Types, Error]:
        action = "decrement" if node.id.type == TokType.MINUS_MINUS else "increment"
        if not (
            isinstance(node.identifier, ArrayAccessNode)
            or isinstance(node.identifier, VarAccessNode)
        ):
            SyntaxError(
                node.identifier.range, f"Variable is required for {action}"
            ).throw()
        value = self.visit(node.identifier)
        if value == Types.NUMBER:
            return Types.NUMBER
        else:
            TypeError(
                node.range, f"Illegal {action} operation on type '{typeToStr(value)}'"
            ).throw()

    def visitVarAccessNode(self, node: VarAccessNode) -> Tuple[Types, Error]:
        var_name = node.var_name.value
        value = self.context.symbol_table.get(var_name)
        if value == None:
            NameError(
                node.var_name.range, node.var_name.range, f"'{var_name}' is not defined"
            )
        return value

    def visitStmtsNode(self, node: StmtsNode) -> Tuple[Types, Error]:
        rt = Types.VOID
        for expr in node.stmts:
            s = self.visit(expr)
            e = s

            if self.shoudlReturn:
                self.shoudlReturn = False
                rt = e
        return rt

    def visitVarAssignNode(self, node: VarAssignNode) -> Tuple[Types, Error]:
        var_name = node.var_name.value
        if var_name.isupper() and self.context.symbol_table.get(var_name) != None:
            TypeError(
                node.var_name.range,
                node.range,
                f"Cannot change value of the constant {var_name}",
            )
        if var_name in self.reserved.keys():
            TypeError(
                node.var_name.range,
                node.var_name.range,
                f"{var_name} is a reserved constant",
            )
        if node.val_type:
            expected_type = self.visit(node.val_type)

        else:
            expected_type = self.context.symbol_table.get(var_name) or Types.VOID
        type = self.visit(node.value)
        if type == Types.ANY and expected_type == Types.VOID:
            TypeError(
                node.range,
                f"Type cannot be infered be sure to add a type on variable assignment",
            ).throw()
        elif expected_type != Types.VOID and type == Types.ANY:
            type = expected_type
        if type == expected_type or expected_type == Types.VOID:
            self.context.symbol_table.set(var_name, type)
            return type
        else:
            TypeError(
                node.range,
                f"Assigning '{typeToStr(type)}' to type '{typeToStr(expected_type)}'",
            ).throw()

    def visitIfNode(self, node: IfNode) -> Tuple[Types, Error]:
        for cond, expr in node.cases:
            cond_type = self.visit(cond)

            if not (cond_type == Types.NUMBER or cond_type == Types.BOOL):
                TypeError(
                    cond.range,
                    f"Expected type 'num' or 'bool' but got type '{typeToStr(cond_type)}'",
                ).throw()
            else:
                self.shoudlReturn = False
                _ = self.visit(expr)

        if node.else_case:
            _ = self.visit(node.else_case)

        return _ if self.shoudlReturn else Types.VOID

    def visitForNode(self, node: ForNode) -> Tuple[Types, Error]:
        _ = self.visit(node.init)
        cond_type = self.visit(node.cond)
        if not (cond_type == Types.NUMBER or cond_type == Types.BOOL):
            TypeError(
                node.cond.range,
                f"Expected type 'num' or 'bool' but got type '{cond_type}'",
            ).throw()
        index = len(self.inLoop)
        self.inLoop.append(True)
        _ = self.visit(node.stmt)
        self.inLoop.pop(index)
        _ = self.visit(node.incr_decr)
        return Types.VOID

    def visitForEachNode(self, node: ForEachNode):
        it = self.visit(node.iterator)
        if (
            (not isinstance(it, arrayType))
            and (it != Types.STRING)
            and (not isinstance(it, dictType))
        ):
            TypeError(
                node.iterator.range,
                f"Expected type of 'str', dict or 'array' but got type '{typeToStr(it)}'",
            ).throw()
        index = len(self.inLoop)
        self.inLoop.append(True)
        type = (
            Types.STRING
            if it == Types.STRING or isinstance(it, dictType)
            else it.elementType
        )
        self.context.symbol_table.set(node.identifier.value, type)
        _ = self.visit(node.stmt)
        self.context.symbol_table.set(node.identifier.value)
        self.inLoop.pop(index)
        return Types.VOID

    def visitWhileNode(self, node: WhileNode) -> Tuple[Types, Error]:
        cond_type = self.visit(node.cond)
        if not (cond_type == Types.NUMBER or cond_type == Types.BOOL):
            TypeError(
                node.cond.range,
                f"Expected type 'num' or 'bool' but got type '{cond_type}'",
            ).throw()
        index = len(self.inLoop)
        self.inLoop.append(True)
        _ = self.visit(node.stmt)
        self.inLoop.pop(index)
        return Types.VOID

    def visitFncDefNode(self, node: FncDefNode) -> Tuple[Types, Error]:
        fnc_name = node.var_name.value
        if fnc_name in self.reserved.keys():
            TypeError(
                node.var_name.range,
                node.var_name.range,
                f"{fnc_name} is a reserved constant",
            )
        if isinstance(self.context.symbol_table.get(fnc_name), fncType):
            NameError(
                node.var_name.range,
                node.var_name.range,
                f"{fnc_name} is already defined",
            )
        fnc_type = self.visit(node.return_type)
        if fnc_type == None:
            TypeError(
                node.var_name.range, f"No return type for function '{fnc_name}'"
            ).throw()
        args = []
        count = {}
        savedTbl = self.context.symbol_table.copy()
        for arg, t in node.args:
            type = self.visit(t)
            if count.get(arg.value) != None:
                NameError(
                    arg.range,
                    f"parameter '{arg.value}' defined twice in function parameters",
                ).throw()
            elif type == None:
                TypeError(
                    arg.range, f"parameter '{arg.value}' has an unknown type"
                ).throw()
            elif arg.value == fnc_name:
                NameError(
                    arg.range, f"parameter '{arg.value}' has same name as function"
                ).throw()
            else:
                count[arg.value] = 1
                self.context.symbol_table.set(arg.value, type)
                args.append(type)
        rtype = fncType(fnc_type, args)
        self.context.symbol_table.set(fnc_name, rtype)
        self.funcStack.append(fnc_type)
        bodyType = self.visit(node.body)
        self.funcStack.pop()
        self.context.symbol_table = savedTbl
        if bodyType != fnc_type:
            TypeError(
                node.range,
                f"Expected return type of '{typeToStr(fnc_type)}' but got '{typeToStr(bodyType)}'",
            ).throw()
        if fnc_name:
            self.context.symbol_table.set(fnc_name, rtype)
        return rtype

    def visitReturnNode(self, node: ReturnNode) -> Tuple[Types, Error]:
        self.shoudlReturn = True
        if len(self.funcStack) == 0:
            SyntaxError(node.range, "Illegal return outside a function").throw()
        if node.value:
            val = self.visit(node.value)

            rt = self.funcStack[-1]
            if rt == val:
                return val
            else:
                TypeError(
                    node.range,
                    f"Expected return type of '{typeToStr(rt)}' but got '{typeToStr(val)}'",
                ).throw()
        else:
            return Types.VOID

    def visitContinueNode(self, node: ContinueNode) -> Tuple[Types, Error]:
        if not self.inLoop[-1]:
            SyntaxError(node.range, "Illegal continue outside of a loop").throw()
        return Types.VOID

    def visitBreakNode(self, node: BreakNode) -> Tuple[Types, Error]:
        if not self.inLoop[-1]:
            SyntaxError(node.range, "Illegal break outside of a loop").throw()
        return Types.VOID

    def visitFncCallNode(self, node: FncCallNode) -> Tuple[Types, Error]:
        fn = self.visit(node.name)
        if not isinstance(fn, fncType):
            TypeError(
                node.range, f"{node.name.var_name.value} is not a function"
            ).throw()
        if len(fn.argTypes) != len(node.args):
            TypeError(
                node.range,
                f"Expected {len(fn.argTypes)} arguments, but got {len(node.args)}",
            ).throw()
        for i in range(len(node.args)):
            argType = self.visit(node.args[i])

            if (
                argType != fn.argTypes[i]
                and not fn.argTypes[i] == Types.ANY
                and not argType == Types.ANY
            ):
                TypeError(
                    node.args[i].range,
                    f"Expected type '{typeToStr(fn.argTypes[i])}' but got '{typeToStr(argType)}'",
                ).throw()
        return fn.returnType

    def visitTypeNode(self, node: TypeNode):
        return node.type

    def visitArrayNode(self, node: ArrayNode):
        if len(node.elements) == 0:
            return Types.ANY
        expected_type = self.visit(node.elements[0])
        for elem in node.elements[1:]:
            type = self.visit(elem)

            if type != expected_type:
                TypeError(
                    elem.range,
                    f"Expected array to be of type '{typeToStr(expected_type)}' because of first element but got '{typeToStr(type)}'",
                ).throw()
        return arrayType(expected_type)

    def visitArrayAccessNode(self, node: ArrayAccessNode):
        arr = self.visit(node.name)
        isDict = False
        if isinstance(arr, dictType):
            isDict = True
        elif not isinstance(arr, arrayType) and arr != Types.STRING:
            TypeError(
                node.name.range, f"Expected array or string but got '{typeToStr(arr)}'"
            ).throw()
        index = self.visit(node.index)
        if index != Types.NUMBER and not isDict:
            TypeError(
                node.index.range,
                f"Expected index to be of type 'num' but got '{typeToStr(index)}'",
            ).throw()
        elif isDict and index != Types.STRING:
            TypeError(
                node.index.range,
                f"Expected key to be of type 'str' but got '{typeToStr(index)}'",
            ).throw()
        if isinstance(arr, arrayType) or isDict:
            return arr.elementType
        else:
            return Types.STRING

    def visitArrayAssignNode(self, node: ArrayAssignNode):
        arr = self.visit(node.array)
        value = self.visit(node.value)
        if arr != value:
            TypeError(
                node.range,
                f"Expected assigned value to be of type '{typeToStr(arr)}' but got '{typeToStr(value)}'",
            ).throw()
        return arr

    def visitImportNode(self, node: ImportNode) -> Tuple[Types, Error]:
        module_path = path.join(
            path.dirname(self.context.display_name), node.path.value
        )
        identifiers = node.ids
        if not path.isfile(module_path):
            IOError(
                node.path.range, f"Could not find module named '{node.path.value}'"
            ).throw()
        with open(module_path, "r") as f:
            code = f.read()
            lexer = Lexer(module_path, code)
            tokens = lexer.tokenize()

            parser = Parser(tokens)
            ast = parser.parse()

            BuildCache.module_asts[node.path.value] = ast
            savedCtx = self.context
            ctx = Context(module_path)
            ctx.symbol_table = SymbolTable()
            ctx.symbol_table.symbols = self.reserved.copy()
            self.context = ctx
            _ = self.visit(ast)
            if node.all:
                savedCtx.symbol_table.symbols.update(self.context.symbol_table.symbols)
            else:
                for identifier in identifiers:
                    val = self.context.symbol_table.get(identifier.value)
                    if val != None:
                        savedCtx.symbol_table.set(identifier.value, val)
                    else:
                        TypeError(
                            identifier.range,
                            f"Cannot find identifier {identifier.value} in module {module_path}",
                        ).throw()
            self.context = savedCtx
        return Types.VOID

    def visitDictNode(self, node: DictNode):
        if len(node.values) == 0:
            return Types.ANY
        expectedType = self.visit(node.values[0][1])
        for (key, value) in node.values:
            ktype = self.visit(key)

            if ktype != Types.STRING:
                TypeError(key.range, "Expected type of 'str'").throw()
            vtype = self.visit(value)

            if vtype != expectedType:
                TypeError(
                    value.range,
                    f"Expected type of '{typeToStr(expectedType)}' because of type of first element",
                ).throw()
        return dictType(expectedType)

    def checkisCastable(self, left, right, range):
        if left == Types.STRING:
            if right == Types.NUMBER:
                return Types.NUMBER
            elif right == Types.BOOL:
                return Types.BOOL
            elif isinstance(right, arrayType):
                if right.elementType == Types.STRING:
                    return right
        elif left == Types.NUMBER:
            if right == Types.STRING:
                return Types.STRING
            elif right == Types.BOOL:
                return Types.BOOL
        elif left == Types.BOOL:
            if right == Types.NUMBER:
                return Types.NUMBER
        elif isinstance(left, arrayType):
            if right == Types.STRING:
                return Types.STRING
            if isinstance(right, arrayType):
                if (
                    right.elementType == Types.NUMBER
                    and left.elementType == Types.STRING
                ):
                    return arrayType(Types.NUMBER)
                elif (
                    right.elementType == Types.BOOL and left.elementType == Types.STRING
                ):
                    return arrayType(Types.BOOL)
                elif (
                    right.elementType == Types.STRING
                    and left.elementType == Types.NUMBER
                ):
                    return arrayType(Types.STRING)
                elif (
                    right.elementType == Types.NUMBER and left.elementType == Types.BOOL
                ):
                    return arrayType(Types.NUMBER)
                elif (
                    right.elementType == Types.BOOL and left.elementType == Types.NUMBER
                ):
                    return arrayType(Types.BOOL)
        TypeError(range, f"Cannot cast {typeToStr(left)} to {typeToStr(right)}").throw()
