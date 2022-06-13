from typing import List
from flotypes import *
from astree import *
from lexer import TokType, Token
from errors import SyntaxError
from errors import Range

def str_to_flotype(str):
    if str == "int":
        return FloInt(None)
    if str == "float":
        return FloFloat(None)
    elif str == "void":
        return FloVoid(None)
        
class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.current_tok = None
        self.current_i = -1
        self.advance()

    def advance(self):
        self.current_i += 1
        if self.current_i < len(self.tokens):
            self.current_tok = self.tokens[self.current_i]
        else:
            self.current_tok = self.tokens[-1]

    def parse(self):
        res = self.stmts()
        if self.current_tok.type != TokType.EOF:
            SyntaxError(
                self.current_tok.range,
                f"Unexpected '{self.current_tok.type.value}', Expected '+', '-', '*' '/', '^' or an identifier",
            ).throw()
        return res

    def skip_new_lines(self) -> None:
        while self.current_tok.type == TokType.LN:
            self.advance()

    def stmts(self):
        stmts = []
        range_start = self.current_tok.range
        self.skip_new_lines()
        while (
            self.current_tok.type != TokType.RBRACE
            and self.current_tok.type != TokType.EOF
        ):
            stmt = self.stmt()
            stmts.append(stmt)
            self.skip_new_lines()
        return StmtsNode(stmts, Range.merge(range_start, self.current_tok.range))

    def block(self):
        self.skip_new_lines()
        if self.current_tok.type != TokType.LBRACE:
            return self.expression()
        self.advance()
        if self.current_tok.type == TokType.RBRACE:
            self.advance()
            return []
        stmts = self.expressions()
        if self.current_tok.type != TokType.RBRACE:
            SyntaxError(self.current_tok.range, "Expected '}'").throw()
        self.advance()
        return stmts

    def stmt(self):
        self.skip_new_lines()
        tok = self.current_tok
        if tok.isKeyword("import"):
            return self.import_stmt()
        if tok.isKeyword("const"):
            return self.const_declaration()
        if tok.isKeyword("type"):
            return self.type_alias()
        if tok.isKeyword("class"):
            return self.class_declaration()
        if tok.isKeyword("enum"):
            return self.enum_declaration()
        elif tok.isKeyword(("fnc")):
            return self.fnc_def_stmt()
        else:
            SyntaxError(tok.range, f"Unexpected '{tok.value}'").throw()
    
    def expressions(self):
        expressions = []
        range_start = self.current_tok.range
        self.skip_new_lines()
        while (
            self.current_tok.type != TokType.RBRACE
            and self.current_tok.type != TokType.EOF
        ):
            stmt = self.expression()
            expressions.append(stmt)
            self.skip_new_lines()
        return StmtsNode(expressions, Range.merge(range_start, self.current_tok.range))

    def expression(self):
        tok = self.current_tok
        if tok.isKeyword("if"):
            return self.if_stmt()
        elif tok.isKeyword("for"):
            return self.for_stmt()
        elif tok.isKeyword("while"):
            return self.while_stmt()
        elif tok.inKeywordList(("return", "continue", "break")):
            return self.change_flow_stmt()
        return self.expr()

    def import_stmt(self):
        range_start = self.current_tok.range
        self.advance()
        ids = []
        path = ""
        if self.current_tok.type == TokType.IDENTIFER:
            ids = self.identifier_list()
            if not self.current_tok.isKeyword("from"):
                SyntaxError(self.current_tok.range,
                            "Expected keyword 'from'").throw()
            self.advance()
        if self.current_tok.type != TokType.STR:
            SyntaxError(self.current_tok.range, "Expected a string").throw()
        path = self.current_tok
        self.advance()
        return ImportNode(
            ids, path, Range.merge(
                range_start, path.range)
        )

    def if_stmt(self) -> IfNode:
        range_start = self.current_tok.range
        self.advance()
        cases = []
        else_case = None
        cond = self.expr()
        stmts = self.block()
        self.skip_new_lines()
        cases.append((cond, stmts))
        if self.current_tok.isKeyword("else"):
            self.advance()
            if self.current_tok.isKeyword("if"):
                resCases = self.if_stmt()
                cases += resCases.cases
                else_case = resCases.else_case
            else:
                stmts = self.block()
                else_case = stmts
        range_end = (else_case or cases[len(cases) - 1][0]).range
        return IfNode(cases, else_case, Range.merge(range_start, range_end))

    def const_declaration(self) -> ConstDeclarationNode:
        self.advance()
        range_start = self.current_tok.range
        if self.current_tok.type != TokType.IDENTIFER:
            SyntaxError(range_start, "Expected and identifier").throw()
        name_tok = self.current_tok
        self.advance()
        if self.current_tok.type != TokType.EQ:
            SyntaxError(self.current_tok.range, "Expected '='").throw()
        self.advance()
        value_node = self.expr()
        node_range = Range.merge(range_start, self.current_tok.range)
        return ConstDeclarationNode(name_tok, value_node, node_range)

    def type_alias(self):
        range_start = self.current_tok.range
        self.advance()
        identifier = self.current_tok
        self.advance()
        if self.current_tok.type != TokType.EQ:
            SyntaxError(self.current_tok.range, "Expected =").throw()
        self.advance()
        type = self.composite_type()
        node_range = Range.merge(range_start, type.range)
        return TypeAliasNode(identifier, type, node_range)
    
    def generic_constraint(self):
        tok = self.current_tok
        if tok.type != TokType.IDENTIFER:
            SyntaxError(tok.range, "Expected an identifer").throw()
        self.advance()
        return tok

    def generic_constraints(self):
        constraints = [self.generic_constraint()]
        while self.current_tok.type == TokType.COMMA:
            self.advance()
            constraints.append(self.generic_constraint())
        return constraints

    def class_declaration(self) -> Union[ClassDeclarationNode, GenericClassNode]:
        self.advance()
        range_start = self.current_tok.range
        if self.current_tok.type != TokType.IDENTIFER:
            SyntaxError(range_start, "Expected and identifier").throw()
        name = self.current_tok
        self.advance()
        constraints = None
        if self.current_tok.type == TokType.LT:
            self.advance()
            constraints = self.generic_constraints()
            if self.current_tok.type != TokType.GT:
                SyntaxError(self.current_tok.range, "Expected a '>'").throw()
            self.advance()
        parent = None
        if self.current_tok.isKeyword("extends"):
            self.advance()
            parent = self.prim_type()
        class_body = self.class_block()
        node_range = Range.merge(range_start, self.current_tok.range)
        node = ClassDeclarationNode(name, parent, class_body, node_range)
        if constraints != None:
            node = GenericClassNode(constraints, node, node_range)
        return node
    
    def class_block(self):
        if self.current_tok.type != TokType.LBRACE:
            SyntaxError(self.current_tok.range, "Expected '{'").throw()
        self.advance()
        statements = []
        range_start = self.current_tok.range
        while self.current_tok.type != TokType.RBRACE:
            self.skip_new_lines()
            statements.append(self.class_stmt())
        if self.current_tok.type != TokType.RBRACE:
            SyntaxError(self.current_tok.range, "Expected '}'").throw()
        node_range = Range.merge(range_start, self.current_tok.range)
        self.advance()
        return StmtsNode(statements, node_range)

    def class_stmt(self):
        access_modifier = None
        if self.current_tok.inKeywordList(["public", "private", "static"]):
            access_modifier = self.current_tok
            self.advance()
        if self.current_tok.type != TokType.IDENTIFER: 
            SyntaxError(self.current_tok.range, "Expected an Identifer").throw()
        name = self.current_tok
        self.advance()
        if self.current_tok.type == TokType.COL:
            self.advance()
            property_type = self.composite_type()
            node_range = Range.merge(name.range, property_type.range)
            return PropertyDeclarationNode(access_modifier, name, property_type, node_range)
        elif self.current_tok.type == TokType.LPAR:
            method_body = self.function_body()
            node_range = Range.merge(name.range, method_body.range)
            return MethodDeclarationNode(access_modifier, name, method_body, node_range)
        else:
            SyntaxError(self.current_tok.range, "Expected a property declaration or a method declaration").throw()
    
    def enum_declaration(self) -> EnumDeclarationNode:
        self.advance()
        range_start = self.current_tok.range
        token_list = []
        if self.current_tok.type != TokType.IDENTIFER:
            SyntaxError(self.current_tok.range, "Expected an Identifier").throw()
        name = self.current_tok
        self.advance()
        if self.current_tok.type != TokType.LBRACE:
            SyntaxError(self.current_tok.range, "Expected '{'").throw()
        self.advance()
        self.skip_new_lines()
        while self.current_tok.type == TokType.IDENTIFER:
            token_list.append(self.current_tok)
            self.advance()
            self.skip_new_lines()
        if self.current_tok.type != TokType.RBRACE:
            SyntaxError(self.current_tok.range, "Expected '}'").throw()
        self.advance()
        node_range = Range.merge(range_start, self.current_tok.range)
        return EnumDeclarationNode(name, token_list, node_range)


    def for_stmt(self) -> ForNode:
        self.advance()
        init = None
        range_start = self.current_tok.range
        init = self.expr()
        if self.current_tok.isKeyword("in"):
            self.advance()
            it = self.expr()
            stmts = self.block()
            return ForEachNode(
                init, it, stmts, Range.merge(
                    range_start, self.current_tok.range)
            )
        if self.current_tok.type != TokType.SEMICOL:
            SyntaxError(self.current_tok.range, "Expected ';'").throw()
        self.advance()
        cond = self.expr()
        if self.current_tok.type != TokType.SEMICOL:
            SyntaxError(self.current_tok.range, "Expected ';'").throw()
        self.advance()
        incr_decr = self.expr()
        stmts = self.block()
        return ForNode(
            init, cond, incr_decr, stmts, Range.merge(range_start, stmts.range)
        )

    def while_stmt(self):
        self.advance()
        cond = self.expr()
        stmts = self.block()
        return WhileNode(cond, stmts, Range.merge(cond.range, stmts.range))

    def fnc_def_stmt(self):
        self.advance()
        range_start = self.current_tok.range
        if self.current_tok.type != TokType.IDENTIFER:
            SyntaxError(self.current_tok.range, "Expected Identifier").throw()
        var_name = self.current_tok
        self.advance()
        if self.current_tok.type != TokType.LPAR:
            SyntaxError(self.current_tok.range, "Expected '('").throw()
        function_body = self.function_body()
        return FncDefNode(var_name, function_body, Range.merge(range_start, function_body.range))
    
    def function_body(self):
        self.advance()
        range_start = self.current_tok.range
        args, is_var_arg = self.arg_list()
        if self.current_tok.type != TokType.RPAR:
            SyntaxError(self.current_tok.range, "Expected ')'").throw()
        self.advance()
        return_type = None
        if self.current_tok.type == TokType.COL:
            self.advance()
            return_type = self.composite_type()
        body = None
        if self.current_tok.type == TokType.LBRACE:
            body = self.block()
        return FncNode(
            args,
            body,
            is_var_arg,
            Range.merge(range_start, self.current_tok.range),
            return_type,
        )

    def identifier_list(self):
        args = []
        if self.current_tok.type == TokType.IDENTIFER:
            id = self.current_tok
            self.advance()
            args.append(id)
            while self.current_tok.type == TokType.COMMA:
                self.advance()
                if self.current_tok.type != TokType.IDENTIFER:
                    SyntaxError(
                        self.current_tok.range, "Expected an Identifier"
                    ).throw()
                args.append(self.current_tok)
                self.advance()
        return args

    def arg_item(self):
        id = self.current_tok
        default_val = None
        self.advance()
        if self.current_tok.type == TokType.EQ:
            self.advance()
            default_val = self.expr()
            return (id, None, default_val)
        if self.current_tok.type != TokType.COL:
            SyntaxError(
                id.range, "Expected ':' or '=' after identifier").throw()
        self.advance()
        type_id = self.composite_type()
        if self.current_tok.type == TokType.EQ:
            self.advance()
            default_val = self.expr()
        return (id, type_id, default_val)

    def arg_list(self):
        args = []
        is_var_arg = False
        if self.current_tok.type == TokType.DOT_DOT_DOT:
            is_var_arg = True
            self.advance()
        if self.current_tok.type == TokType.IDENTIFER:
            args.append(self.arg_item())
            while self.current_tok.type == TokType.COMMA and not is_var_arg:
                self.advance()
                if self.current_tok.type == TokType.DOT_DOT_DOT:
                    is_var_arg = True
                    self.advance()
                if self.current_tok.type != TokType.IDENTIFER:
                    SyntaxError(
                        self.current_tok.range, "Expected an Identifier"
                    ).throw()
                args.append(self.arg_item())
        return args, is_var_arg

    def change_flow_stmt(self):
        range_start = self.current_tok.range
        if self.current_tok.isKeyword("return"):
            self.advance()
            expr = None
            if self.current_tok.type not in (TokType.LN, TokType.EOF, TokType.RBRACE):
                expr = self.expr()

            range = (
                range_start if expr is None else Range.merge(
                    range_start, expr.range)
            )
            return ReturnNode(expr, range)
        elif self.current_tok.isKeyword("continue"):
            self.advance()
            return ContinueNode(range_start)
        elif self.current_tok.isKeyword("break"):
            self.advance()
            return BreakNode(range_start)

    def expr(self):
        return self.num_op(
            self.bit_expr,
            ((TokType.KEYWORD, "as"), (TokType.KEYWORD, "is")),
            self.composite_type,
        )

    def bit_expr(self):
        return self.num_op(
            self.comp_expr,
            (
                (TokType.KEYWORD, "and"),
                (TokType.KEYWORD, "or"),
                (TokType.KEYWORD, "xor"),
                (TokType.KEYWORD, "in"),
                TokType.SL,
                TokType.SR,
            ),
        )

    def comp_expr(self):
        if self.current_tok.type == TokType.NOT:
            tok = self.current_tok
            self.advance()
            expr = self.comp_expr()
            return UnaryNode(tok, expr, Range.merge(tok.range, expr.range))
        return self.num_op(
            self.arith_expr,
            (
                TokType.NEQ,
                TokType.EEQ,
                TokType.LT,
                TokType.LEQ,
                TokType.GT,
                TokType.GTE,
            ),
        )

    def arith_expr(self):
        return self.num_op(self.range_expr, (TokType.PLUS, TokType.MINUS))

    def range_expr(self):
        node = None
        if self.current_tok.type != TokType.DOT_DOT:
            node = self.arith_expr1()
            start_range = node.range
        else:
            start_range = self.current_tok.range
        if self.current_tok.type ==  TokType.DOT_DOT:
            self.advance()
            end = self.arith_expr1()
            node = RangeNode(node, end, Range.merge(start_range, end.range))
        return node


    def arith_expr1(self):
        return self.num_op(
            self.unary_expr, (TokType.MULT, TokType.DIV,
                              TokType.MOD, TokType.POW)
        )

    def unary_expr(self):
        tok = self.current_tok
        if tok.type in (TokType.PLUS, TokType.MINUS, TokType.AMP):
            self.advance()
            f = self.unary_expr()
            return UnaryNode(tok, f, Range.merge(tok.range, f.range))
        elif tok.type in (TokType.PLUS_PLUS, TokType.MINUS_MINUS):
            self.advance()
            f = self.unary_expr()
            return IncrDecrNode(
                tok, f, True, Range.merge(tok.range, self.current_tok.range)
            )
        elif tok.isKeyword("new"):
            return self.new_memexpr()
        return self.unary_expr1()

    def new_memexpr(self):
        tok = self.current_tok
        self.advance()
        type = self.composite_type()
        args = None
        end_range = self.current_tok.range
        if self.current_tok.type == TokType.LPAR:
            self.advance()
            if self.current_tok.type == TokType.RPAR:
                node_range = Range.merge(tok.range, self.current_tok.range)
                self.advance()
                return NewMemNode(type, [], node_range)
            args = self.expr_list()
            if self.current_tok.type != TokType.RPAR:
                SyntaxError(self.current_tok.range, "Expected )").throw()
            end_range = self.current_tok.range
            self.advance()
        node_range = Range.merge(tok.range, end_range)
        return NewMemNode(type, args, node_range)

    def unary_expr1(self):
        node = self.expr_value_op()
        if self.current_tok.type in (TokType.PLUS_PLUS, TokType.MINUS_MINUS) and (isinstance(node, VarAccessNode)
                                                                                  or isinstance(node, ArrayAccessNode) or isinstance(node, PropertyAccessNode)):
            tok = self.current_tok
            self.advance()
            return IncrDecrNode(
                tok, node, False, Range.merge(
                    tok.range, self.current_tok.range)
            )
        return node

    def expr_list(self):
        args = []
        expr = self.expr()
        args.append(expr)
        while self.current_tok.type == TokType.COMMA:
            self.advance()
            expr = self.expr()
            args.append(expr)
        return args

    def assign_part(self, node: Node):
        self.advance()
        value = self.expr()
        node_range = Range.merge(node.range, value.range)
        if isinstance(node, VarAccessNode):
            return VarAssignNode(node.var_name, value, None, node_range)
        if isinstance(node, ArrayAccessNode):
            return ArrayAssignNode(node, value, node_range)
        elif isinstance(node, PropertyAccessNode):
            return PropertyAssignNode(node, value, node_range)
        else:
            SyntaxError(
                node.range, "Unexpected expression expected identifier or array").throw()

    def expr_value_op(self):
        range_start = self.current_tok.range
        node = self.expr_value()
        while (
            self.current_tok.type == TokType.LBRACKET
            or self.current_tok.type == TokType.LPAR
            or self.current_tok.type == TokType.DOT
        ):
            if self.current_tok.type == TokType.DOT:
                node = self.property_access(node)
            elif self.current_tok.type == TokType.LBRACKET:
                self.advance()
                expr = self.expr()
                if self.current_tok.type != TokType.RBRACKET:
                    SyntaxError(self.current_tok.range, "Expected ']'").throw()
                end_range = self.current_tok.range
                self.advance()
                node = ArrayAccessNode(
                    node, expr, Range.merge(node.range, end_range))

            elif self.current_tok.type == TokType.LPAR:
                self.advance()
                args = []
                if self.current_tok.type != TokType.RPAR:
                    args = self.expr_list()

                if self.current_tok.type != TokType.RPAR:
                    SyntaxError(self.current_tok.range, "Expected ')'").throw()
                end_range = self.current_tok.range
                self.advance()
                node = FncCallNode(
                    node, args, Range.merge(node.range, end_range))
        if self.current_tok.type == TokType.EQ:
            return self.assign_part(node)
        node.range  = Range.merge(range_start, node.range)
        return node

    def expr_value(self):
        tok = self.current_tok
        if tok.type == TokType.INT:
            self.advance()
            return IntNode(tok, tok.range)
        if tok.type == TokType.FLOAT:
            self.advance()
            return FloatNode(tok, tok.range)
        if tok.type == TokType.CHAR:
            self.advance()
            return CharNode(tok, tok.range)
        elif tok.type == TokType.STR:
            self.advance()
            return StrNode(tok, tok.range)
        elif tok.type == TokType.IDENTIFER:
            self.advance()
            node_type = None
            if self.current_tok.type != TokType.EQ and self.current_tok.type != TokType.COL:
                return VarAccessNode(tok, tok.range)
            elif self.current_tok.type == TokType.COL:
                self.advance()
                node_type = self.composite_type()
            if self.current_tok.type != TokType.EQ:
                SyntaxError(self.current_tok.range, "Expected '='").throw()
            self.advance()
            value = self.expr()
            node_range = Range.merge(tok.range, value.range)
            return VarAssignNode(tok, value, node_type, node_range)
        elif tok.type == TokType.LPAR:
            self.advance()
            exp = self.expr()
            if self.current_tok.type == TokType.RPAR:
                self.advance()
                return exp
            SyntaxError(self.current_tok.range, "Expected ')'").throw()
        elif tok.type == TokType.LBRACKET:
            self.advance()
            list = []
            if self.current_tok.type != TokType.RBRACKET:
                list = self.expr_list()

                if self.current_tok.type != TokType.RBRACKET:
                    SyntaxError(self.current_tok.range, "Expected ']'").throw()
            end_range = self.current_tok.range
            self.advance()
            return ArrayNode(list, Range.merge(tok.range, end_range))
        SyntaxError(
            tok.range, f"Expected an expression value before '{tok}'").throw()

    def property_access(self, expr):
        self.advance()
        ident = self.current_tok
        node_range = ident.range
        expr = PropertyAccessNode(expr, ident, node_range)
        if ident.type != TokType.IDENTIFER:
            SyntaxError(node_range, "Expected an Identifier").throw()
        self.advance()
        return expr

    def prim_type(self):
        tok = self.current_tok
        self.advance()
        if tok.type == TokType.LBRACE:
            if self.current_tok.type != TokType.INT:
                SyntaxError(self.current_tok.range, "Expected an int constant").throw()
            size = self.current_tok.value
            self.advance()
            if self.current_tok.type != TokType.RBRACE:
                SyntaxError(self.current_tok.range, "Expected a }").throw()
            self.advance()
            if not self.current_tok.inKeywordList(("int", "float")):
                SyntaxError(self.current_tok.range,
                            "Expected an 'int' or 'float'").throw()
            type = str_to_flotype(self.current_tok.value)
            type.bits = size
            end_range = self.current_tok.range
            self.advance()
            return TypeNode(type, Range.merge(tok.range, end_range))
        elif tok.inKeywordList(("int", "float", "void")):
            type = str_to_flotype(tok.value)
            return TypeNode(type, tok.range)
        elif tok.type == TokType.IDENTIFER:
            type = FloObject(tok)
            if self.current_tok.type == TokType.LT:
                self.advance()
                arg_list = self.type_list()
                type = FloGeneric(tok, arg_list)
                if self.current_tok.type != TokType.GT and self.current_tok.type != TokType.SR:
                    SyntaxError(self.current_tok.range, "Expected '>'").throw()
                if self.current_tok.type == TokType.GT:
                    self.advance()
                else:
                    self.current_tok.type = TokType.GT
            return TypeNode(type, tok.range)
    
    def type_list(self):
        types = [self.composite_type()]
        while(self.current_tok.type == TokType.COMMA):
            self.advance()
            types.append(self.composite_type())
        return types

    def fnc_type(self):
        range_start = self.current_tok.range
        self.advance()
        arg_types = []
        if self.current_tok.type != TokType.RPAR:
            arg_types = self.type_list()
            if self.current_tok.type != TokType.RPAR:
                SyntaxError(self.current_tok.range, "Expected ')'").throw()
        self.advance()
        if self.current_tok.type != TokType.ARROW:
            SyntaxError(self.current_tok.range, "Expected '=>'").throw()
        self.advance()
        type = FloInlineFunc(None, arg_types, self.composite_type())
        return TypeNode(type, Range.merge(range_start, type.return_type.range))

    def composite_type(self):
        tok = self.current_tok
        type = None
        if tok.inKeywordList(("int", "float", "void")) or tok.type == TokType.IDENTIFER or tok.type == TokType.LBRACE:
            type = self.prim_type()
        elif tok.type == TokType.LPAR:
            return self.fnc_type()
        while self.current_tok.type == TokType.MULT or self.current_tok.type == TokType.LBRACKET:
            if self.current_tok.type == TokType.MULT:
                end_range = self.current_tok.range
                self.advance()
                type = TypeNode(FloPointer(type), Range.merge(type.range, end_range))
            else:
                self.advance()
                size = self.expr()
                if self.current_tok.type != TokType.RBRACKET:
                    if self.current_tok.type != TokType.RBRACKET:
                        SyntaxError(self.current_tok.range,
                                    "Expected ']'").throw()
                end_range = self.current_tok.range
                self.advance()
                arr_ty = FloArray(None, size)
                arr_ty.elm_type = type
                type = TypeNode(arr_ty, Range.merge(type.range, end_range))
        if type:
            return type
        else:
            SyntaxError(tok.range, "Expected type definition").throw()

    def num_op(self, func_a, toks, func_b=None):
        if func_b == None:
            func_b = func_a
        left_node = func_a()
        while (
            self.current_tok.type in toks
            or (self.current_tok.type, self.current_tok.value) in toks
        ):
            op_tok = self.current_tok
            self.advance()
            if self.current_tok.type == TokType.EQ:
                assign_node = self.assign_part(left_node)
                node_range = Range.merge(left_node.range, assign_node.range)
                num_op_node = NumOpNode(
                    left_node, op_tok, assign_node.value, assign_node.value.range)
                assign_node.value = num_op_node
                assign_node.range = node_range
                return assign_node
            else:
                right_node = func_b()
                left_node = NumOpNode(
                    left_node,
                    op_tok,
                    right_node,
                    Range.merge(left_node.range, right_node.range),
                )
        return left_node
