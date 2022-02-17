from os import path
from typing import List
from context import Context, SymbolTable
from errors import TypeError, SyntaxError, NameError, IOError
from flotypes import FloArray, FloBool, FloFloat, FloInlineFunc, FloInt, FloStr, FloType, FloVoid
from lexer import TokType
from lexer import Lexer
from parser import Parser
from interfaces.astree import *


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
        self.context = context.copy()
        self.reserved = context.symbol_table.symbols.copy()
        self.funcStack: List[FloInlineFunc] = []
        self.inLoop = [False]
        self.shoudlReturn = False

    def visit(self, node: Node):
        return super().visit(node)

    def analyze(self, entry_node: Node):
        self.visit(entry_node)

    def visitIntNode(self, _):
        return FloInt

    def visitFloatNode(self, _: FloatNode):
        return FloFloat

    def visitStrNode(self, _: StrNode):
        return FloStr

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
            isNum = isNum and (type == FloInt or type == FloFloat)
        return isNum

    def visitNumOpNode(self, node: NumOpNode):
        left = self.visit(node.left_node)
        right = self.visit(node.right_node)
        if node.op.type in self.arithmetic_ops_1:
            # IMPROVE: This if statement and the one beneath it are repetitive.
            if left == FloFloat and right == FloInt:
                node.right_node = self.cast(node.right_node, FloFloat)
                return FloFloat
            if left == FloInt and right == FloFloat:
                node.left_node = self.cast(node.left_node, FloFloat)
                return FloFloat
            # Special case for division
            if node.op.type == TokType.DIV or node.op.type == TokType.POW:
                if left == FloInt:
                    node.left_node = self.cast(node.left_node, FloFloat)
                if right == FloInt:
                    node.right_node = self.cast(node.right_node, FloFloat)
                if self.isNumeric(left, right):
                    return FloFloat

            # Checking for adding nums and concatenating
            if (
                (
                    left == FloStr
                    or self.isNumeric(left)
                    or isinstance(left, FloArray)
                )
                and left == right
                and node.op.type == TokType.PLUS
            ):
                return left
            # All these ops are valid numeric ops
            if self.isNumeric(left) and left == right:
                return left

        elif node.op.type in self.arithmetic_ops_2 or node.op.isKeyword("xor"):
            if isinstance(left, FloArray) and (
                node.op.type == TokType.SL or node.op.type == TokType.SL
            ):
                if (not self.isNumeric(right)) and node.op.type == TokType.SR:
                    TypeError(
                        node.right_node.range,
                        f"Expected type '{FloInt.str()}' or '{FloFloat.str()}' but got type '{right.str()}' on bit shift",
                    ).throw()
                if left.elm_type != right and node.op.type == TokType.SL:
                    TypeError(
                        node.right_node.range,
                        f"Expected type '{left.elm_type.str()}' but got type '{right.str()}' on append",
                    ).throw()
                return left if node.op.type == TokType.SL else left.elm_type
            # IMPROVE: Duplicate code with second if of or/and check
            if self.isNumeric(left, right):
                if left == FloFloat:
                    node.left_node = self.cast(node.left_node, FloInt)
                if right == FloFloat:
                    node.right_node = self.cast(node.right_node, FloInt)
                return FloInt
        elif node.op.type in Analyzer.comparason_ops or node.op.isKeyword("is"):
            if node.op.type in Analyzer.comparason_ops:
                if left == FloFloat and right == FloInt:
                    node.right_node = self.cast(node.right_node, FloFloat)
                if left == FloInt and right == FloFloat:
                    node.left_node = self.cast(node.left_node, FloFloat)
            return FloBool
        elif node.op.isKeyword("or") or node.op.isKeyword("and"):
            if left == right == FloBool:
                return FloBool
            if self.isNumeric(left, right):
                if left == FloFloat:
                    node.left_node = self.cast(node.left_node, FloInt)
                if right == FloFloat:
                    node.right_node = self.cast(node.right_node, FloInt)
                return FloInt
        elif node.op.isKeyword("in"):
            if isinstance(right, FloArray) or right == FloStr:
                return FloBool
            else:
                TypeError(
                    node.right_node.range,
                    f"Illegal operation in on type '{right.str()}' expected type 'str' or 'array'",
                ).throw()
        elif node.op.isKeyword("as"):
            if left == right:
                node = node.left_node
            return right

        TypeError(
            node.range,
            f"Illegal operation {node.op} between types '{left.str()}' and '{right.str()}'",
        ).throw()

    def visitUnaryNode(self, node: UnaryNode):
        type = self.visit(node.value)
        if type != FloBool and (not self.isNumeric(type)):
            TypeError(
                node.value.range,
                f"Expected type of '{FloBool.str()}', '{FloFloat.str()}' or '{FloFloat.str()}' but got '{type.str()}'",
            ).throw()
        if node.op.type == TokType.MINUS and (not self.isNumeric(type)):
            TypeError(
                node.value.range,
                f"Illegal negative {type}",
            ).throw()
        if node.op.type == TokType.NOT:
            if type == FloBool:
                return FloBool
            else:
                if type == FloFloat:
                    node.value = self.cast(node.value, FloInt)
                return FloInt
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
                node.range, f"Illegal {action} operation on type '{type.str()}'"
            ).throw()

    def visitVarAccessNode(self, node: VarAccessNode):
        var_name = node.var_name.value
        value = self.context.symbol_table.get(var_name)
        if value == None:
            NameError(node.var_name.range,
                      f"'{var_name}' is not defined").throw()
        return value

    def visitStmtsNode(self, node: StmtsNode):
        rt_value = FloVoid
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
                var_name) or FloVoid
        type = self.visit(node.value)
        if type == None and expected_type == FloVoid:
            TypeError(
                node.range,
                f"Type cannot be infered be sure to add a type on variable assignment",
            ).throw()
        elif expected_type != FloVoid and type == None:
            type = expected_type
        if type == expected_type or expected_type == FloVoid:
            self.context.symbol_table.set(var_name, type)
            return type
        else:
            TypeError(
                node.range,
                f"Assigning '{type.str()}' to type '{expected_type.str()}'",
            ).throw()

    def condition_check(self, cond_node: Node):
        cond_type = self.visit(cond_node)
        if (cond_type.__class__ != FloBool and cond_type != FloBool) and (not self.isNumeric(cond_type)):
            TypeError(
                cond_node.range,
                f"Expected type '{FloBool.str()}', '{FloInt.str()}' or '{FloFloat.str()}' but got type '{cond_type.str()}'",
            ).throw()
        if self.isNumeric(cond_type):
            cond_node = self.cast(cond_node, FloBool)
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
        return returned_type if self.shoudlReturn else FloVoid

    def visitForNode(self, node: ForNode):
        self.visit(node.init)
        node.cond = self.condition_check(node.cond)
        index = len(self.inLoop)
        self.inLoop.append(True)
        self.visit(node.stmt)
        self.inLoop.pop(index)
        self.visit(node.incr_decr)
        return FloVoid

    def visitForEachNode(self, node: ForEachNode):
        it = self.visit(node.iterator)
        if (
            (not isinstance(it, FloArray))
            and (it != FloStr)
        ):
            TypeError(
                node.iterator.range,
                f"Expected type of 'str', dict or 'array' but got type '{it.str()}'",
            ).throw()
        index = len(self.inLoop)
        self.inLoop.append(True)
        type = (
            FloStr
            if it == FloStr
            else it.elm_type
        )
        self.context.symbol_table.set(node.identifier.value, type)
        self.visit(node.stmt)
        self.context.symbol_table.set(node.identifier.value)
        self.inLoop.pop(index)
        return FloVoid

    def visitWhileNode(self, node: WhileNode):
        node.cond = self.condition_check(node.cond)
        index = len(self.inLoop)
        self.inLoop.append(True)
        self.visit(node.stmt)
        self.inLoop.pop(index)
        return FloVoid

    def visitFncDefNode(self, node: FncDefNode):
        fnc_name = node.var_name.value
        if fnc_name in self.reserved.keys():
            TypeError(
                node.var_name.range,
                node.var_name.range,
                f"{fnc_name} is a reserved constant",
            ).throw()
        if isinstance(self.context.symbol_table.get(fnc_name), FloInlineFunc):
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
        rtype = FloInlineFunc(None, args, fnc_type)
        self.context.symbol_table.set(fnc_name, rtype)
        self.funcStack.append(fnc_type)
        bodyType = self.visit(node.body)
        if (
            not isinstance(node.body, StmtsNode)
            and self.shoudlReturn == False
            and bodyType != FloVoid
        ):
            node.body = ReturnNode(node.body, node.body.range)
        self.funcStack.pop()
        self.context.symbol_table = savedTbl
        if bodyType != fnc_type:
            TypeError(
                node.range,
                f"Expected return type of '{fnc_type.str()}' but got '{bodyType.str()}'",
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
                    f"Expected return type of '{rt.str()}' but got '{val.str()}'",
                ).throw()
        else:
            return FloVoid

    def visitContinueNode(self, node: ContinueNode):
        if not self.inLoop[-1]:
            SyntaxError(
                node.range, "Illegal continue outside of a loop").throw()
        return FloVoid

    def visitBreakNode(self, node: BreakNode):
        if not self.inLoop[-1]:
            SyntaxError(node.range, "Illegal break outside of a loop").throw()
        return FloVoid

    def visitFncCallNode(self, node: FncCallNode):
        fn = self.visit(node.name)
        if not isinstance(fn, FloInlineFunc):
            TypeError(
                node.range, f"{node.name.var_name.value} is not a function"
            ).throw()
        if len(fn.arg_types) != len(node.args):
            TypeError(
                node.range,
                f"Expected {len(fn.arg_types)} arguments, but got {len(node.args)}",
            ).throw()
        for i in range(len(node.args)):
            argType = self.visit(node.args[i])

            if (
                argType != fn.arg_types[i]
                and not fn.arg_types[i] == FloType
                and not argType == FloType
            ):
                TypeError(
                    node.args[i].range,
                    f"Expected type '{fn.arg_types[i].str()}' but got '{argType.str()}'",
                ).throw()
        return fn.return_type

    def visitTypeNode(self, node: TypeNode):
        return node.type

    def visitArrayNode(self, node: ArrayNode):
        if len(node.elements) == 0:
            return None
        expected_type = self.visit(node.elements[0])
        for elem in node.elements[1:]:
            type = self.visit(elem)

            if type != expected_type:
                TypeError(
                    elem.range,
                    f"Expected array to be of type '{expected_type}' because of first element but got '{type}'",
                ).throw()
        return FloArray(None, expected_type)

    def visitArrayAccessNode(self, node: ArrayAccessNode):
        collection = self.visit(node.name)
        index = self.visit(node.index)
        if isinstance(collection, FloArray) or collection == FloStr:
            if not self.isNumeric(index):
                TypeError(
                    node.index.range,
                    f"Expected key to be of type '{FloInt.str()}' but got '{index.str()}'",
                ).throw()
            return (
                FloStr if collection == FloStr else collection.elm_type
            )
        else:
            TypeError(
                node.name.range,
                f"Expected array, dict or string but got '{collection.str()}'",
            ).throw()

    def visitArrayAssignNode(self, node: ArrayAssignNode):
        arr: FloArray = self.visit(node.array)
        value = self.visit(node.value)
        if arr != value:
            TypeError(
                node.range,
                f"Expected assigned value to be of type '{arr.str()}' but got '{value.str()}'",
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
        return FloVoid

    # TODO: Look for types that are incompatible for casting.
