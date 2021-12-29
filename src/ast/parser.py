from typing import List
from src.ast.nodes import *
from src.ast.tokens import TokType, Token
from src.errors import SyntaxError
from src.errors import Range
from src.valtypes.checks import arrayType, dictType, strToType



class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.current_tok = None
        self.current_i = -1
        self.advance()

    def advance(self):
        self.current_i+=1
        if(self.current_i < len(self.tokens)):
            self.current_tok = self.tokens[self.current_i]
        else:
            self.current_tok = self.tokens[-1]

    def parse(self):
        res, error = self.stmts()
        if not error and self.current_tok.type != TokType.EOF:
            return None, SyntaxError(self.current_tok.range,  f"Unexpected '{self.current_tok.type.value}', Expected '+', '-', '*' '/', '^' or an identifier")
        elif error:
            return None, error
        return res, None

    def skipNewLines(self)->None:
        while self.current_tok.type == TokType.LN:
            self.advance()

    def stmts(self):
        stmts = []
        range_start = self.current_tok.range
        self.skipNewLines()
        stmt, error = self.stmt()
        if error: return None, error
        stmts.append(stmt)
        self.skipNewLines()
        while self.current_tok.type != TokType.RBRACE and self.current_tok.type != TokType.EOF:
            stmt, error = self.stmt()
            if error: return None, error
            stmts.append(stmt)
            self.skipNewLines()
        return StmtsNode(stmts, Range.merge(range_start, self.current_tok.range)), None

    def block(self):
        self.skipNewLines()
        if self.current_tok.type != TokType.LBRACE:
            return self.stmt()
        self.advance()
        if self.current_tok.type == TokType.RBRACE:
            self.advance()
            return [], None
        stmts, error = self.stmts()
        if error: return None, error
        if self.current_tok.type != TokType.RBRACE:
             return None, SyntaxError(self.current_tok.range, "Expected '}'")
        self.advance()
        return stmts, None

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
            ids, error = self.identifier_list()
            if error: return None, error
        if not self.current_tok.isKeyword("from"):
            return None, SyntaxError(self.current_tok.range, "Expected keyword 'from'")
        self.advance()
        if self.current_tok.type != TokType.STR:
            return None, SyntaxError(self.current_tok.range, "Expected a string")
        path = self.current_tok
        self.advance()
        return ImportNode(ids, importAll, path, Range.merge(range_start, self.current_tok.range)), None

    def if_stmt(self):
        range_start = self.current_tok.range
        self.advance()
        cases = []
        else_case = None
        cond, error = self.expr()
        if error: return None, error
        stmts, error = self.block()
        self.skipNewLines()
        if error: return None, error
        cases.append((cond, stmts))
        if self.current_tok.isKeyword("else"):
            self.advance()
            if self.current_tok.isKeyword("if"):
                resCases, error = self.if_stmt()
                if error: return None, error
                cases+=resCases.cases
                else_case = resCases.else_case
            else:
                stmts, error = self.block()
                if error: return None, error
                else_case = stmts
        range_end = (else_case or cases[len(cases) - 1][0]).range
        return IfNode(cases, else_case, Range.merge(range_start, range_end)), None

    def for_stmt(self):
        self.advance()
        init = None
        range_start = self.current_tok.range
        init, error = self.expr()
        if error: return None, error
        if self.current_tok.type != TokType.SEMICOL:
            return None, SyntaxError(self.current_tok.range, "Expected ';'")
        self.advance()
        cond, error = self.expr()
        if error: return None, error
        if self.current_tok.type != TokType.SEMICOL:
            return None, SyntaxError(self.current_tok.range, "Expected ';'")
        self.advance()
        incr_decr, error = self.expr()
        if error: return None, error
        stmts, error = self.block()
        if error: return None, error
        return ForNode(init, cond, incr_decr, stmts, Range.merge(range_start, stmts.range)), None

    def foreach_stmt(self):
        range_start = self.current_tok.range
        self.advance()
        if self.current_tok.type != TokType.IDENTIFER:
            return None, SyntaxError(self.current_tok.range, "Expected an Identifier")
        id = self.current_tok
        self.advance()
        if not self.current_tok.isKeyword("in"):
            return None, SyntaxError(self.current_tok.range, "Expected keyword 'in'")
        self.advance()
        it, error = self.expr()
        if error: return None, error
        stmts, error = self.block()
        if error: return None, error
        return ForEachNode(id, it, stmts, Range.merge(range_start, self.current_tok.range)), None

    def while_stmt(self):
        self.advance()
        cond, error = self.expr()
        if error: return None, error
        stmts, error = self.block()
        if error: return None, error
        return WhileNode(cond, stmts, Range.merge(cond.range, stmts.range)), None

    def fnc_def_stmt(self):
        self.advance()
        start_range = self.current_tok.range
        var_name = None
        if self.current_tok.type != TokType.IDENTIFER:
            return None, SyntaxError(self.current_tok.range, "Expected Identifier")
        var_name = self.current_tok
        self.advance()
        if self.current_tok.type != TokType.LPAR:
            return None, SyntaxError(self.current_tok.range, "Expected '('")
        self.advance()
        args, error = self.param_list()
        if error: return None, error
        if self.current_tok.type != TokType.RPAR:
            return None, SyntaxError(self.current_tok.range, "Expected ')'")
        self.advance()
        if self.current_tok.type != TokType.COL:
            return None, SyntaxError(self.current_tok.range, "Expected function type definition")
        self.advance()
        return_type, error = self.composite_type()
        if error: return None, error
        if self.current_tok.type != TokType.ARROW:
            return None, SyntaxError(self.current_tok.range, "Expected '=>'")
        self.advance()
        body, error = self.block()
        if error: return None, error
        return FncDefNode(var_name, args, body, Range.merge(start_range, self.current_tok.range), return_type), None

    def identifier_list(self):
        args = []
        if self.current_tok.type == TokType.IDENTIFER:
            id = self.current_tok
            self.advance()
            args.append(id)
            while self.current_tok.type == TokType.COMMA:
                self.advance()
                if self.current_tok.type != TokType.IDENTIFER:
                    return None, SyntaxError(self.current_tok.range, "Expected an Identifier")
                args.append(self.current_tok)
                self.advance()
        return args, None

    def param_list(self):
        args = []
        if self.current_tok.type == TokType.IDENTIFER:
            id = self.current_tok
            self.advance()
            if self.current_tok.type != TokType.COL:
                return None, SyntaxError(id.range, "Expected ':' after identifier")
            self.advance()
            type_id, error = self.composite_type()
            if error: return None, error
            args.append((id, type_id))
            while self.current_tok.type == TokType.COMMA:
                self.advance()
                if self.current_tok.type != TokType.IDENTIFER:
                    return None, SyntaxError(self.current_tok.range, "Expected an Identifier")
                id =  self.current_tok
                self.advance()
                if self.current_tok.type != TokType.COL:
                    return None, SyntaxError(id.range, "Expected ':' after identifier")
                self.advance()
                type_id, error = self.composite_type()
                if error: return None, error
                args.append((id, type_id))
        return args, None        

    def change_flow_stmt(self):
        range_start = self.current_tok.range
        if self.current_tok.isKeyword("return"):
            self.advance()
            expr = None
            if self.current_tok.type != TokType.LN:
                expr, error  = self.expr()
                if error: return None, error
            range = range_start if expr is None else Range.merge(range_start, expr.range)
            return ReturnNode(expr, range), None
        elif self.current_tok.isKeyword("continue"):
            self.advance()
            return ContinueNode(range_start), None
        elif self.current_tok.isKeyword("break"):
            self.advance()
            return BreakNode(range_start), None

    def expr(self):
        return self.num_op(self.comp_expr, ((TokType.KEYWORD, "and"), (TokType.KEYWORD, "or"), (TokType.KEYWORD, "in"),  TokType.SL, TokType.SR))

    def comp_expr(self):
        if self.current_tok.type == TokType.NOT:
            tok = self.current_tok
            self.advance()
            expr, error = self.comp_expr()
            if error: return None, SyntaxError(error.range, error.msg+" '!'")
            return UnaryNode(tok, expr, Range.merge(tok.range, expr.range)), None
        return self.num_op(self.arith_expr, (TokType.NEQ, TokType.EEQ, TokType.LT, TokType.LEQ, TokType.GT, TokType.GTE))


    def arith_expr(self):
        return self.num_op(self.arith_expr1, (TokType.PLUS, TokType.MINUS), True)

    def arith_expr1(self):
        return self.num_op(self.unary_expr, (TokType.MULT, TokType.DIV, TokType.MOD, TokType.POW), True)
    
    def unary_expr(self):
        tok = self.current_tok
        if tok.type in (TokType.PLUS, TokType.MINUS):
            self.advance()
            f, error = self.unary_expr()
            if error: return None, error
            return UnaryNode(tok, f, Range.merge(tok.range, f.range)), None
        elif tok.type in (TokType.PLUS_PLUS, TokType.MINUS_MINUS):
            self.advance()
            f, error = self.unary_expr()
            if error: return None, error
            return IncrDecrNode(tok, f, True, Range.merge(tok.range, self.current_tok.range)), None
        return self.value_expr()
    

    def value_expr(self):
        node, error = self.expr_value_op()
        if error: return None, error
        if isinstance(node, VarAccessNode):
            id_type = None
            if self.current_tok.type == TokType.COL:
                self.advance()
                id_type, error = self.composite_type()
                if error: return None, error
        if self.current_tok.type == TokType.EQ:
            self.advance()
            expr, error = self.expr()
            if error: return None, error
            if isinstance(node, ArrayAccessNode):
                return ArrayAssignNode(node, expr, Range.merge(node.range, expr.range)), None
            else:
                return VarAssignNode(node.var_name, expr, Range.merge(node.range, expr.range), id_type), None
        if self.current_tok.type in (TokType.PLUS_PLUS, TokType.MINUS_MINUS):
            tok = self.current_tok
            self.advance()
            return IncrDecrNode(tok, node, False, Range.merge(tok.range, self.current_tok.range)), None
        if self.current_tok.isKeyword('as'):
            self.advance()
            type, error = self.composite_type()
            if error: return None, error
            return TypeCastNode(node, type, Range.merge(node.range, self.current_tok.range)), None
        return node, None

    def expr_list(self):
        args = []
        expr, error = self.expr()
        if error: return None, error
        args.append(expr)
        while self.current_tok.type == TokType.COMMA:
            self.advance()
            expr, error = self.expr()
            if error: return None, error
            args.append(expr)
        return args, None

    def expr_value_op(self):
        node, error = self.expr_value()
        if error: return None, error
        while self.current_tok.type == TokType.LBRACKET or self.current_tok.type == TokType.LPAR:
            if self.current_tok.type == TokType.LBRACKET:
                self.advance()
                expr, error = self.expr()
                if error: return None, error
                if self.current_tok.type != TokType.RBRACKET:
                    return None, SyntaxError(self.current_tok.range, "Expected ']'")
                end_range = self.current_tok.range
                self.advance()
                node = ArrayAccessNode(node, expr, Range.merge(node.range, end_range))
            elif self.current_tok.type == TokType.LPAR:
                self.advance()
                args = []
                if self.current_tok.type != TokType.RPAR:
                    args, error = self.expr_list()    
                    if error: return None, error
                if self.current_tok.type != TokType.RPAR:
                    return None, SyntaxError(self.current_tok.range, "Expected ')'")
                end_range = self.current_tok.range
                self.advance()
                node = FncCallNode(node, args, Range.merge(node.range, end_range))
        return node, None
        
    def expr_value(self):
        tok = self.current_tok
        if tok.type == TokType.NUM:
            self.advance()
            return NumNode(tok, tok.range), None
        elif tok.type == TokType.STR:
            self.advance()
            return StrNode(tok, tok.range), None
        elif tok.type == TokType.IDENTIFER:
            node = VarAccessNode(tok, tok.range)
            self.advance()
            return node, None
        elif tok.type == TokType.LPAR:
            self.advance()
            exp, error = self.expr()
            if error: return None, error
            if self.current_tok.type == TokType.RPAR:
                self.advance()
                return exp, None
            return None, SyntaxError(self.current_tok.range,  'Expected \')\'')
        elif tok.type == TokType.LBRACKET:
            self.advance()
            list = []
            if self.current_tok.type != TokType.RBRACKET:
                list, error = self.expr_list()
                if error: return None, error
                if self.current_tok.type != TokType.RBRACKET:
                    return None, SyntaxError(self.current_tok.range,  'Expected \']\'')
            end_range = self.current_tok.range
            self.advance()
            return ArrayNode(list, Range.merge(tok.range, end_range)), None
        elif tok.type == TokType.LBRACE:
            self.advance()
            values = []
            if self.current_tok.type != TokType.RBRACE:
                k, error = self.expr()
                if error: return None, error
                if self.current_tok.type != TokType.COL:
                    return None, SyntaxError(self.current_tok.range, "Expected '}'")
                self.advance()
                v, error = self.expr()
                if error: return None, error
                values.append((k,v))
                while self.current_tok.type == TokType.COMMA:
                    self.advance()
                    k, error = self.expr()
                    if error: return None, error
                    if self.current_tok.type != TokType.COL:
                        return None, SyntaxError(self.current_tok.range, f"Expected ':'")
                    self.advance()
                    v, error = self.expr()
                    if error: return None, error
                    values.append((k,v))
            if self.current_tok.type != TokType.RBRACE:
                return None, SyntaxError(self.current_tok.range, "Expected '}'")
            self.advance()
            return DictNode(Range.merge(tok.range, self.current_tok.range), values), None
        return None, SyntaxError(tok.range, f"Expected an expression value before '{tok}'")


    def composite_type(self):
        if self.current_tok.type == TokType.LBRACE:
            self.advance()
            if not self.current_tok.inKeywordList(("num", "bool", "str", "void")):
                return None, SyntaxError(self.current_tok.range, "Expected keyword 'num', 'bool', 'str'or 'void'")
            type = strToType(self.current_tok.value)
            self.advance()
            if self.current_tok.type != TokType.RBRACE:
                return None, SyntaxError(self.current_tok.range, "Expected '}'")
            self.advance()
            return dictType(type), None
        if self.current_tok.inKeywordList(("num", "bool", "str", "void")):
            type = strToType(self.current_tok.value)
            self.advance()
            while self.current_tok.type == TokType.LBRACKET:
                self.advance()
                type = arrayType(type)
                if self.current_tok.type != TokType.RBRACKET:
                    return None, SyntaxError(self.current_tok.range, "Expected ']'")
                self.advance()
            return type, None
        else:
            return None, SyntaxError(self.current_tok.range, 'Expected type definition')

    def num_op(self, func_a, toks, checkEq= False):
        tok = self.current_tok
        left_node, error = func_a()
        if error: return None, error
        while self.current_tok.type in toks or (self.current_tok.type, self.current_tok.value) in toks:
            op_tok = self.current_tok
            self.advance()
            if self.current_tok.type == TokType.EQ and checkEq:
                self.advance()
            else: checkEq = False
            right_node, error = func_a()
            if error: return None, error
            left_node = NumOpNode(left_node, op_tok, right_node, Range.merge(left_node.range, right_node.range))
            if checkEq:
                if isinstance(left_node.left_node, VarAccessNode):
                  left_node = VarAssignNode(tok, left_node, Range.merge(tok.range, self.current_tok.range))
                elif isinstance(left_node.left_node, ArrayAccessNode):
                  left_node = ArrayAssignNode(left_node.left_node, left_node, Range.merge(tok.range, self.current_tok.range))
        return left_node, None

        