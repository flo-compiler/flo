from collections import OrderedDict
from os import path
from typing import List
from context import Context
from flotypes import FloObject
from astree import ArrayAssignNode, ClassDeclarationNode, ConstDeclarationNode, FncCallNode, FncDefNode, ForEachNode, ForNode, IfNode, ImportNode, NoOpNode, Node, NumOpNode, ObjectCreateNode, PropertyAssignNode, ReturnNode, StmtsNode, TypeNode, VarAccessNode, VarAssignNode, Visitor, WhileNode
from lexer import TokType, Token


class NodeFinder(Visitor):
    cached_modules = {}

    def __init__(self, context: Context):
        super().__init__(context)
        self.in_func = False
        self.in_class = False
        self.module_root_node = None
        self.dependencies = []
        self.names = []
        self.local_vars = []
        self.nodes = OrderedDict()

    @staticmethod
    def cache(module_name, nodes):
        prev_cached = NodeFinder.cached_modules.get(module_name)
        if prev_cached != None:
            NodeFinder.cached_modules[module_name].update(nodes)
        else:
            NodeFinder.cached_modules[module_name] = nodes

    @staticmethod
    def get_abs_path(m_path, current_file):
        abs_path = ""
        if m_path[:5] == "@flo/":
            abs_path = path.join(path.dirname(
                __file__), "../packages", m_path[5:])
        else:
            abs_path = path.join(path.dirname(
                current_file), m_path)
        if path.isdir(abs_path):
            nested_dirs = abs_path.split("/")
            abs_path += "/"+nested_dirs[len(nested_dirs)-1]+".flo"
        return abs_path

    def find(self, names: List[str], node: Node, skip_names=[]):
        self.module_root_node = node
        prev_names = self.names
        self.ignored_names = skip_names
        self.names = names
        self.visit(node)
        self.names = prev_names
        return self.nodes
    
    def visitNumOpNode(self, node: NumOpNode):
        self.visit(node.left_node)
        self.visit(node.right_node)

    def visitStmtsNode(self, node: StmtsNode):
        for stmt in node.stmts:
            self.visit(stmt)

    def process_dependencies(self):
        if len(self.dependencies) > 0:
            dependency_nodes = self.find(
                self.dependencies, self.module_root_node)
            self.nodes.update(dependency_nodes)
            self.dependencies = []

    def visitFncDefNode(self, node: FncDefNode):
        fnc_name = node.var_name.value
        prev_local_vars = self.local_vars
        prev_dependencies = self.dependencies
        if not self.in_class and fnc_name in self.names and self.nodes.get(fnc_name) == None and not fnc_name in self.ignored_names:
            self.nodes[fnc_name] = node
            self.in_func = True
        if self.in_class or self.in_func and node.body:
            for (_, type_node, _) in node.args:
                self.visit(type_node)
            if node.return_type:
                self.visit(node.return_type)
            self.visit(node.body)
            self.in_func = False
            self.process_dependencies()
            self.local_vars = prev_local_vars
            self.dependencies = prev_dependencies

    def visitVarAssignNode(self, node: VarAssignNode):
        var_name = node.var_name.value
        if node.type != None:
            self.visit(node.type)
        if self.in_func or self.in_class:
            self.local_vars.append(var_name)
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
        if self.in_func or self.in_class and (var_name not in self.local_vars) and self.nodes.get(var_name) == None and var_name not in self.dependencies and var_name not in self.ignored_names:
            self.dependencies.append(var_name)

    def visitFncCallNode(self, node: FncCallNode):
        self.visit(node.name)

    def visitConstDeclarationNode(self, node: ConstDeclarationNode):
        var_name = node.declaration.var_name.value
        if var_name in self.names and var_name not in self.ignored_names and self.nodes.get(var_name) == None:
            self.nodes[var_name] = node
    
    def visitForEachNode(self, node: ForEachNode):
        self.visit(node.stmt)

    def visitForNode(self, node: ForNode):
        self.visit(node.stmt)
    
    def visitWhileNode(self, node: WhileNode):
        self.visit(node.stmt)
    
    def visitReturnNode(self, node: ReturnNode):
        if node.value:
            self.visit(node.value)

    def visitObjectCreateNode(self, node: ObjectCreateNode):
        name = node.class_name.type.referer.value
        if self.in_func or self.in_class and self.nodes.get(name) == None and name not in self.dependencies and name not in self.ignored_names:
            self.dependencies.append(name)

    def visitIfNode(self, node: IfNode):
        for cond, case in node.cases:
            self.visit(cond)
            self.visit(case)
        if node.else_case:
            self.visit(node.else_case)

    def visitTypeNode(self, node: TypeNode):
        if isinstance(node.type, FloObject):
            class_name = node.type.referer.value
            if (self.in_class or self.in_func) and self.nodes.get(class_name) == None and class_name not in self.dependencies and class_name not in self.ignored_names:
                self.dependencies.append(class_name)

    def visitClassDeclarationNode(self, node: ClassDeclarationNode):
        prev_local_vars = self.local_vars
        class_name = node.name.value
        if class_name in self.names and self.nodes.get(class_name) == None and class_name not in self.ignored_names:
            self.nodes[class_name] = node
            self.in_class = True
            self.visit(node.body)
            self.in_class = False
            self.process_dependencies()
            self.local_vars = prev_local_vars

    def visitImportNode(self, node: ImportNode):
        selected_ids = []
        exported_name = None
        if len(node.ids) == 0:
            self.nodes[node.path.value] = node
            return
        for identifier in node.ids:
            id_name = identifier.value
            if id_name in self.names and self.nodes.get(id_name) == None and id_name not in self.ignored_names:
                exported_name = id_name
                self.nodes[id_name] = NoOpNode(None)
                selected_ids.append(identifier)
        if exported_name != None:
            new_path = path.join(path.dirname(
                self.context.display_name), node.path.value)
            new_node = ImportNode(selected_ids, Token(
                TokType.IDENTIFER, node.path.range, new_path), node.range)
            self.nodes[exported_name] = new_node
