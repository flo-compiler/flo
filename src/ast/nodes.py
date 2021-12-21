from typing import List, Tuple
from ast.visitor import Visitor
from buildchain.tokens import Token
from utils.range import Range

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
    def accept(self, visitor: Visitor):
        return visitor.visitArrayNode(self)

class BreakNode(Node):
    def __init__(self, range: Range):
        self.range = range
    def accept(self, visitor: Visitor):
        return visitor.visitBreakNode(self)    


class ContinueNode(Node):
    def __init__(self, range: Range):
        self.range = range
    def accept(self, visitor: Visitor):
        return visitor.visitContinueNode(self)

class FncCallNode:
    def __init__(self, name: VarAccessNode, args:List[Node], range: Range):
        self.name = name
        self.args = args
        self.range = range
    def accept(self, visitor: Visitor):
        return visitor.visitFncCallNode(self)

class StmtsNode(Node):
    def __init__(self, stmts: List[Node], range: Range):
        self.stmts = stmts
        self.range = range
    def accept(self, visitor: Visitor):
        return visitor.visitStmtsNode(self)


class TypeNode(Node):
    def __init__(self, type, range: Range):
        self.type = type
        self.range = range
    def accept(self, visitor: Visitor):
        return visitor.visitTypeNode(self)


class FncDefNode:
    def __init__(self, var_name: Token, args:List[Tuple[Token, TypeNode]], body: StmtsNode, range: Range, return_type: TypeNode=None):
        self.var_name = var_name
        self.args = args
        self.body = body
        self.range = range
        self.return_type = return_type
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
    def __init__(self, cases: List[Tuple[Node, StmtsNode]], else_case:StmtsNode, range: Range) -> None:
        self.cases = cases
        self.else_case = else_case
        self.range = range
    def accept(self, visitor: Visitor):
        return visitor.visitIfNode(self)


class IncrDecrNode(Node):
    def __init__(self, id: Token, identifier: VarAccessNode, ispre: bool, range: Range):
        self.id = id
        self.identifier = identifier
        self.ispre = ispre
        self.range = range
    def accept(self, visitor: Visitor):
        return visitor.visitIncrDecrNode(self)

class ImportNode(Node):
    def __init__(self, ids: List[Token] , path: Token, range: Range):
        self.ids = ids
        self.path = path
        self.range = range
    def accept(self, visitor: Visitor):
        return visitor.visitImportNode(self)


class NumNode(Node):
    def __init__(self, tok: Token, range: Range):
        self.tok = tok
        self.range = range
    def accept(self, visitor: Visitor):
        return visitor.visitNumNode(self)


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



class StrNode(Node):
    def __init__(self, tok: Token, range: Range):
        self.tok = tok
        self.range = range
    def accept(self, visitor: Visitor):
        return visitor.visitStrNode(self)


class UnaryNode(Node):
    def __init__(self, op: Token, tok: Node, range):
        self.op = op
        self.tok = tok
        self.range = range
    def accept(self, visitor: Visitor):
        return visitor.visitUnaryNode(self)


class VarAssignNode(Node):
    def __init__(self, var_name: Token, value: Node, range: Range, val_type: TypeNode=None):
        self.var_name = var_name
        self.value = value
        self.range = range
        self.val_type = val_type
    def accept(self, visitor: Visitor):
        return visitor.visitVarAssignNode(self)


class WhileNode(Node):
    def __init__(self, cond: Node, stmt: StmtsNode, range: Range):
        self.cond = cond
        self.stmt = stmt
        self.range = range
    def accept(self, visitor: Visitor):
        return visitor.visitWhileNode(self)
