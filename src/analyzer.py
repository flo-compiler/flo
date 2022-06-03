from typing import List
from context import Context
from errors import GeneralError, TypeError, SyntaxError, NameError
from flotypes import FloArray, FloClass, FloFloat, FloInlineFunc, FloInt, FloObject, FloPointer, FloType, FloVoid
from lexer import TokType
from astree import *
from nodefinder import NodeFinder, resource_path
from glob import glob

from utils import get_ast_from_file

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
        self.context = Context(context.display_name, context)
        self.constants = context.get_symbols()
        self.class_within: str = None
        self.current_block = Block.stmt()
        self.imported_module_names = [] #denotes full imported module
        self.types_aliases = {}

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

    def visitIntNode(self, _):
        return FloInt(None)

    def visitFloatNode(self, _: FloatNode):
        return FloFloat(None)

    def visitCharNode(self, _: CharNode):
        return FloInt(None, 8)

    def visitStrNode(self, node: StrNode):
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
        left = self.visit(node.left_node)
        right = self.visit(node.right_node)
        if node.op.type in self.arithmetic_ops_1:
            if isinstance(left, FloFloat) and isinstance(right, FloInt):
                node.right_node = self.cast(node.right_node, left)
                return FloFloat
            if isinstance(left, FloInt) and isinstance(right, FloFloat):
                node.left_node = self.cast(node.left_node, right)
                return FloFloat
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
            if node.op.type == TokType.PLUS and isinstance(left, FloObject):
                add_method = left.referer.methods.get("__add__")
                if add_method != None:
                    add_arg = add_method.arg_types[0]
                    if add_arg != right:
                        TypeError(
                            node.right_node.range, f"Expected type {add_arg.str()} but got {right.str()}").throw()
                    return add_method.return_type

        elif node.op.type in self.bit_operators or node.op.isKeyword("xor") or node.op.isKeyword("or") or node.op.isKeyword("and"):
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
                    node.right_node = self.cast(node.right_node, FloFloat)
                if left == FloInt and right == FloFloat:
                    node.left_node = self.cast(node.left_node, FloFloat)
            return FloInt(None, 1)
        elif node.op.isKeyword("in"):
            # TODO: In For Objects and Arrays
            raise Exception("Unimplemented")
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
                #TODO: Object types
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
        s = None
        for i, expr in enumerate(node.stmts):
            s = self.visit(expr)
            if self.current_block.always_returns:
                node.stmts = node.stmts[:i+1]
                break
        self.current_block.pop_block()
        return s

    def visitConstDeclarationNode(self, node: ConstDeclarationNode):
        const_name = node.const_name.value
        value = self.visit(node.value)
        self.context.set(const_name, value)
        self.constants.append(const_name)

    def declare_value(self, var_name: str, var_value, var_type: Node, range: Range):
        if var_type:
            expected_type = self.visit(var_type)
            #TODO: Int-Type/Float-type bitsize casting
            if var_value != expected_type:
                TypeError(
                    range, f"Expected type '{expected_type.str()}' but got type '{var_value.str()}'").throw()
        else:
            expected_type = var_value
        self.context.set(var_name, expected_type)
        return expected_type

    def set_array_type(self, node: ArrayNode, node_type: TypeNode):
        if not node_type:
            return
        var_type = self.visit(node_type)
        if isinstance(var_type, FloObject) and var_type.referer.name == 'Array':
            node.is_const_array = False

    def visitVarAssignNode(self, node: VarAssignNode):
        var_name = node.var_name.value
        if var_name in self.constants:
            TypeError(
                node.var_name.range,
                f"changing constant's {var_name} value"
            ).throw()
        defined_var_value = self.context.get(var_name)
        if node.value:
            if isinstance(node.value, ArrayNode):
                self.set_array_type(node.value, node.type)
            var_value = self.visit(node.value)
        else:
            var_value = self.visit(node.type)
        if self.class_within != None and not self.current_block.can_return():
            self.class_within.properties[var_name] = var_value
            return var_value
        if defined_var_value == None:
            return self.declare_value(var_name, var_value, node.type, node.range)
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
        #TODO: Handle iteration
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

    def visitFncDefNode(self, node: FncDefNode):
        fnc_name = node.var_name.value
        if self.context.get(fnc_name) != None and self.class_within == None:
            NameError(
                node.var_name.range,
                f"{fnc_name} is already defined",
            ).throw()
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
        fn_type = FloInlineFunc(None, arg_types, rt_type,
                                node.is_variadic, default_args)
        # class stuff
        if self.class_within == None:
            self.context.set(fnc_name, fn_type)
            self.context = self.context.create_child(fnc_name)
        else:
            self.context = self.context.create_child(fnc_name)
            self.context.set(
                "this", FloObject(self.class_within))
            self.class_within.methods[fnc_name] = fn_type
            if fnc_name == "constructor":
                self.class_within.constructor = fn_type
        for arg_name, arg_type in zip(arg_names, arg_types):
            self.context.set(arg_name, arg_type)

        if node.is_variadic:
            var_arr = FloArray(None)
            var_arr.elm_type = arg_types[-1]
            self.context.set(arg_names[-1], var_arr)

        fn_descriptor = FncDescriptor(fnc_name, rt_type, arg_names)
        self.current_block.append_block(Block.fnc(fn_descriptor))
        if node.body:
            self.visit(node.body)
            if not self.current_block.always_returns:
                if rt_type == FloVoid(None):
                    node.body.stmts.append(ReturnNode(None, node.range))
                else:
                    GeneralError(node.return_type.range,
                                 "Function missing ending return statement").throw()
        self.current_block.pop_block()
        self.context = self.context.parent

    def visitReturnNode(self, node: ReturnNode):
        if not self.current_block.can_return():
            SyntaxError(
                node.range, "Illegal return outside a function").throw()
        val = self.visit(node.value) if node.value else FloVoid()
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
        for node_arg, fn_arg_ty in zip(args, fn_args):
            passed_arg_ty = self.visit(node_arg)
            if (
                passed_arg_ty != fn_arg_ty
                and fn_arg_ty != FloType
            ):
                TypeError(
                    node_arg.range,
                    f"Expected type '{fn_arg_ty.str()}' but got '{passed_arg_ty.str()}'",
                ).throw()
        return fn.return_type

    def get_object_class(self, node_type, node):
        class_name = node_type.referer.value if isinstance(
            node_type.referer, Token) else node_type.referer.name
        class_ = self.context.get(class_name)
        if class_ == None:
            if self.class_within == None or (class_name != self.class_within.name):
                NameError(
                    node.range, f"type {class_name} not defined").throw()
            else:
                class_ = self.class_within
        return class_
        

    def visitTypeNode(self, node: TypeNode):
        node_type = node.type
        if isinstance(node_type, FloObject):
            alias = self.types_aliases.get(node_type.referer.value)
            if alias:
                aliased = self.visit(alias)
                node.type = aliased
                return aliased
            class_ = self.get_object_class(node_type, node)
            node.type.referer = class_
            node.type.llvmtype = class_.value.as_pointer()
        elif isinstance(node_type, FloPointer) or isinstance(node_type, FloArray):
            if isinstance(node_type.elm_type, TypeNode):
                node_type.elm_type = self.visit(node_type.elm_type)
            return node_type
        elif isinstance(node_type, FloInlineFunc):
            for i, arg_ty in enumerate(node_type.arg_types):
                if isinstance(arg_ty, TypeNode):
                    node_type.arg_types[i] = self.visit(arg_ty)
            if isinstance(node_type.return_type, TypeNode):
                node_type.return_type = self.visit(node_type.return_type)
        return node_type

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
        if not node.is_const_array:
            return FloObject(self.context.get('Array'))
        arr = FloArray(None, len(node.elements))
        arr.elm_type = expected_type
        return arr

    def check_subscribable(self, collection, index, node: PropertyAccessNode, set_value=None):
        method_name = '__getitem__' if set_value == None else '__setitem__'
        fnc: FloInlineFunc = collection.referer.methods.get(method_name)
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
        value = self.visit(node.value)
        if isinstance(arr, FloObject):
            index = self.visit(node.array.index)
            obj = self.visit(node.array.name)
            if isinstance(obj, FloArray):
                obj = arr
            else:
                return self.check_subscribable(obj, index, node.array, value)
        if arr != value:
            TypeError(
                node.range,
                f"Expected assigned value to be of type '{arr.str()}' but got '{value.str()}'",
            ).throw()
        return value

    def visitClassDeclarationNode(self, node: ClassDeclarationNode):
        self.current_block.append_block(Block.class_())
        class_name = node.name.value
        class_ob = FloClass(class_name)
        self.context.set(class_name, class_ob)
        self.class_within = class_ob
        self.constants.append(class_name)
        self.visit(node.body)
        self.class_within = None
        self.current_block.pop_block()

    def visitTypeAliasNode(self, node: TypeAliasNode):
        self.types_aliases[node.identifier.value] = node.type

    def visitPropertyAccessNode(self, node: PropertyAccessNode):
        root: FloObject = self.visit(node.expr)
        if not isinstance(root, FloObject):
            TypeError(node.expr.range, "Expected an object").throw()
        property_name = node.property.value
        value = root.referer.properties.get(
            property_name) or root.referer.methods.get(property_name)
        if value == None:
            GeneralError(node.property.range,
                         f"{property_name} not defined on {root.referer.name} object").throw()
        return value

    def visitPropertyAssignNode(self, node: PropertyAssignNode):
        expr = self.visit(node.expr)
        value = self.visit(node.value)
        if expr != value:
            TypeError(
                node.range, f"Expected type {expr.str()} but got type {value.str()}").throw()
        return value

    def visitNewMemNode(self, node: NewMemNode):
        typeval = self.visit(node.type)
        if isinstance(typeval, FloObject):
            if typeval.referer.constructor:
                self.check_fnc_call(
                    typeval.referer.constructor, node.args, node)
            return typeval
        else:
            if len(node.args) > 1:
                GeneralError(node.args[1].range,
                             "Expecting only 1 or no argument").throw()
            if len(node.args) > 0:
                if not isinstance(self.visit(node.args[0]), FloInt):
                    GeneralError(node.args[2].range,
                                 "Expecting arg to be int ").throw()
            return FloPointer(typeval)

    def visitImportNode(self, node: ImportNode):
        #TODO: Needs work using NodeFinder.get_abs_path twice
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
