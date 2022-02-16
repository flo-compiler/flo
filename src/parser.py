from typing import List
from flotypes import FloArray, FloDict, str_to_flotype
from interfaces.astree import *
from lexer import TokType, Token
from errors import SyntaxError
from errors import Range


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

    def skipNewLines(self) -> None:
        while self.current_tok.type == TokType.LN:
            self.advance()

    def stmts(self):
        stmts = []
        range_start = self.current_tok.range
        self.skipNewLines()
        stmt = self.stmt()
        stmts.append(stmt)
        self.skipNewLines()
        while (
            self.current_tok.type != TokType.RBRACE
            and self.current_tok.type != TokType.EOF
        ):
            stmt = self.stmt()
            stmts.append(stmt)
            self.skipNewLines()
        return StmtsNode(stmts, Range.merge(range_start, self.current_tok.range))

    def block(self):
        self.skipNewLines()
        if self.current_tok.type != TokType.LBRACE:
            return self.stmt()
        self.advance()
        if self.current_tok.type == TokType.RBRACE:
            self.advance()
            return []
        stmts = self.stmts()
        if self.current_tok.type != TokType.RBRACE:
            SyntaxError(self.current_tok.range, "Expected '}'").throw()
        self.advance()
        return stmts

    def stmt(self):
        tok = self.current_tok
        if tok.isKeyword("import"):
            return self.import_stmt()
        if tok.isKeyword("if"):
            return self.if_stmt()
        elif tok.isKeyword("for"):
            return self.for_stmt()
        elif tok.isKeyword("foreach"):
            return self.foreach_stmt()
        elif tok.isKeyword("while"):
            return self.while_stmt()
        elif tok.isKeyword("fnc"):
            return self.fnc_def_stmt()
        elif tok.inKeywordList(("return", "continue", "break")):
            return self.change_flow_stmt()
        return self.expr()

    def import_stmt(self):
        range_start = self.current_tok.range
        self.advance()
        ids = []
        path = ""
        importAll = False
        if self.current_tok.type == TokType.MULT:
            ids = []
            importAll = True
            self.advance()
        elif self.current_tok.type == TokType.IDENTIFER:
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
            ids, importAll, path, Range.merge(
                range_start, self.current_tok.range)
        )

    def if_stmt(self) -> IfNode:
        range_start = self.current_tok.range
        self.advance()
        cases = []
        else_case = None
        cond = self.expr()
        stmts = self.block()
        self.skipNewLines()
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

    def for_stmt(self) -> ForNode:
        self.advance()
        init = None
        range_start = self.current_tok.range
        init = self.expr()
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

    def foreach_stmt(self):
        range_start = self.current_tok.range
        self.advance()
        if self.current_tok.type != TokType.IDENTIFER:
            SyntaxError(self.current_tok.range,
                        "Expected an Identifier").throw()
        id = self.current_tok
        self.advance()
        if not self.current_tok.isKeyword("in"):
            SyntaxError(self.current_tok.range,
                        "Expected keyword 'in'").throw()
        self.advance()
        it = self.expr()
        stmts = self.block()
        return ForEachNode(
            id, it, stmts, Range.merge(range_start, self.current_tok.range)
        )

    def while_stmt(self):
        self.advance()
        cond = self.expr()
        stmts = self.block()
        return WhileNode(cond, stmts, Range.merge(cond.range, stmts.range))

    def fnc_def_stmt(self):
        self.advance()
        start_range = self.current_tok.range
        var_name = None
        if self.current_tok.type != TokType.IDENTIFER:
            SyntaxError(self.current_tok.range, "Expected Identifier").throw()
        var_name = self.current_tok
        self.advance()
        if self.current_tok.type != TokType.LPAR:
            SyntaxError(self.current_tok.range, "Expected '('").throw()
        self.advance()
        args = self.param_list()
        if self.current_tok.type != TokType.RPAR:
            SyntaxError(self.current_tok.range, "Expected ')'").throw()
        self.advance()
        if self.current_tok.type != TokType.COL:
            SyntaxError(
                self.current_tok.range, "Expected function type definition"
            ).throw()
        self.advance()
        return_type = self.composite_type()
        if self.current_tok.type != TokType.ARROW:
            SyntaxError(self.current_tok.range, "Expected '=>'").throw()
        self.advance()
        body = self.block()
        return FncDefNode(
            var_name,
            args,
            body,
            Range.merge(start_range, self.current_tok.range),
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

    def param_list(self):
        args = []
        if self.current_tok.type == TokType.IDENTIFER:
            id = self.current_tok
            self.advance()
            if self.current_tok.type != TokType.COL:
                SyntaxError(id.range, "Expected ':' after identifier").throw()
            self.advance()
            type_id = self.composite_type()
            args.append((id, type_id))
            while self.current_tok.type == TokType.COMMA:
                self.advance()
                if self.current_tok.type != TokType.IDENTIFER:
                    SyntaxError(
                        self.current_tok.range, "Expected an Identifier"
                    ).throw()
                id = self.current_tok
                self.advance()
                if self.current_tok.type != TokType.COL:
                    SyntaxError(
                        id.range, "Expected ':' after identifier").throw()
                self.advance()
                type_id = self.composite_type()

                args.append((id, type_id))
        return args

    def change_flow_stmt(self):
        range_start = self.current_tok.range
        if self.current_tok.isKeyword("return"):
            self.advance()
            expr = None
            if (
                self.current_tok.type != TokType.LN
                and self.current_tok.type != TokType.EOF
            ):
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
            False,
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
        return self.num_op(self.arith_expr1, (TokType.PLUS, TokType.MINUS), True)

    def arith_expr1(self):
        return self.num_op(
            self.unary_expr, (TokType.MULT, TokType.DIV,
                              TokType.MOD, TokType.POW), True
        )

    def unary_expr(self):
        tok = self.current_tok
        if tok.type in (TokType.PLUS, TokType.MINUS):
            self.advance()
            f = self.unary_expr()
            return UnaryNode(tok, f, Range.merge(tok.range, f.range))
        elif tok.type in (TokType.PLUS_PLUS, TokType.MINUS_MINUS):
            self.advance()
            f = self.unary_expr()
            return IncrDecrNode(
                tok, f, True, Range.merge(tok.range, self.current_tok.range)
            )
        return self.value_expr()

    def value_expr(self):
        node = self.expr_value_op()
        if self.current_tok.type in (TokType.PLUS_PLUS, TokType.MINUS_MINUS):
            tok = self.current_tok
            self.advance()
            return IncrDecrNode(
                tok, node, False, Range.merge(
                    tok.range, self.current_tok.range)
            )
        id_type = None
        if self.current_tok.type == TokType.COL:
            self.advance()
            id_type = self.composite_type()

        if self.current_tok.type == TokType.EQ:
            self.advance()
            expr = self.expr()
            if isinstance(node, ArrayAccessNode):
                return ArrayAssignNode(node, expr, Range.merge(node.range, expr.range))
            elif isinstance(node, VarAccessNode):
                return VarAssignNode(
                    node.var_name, expr, Range.merge(
                        node.range, expr.range), id_type
                )
            else:
                SyntaxError(node.range, "Expected an Identifier").throw()
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

    def expr_value_op(self):
        node = self.expr_value()
        while (
            self.current_tok.type == TokType.LBRACKET
            or self.current_tok.type == TokType.LPAR
        ):
            if self.current_tok.type == TokType.LBRACKET:
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
        return node

    def expr_value(self):
        tok = self.current_tok
        if tok.type == TokType.INT:
            self.advance()
            return IntNode(tok, tok.range)
        if tok.type == TokType.FLOAT:
            self.advance()
            return FloatNode(tok, tok.range)
        elif tok.type == TokType.STR:
            self.advance()
            return StrNode(tok, tok.range)
        elif tok.type == TokType.IDENTIFER:
            node = VarAccessNode(tok, tok.range)
            self.advance()
            return node
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
        elif tok.type == TokType.LBRACE:
            self.advance()
            values = []
            if self.current_tok.type != TokType.RBRACE:
                k = self.expr()

                if self.current_tok.type != TokType.COL:
                    SyntaxError(self.current_tok.range, "Expected '}'").throw()
                self.advance()
                v = self.expr()

                values.append((k, v))
                while self.current_tok.type == TokType.COMMA:
                    self.advance()
                    k = self.expr()

                    if self.current_tok.type != TokType.COL:
                        SyntaxError(self.current_tok.range,
                                    f"Expected ':'").throw()
                    self.advance()
                    v = self.expr()

                    values.append((k, v))
            if self.current_tok.type != TokType.RBRACE:
                SyntaxError(self.current_tok.range, "Expected '}'").throw()
            self.advance()
            return DictNode(Range.merge(tok.range, self.current_tok.range), values)
        SyntaxError(
            tok.range, f"Expected an expression value before '{tok}'").throw()

    def composite_type(self):
        # TODO: Doesn't cover for array of dictionaries
        start_range = self.current_tok.range
        if self.current_tok.type == TokType.LBRACE:
            self.advance()
            node = self.composite_type()
            if self.current_tok.type != TokType.RBRACE:
                SyntaxError(self.current_tok.range, "Expected '}'").throw()
            self.advance()
            return TypeNode(
                FloDict(node.type), Range.merge(
                    start_range, self.current_tok.range)
            )
        if self.current_tok.inKeywordList(("int", "float", "bool", "str", "void")):
            type = str_to_flotype(self.current_tok.value)
            self.advance()
            while self.current_tok.type == TokType.LBRACKET:
                self.advance()
                type = FloArray(None, type)
                if self.current_tok.type == TokType.RBRACKET:
                    self.advance()
                else:
                    type.size = self.expr()
                    if self.current_tok.type != TokType.RBRACKET:
                        SyntaxError(self.current_tok.range, "Expected ']'").throw()
                    self.advance()
            return TypeNode(type, Range.merge(start_range, self.current_tok.range))
        else:
            SyntaxError(self.current_tok.range,
                        "Expected type definition").throw()

    def num_op(self, func_a, toks, checkEq=False, func_b=None):
        tok = self.current_tok
        if func_b == None:
            func_b = func_a
        left_node = func_a()
        while (
            self.current_tok.type in toks
            or (self.current_tok.type, self.current_tok.value) in toks
        ):
            op_tok = self.current_tok
            self.advance()
            if self.current_tok.type == TokType.EQ and checkEq:
                self.advance()
            else:
                checkEq = False
            right_node = func_b()
            left_node = NumOpNode(
                left_node,
                op_tok,
                right_node,
                Range.merge(left_node.range, right_node.range),
            )
            if checkEq:
                if isinstance(left_node.left_node, VarAccessNode):
                    left_node = VarAssignNode(
                        tok, left_node, Range.merge(
                            tok.range, self.current_tok.range)
                    )
                elif isinstance(left_node.left_node, ArrayAccessNode):
                    left_node = ArrayAssignNode(
                        left_node.left_node,
                        left_node,
                        Range.merge(tok.range, self.current_tok.range),
                    )
        return left_node
