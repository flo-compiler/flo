from context import Context
from typing import List, Tuple, Union
from lexer import Token
from errors import Range


class Visitor:
    def __init__(self, context: Context):
        self.context = context
        
    def visit(self, node):
        return node.accept(self)

    def visitIntNode(self, node): pass

    def visitFloatNode(self, node): pass

    def visitStrNode(self, node): pass

    def visitNumOpNode(self, node): pass

    def visitUnaryNode(self, node): pass

    def visitIncrDecrNode(self, node): pass

    def visitVarAccessNode(self, node): pass

    def visitStmtsNode(self, node): pass

    def visitConstDeclarationNode(self, node): pass
    
    def visitClassDeclarationNode(self, node): pass

    def visitVarAssignNode(self, node): pass

    def visitIfNode(self, node): pass

    def visitForNode(self, node): pass

    def visitForEachNode(self, node): pass

    def visitWhileNode(self, node): pass

    def visitFncNode(self, node): pass

    def visitFncDefNode(self, node): pass

    def visitReturnNode(self, node): pass

    def visitContinueNode(self, node): pass

    def visitBreakNode(self, node): pass

    def visitFncCallNode(self, node): pass

    def visitPropertyAccessNode(self, node): pass
    
    def visitPropertyAssignNode(self, node): pass

    def visitMethodDeclarationNode(self, node): pass

    def visitPropertyDeclarationNode(self, node): pass

    def visitTypeNode(self, node): pass

    def visitTypeAliasNode(self, node): pass

    def visitArrayNode(self, node): pass

    def visitArrayAccessNode(self, node): pass

    def visitArrayAssignNode(self, node): pass

    def visitNewMemNode(self, node): pass

    def visitContinueNode(self, node): pass

    def visitImportNode(self, node): pass

    def visitCharNode(self, node): pass

    def visitEnumDeclarationNode(self, node): pass



class Node:
    def __init__(self, range: Range):
        self.range = range

    def accept(self, _: Visitor): pass


class VarAccessNode(Node):
    def __init__(self, var_name: Token, range: Range):
        self.var_name = var_name
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitVarAccessNode(self)


class ArrayAccessNode(Node):
    def __init__(self, name: VarAccessNode, index: Node, range: Range):
        self.name = name
        self.index = index
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitArrayAccessNode(self)


class ArrayAssignNode(Node):
    def __init__(self, array: ArrayAccessNode, value: Node, range: Range):
        self.array = array
        self.value = value
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitArrayAssignNode(self)


class ArrayNode(Node):
    def __init__(self, elements: List[Node], range: Range):
        self.elements = elements
        self.range = range
        self.is_const_array = True

    def accept(self, visitor: Visitor):
        return visitor.visitArrayNode(self)


class BreakNode(Node):
    def __init__(self, range: Range):
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitBreakNode(self)


class TypeNode(Node):
    def __init__(self, type, range: Range):
        self.type = type
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitTypeNode(self)

class TypeAliasNode(Node):
    def __init__(self, identifier: Token, type: TypeNode, range: Range):
        self.identifier = identifier
        self.type = type
        self.range = range
    def accept(self, visitor: Visitor):
        return visitor.visitTypeAliasNode(self)


class VarAssignNode(Node):
    def __init__(self, var_name: Token, value: Node, type: TypeNode, range: Range):
        self.var_name = var_name
        self.type = type
        self.value = value
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitVarAssignNode(self)

class StmtsNode(Node):
    def __init__(self, stmts: List[Node], range: Range):
        self.stmts = stmts
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitStmtsNode(self)

class ClassDeclarationNode(Node):
    def __init__(self, name: Token, parent: TypeNode, body: StmtsNode, range: Range):
        self.name = name
        self.parent = parent
        self.body = body
        self.range = range
    
    def accept(self, visitor: Visitor):
        return visitor.visitClassDeclarationNode(self)

class ConstDeclarationNode(Node):
    def __init__(self, const_name: Token, value: Node, range: Range):
        self.const_name = const_name
        self.value = value
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitConstDeclarationNode(self)


class ContinueNode(Node):
    def __init__(self, range: Range):
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitContinueNode(self)


class FncCallNode(Node):
    def __init__(self, name: VarAccessNode, args: List[Node], range: Range):
        self.name = name
        self.args = args
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitFncCallNode(self)

class PropertyAccessNode(Node):
    def __init__(self, expr: Node, property: Token, range: Range):
        self.expr = expr
        self.property = property
        self.range = range
    
    def accept(self, visitor: Visitor):
        return visitor.visitPropertyAccessNode(self)

class PropertyAssignNode(Node):
    def __init__(self, expr: PropertyAccessNode, value: Node, range: Range):
        self.expr = expr
        self.value = value
        self.range = range
    def accept(self, visitor: Visitor):
        return visitor.visitPropertyAssignNode(self)

class FncNode(Node):
    def __init__(self, args: List[Tuple[Token, TypeNode, Node]], body: StmtsNode, is_variadic: bool, range: Range, return_type: TypeNode = None):
        self.args = args
        self.body = body
        self.range = range
        self.is_variadic = is_variadic
        self.return_type = return_type
    
    def accept(self, visitor: Visitor):
        return visitor.visitFncNode(self)

class PropertyDeclarationNode(Node):
    def __init__(self, access_modifier: Token, property_name: Token, type: TypeNode, range: Range):
        self.access_modifier = access_modifier
        self.property_name = property_name
        self.type = type
        self.range = range
    def accept(self, visitor: Visitor):
        return visitor.visitPropertyDeclarationNode(self)
    
class MethodDeclarationNode(Node):
    def __init__(self, access_modifier: Token, method_name: Token, method_body: FncNode, range: Range):
        self.access_modifier = access_modifier
        self.method_name = method_name
        self.method_body = method_body
        self.range = range
    
    def accept(self, visitor: Visitor):
        return visitor.visitMethodDeclarationNode(self)

class FncDefNode(Node):
    def __init__(self, func_name: Token, func_body: FncNode, range: Range):
        self.func_name = func_name
        self.func_body = func_body
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitFncDefNode(self)


class ForNode(Node):
    def __init__(self, init: Node, cond: Node, incr_decr: Node, stmt: StmtsNode, range):
        self.init = init
        self.cond = cond
        self.incr_decr = incr_decr
        self.stmt = stmt
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitForNode(self)


class ForEachNode(Node):
    def __init__(self, identifier: Token, iterator: Node, stmt: StmtsNode, range):
        self.identifier = identifier
        self.iterator = iterator
        self.stmt = stmt
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitForEachNode(self)


class IfNode(Node):
    def __init__(self, cases: List[Tuple[Node, StmtsNode]], else_case: StmtsNode, range: Range) -> None:
        self.cases = cases
        self.else_case = else_case
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitIfNode(self)


class IncrDecrNode(Node):
    def __init__(self, id: Token, identifier: Union[VarAccessNode, ArrayAccessNode], ispre: bool, range: Range):
        self.id = id
        self.identifier = identifier
        self.ispre = ispre
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitIncrDecrNode(self)


class ImportNode(Node):
    def __init__(self, ids: List[Token], path: Token, range: Range):
        self.ids = ids
        self.path = path
        self.range = range
        self.resolved_as = []

    def accept(self, visitor: Visitor):
        return visitor.visitImportNode(self)


class IntNode(Node):
    def __init__(self, tok: Token, range: Range):
        self.tok = tok
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitIntNode(self)

class CharNode(Node):
    def __init__(self, tok: Token, range: Range):
        self.tok = tok
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitCharNode(self)
class FloatNode(Node):
    def __init__(self, tok: Token, range: Range):
        self.tok = tok
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitFloatNode(self)


class NumOpNode(Node):
    def __init__(self, left_node: Node, op_tok: Token, right_node: Node, range: Range):
        self.left_node = left_node
        self.op = op_tok
        self.right_node = right_node
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitNumOpNode(self)


class ReturnNode(Node):
    def __init__(self, value: Node, range: Range):
        self.value = value
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitReturnNode(self)

class NewMemNode(Node):
    def __init__(self, type: TypeNode, args:List[Node] , range: Range):
        self.type = type
        self.args = args
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitNewMemNode(self)
    



class StrNode(Node):
    def __init__(self, tok: Token, range: Range):
        self.tok = tok
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitStrNode(self)


class UnaryNode(Node):
    def __init__(self, op: Token, value: Node, range):
        self.op = op
        self.value = value
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitUnaryNode(self)


class WhileNode(Node):
    def __init__(self, cond: Node, stmt: StmtsNode, range: Range):
        self.cond = cond
        self.stmt = stmt
        self.range = range

    def accept(self, visitor: Visitor):
        return visitor.visitWhileNode(self)

class EnumDeclarationNode(Node):
    def __init__(self, name: Token, tokens: List[Token], range: Range):
        self.name = name
        self.tokens = tokens
        self.range = range
    
    def accept(self, visitor: Visitor):
        return visitor.visitEnumDeclarationNode(self)