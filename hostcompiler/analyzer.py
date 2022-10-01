from typing import Dict, List
from context import Context
from errors import GeneralError, TypeError, SyntaxError, NameError
from flotypes import FloArray, FloClass, FloEnum, FloFloat, FloGeneric, FloInlineFunc, FloInt, FloObject, FloPointer, FloType, FloVoid, is_string_object
from lexer import TokType
from astree import *
from nodefinder import NodeFinder, resource_path
from glob import glob
from utils import get_ast_from_file


class FncDescriptor:
    def __init__(self, rtype: FloType, arg_names: List[str]):
        self.rtype = rtype
        self.arg_names = arg_names


class Block:
    @staticmethod
    def loop():
        return Block('loop')

    @staticmethod
    def class_():
        return Block('class')

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
    bit_operators = (TokType.SL, TokType.SR)

    def __init__(self, context: Context):
        self.context = Context(context.display_name+"_typecheck", context)
        self.constants = context.get_symbols()
        self.class_within: str = None
        self.current_block = Block.stmt()
        self.imported_module_names = []  # denotes full imported module
        self.types_aliases = {}
        self.generic_aliases = {}
        self.generics: Dict[str, GenericClassNode] = {}

    def visit(self, node: Node):
        return super().visit(node)

    def analyze(self, entry_node: Node):
        self.include_builtins(entry_node)
        self.visit(entry_node)

    def include_builtins(self, node: StmtsNode):
        mpath = resource_path("builtins")
        files = glob(f"{mpath}/*.flo")
        for file in files:
            ast = get_ast_from_file(file, None)
            node.stmts = ast.stmts + node.stmts

    def visitIntNode(self, node: IntNode):
        if node.expects:
            if isinstance(node.expects, FloInt):
                return FloInt(None, node.expects.bits)
        return FloInt(None)

    def visitFloatNode(self, _: FloatNode):
        return FloFloat(None)

    def visitCharNode(self, _: CharNode):
        return FloInt(None, 8)

    def visitStrNode(self, node: StrNode):
        if node.expects == FloPointer(FloInt(None, 8)):
            return node.expects
        return FloObject(self.context.get("string"))

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
            isNum = isNum and isinstance(
                type, FloInt) or isinstance(type, FloFloat)
        return isNum

    def visitNumOpNode(self, node: NumOpNode):
        node.left_node.expects = node.expects
        node.right_node.expects = node.expects
        left = self.visit(node.left_node)
        right = self.visit(node.right_node)
        if isinstance(left, FloInt) and isinstance(right, FloInt) and left != right:
            if isinstance(node.left_node, IntNode) or isinstance(node.left_node, UnaryNode):
                node.left_node.expects = right
            elif isinstance(node.right_node, IntNode) or isinstance(node.right_node, UnaryNode):
                node.right_node.expects = left
            left = self.visit(node.left_node)
            right = self.visit(node.right_node)
        if not isinstance(node.right_node, TypeNode):
            if left != right and isinstance(left, FloInt) and isinstance(right, FloInt):
                node.left_node = self.cast(node.left_node, FloInt(None, max(left.bits, right.bits)))
                node.right_node = self.cast(node.right_node, FloInt(None, max(left.bits, right.bits)))
            if left != right and isinstance(left, FloFloat) and isinstance(right, FloFloat):
                node.left_node = self.cast(node.left_node, FloFloat(None, max(left.bits, right.bits)))
                node.right_node = self.cast(node.right_node, FloFloat(None, max(left.bits, right.bits)))
        if node.op.type in self.arithmetic_ops_1:
            if isinstance(left, FloFloat) and isinstance(right, FloInt):
                node.right_node = self.cast(node.right_node, left)
                return FloFloat(0)
            if isinstance(left, FloInt) and isinstance(right, FloFloat):
                node.left_node = self.cast(node.left_node, right)
                return FloFloat(0)
            if isinstance(left, FloInt) and isinstance(right, FloInt):
                # TODO: Check sizes and choose the biggest and cast the smallest
                return left
            if isinstance(left, FloFloat) and isinstance(right, FloFloat):
                # TODO: Check sizes and choose the biggest and cast the smallest
                return right
            if isinstance(left, FloPointer) and isinstance(right, FloInt):
                return left
            # TODO: Other object types arithmetic operators/operator overloading.
            # NOTE: For string and other type concatenation, Generics will handle it.
            if node.op.type == TokType.PLUS and is_string_object(left):
                node.right_node = self.cast(node.right_node, left)
                return left
            elif node.op.type == TokType.PLUS and is_string_object(right):
                node.left_node = self.cast(node.left_node, right)
                return right
            if node.op.type == TokType.PLUS and isinstance(left, FloObject):
                add_method = left.referer.get_method("__add__")
                if add_method != None:
                    return self.check_fnc_call(add_method, [node.right_node], node)

        elif node.op.type in self.bit_operators or node.op.isKeyword("xor") or node.op.isKeyword("or") or node.op.isKeyword("and"):
            if isinstance(left, FloObject):
                sl = left.referer.get_method("__sl__")
                if sl:
                    return self.check_fnc_call(sl, [node.right_node], node)
            if self.isNumeric(left, right):
                if isinstance(left, FloFloat):
                    node.left_node = self.cast(node.left_node, right)
                    return right
                if isinstance(right, FloFloat):
                    node.right_node = self.cast(node.right_node, left)
                    return left
                if isinstance(left, FloInt) and isinstance(right, FloInt):
                    # TODO: Check sizes and choose the biggest and cast the smallest
                    return left
                # TODO: Object types bitwise
        elif node.op.type in Analyzer.comparason_ops or node.op.isKeyword("is"):
            if node.op.type in Analyzer.comparason_ops:
                if left == FloFloat and right == FloInt:
                    node.right_node = self.cast(node.right_node, left)
                if left == FloInt and right == FloFloat:
                    node.left_node = self.cast(node.left_node, left)
            return FloInt(None, 1)
        elif node.op.isKeyword("in"):
            # TODO: In For Objects and Arrays
            if isinstance(right, FloObject):
                in_method = right.referer.get_method("__in__")
                if in_method:
                    return self.check_fnc_call(in_method, [node.left_node], node)
        elif node.op.isKeyword("as"):
            if left == right:
                node = node.left_node
            return right
        TypeError(
            node.range,
            f"Illegal operation {node.op} between types '{left.str()}' and '{right.str()}'",
        ).throw()

    def visitUnaryNode(self, node: UnaryNode):
        node.value.expects = node.expects
        type = self.visit(node.value)
        if node.op.type == TokType.AMP:
            return FloPointer(type)
        if type != FloInt(None, 1) and (not self.isNumeric(type)):
            TypeError(
                node.value.range,
                f"Expected type of '{FloInt(None, 1).str()}', '{FloFloat.str()}' or '{FloFloat.str()}' but got '{type.str()}'",
            ).throw()
        if node.op.type == TokType.MINUS and (not self.isNumeric(type)):
            TypeError(
                node.value.range,
                f"Illegal negative {type.str()}",
            ).throw()
        if node.op.type == TokType.NOT:
            if isinstance(type, FloFloat):
                node.value = self.cast(node.value, FloInt(None, 1))
            if self.isNumeric(type):
                return type
            else:
                # TODO: Object types
                TypeError(
                    node.value.range,
                    f"Illegal not on {type.str()}",
                ).throw()
        else:
            return type

    def visitIncrDecrNode(self, node: IncrDecrNode):
        action = "decrement" if node.id.type == TokType.MINUS_MINUS else "increment"
        if not (
            isinstance(node.identifier, ArrayAccessNode)
            or isinstance(node.identifier, VarAccessNode)
            or isinstance(node.identifier, PropertyAccessNode)
        ):
            SyntaxError(
                node.identifier.range, f"Illegal {action} on non-identifier"
            ).throw()
        type = self.visit(node.identifier)
        if self.isNumeric(type) or isinstance(type, FloPointer):
            return type
        else:
            TypeError(
                node.range, f"Illegal {action} operation on type '{type.str()}'"
            ).throw()

    def visitVarAccessNode(self, node: VarAccessNode):
        var_name = node.var_name.value
        value = self.context.get(var_name)
        if value == None:
            NameError(node.var_name.range,
                      f"'{var_name}' is not defined").throw()
        return value

    def visitStmtsNode(self, node: StmtsNode):
        self.current_block.append_block(Block.stmt())
        for i, expr in enumerate(node.stmts):
            self.visit(expr)
            if self.current_block.always_returns:
                node.stmts = node.stmts[:i+1]
                break
        self.current_block.pop_block()

    def visitConstDeclarationNode(self, node: ConstDeclarationNode):
        const_name = node.const_name.value
        value = self.visit(node.value)
        self.context.set(const_name, value)
        self.constants.append(const_name)

    def declare_value(self, var_name: str, var_value, node: Node):
        if node.type:
            expected_type = self.visit(node.type)
            # TODO: Int-Type/Float-type bitsize casting
            c = None
            if isinstance(expected_type, FloObject):
                c = self.check_inheritance(expected_type, var_value, node)
            if c == None and var_value != expected_type:
                TypeError(
                    node.range, f"Expected type '{expected_type.str()}' but got type '{var_value.str()}'").throw()
        else:
            expected_type = var_value
        self.context.set(var_name, expected_type)
        return expected_type

    def visitEnumDeclarationNode(self, node: EnumDeclarationNode):
        enum_name = node.name.value
        self.context.set(enum_name, FloEnum(
            [token.value for token in node.tokens]))

    def check_inheritance(self, parent, child, node: Node):
        if parent == child:
            return None
        if not isinstance(child, FloObject): return None
        if child.referer.has_parent(parent.referer):
            node.value = self.cast(node.value, parent)
            return parent

    def visitVarAssignNode(self, node: VarAssignNode):
        var_name = node.var_name.value
        if var_name in self.constants:
            TypeError(
                node.var_name.range,
                f"changing constant's {var_name} value"
            ).throw()
        defined_var_value = self.context.get(var_name)
        if node.type:
            expected_ty = self.visit(node.type)
            node.value.expects = expected_ty
        if defined_var_value:
            node.value.expects = defined_var_value
        var_value = self.visit(node.value)
        if defined_var_value == None:
            return self.declare_value(var_name, var_value, node)
        if isinstance(defined_var_value, FloObject) and node.value:
            c = self.check_inheritance(defined_var_value, var_value, node)
            if c:
                return c
        if var_value != defined_var_value:
            TypeError(
                node.range,
                f"Illegal assignment of type {var_value.str()} to {defined_var_value.str()}").throw()
        return defined_var_value

    def condition_check(self, cond_node: Node):
        cond_type = self.visit(cond_node)
        if cond_type == None:
            return cond_node
        if self.isNumeric(cond_type):
            cond_node = self.cast(cond_node, FloInt(None, 1))
        else:
            TypeError(
                cond_node.range,
                f"Expected type numeric but got type '{cond_type.str()}'",
            ).throw()
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

    def visitForNode(self, node: ForNode):
        self.current_block.append_block(Block.loop())
        self.visit(node.init)
        node.cond = self.condition_check(node.cond)
        self.visit(node.stmt)
        self.visit(node.incr_decr)
        self.current_block.pop_block()

    def visitForEachNode(self, node: ForEachNode):
        self.current_block.append_block(Block.loop())
        it = self.visit(node.iterator)
        # TODO: Handle iteration
        if not (isinstance(it, FloArray) or isinstance(it, FloObject)):
            TypeError(
                node.iterator.range,
                f"Expected iterable but got type '{it.str()}'",
            ).throw()
        type = it.elm_type
        self.context.set(node.identifier.value, type)
        self.visit(node.stmt)
        self.current_block.pop_block()
        self.context.set(node.identifier.value, None)

    def visitWhileNode(self, node: WhileNode):
        self.current_block.append_block(Block.loop())
        node.cond = self.condition_check(node.cond)
        self.visit(node.stmt)
        self.current_block.pop_block()

    def visitFncNode(self, node: FncNode):
        if node.return_type:
            rt_type = self.visit(node.return_type)
        else:
            node.return_type = TypeNode(FloVoid(None), node.range)
            rt_type = FloVoid(None)
        arg_types = []
        default_args = []
        arg_names = []
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
                    default_value, (type_node or default_value_node).range), default_value_node)
            if arg_name in arg_names:
                NameError(
                    node.args[i][0].range,
                    f"Parameter '{arg_name}' defined twice in function parameters",
                ).throw()
            else:
                arg_names.append(arg_name)
                arg_types.append(arg_type)
                default_args.append(default_value_node)
        fnc_type = FloInlineFunc(
            None, arg_types, rt_type, node.is_variadic, default_args)
        fnc_type.arg_names = arg_names
        return fnc_type

    def evaluate_function_body(self, fnc_type: FloInlineFunc, node: FncNode):
        for arg_name, arg_type in zip(fnc_type.arg_names, fnc_type.arg_types):
            self.context.set(arg_name, arg_type)

        if node.is_variadic:
            var_arr = FloArray(None)
            var_arr.elm_type = fnc_type.arg_types[-1]
            self.context.set(fnc_type.arg_names[-1], var_arr)

        fn_descriptor = FncDescriptor(fnc_type.return_type, fnc_type.arg_names)
        self.current_block.append_block(Block.fnc(fn_descriptor))
        if node.body:
            self.visit(node.body)
            if not self.current_block.always_returns:
                if fnc_type.return_type == FloVoid(None):
                    node.body.stmts.append(ReturnNode(None, node.range))
                else:
                    GeneralError(node.return_type.range,
                                 "Function missing ending return statement").throw()
        self.current_block.pop_block()
        self.context = self.context.parent

    def visitFncDefNode(self, node: FncDefNode):
        fnc_name = node.func_name.value
        fnc_type = self.visit(node.func_body)
        if self.context.get(fnc_name) != None:
            NameError(
                node.func_name.range,
                f"{fnc_name} is already defined",
            ).throw()
        self.context.set(fnc_name, fnc_type)
        self.context = self.context.create_child(fnc_name)
        self.evaluate_function_body(fnc_type, node.func_body)

    def visitMethodDeclarationNode(self, node: MethodDeclarationNode):
        assert self.class_within
        # TODO: think about access
        method_name = node.method_name.value
        method_ty = self.class_within.methods.get(method_name)
        assert method_ty
        self.context = self.context.create_child(method_name)
        self.context.set("this", FloObject(self.class_within))
        if method_name == "constructor":
            self.class_within.constructor = method_ty
        else:
            if self.class_within.parent:
                expected_ty = self.class_within.parent.get_method(method_name)
                if expected_ty and expected_ty != method_ty:
                    TypeError(node.method_name.range,
                              f"Method '{method_name}' in type '{self.class_within.name}' is not assignable to the same method in base type '{self.class_within.parent.name}'."
                              + "\n\t\t\t\t" +
                              f"Type '{method_ty.str()}' is not assignable to type '{expected_ty.str()}'.\n"
                              ).throw()
            self.class_within.methods[method_name] = method_ty
        self.evaluate_function_body(method_ty, node.method_body)

    def visitPropertyDeclarationNode(self, node: PropertyDeclarationNode):
        assert self.class_within != None
        property_name = node.property_name.value
        property_ty = self.visit(node.type)
        if self.class_within.parent:
            expected_ty = self.class_within.parent.properties.get(
                property_name)
            if expected_ty and expected_ty != property_ty:
                TypeError(node.property_name.range,
                          f"Property '{property_name}' in type '{self.class_within.name}' is not assignable to the same property in base type '{self.class_within.parent.name}'."
                          + "\n\t\t\t\t" +
                          f"Type '{property_ty.str()}' is not assignable to type '{expected_ty.str()}'.\n"
                          ).throw()
        self.class_within.properties[property_name] = property_ty

    def visitReturnNode(self, node: ReturnNode):
        if not self.current_block.can_return():
            SyntaxError(
                node.range, "Illegal return outside a function").throw()
        val = self.visit(node.value) if node.value else FloVoid(None)
        
        if isinstance(val, FloObject) and isinstance(self.current_block.fn_within.rtype, FloObject):
            if val.referer.has_parent(self.current_block.fn_within.rtype.referer):
                node.value = self.cast(node.value, self.current_block.fn_within.rtype)
                val = self.current_block.fn_within.rtype
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
        return self.check_fnc_call(fn, node.args, node)

    def check_fnc_call(self, fn, args, node):
        # Replacing missing args with defaults
        for i, _ in enumerate(fn.arg_types):
            if i == len(args) and fn.defaults[i] != None:
                args.append(fn.defaults[i])
            elif i >= len(args):
                break
            elif args[i] == None and fn.defaults[i] != None:
                args[i] = fn.defaults[i]
        # Checking for varargs and alignings
        fn_args = fn.arg_types.copy()
        if fn.var_args:
            last_arg = fn_args.pop()
            fn_args += [last_arg]*(len(args)-len(fn_args))
        if len(args) != len(fn_args):
            TypeError(
                node.range,
                f"Expected {len(fn.arg_types)} arguments, but got {len(args)}",
            ).throw()
        for i, (node_arg, fn_arg_ty) in enumerate(zip(args, fn_args)):
            node_arg.expects = fn_arg_ty
            passed_arg_ty = self.visit(node_arg)
            c = None
            if isinstance(passed_arg_ty, FloObject) and fn_arg_ty != FloType and isinstance(fn_arg_ty, FloObject):
                c = self.check_inheritance(
                    fn_arg_ty, passed_arg_ty, VarAssignNode(None, node_arg, None, None))
                if c:
                    args[i] = self.cast(node_arg, fn_arg_ty)
            if (
                passed_arg_ty != fn_arg_ty
                and fn_arg_ty != FloType
                and c == None
            ):
                TypeError(
                    node_arg.range,
                    f"Expected type '{fn_arg_ty.str()}' but got '{passed_arg_ty.str()}'",
                ).throw()
            if isinstance(fn_arg_ty, FloInlineFunc) and isinstance(node_arg, PropertyAccessNode):
                GeneralError(
                    node_arg.range,
                    "Cannot decouple method from object to pass as argument."
                ).throw()
        return fn.return_type

    def get_object_class(self, node_type, node):
        class_name = node_type.referer.value
        class_ = self.context.get(class_name)
        if class_ == None:
            if self.class_within == None or (class_name != self.class_within.name):
                NameError(
                    node.range, f"type {class_name} not defined").throw()
            else:
                class_ = self.class_within
        return class_

    def init_generic(self, generic: FloGeneric, node):
        # if it has it's referer is a token
        if isinstance(generic.referer, FloClass): return
        generic_name = generic.referer.value
        if self.context.get(generic_name) != None:
            return
        generic_node = self.generics.get(generic.name)
        if generic_node == None:
            NameError(node.range, f"'{generic.name}' type not defined").throw()
        generic_node.class_declaration.name.value = generic_name
        type_aliases = self.generic_aliases.copy()
        for key_tok, type_arg in zip(generic_node.generic_constraints, generic.constraints):
            self.generic_aliases[key_tok.value] = type_arg
        self.visit(generic_node.class_declaration)
        generic_node.class_declaration.name.value = generic.name
        self.generic_aliases = type_aliases

    def visitTypeNode(self, node: TypeNode):
        node_type = node.type
        if isinstance(node_type, FloGeneric):
            generic = FloGeneric(Token(node_type.referer.type, node_type.referer.range, node_type.referer.value), [])
            for constraint in node.type.constraints:
                if isinstance(constraint, TypeNode):
                    generic.constraints.append(self.visit(constraint))
                generic.referer.value = generic.str()
            self.init_generic(generic, node)
            node_type = generic
        if isinstance(node_type, FloObject):
            if isinstance(node_type.referer, FloClass): return node_type
            alias = self.types_aliases.get(node_type.referer.value)
            if alias:
                if isinstance(alias, TypeNode):
                    aliased = self.visit(alias)
                    node.type = aliased
                    return aliased
            alias = self.generic_aliases.get(node_type.referer.value)
            if alias:
                return alias
            class_ = self.get_object_class(node_type, node)
            if isinstance(node_type, FloGeneric):
                return FloGeneric(class_, node_type.constraints)
            elif isinstance(class_, FloEnum):
                return FloInt(None)
            else:
                return FloObject(class_)
        elif isinstance(node_type, FloPointer) or isinstance(node_type, FloArray):
            if isinstance(node_type.elm_type, TypeNode):
                mm = node_type.__class__(None)
                mm.elm_type = self.visit(node_type.elm_type)
                node_type = mm
            if isinstance(node_type, FloArray) and isinstance(node_type.len, TypeNode):
                nn = FloArray(None, self.visit(node_type.len))
                nn.elm_type = node_type.elm_type
                if not isinstance(nn.len, FloInt): TypeError(node.type.len.range, "Expected an int").throw()
                return nn
        elif isinstance(node_type, FloInlineFunc):
            fnc_ty = FloInlineFunc(None, [], None, node_type.var_args, node_type.defaults)
            for arg_ty in node_type.arg_types:
                fnc_ty.arg_types.append(self.visit(arg_ty))
            fnc_ty.return_type = self.visit(node_type.return_type)
            return fnc_ty
        return node_type

    def visitArrayNode(self, node: ArrayNode):
        if len(node.elements) == 0:
            return node.expects
        expected_type = self.visit(node.elements[0])
        expected_elm_ty = None
        if node.expects:
            if isinstance(node.expects, FloGeneric):
                if node.expects.name == "Array" and node.expects.constraints[0] == expected_type:
                    return node.expects
                else:
                    gen_name = 'Array<'+expected_type.str()+'>'
                    if node.expects.str() == gen_name:
                        return node.expects
                    TypeError(node.range, f"Expected '{node.expects.str()}' but got '{gen_name}'").throw()
            elif isinstance(node.expects, FloArray):
                expected_elm_ty = node.expects.elm_type
                expected_type = expected_elm_ty
        for elem in node.elements:
            elem.expects = expected_elm_ty
            type = self.visit(elem)
            if type != expected_type:
                TypeError(
                    elem.range,
                    f"Expected array to be of type '{expected_type.str()}' because of first element but got '{type.str()}'",
                ).throw()
        arr = FloArray(None, len(node.elements))
        arr.elm_type = expected_type
        return arr

    def check_subscribable(self, collection, index, node: PropertyAccessNode, set_value=None):
        method_name = '__getitem__' if set_value == None else '__setitem__'
        fnc: FloInlineFunc = collection.referer.get_method(method_name)
        if fnc == None:
            TypeError(
                node.name.range,
                f"{collection.referer.name} object has no method {method_name}").throw()
        if index != fnc.arg_types[0]:
            TypeError(
                node.index.range,
                f"{collection.referer.name} object expects type {fnc.arg_types[0].str()} as index").throw()
        if set_value:
            if set_value != fnc.arg_types[1]:
                TypeError(
                    node.index.range,
                    f"{collection.referer.name} object expects type {fnc.arg_types[1].str()} for index assignment").throw()
        return fnc.return_type

    def visitRangeNode(self, node: RangeNode):
        if node.start:
            start = self.visit(node.start)
        else:
            start = FloInt(0)
        end = self.visit(node.end)
        if not (isinstance(start, FloInt)):
            TypeError(node.start.range,
                      f"Excpected an 'int' but got a {start.str()}").throw()
        if not (isinstance(end, FloInt)):
            TypeError(node.end.range,
                      f"Excpected an 'int' but got a {end.str()}").throw()
        return FloObject(self.context.get("Range"))

    def visitArrayAccessNode(self, node: ArrayAccessNode):
        collection = self.visit(node.name)
        index = self.visit(node.index)
        if isinstance(collection, FloArray) or isinstance(collection, FloPointer):
            if not self.isNumeric(index):
                TypeError(
                    node.index.range,
                    f"Expected key to be of type 'int' but got '{index.str()}'",
                ).throw()
            return collection.elm_type
        elif isinstance(collection, FloObject):
            return self.check_subscribable(collection, index, node)
        else:
            TypeError(
                node.name.range,
                f"Expected array, pointer or object but got '{collection.str()}'",
            ).throw()

    def visitArrayAssignNode(self, node: ArrayAssignNode):
        arr: FloArray = self.visit(node.array)
        node.value.expects = arr
        value = self.visit(node.value)
        if isinstance(arr, FloObject):
            index = self.visit(node.array.index)
            obj = self.visit(node.array.name)
            if isinstance(obj, FloArray) or isinstance(obj, FloPointer):
                obj = arr
            else:
                return self.check_subscribable(obj, index, node.array, value)
        if arr != value:
            TypeError(
                node.range,
                f"Expected assigned value to be of type '{arr.str()}' but got '{value.str()}'",
            ).throw()
        return value
    
    def declare_class(self, class_ob: FloClass, node: StmtsNode):
        for stmt in node.stmts:
            if isinstance(stmt, MethodDeclarationNode):
                method_name = stmt.method_name.value
                if class_ob.methods.get(method_name) != None:
                            NameError(
                            stmt.method_name.range,
                            f"{method_name} is already defined in class {class_ob.name}",
                        ).throw()
                class_ob.methods[method_name] = self.visit(stmt.method_body)

    def visitClassDeclarationNode(self, node: ClassDeclarationNode):
        self.current_block.append_block(Block.class_())
        class_name = node.name.value
        parent = None
        prev_super = self.context.get("super")
        if node.parent:
            parent_type = self.visit(node.parent)
            self.context.set("super", parent_type.referer.constructor)
            if not isinstance(parent_type, FloObject):
                TypeError(
                    node.name.range, f"Type '{parent_type.str()}' cannot be base type of class '{class_name}'.").throw()
            else:
                parent = parent_type.referer
        class_ob = FloClass(class_name, parent, False)
        self.context.set(class_name, class_ob)
        self.declare_class(class_ob, node.body)
        prev_class = self.class_within
        self.class_within = class_ob
        self.constants.append(class_name)
        self.visit(node.body)
        self.class_within = prev_class
        self.context.set("super", prev_super)
        self.current_block.pop_block()

    def visitGenericClassNode(self, node: GenericClassNode):
        self.generics[node.class_declaration.name.value] = node

    def visitTypeAliasNode(self, node: TypeAliasNode):
        self.types_aliases[node.identifier.value] = node.type

    def visitPropertyAccessNode(self, node: PropertyAccessNode):
        root = self.visit(node.expr)
        property_name = node.property.value
        if isinstance(root, FloEnum):
            try:
                return root.get_property(property_name)
            except:
                NameError(node.property.range, f"property '{property_name}' is not defined on enum '{node.expr.var_name.value}'").throw()
        if isinstance(root, FloPointer):
            method = root.methods.get(property_name)
            if method == None:
                GeneralError(node.property.range,
                         f"{property_name} not defined on pointer").throw()
            return method
        if not isinstance(root, FloObject):
            TypeError(node.expr.range, "Expected an object").throw()
        value = root.referer.properties.get(property_name)
        if value == None:
            value = root.referer.get_method(property_name)
        if value == None:
            GeneralError(node.property.range,
                         f"{property_name} not defined on {root.referer.name} object").throw()
        return value

    def visitPropertyAssignNode(self, node: PropertyAssignNode):
        expr = self.visit(node.expr)
        node.value.expects = expr
        value = self.visit(node.value)
        if isinstance(expr, FloObject) and isinstance(value, FloObject):
            c = self.check_inheritance(expr, value, node)
            if c:
                return c
        if expr != value:
            TypeError(
                node.range, f"Expected type {expr.str()} but got type {value.str()}").throw()
        return value

    def visitNewMemNode(self, node: NewMemNode):
        typeval = self.visit(node.type)
        if isinstance(typeval, FloObject):
            if typeval.referer.constructor:
                self.check_fnc_call(
                    typeval.referer.constructor, node.args or [], node)
            return typeval
        else:
            if not isinstance(typeval, FloArray):
                TypeError(node.type.range, "Type can only be an object or an array").throw()
            if node.args or isinstance(node.args, list):
                TypeError(node.range, "New array intialization doesn't take any arguments.").throw()
            return FloPointer(typeval.elm_type)

    def visitImportNode(self, node: ImportNode):
        # TODO: Needs work using NodeFinder.get_abs_path twice
        relative_path = node.path.value
        names_to_find = [id.value for id in node.ids]
        importer = NodeFinder(Context(relative_path))
        mpath = NodeFinder.get_abs_path(relative_path, node.range.start.fn)
        if mpath in self.imported_module_names:
            return
        if len(names_to_find) == 0:
            self.imported_module_names.append(mpath)
        names_to_ignore = self.context.get_symbols()
        find_result = importer.find(names_to_find, names_to_ignore, node.range)
        node.resolved_as = find_result.resolved
        for res_node in find_result.resolved:
            self.visit(res_node)
