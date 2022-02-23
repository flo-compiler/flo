from os import path
from typing import List
from context import Context, SymbolTable
from errors import GeneralError, TypeError, SyntaxError, NameError, IOError
from flotypes import FloArray, FloBool, FloFloat, FloInlineFunc, FloInt, FloStr, FloType, FloVoid
from lexer import TokType
from lexer import Lexer
from parser import Parser
from interfaces.astree import *


class BuildCache:
    module_asts = {}


class FncDescriptor:
    def __init__(self, name: str, rtype: FloType, arg_names: List[str], is_inline: bool):
        self.name = name
        self.rtype = rtype
        self.arg_names = arg_names
        self.is_inline = is_inline


class Block:
    @staticmethod
    def loop():
        return Block('loop')

    @staticmethod
    def fnc(func: FncDescriptor):
        return Block('function', func)

    @staticmethod
    def stmt():
        return Block('stmt')

    @staticmethod
    def if_():
        return Block('if')

    def else_():
        return Block('else')

    def __init__(self, name, fn: FncDescriptor = None):
        self.name = name
        self.fn_within = fn
        self.always_returns = False
        self.parent_blocks = []

    def can_continue(self):
        return self.is_in_block('loop')

    def can_break(self):
        return self.can_continue()

    def is_in_block(self, name):
        for (p_name, _, _) in self.parent_blocks:
            if p_name == name:
                return True
        return False

    def get_parent_fnc_ty(self):
        return self.fn_within.rtype

    def can_return(self):
        return self.fn_within != None

    def can_return_value(self, value):
        return value == self.fn_within.rtype

    def return_value(self, _):
        if self.name == 'stmt':
            self.always_returns = True
        elif self.name == 'if' or self.name == 'else':
            self.always_returns = self.always_returns and True
        else:
            self.always_returns = True

    def append_block(self, block):
        new_rt_state = block.always_returns if block.name == 'function' else self.always_returns
        fn_state = block.fn_within or self.fn_within
        self.parent_blocks.append(
            (self.name, self.fn_within, self.always_returns))
        (self.name, self.fn_within, self.always_returns) = (
            block.name, fn_state, new_rt_state)

    def in_inline_fnc(self):
        return self.is_in_block("function") and self.fn_within.is_inline

    def pop_block(self):
        popped = self.parent_blocks.pop()
        (self.name, self.fn_within, _) = popped
        if popped[0] != 'function':
            self.always_returns = popped[2]


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
        self.current_block = Block.stmt()

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
        self.current_block.append_block(Block.stmt())
        i = 1
        for expr in node.stmts:
            s = self.visit(expr)
            if self.current_block.always_returns:
                node.stmts = node.stmts[0:i]
                break
            i += 1
        self.current_block.pop_block()
        return s

    def visitVarAssignNode(self, node: VarAssignNode):
        var_name = node.var_name.value
        if self.current_block.in_inline_fnc() and var_name in self.current_block.fn_within.arg_names:
            GeneralError(
                node.range, f"Arguments are not mutable in inline function").throw()
        var_value = self.context.symbol_table.get(var_name)
        if self.current_block.in_inline_fnc() and var_value == None:
            GeneralError(
                node.range, f"Variable definition not permitted in inline function").throw()
        if var_name.isupper() and var_value != None:
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
        for i, (cond, expr) in enumerate(node.cases):
            self.current_block.append_block(Block.if_())
            node.cases[i] = (self.condition_check(cond), expr)
            self.visit(expr)
            self.current_block.pop_block()
        if node.else_case:
            self.current_block.append_block(Block.else_())
            self.visit(node.else_case)
            self.current_block.pop_block()
        return FloVoid

    def visitForNode(self, node: ForNode):
        self.current_block.append_block(Block.loop())
        self.visit(node.init)
        node.cond = self.condition_check(node.cond)
        self.visit(node.stmt)
        self.visit(node.incr_decr)
        self.current_block.pop_block()
        return FloVoid

    def visitForEachNode(self, node: ForEachNode):
        if self.current_block.in_inline_fnc():
            GeneralError(node.identifier.range,
                         f"foreach loop not permitted in inline function").throw()
        self.current_block.append_block(Block.loop())
        it = self.visit(node.iterator)
        if (
            (not isinstance(it, FloArray))
            and (it != FloStr)
        ):
            TypeError(
                node.iterator.range,
                f"Expected type of 'str', dict or 'array' but got type '{it.str()}'",
            ).throw()
        type = (
            FloStr
            if it == FloStr
            else it.elm_type
        )
        self.context.symbol_table.set(node.identifier.value, type)
        self.visit(node.stmt)
        self.current_block.pop_block()
        self.context.symbol_table.set(node.identifier.value, None)
        return FloVoid

    def visitWhileNode(self, node: WhileNode):
        self.current_block.append_block(Block.loop())
        node.cond = self.condition_check(node.cond)
        self.visit(node.stmt)
        self.current_block.pop_block()
        return FloVoid

    def visitFncDefNode(self, node: FncDefNode):
        if self.current_block.in_inline_fnc():
            GeneralError(
                node.var_name.range, f"Function definition not permitted in inline function").throw()
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
        rt_type = self.visit(node.return_type)
        arg_types = []
        arg_names = []
        savedTbl = self.context.symbol_table.copy()
        if not node.is_inline:
            self.context.symbol_table.symbols = self.reserved.copy()
        for arg_name_tok, type_node in node.args:
            arg_type = self.visit(type_node)
            arg_name = arg_name_tok.value
            if arg_name in arg_names:
                NameError(
                    arg_name.range,
                    f"parameter '{arg_name}' defined twice in function parameters",
                ).throw()
            elif arg_type == None:
                TypeError(
                    arg_name.range, f"parameter '{arg_name}' has an unknown type"
                ).throw()
            elif arg_name == fnc_name:
                NameError(
                    arg_name.range, f"parameter '{arg_name}' has same name as function"
                ).throw()
            else:
                arg_names.append(arg_name)
                arg_types.append(arg_type)
                self.context.symbol_table.set(arg_name, arg_type)
        fn_type = FloInlineFunc(None, arg_types, rt_type)
        # Recursion only for non-inline function
        fn_descriptor = FncDescriptor(
            fnc_name, rt_type, arg_names, node.is_inline)
        self.current_block.append_block(Block.fnc(fn_descriptor))
        if not isinstance(node.body, StmtsNode):
            node.body = StmtsNode(
                [ReturnNode(node.body, node.body.range)], node.body.range)
        self.visit(node.body)
        if not self.current_block.always_returns:
            GeneralError(node.return_type.range,
                         "Function missing ending return statement").throw()
        self.current_block.pop_block()
        self.context.symbol_table = savedTbl
        self.context.symbol_table.set(fnc_name, fn_type)

    def visitReturnNode(self, node: ReturnNode):
        if not self.current_block.can_return():
            SyntaxError(
                node.range, "Illegal return outside a function").throw()
        val = self.visit(node.value) if node.value else FloVoid
        if not self.current_block.can_return_value(val):
            TypeError(
                node.range,
                f"Expected return type of '{self.current_block.get_parent_fnc_ty().str()}' but got '{val.str()}'",
            ).throw()
        else:
            self.current_block.return_value(val)

    def visitContinueNode(self, node: ContinueNode):
        if not self.current_block.can_continue():
            SyntaxError(
                node.range, "Illegal continue outside of a loop").throw()

    def visitBreakNode(self, node: BreakNode):
        if not self.current_block.can_break():
            SyntaxError(node.range, "Illegal break outside of a loop").throw()

    def visitFncCallNode(self, node: FncCallNode):
        if (self.current_block.in_inline_fnc() and
                self.current_block.fn_within.name == node.name.var_name.value):
            GeneralError(
                node.range, "Recursive function call not permitted in inline function").throw()
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
        for node_arg, fn_arg_ty in zip(node.args, fn.arg_types):
            passed_arg_ty = self.visit(node_arg)
            if (
                passed_arg_ty != fn_arg_ty
                and not fn_arg_ty == FloType
                and not passed_arg_ty == FloType
            ):
                TypeError(
                    node_arg.range,
                    f"Expected type '{fn_arg_ty.str()}' but got '{passed_arg_ty.str()}'",
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
                    f"Expected array to be of type '{expected_type.str()}' because of first element but got '{type.str()}'",
                ).throw()
        arr = FloArray(None)
        arr.elm_type = expected_type
        return arr

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
