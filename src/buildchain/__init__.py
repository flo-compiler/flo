class BuildCache:
    module_asts = {}
from src.context import Context

class Visitor:
    def __init__(self, context: Context):
        self.context = context

    def visit(self, node):
        return node.accept(self)

    def visitNumNode(self, node): pass
    
    def visitStrNode(self, node): pass

    def visitNumOpNode(self, node): pass
        
    def visitUnaryNode(self, node): pass
    
    def visitIncrDecrNode(self, node): pass

    def visitVarAccessNode(self, node): pass

    def visitStmtsNode(self, node): pass

    def visitVarAssignNode(self, node): pass
    
    def visitIfNode(self, node): pass

    def visitForNode(self, node): pass

    def visitForEachNode(self, node): pass

    def visitWhileNode(self, node): pass
    
    def visitFncDefNode(self, node): pass
    
    def visitReturnNode(self, node): pass

    def visitContinueNode(self, node): pass

    def visitBreakNode(self, node): pass

    def visitFncCallNode(self, node): pass
    
    def visitTypeNode(self, node): pass

    def visitArrayNode(self, node): pass

    def visitArrayAccessNode(self, node): pass

    def visitDictNode(self, node): pass

    def visitContinueNode(self, node): pass

    def visitTypeCastNode(self, node): pass

    def visitImportNode(self, node): pass