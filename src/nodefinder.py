import sys
from enum import Enum
from os import path
from typing import List

from utils import get_ast_from_file
from context import Context
from flotypes import FloArray, FloInlineFunc, FloObject, FloPointer
from astree import ArrayAssignNode, ClassDeclarationNode, ConstDeclarationNode, FncCallNode, FncDefNode, ForEachNode, ForNode, IfNode, ImportNode, NewMemNode, NoOpNode, Node, NumOpNode, PropertyAssignNode, ReturnNode, StmtsNode, TypeAliasNode, TypeNode, VarAccessNode, VarAssignNode, Visitor, WhileNode
from errors import Range, NameError

def resource_path(relative_path):
     if hasattr(sys, '_MEIPASS'):
         return path.join(sys._MEIPASS, relative_path)
     return path.join(path.abspath("."), relative_path)

class NodesFindResult:
    def __init__(self, resolved: List[Node], unresolved: List[str]):
        self.resolved = resolved
        self.unresolved = unresolved

class BlockTy(Enum):
    class_ = "class"
    func = "function"

class Block:
    def __init__(self, name: str, ty: BlockTy):
        self.name = name
        self.type = ty

class NodeFinder(Visitor):
    def __init__(self, context: Context):
        super().__init__(context)
        self.block_in = None
        self.dependency_map: dict[str, List[str]] = {}

    @staticmethod
    def get_abs_path(m_path, current_file):
        abs_path = ""
        if m_path[:5] == "@flo/":
            stddir = resource_path('packages')
            abs_path = path.join(stddir, m_path[5:])
        else:
            abs_path = path.join(path.dirname(current_file), m_path)
        if path.isdir(abs_path):
            abs_path += "/"+abs_path.split("/")[-1]
        if abs_path.split(".")[-1] != "flo":
            abs_path+=".flo"
        return abs_path

    def resolve_dependencies(self, names: List[str], ignore: List[str]):
        unresolved = []
        resolved_nodes = []
        for name in names:
            if name in ignore: continue
            resolved_node = self.context.get(name)
            if resolved_node == None:
                unresolved.append(name)
            else:
                dependencies_for_name = self.dependency_map.get(name)
                if dependencies_for_name != None and len(dependencies_for_name) != 0:
                    dependency_nodes, unresolved_names = self.resolve_dependencies(dependencies_for_name, ignore)
                    resolved_nodes += dependency_nodes
                    unresolved += unresolved_names
                ignore.append(name)
                resolved_nodes.append(resolved_node)
        return resolved_nodes, unresolved

    def find(self, names_to_find: List[str], resolved_names: List[str], range: Range):
        module_path = NodeFinder.get_abs_path(self.context.display_name, range.start.fn)
        self.module_path = module_path
        ast = get_ast_from_file(self.module_path, range)
        if len(names_to_find) == 0:
            return NodesFindResult([ast], [])
        self.ignore = resolved_names
        self.visit(ast)
        resolved_nodes, unresolved_names = self.resolve_dependencies(names_to_find, resolved_names)
        not_found_names = list(filter(lambda name: name in names_to_find, unresolved_names))
        if len(not_found_names) > 0:
            NameError(range, f"Could not find {', '.join(not_found_names)} in {self.context.display_name}").throw()
        return NodesFindResult(resolved_nodes, not_found_names)

    
    def visitNumOpNode(self, node: NumOpNode):
        self.visit(node.left_node)
        self.visit(node.right_node)

    def visitStmtsNode(self, node: StmtsNode):
        for stmt in node.stmts:
            self.visit(stmt)

    def visitFncDefNode(self, node: FncDefNode):
        fnc_name = node.var_name.value
        if fnc_name in self.ignore: return
        has_parent_block = self.block_in != None
        if not has_parent_block:
            self.context.set(fnc_name, node)
            self.context = self.context.create_child(fnc_name)
            self.local_vars = []
            self.dependency_map[fnc_name] = []
            self.block_in = Block(fnc_name, BlockTy.func)
        for (_, ty, defval) in node.args:
            if ty:
                self.visit(ty)
            if defval:
                self.visit(defval)
        if node.body: self.visit(node.body)
        if node.return_type: self.visit(node.return_type)
        if not has_parent_block:
            self.context = self.context.parent
            self.local_vars = []
            self.block_in = None


    def visitVarAssignNode(self, node: VarAssignNode):
        var_name = node.var_name.value
        if var_name in self.ignore: return
        self.context.set(var_name, node)
        if self.block_in and self.block_in.type == BlockTy.func:
            self.local_vars.append(var_name)
        if node.type != None:
            self.visit(node.type)
        if node.value:
            self.visit(node.value)

    def visitArrayAssignNode(self, node: ArrayAssignNode):
        if node.value:
            self.visit(node.value)

    def visitPropertyAssignNode(self, node: PropertyAssignNode):
        if node.value:
            self.visit(node.value)

    def visitVarAccessNode(self, node: VarAccessNode):
        var_name = node.var_name.value
        if var_name in self.ignore: return
        if self.block_in and var_name not in self.local_vars:
            self.dependency_map.get(self.block_in.name).append(var_name)

    def visitFncCallNode(self, node: FncCallNode):
        self.visit(node.name)

    def visitConstDeclarationNode(self, node: ConstDeclarationNode):
        const_name = node.const_name.value
        if const_name in self.ignore: return
        self.context.set(const_name, node)
        self.visit(node.value)
    
    def visitForEachNode(self, node: ForEachNode):
        self.visit(node.stmt)

    def visitForNode(self, node: ForNode):
        self.visit(node.stmt)
    
    def visitWhileNode(self, node: WhileNode):
        self.visit(node.stmt)
    
    def visitReturnNode(self, node: ReturnNode):
        if node.value:
            self.visit(node.value)

    def visitNewMemNode(self, node: NewMemNode):
        self.visit(node.type)
        for arg in node.args:
            self.visit(arg)

    def visitIfNode(self, node: IfNode):
        for cond, case in node.cases:
            self.visit(cond)
            self.visit(case)
        if node.else_case:
            self.visit(node.else_case)
  

    def visitTypeNode(self, node: TypeNode):
        if isinstance(node.type, FloObject):
            class_name = node.type.referer.value
            if self.block_in != None and self.block_in.name != class_name:
                self.dependency_map.get(self.block_in.name).append(class_name)
        
        if isinstance(node.type, FloPointer) or isinstance(node.type, FloArray):
            self.visit(node.type.elm_type)
        if isinstance(node.type, FloInlineFunc):
            for arg in node.type.arg_types:
                self.visit(arg)
    
    def visitTypeAliasNode(self, node: TypeAliasNode):
        type_name = node.identifier.value
        if type_name in self.ignore: return
        self.visit(node.type)
        self.context.set(type_name, node)
    

    def visitClassDeclarationNode(self, node: ClassDeclarationNode):
        class_name = node.name.value
        if class_name in self.ignore: return
        self.context.set(class_name, node)
        self.context = self.context.create_child(class_name)
        self.block_in = Block(class_name, BlockTy.class_)
        self.dependency_map[class_name] = []
        self.local_vars = []
        self.visit(node.body)
        self.context = self.context.parent
        self.local_vars = []
        self.block_in = None

    def visitImportNode(self, node: ImportNode):
        symbols_to_import = filter(lambda name: name not in self.ignore, [id.value for id in node.ids])
        ctx = self.context.create_child(node.path.value)
        node_finder = NodeFinder(ctx)
        result = node_finder.find(list(symbols_to_import), self.context.get_symbols(), node.range)
        for resolved_node in result.resolved:
            self.visit(resolved_node)