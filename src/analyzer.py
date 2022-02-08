from os import path
from typing import List
from context import Context, SymbolTable
from errors import TypeError, SyntaxError, NameError, IOError
from lexer import TokType
from lexer import Lexer
from parser import Parser
from interfaces.astree import *
from itypes import *


class BuildCache:
    module_asts = {}


class Analyzer(Visitor):
    comparason_ops = (
        TokType.EEQ,
        TokType.NEQ,
        TokType.GT,
        TokType.LT,
        TokType.GTE,
        TokType.LTE,
        TokType.NEQ,
    )
    arithmetic_ops_1 = (
        TokType.PLUS,
        TokType.MINUS,
        TokType.MULT,
        TokType.DIV,
        TokType.POW,
        TokType.MOD,
    )
    arithmetic_ops_2 = (TokType.SL, TokType.SR)

    def __init__(self, context: Context):
        self.context = context
        self.reserved = context.symbol_table.symbols.copy()
        self.funcStack: List[fncType] = []
        self.inLoop = [False]
        self.shoudlReturn = False

    def visit(self, node: Node) -> Types:
        return super().visit(node)

    def analyze(self, entry_node: Node):
        self.visit(entry_node)

    def visitIntNode(self, _):
        return Types.INT

    def visitFloatNode(self, _: FloatNode):
        return Types.FLOAT

    def visitStrNode(self, _: StrNode):
        return Types.STRING

    def cast(self, node: Node, type):
        return NumOpNode(
            node,
            Token(TokType.KEYWORD, node.range, "as"),
            TypeNode(type, node.range),
            node.range,
        )

    def isNumeric(self, *types):
        isNum = True
        for type in types:
            isNum = isNum and (type == Types.INT or type == Types.FLOAT)
        return isNum

    def visitNumOpNode(self, node: NumOpNode):
        left = self.visit(node.left_node)
        right = self.visit(node.right_node)
        if node.op.type in self.arithmetic_ops_1:
            # IMPROVE: This if statement and the one beneath it are repetitive.
            if left == Types.FLOAT and right == Types.INT:
                node.right_node = self.cast(node.right_node, Types.FLOAT)
                return Types.FLOAT
            if left == Types.INT and right == Types.FLOAT:
                node.left_node = self.cast(node.left_node, Types.FLOAT)
                return Types.FLOAT
            # Special case for division
            if node.op.type == TokType.DIV or node.op.type == TokType.POW:
                if left == Types.INT:
                    node.left_node = self.cast(node.left_node, Types.FLOAT)
                if right == Types.INT:
                    node.right_node = self.cast(node.right_node, Types.FLOAT)
                if self.isNumeric(left, right):
                    return Types.FLOAT

            # Checking for adding nums and concatenating
            if (
                (
                    left == Types.STRING
                    or self.isNumeric(left)
                    or isinstance(left, arrayType)
                )
                and left == right
                and node.op.type == TokType.PLUS
            ):
                return left
            # All these ops are valid numeric ops
            if self.isNumeric(left) and left == right:
                return left

        elif node.op.type in self.arithmetic_ops_2 or node.op.isKeyword("xor"):
            if isinstance(left, arrayType) and (
                node.op.type == TokType.SL or node.op.type == TokType.SL
            ):
                if (not self.isNumeric(right)) and node.op.type == TokType.SR:
                    TypeError(
                        node.right_node.range,
                        f"Expected type '{typeToStr(Types.INT)}' or '{typeToStr(Types.FLOAT)}' but got type '{typeToStr(right)}' on bit shift",
                    ).throw()
                if left.elementType != right and node.op.type == TokType.SL:
                    TypeError(
                        node.right_node.range,
                        f"Expected type '{typeToStr(left.elementType)}' but got type '{typeToStr(right)}' on append",
                    ).throw()
                return left if node.op.type == TokType.SL else left.elementType
            # IMPROVE: Duplicate code with second if of or/and check
            if self.isNumeric(left, right):
                if left == Types.FLOAT:
                    node.left_node = self.cast(node.left_node, Types.INT)
                if right == Types.FLOAT:
                    node.right_node = self.cast(node.right_node, Types.INT)
                return Types.INT
        elif node.op.type in Analyzer.comparason_ops or node.op.isKeyword("is"):
            if node.op.type in Analyzer.comparason_ops:
                if left == Types.FLOAT and right == Types.INT:
                    node.right_node = self.cast(node.right_node, Types.FLOAT)
                if left == Types.INT and right == Types.FLOAT:
                    node.left_node = self.cast(node.left_node, Types.FLOAT)
            return Types.BOOL
        elif node.op.isKeyword("or") or node.op.isKeyword("and"):
            if left == right == Types.BOOL:
                return Types.BOOL
            if self.isNumeric(left, right):
                if left == Types.FLOAT:
                    node.left_node = self.cast(node.left_node, Types.INT)
                if right == Types.FLOAT:
                    node.right_node = self.cast(node.right_node, Types.INT)
                return Types.INT
        elif node.op.isKeyword("in"):
            if isinstance(right, arrayType) or right == Types.STRING:
                return Types.BOOL
            else:
                TypeError(
                    node.right_node.range,
                    f"Illegal operation in on type '{typeToStr(right)}' expected type 'str' or 'array'",
                ).throw()
        elif node.op.isKeyword("as"):
            if left == right:
                node = node.left_node
                return right
            if self.isCastable(left, right):
                return right
            else:
                TypeError(
                    range, f"Cannot cast {typeToStr(left)} to {typeToStr(right)}"
                ).throw()
        TypeError(
            node.range,
            f"Illegal operation {node.op} between types '{typeToStr(left)}' and '{typeToStr(right)}'",
        ).throw()

    def visitUnaryNode(self, node: UnaryNode):
        type = self.visit(node.value)
        if type != Types.BOOL and (not self.isNumeric(type)):
            TypeError(
                node.value.range,
                f"Expected type of '{typeToStr(Types.BOOL)}', '{typeToStr(Types.FLOAT)}' or '{typeToStr(Types.FLOAT)}' but got '{typeToStr(type)}'",
            ).throw()
        if node.op.type == TokType.MINUS and (not self.isNumeric(type)):
            TypeError(
                node.value.range,
                f"Illegal negative {typeToStr(type)}",
            ).throw()
        if node.op.type == TokType.NOT:
            if type == Types.BOOL:
                return Types.BOOL
            else:
                if type == Types.FLOAT:
                    node.value = self.cast(node.value, Types.INT)
                return Types.INT
        else:
            return type

    def visitIncrDecrNode(self, node: IncrDecrNode):
        action = "decrement" if node.id.type == TokType.MINUS_MINUS else "increment"
        if not (
            isinstance(node.identifier, ArrayAccessNode)
            or isinstance(node.identifier, VarAccessNode)
        ):
            SyntaxError(
                node.identifier.range, f"Illegal {action} on non-identifier"
            ).throw()
        type = self.visit(node.identifier)
        if self.isNumeric(type):
            return type
        else:
            TypeError(
                node.range, f"Illegal {action} operation on type '{typeToStr(type)}'"
            ).throw()

    def visitVarAccessNode(self, node: VarAccessNode):
        var_name = node.var_name.value
        value = self.context.symbol_table.get(var_name)
        if value == None:
            NameError(node.var_name.range,
                      f"'{var_name}' is not defined").throw()
        return value

    def visitStmtsNode(self, node: StmtsNode):
        rt_value = Types.VOID
        for expr in node.stmts:
            s = self.visit(expr)
            e = s
            if self.shoudlReturn:
                self.shoudlReturn = False
                rt_value = e
        return rt_value

    def visitVarAssignNode(self, node: VarAssignNode):
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
            expected_type = self.context.symbol_table.get(
                var_name) or Types.VOID
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

    def condition_check(self, cond_node: Node):
        cond_type = self.visit(cond_node)
        if cond_type != Types.BOOL and (not self.isNumeric(cond_type)):
            TypeError(
                cond_node.range,
                f"Expected type '{typeToStr(Types.BOOL)}', '{typeToStr(Types.INT)}' or '{typeToStr(Types.FLOAT)}' but got type '{typeToStr(cond_type)}'",
            ).throw()
        if self.isNumeric(cond_type):
            cond_node = self.cast(cond_node, Types.BOOL)
        return cond_node

    def visitIfNode(self, node: IfNode):
        for i in range(len(node.cases)):
            cond, expr = node.cases[i]
            node.cases[i] = (self.condition_check(cond), expr)
            self.shoudlReturn = False
            returned_type = self.visit(expr)
        if node.else_case:
            returned_type = self.visit(node.else_case)
        # WARNING: Might have to check this concdition all-through the code.
        return returned_type if self.shoudlReturn else Types.VOID

    def visitForNode(self, node: ForNode):
        self.visit(node.init)
        node.cond = self.condition_check(node.cond)
        index = len(self.inLoop)
        self.inLoop.append(True)
        self.visit(node.stmt)
        self.inLoop.pop(index)
        self.visit(node.incr_decr)
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
        self.visit(node.stmt)
        self.context.symbol_table.set(node.identifier.value)
        self.inLoop.pop(index)
        return Types.VOID

    def visitWhileNode(self, node: WhileNode):
        node.cond = self.condition_check(node.cond)
        index = len(self.inLoop)
        self.inLoop.append(True)
        self.visit(node.stmt)
        self.inLoop.pop(index)
        return Types.VOID

    def visitFncDefNode(self, node: FncDefNode):
        fnc_name = node.var_name.value
        if fnc_name in self.reserved.keys():
            TypeError(
                node.var_name.range,
                node.var_name.range,
                f"{fnc_name} is a reserved constant",
            ).throw()
        if isinstance(self.context.symbol_table.get(fnc_name), fncType):
            NameError(
                node.var_name.range,
                f"{fnc_name} is already defined",
            ).throw()
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
        if (
            not isinstance(node.body, StmtsNode)
            and self.shoudlReturn == False
            and bodyType != Types.VOID
        ):
            node.body = ReturnNode(node.body, node.body.range)
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

    def visitReturnNode(self, node: ReturnNode):
        self.shoudlReturn = True
        if len(self.funcStack) == 0:
            SyntaxError(
                node.range, "Illegal return outside a function").throw()
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

    def visitContinueNode(self, node: ContinueNode):
        if not self.inLoop[-1]:
            SyntaxError(
                node.range, "Illegal continue outside of a loop").throw()
        return Types.VOID

    def visitBreakNode(self, node: BreakNode):
        if not self.inLoop[-1]:
            SyntaxError(node.range, "Illegal break outside of a loop").throw()
        return Types.VOID

    def visitFncCallNode(self, node: FncCallNode):
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
        collection = self.visit(node.name)
        index = self.visit(node.index)
        if isinstance(collection, dictType):
            if index != Types.STRING:
                TypeError(
                    node.index.range,
                    f"Expected key to be of type '{typeToStr(Types.STRING)}' but got '{typeToStr(index)}'",
                ).throw()
            return collection.elementType
        elif isinstance(collection, arrayType) or collection == Types.STRING:
            if not self.isNumeric(index):
                TypeError(
                    node.index.range,
                    f"Expected key to be of type '{typeToStr(Types.INT)}' but got '{typeToStr(index)}'",
                ).throw()
            return (
                Types.STRING if collection == Types.STRING else collection.elementType
            )
        else:
            TypeError(
                node.name.range,
                f"Expected array, dict or string but got '{typeToStr(collection)}'",
            ).throw()

    def visitArrayAssignNode(self, node: ArrayAssignNode):
        arr: arrayType = self.visit(node.array)
        value = self.visit(node.value)
        if arr != value:
            TypeError(
                node.range,
                f"Expected assigned value to be of type '{typeToStr(arr)}' but got '{typeToStr(value)}'",
            ).throw()
        return arr

    def visitImportNode(self, node: ImportNode):
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
            self.visit(ast)
            if node.all:
                savedCtx.symbol_table.symbols.update(
                    self.context.symbol_table.symbols)
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
                TypeError(
                    key.range, f"Expected type of '{typeToStr(Types.STRING)}'"
                ).throw()
            vtype = self.visit(value)

            if vtype != expectedType:
                TypeError(
                    value.range,
                    f"Expected type of '{typeToStr(expectedType)}' because of type of first element",
                ).throw()
        return dictType(expectedType)

    # TODO: Look for types that are incompatible for casting.
    def isCastable(self, current_type, target_type):
        return True
