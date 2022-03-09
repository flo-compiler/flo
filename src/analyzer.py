from typing import List
from context import Context
from errors import GeneralError, TypeError, SyntaxError, NameError
from flotypes import FloArray, FloBool, FloFloat, FloInlineFunc, FloInt, FloStr, FloType, FloVoid
from lexer import TokType
from interfaces.astree import *


class FncDescriptor:
    def __init__(self, name: str, rtype: FloType, arg_names: List[str]):
        self.name = name
        self.rtype = rtype
        self.arg_names = arg_names


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
        self.last_if_always_returns = False

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
        if self.is_in_block('else') and self.last_if_always_returns:
            self.always_returns = True
        else:
            self.always_returns = True

    def append_block(self, block):
        new_rt_state = self.always_returns
        if block.name == 'function':
            new_rt_state = block.always_returns
        if block.name == 'if':
            self.last_if_always_returns = False
        fn_state = block.fn_within or self.fn_within
        self.parent_blocks.append(
            (self.name, self.fn_within, self.always_returns))
        (self.name, self.fn_within, self.always_returns) = (
            block.name, fn_state, new_rt_state)

    def pop_block(self):
        if self.is_in_block('if') and self.always_returns:
            self.last_if_always_returns = True
        new_state = self.parent_blocks.pop()
        (self.name, self.fn_within, _) = new_state
        if new_state[0] != 'function':
            self.always_returns = new_state[2]


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
        self.constants = []
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
                node.op.type == TokType.SL or node.op.type == TokType.SR
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

    def visitConstDeclarationNode(self, node: ConstDeclarationNode):
        declaration = node.declaration
        var_name = declaration.var_name.value
        value = declaration.value
        if not (isinstance(value, StrNode) or isinstance(value, IntNode)
                or isinstance(value, FloatNode)):
            GeneralError(value.range, "Expected a constant").throw()
        self.visit(declaration)
        self.constants.append(var_name)

    def declare_value(self, var_name: str, var_value, var_type: Node, range: Range):
        if var_type:
            expected_type = self.visit(var_type)
            if var_value != expected_type:
                TypeError(
                    range, f"Expected type '{expected_type.str()}' but got type '{var_value.str()}'").throw()
        else:
            expected_type = var_value
        self.context.symbol_table.set(var_name, expected_type)

    def visitVarAssignNode(self, node: VarAssignNode):
        var_name = node.var_name.value
        if var_name in self.constants:
            TypeError(
                node.var_name.range,
                f"changing constant's {var_name} value"
            ).throw()
        if var_name in self.reserved.keys():
            TypeError(
                node.var_name.range,
                f"{var_name} is a reserved constant",
            ).throw()
        defined_var_value = self.context.symbol_table.get(var_name)
        var_value = self.visit(node.value)
        if defined_var_value == None:
            return self.declare_value(var_name, var_value, node.type, node.range)
        if var_value != defined_var_value:
            TypeError(
                node.range,
                f"Illegal assignment of type {var_value.str()} to {defined_var_value.str()}").throw()
        return defined_var_value

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
        self.current_block.append_block(Block.loop())
        it = self.visit(node.iterator)
        if (
            (not isinstance(it, FloArray))
            and (it != FloStr)
        ):
            TypeError(
                node.iterator.range,
                f"Expected type of 'str' or 'array' but got type '{it.str()}'",
            ).throw()
        type = FloStr if it == FloStr else it.elm_type
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
        fnc_name = node.var_name.value
        if fnc_name in self.reserved.keys():
            TypeError(
                node.var_name.range,
                node.var_name.range,
                f"{fnc_name} is a reserved constant",
            ).throw()
        if self.context.symbol_table.get(fnc_name) != None:
            NameError(
                node.var_name.range,
                f"{fnc_name} is already defined",
            ).throw()
        if node.return_type:
            rt_type = self.visit(node.return_type)
        else:
            node.return_type = TypeNode(FloVoid, node.range)
            rt_type = FloVoid
        arg_types = []
        default_args = []
        arg_names = []
        savedTbl = self.context.symbol_table.copy()
        # TODO: Need for better functions
        for i, (arg_name_tok, type_node, default_value_node) in enumerate(node.args):
            default_value = None
            arg_type = None
            if type_node:
                arg_type = self.visit(type_node)
            if default_value_node:
                default_value = self.visit(default_value_node)
            arg_name = arg_name_tok.value
            if arg_type and default_value:
                if arg_type != default_value:
                    TypeError(
                        node.range, f"Type mismatch between {arg_type.str()} and ${default_value.str()}")
            elif arg_type == None and default_value:
                arg_type = default_value
                node.args[i] = (arg_name_tok, TypeNode(
                    default_value, node.args[i]), default_value_node)
            if arg_name in arg_names:
                NameError(
                    arg_name.range,
                    f"parameter '{arg_name}' defined twice in function parameters",
                ).throw()
            elif arg_name == fnc_name:
                NameError(
                    arg_name.range, f"parameter '{arg_name}' has same name as function"
                ).throw()
            else:
                arg_names.append(arg_name)
                arg_types.append(arg_type)
                default_args.append(default_value_node)
                self.context.symbol_table.set(arg_name, arg_type)
        if node.is_variadic:
            var_arr = FloArray(None)
            var_arr.elm_type = arg_types[-1]
            self.context.symbol_table.set(arg_names[-1], var_arr)
        
        fn_type = FloInlineFunc(None, arg_types, rt_type, node.is_variadic, default_args)
        fn_descriptor = FncDescriptor(fnc_name, rt_type, arg_names)
        self.current_block.append_block(Block.fnc(fn_descriptor))
        self.context.symbol_table.set(fnc_name, fn_type)
        savedTbl.set(fnc_name, fn_type)
        self.visit(node.body)
        if not self.current_block.always_returns:
            if rt_type == FloVoid:
                node.body.stmts.append(ReturnNode(None, node.range))
            else:
                GeneralError(node.return_type.range,
                             "Function missing ending return statement").throw()
        self.current_block.pop_block()
        self.context.symbol_table = savedTbl

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
        fn = self.visit(node.name)
        if not isinstance(fn, FloInlineFunc):
            TypeError(
                node.range, f"{node.name.var_name.value} is not a function"
            ).throw()
        # Replacing missing args with defaults
        for i, _ in enumerate(fn.arg_types):
            if i == len(node.args) and fn.defaults[i] != None:
                node.args.append(fn.defaults[i])
            elif i >= len(node.args):
                break
            elif node.args[i] == None and fn.defaults[i] != None:
                node.args[i] = fn.defaults[i]
        #TODO check for var_arg types
        fn_args = fn.arg_types.copy()
        if fn.var_args:
              last_arg = fn_args.pop()
              fn_args += [last_arg]*(len(node.args)-len(fn_args))
        if len(node.args) != len(fn_args):
            TypeError(
                node.range,
                f"Expected {len(fn.arg_types)} arguments, but got {len(node.args)}",
            ).throw()
        for node_arg, fn_arg_ty in zip(node.args, fn_args):
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
