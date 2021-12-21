from typing import List
from ast.nodes import *
from buildchain.tokens import TokType, Token
from errors.syntaxError import SyntaxError
from utils.range import Range

class ParserState:
    def __init__(self, tokens: List[Token], current_i=-1):
        self.states_stack = []
        self.tokens = tokens
        self.current_tok = None
        self.current_i = current_i
        self.advance()

    def advance(self):
        self.current_i+=1
        if(self.current_i < len(self.tokens)):
            self.current_tok = self.tokens[self.current_i]
        else:
            self.current_tok = self.tokens[-1]
    
    def push(self):
        self.states_stack.append(self.current_i-1)

    def pop(self):
        self.current_i = self.states_stack.pop()
        self.advance()

class Parser:
    def __init__(self, tokens: List[Token]):
        self.state = ParserState(tokens)

    def parse(self):
        res, error = self.stmts()
        if not error and self.state.current_tok.type != TokType.EOF:
            return None, SyntaxError(self.state.current_tok.range,  f"Unexpected '{self.state.current_tok.type.value}', Expected '+', '-', '*' '/', '^' or an identifier")
        elif error:
            return None, error
        return res, None

    def skipNewLines(self)->None:
        while self.state.current_tok.type == TokType.LN:
            self.state.advance()

    def stmts(self):
        stmts = []
        range_start = self.state.current_tok.range
        self.skipNewLines()
        stmt, error = self.stmt()
        if error: return None, error
        stmts.append(stmt)
        self.skipNewLines()
        while self.state.current_tok.type != TokType.RBRACE and self.state.current_tok.type != TokType.EOF:
            stmt, error = self.stmt()
            if error: return None, error
            stmts.append(stmt)
            self.skipNewLines()
        return StmtsNode(stmts, Range.merge(range_start, self.state.current_tok.range)), None

    def block(self):
        self.skipNewLines()
        if self.state.current_tok.type != TokType.LBRACE:
            return self.stmt()
        self.state.advance()
        if self.state.current_tok.type == TokType.RBRACE:
            self.state.advance()
            return [], None
        stmts, error = self.stmts()
        if error: return None, error
        if self.state.current_tok.type != TokType.RBRACE:
             return None, SyntaxError(self.state.current_tok.range, "Expected '}'")
        self.state.advance()
        return stmts, None

    def stmt(self):
        tok = self.state.current_tok
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
        range_start = self.state.current_tok.range
        self.state.advance()
        ids = []
        path = ""
        if self.state.current_tok.type == TokType.IDENTIFER:
            ids, error = self.identifier_list()
            if error: return None, error
        if not self.state.current_tok.isKeyword("from"):
            return None, SyntaxError(self.state.current_tok.range, "Expected keyword 'from'")
        self.state.advance()
        if self.state.current_tok.type != TokType.STR:
            return None, SyntaxError(self.state.current_tok.range, "Expected a string")
        path = self.state.current_tok
        self.state.advance()
        return ImportNode(ids, path, Range.merge(range_start, self.state.current_tok.range)), None

    def if_stmt(self):
        range_start = self.state.current_tok.range
        self.state.advance()
        cases = []
        else_case = None
        cond, error = self.comp_expr()
        if error: return None, error
        stmts, error = self.block()
        self.skipNewLines()
        if error: return None, error
        cases.append((cond, stmts))
        if self.state.current_tok.isKeyword("else"):
            self.state.advance()
            if self.state.current_tok.isKeyword("if"):
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
        self.state.advance()
        init = None
        range_start = self.state.current_tok.range
        init, error = self.expr()
        if error: return None, error
        if self.state.current_tok.type != TokType.SEMICOL:
            return None, SyntaxError(self.state.current_tok.range, "Expected ';'")
        self.state.advance()
        cond, error = self.comp_expr()
        if error: return None, error
        if self.state.current_tok.type != TokType.SEMICOL:
            return None, SyntaxError(self.state.current_tok.range, "Expected ';'")
        self.state.advance()
        incr_decr, error = self.expr()
        if error: return None, error
        stmts, error = self.block()
        if error: return None, error
        return ForNode(init, cond, incr_decr, stmts, Range.merge(range_start, stmts.range)), None

    def foreach_stmt(self):
        range_start = self.state.current_tok.range
        self.state.advance()
        if self.state.current_tok.type != TokType.IDENTIFER:
            return None, SyntaxError(self.state.current_tok.range, "Expected an Identifier")
        id = self.state.current_tok
        self.state.advance()
        if not self.state.current_tok.isKeyword("in"):
            return None, SyntaxError(self.state.current_tok.range, "Expected keyword 'in'")
        self.state.advance()
        it, error = self.expr()
        if error: return None, error
        stmts, error = self.block()
        if error: return None, error
        return ForEachNode(id, it, stmts, Range.merge(range_start, self.state.current_tok.range)), None

    def while_stmt(self):
        self.state.advance()
        cond, error = self.comp_expr()
        if error: return None, error
        stmts, error = self.block()
        if error: return None, error
        return WhileNode(cond, stmts, Range.merge(cond.range, stmts.range)), None

    def fnc_def_stmt(self):
        self.state.advance()
        start_range = self.state.current_tok.range
        var_name = None
        if self.state.current_tok.type == TokType.IDENTIFER:
            var_name = self.state.current_tok
            self.state.advance()
        if self.state.current_tok.type != TokType.LPAR:
            return None, SyntaxError(self.state.current_tok.range, "Expected '('")
        self.state.advance()
        args, error = self.param_list()
        if error: return None, error
        if self.state.current_tok.type != TokType.RPAR:
            return None, SyntaxError(self.state.current_tok.range, "Expected ')'")
        self.state.advance()
        if self.state.current_tok.type != TokType.COL:
            return None, SyntaxError(self.state.current_tok.range, "Expected function type definition")
        self.state.advance()
        return_type, error = self.composite_type()
        if error: return None, error
        if self.state.current_tok.type != TokType.ARROW:
            return None, SyntaxError(self.state.current_tok.range, "Expected '=>'")
        self.state.advance()
        body, error = self.block()
        if error: return None, error
        return FncDefNode(var_name, args, body, Range.merge(start_range, self.state.current_tok.range), return_type), None

    def identifier_list(self):
        args = []
        if self.state.current_tok.type == TokType.IDENTIFER:
            id = self.state.current_tok
            self.state.advance()
            args.append(id)
            while self.state.current_tok.type == TokType.COMMA:
                self.state.advance()
                if self.state.current_tok.type != TokType.IDENTIFER:
                    return None, SyntaxError(self.state.current_tok.range, "Expected an Identifier")
                args.append(self.state.current_tok)
                self.state.advance()
        return args, None

    def param_list(self):
        args = []
        if self.state.current_tok.type == TokType.IDENTIFER:
            id = self.state.current_tok
            self.state.advance()
            if self.state.current_tok.type != TokType.COL:
                return None, SyntaxError(id.range, "Expected ':' after identifier")
            self.state.advance()
            type_id, error = self.composite_type()
            if error: return None, error
            args.append((id, type_id))
            while self.state.current_tok.type == TokType.COMMA:
                self.state.advance()
                if self.state.current_tok.type != TokType.IDENTIFER:
                    return None, SyntaxError(self.state.current_tok.range, "Expected an Identifier")
                id =  self.state.current_tok
                self.state.advance()
                if self.state.current_tok.type != TokType.COL:
                    return None, SyntaxError(id.range, "Expected ':' after identifier")
                self.state.advance()
                type_id, error = self.composite_type()
                if error: return None, error
                args.append((id, type_id))
        return args, None        

    def change_flow_stmt(self):
        range_start = self.state.current_tok.range
        if self.state.current_tok.isKeyword("return"):
            self.state.advance()
            expr = None
            if self.state.current_tok.type != TokType.LN:
                expr, error  = self.expr()
                if error: return None, error
            range = range_start if expr is None else Range.merge(range_start, expr.range)
            return ReturnNode(expr, range), None
        elif self.state.current_tok.isKeyword("continue"):
            self.state.advance()
            return ContinueNode(range_start), None
        elif self.state.current_tok.isKeyword("break"):
            self.state.advance()
            return BreakNode(range_start), None

    def expr(self):
        return self.num_op(self.comp_expr, ((TokType.KEYWORD, "and"), (TokType.KEYWORD, "or")))

    def comp_expr(self):
        if self.state.current_tok.type == TokType.NOT:
            tok = self.state.current_tok
            self.state.advance()
            expr, error = self.comp_expr()
            if error: return None, SyntaxError(error.range, error.msg+" 'not'")
            return UnaryNode(tok, expr, Range.merge(tok.range, expr.range)), None
        return self.num_op(self.arith_expr, (TokType.NEQ, TokType.EEQ, TokType.LT, TokType.LEQ, TokType.GT, TokType.GTE))


    def arith_expr(self):
        return self.num_op(self.arith_expr1, (TokType.PLUS, TokType.MINUS))

    def arith_expr1(self):
        return self.num_op(self.unary_expr, (TokType.MULT, TokType.DIV, TokType.MOD, TokType.POW))
    
    def unary_expr(self):
        tok = self.state.current_tok
        if tok.type in (TokType.PLUS, TokType.MINUS):
            self.state.advance()
            f, error = self.unary_expr()
            if error: return None, error
            return UnaryNode(tok, f, Range.merge(tok.range, f.range)), None
        elif tok.type in (TokType.PLUS_PLUS, TokType.MINUS_MINUS):
            self.state.advance()
            if self.state.current_tok.type != TokType.IDENTIFER:
                return None, SyntaxError(self.state.current_tok.range, 'Expected an Identifier')
            f, error = self.unary_expr()
            if error: return None, error
            return IncrDecrNode(tok, f, True, Range.merge(tok.range, self.state.current_tok.range)), None
        elif tok.type == TokType.IDENTIFER:
            return self.identifier_op_expr()
        return self.expr_value()
    
    def identifier_op_expr(self):
        tok = self.state.current_tok
        node = VarAccessNode(tok, tok.range)
        self.state.advance()
        id_type = None
        if self.state.current_tok.type == TokType.COL:
            self.state.advance()
            id_type, error = self.composite_type()
            if error: return None, error
        if self.state.current_tok.type in (TokType.PLUS_PLUS, TokType.MINUS_MINUS):
            tok = self.state.current_tok
            self.state.advance()
            return IncrDecrNode(tok, node, False, Range.merge(tok.range, self.state.current_tok.range)), None
        if self.state.current_tok.type in (TokType.PLUS, TokType.MINUS, TokType.MULT, TokType.DIV, TokType.MOD, ):
            op = self.state.current_tok
            self.state.advance()
            if self.state.current_tok.type == TokType.EQ:
               self.state.advance()
               expr, error = self.expr()
               if error: return None, error
               return VarAssignNode(tok, NumOpNode(node, op, expr, Range.merge(node.range, expr.range)),
                Range.merge(tok.range, self.state.current_tok.range)), None
            else:
                expr, error = self.expr()
                if error: return None, error
                return NumOpNode(node, op, expr, Range.merge(node.range, expr.range)), None
        elif self.state.current_tok.type == TokType.LPAR:
            self.state.advance()
            args = []
            if self.state.current_tok.type != TokType.RPAR:
                args, error = self.expr_list()    
                if error: return None, error
            if self.state.current_tok.type != TokType.RPAR:
                return None, SyntaxError(self.state.current_tok.range, "Expected ')'")
            end_range = self.state.current_tok.range
            self.state.advance()
            return FncCallNode(node, args, Range.merge(tok.range, end_range)), None
        elif self.state.current_tok.type == TokType.LBRACKET:
            while self.state.current_tok.type == TokType.LBRACKET:
                self.state.advance()
                expr, error = self.expr()
                if error: return None, error
                if self.state.current_tok.type != TokType.RBRACKET:
                    return None, SyntaxError(self.state.current_tok.range, "Expected ']'")
                end_range = self.state.current_tok.range
                self.state.advance()
                node = ArrayAccessNode(node, expr, Range.merge(tok.range, end_range))
        if self.state.current_tok.type == TokType.EQ:
            self.state.advance()
            if self.state.current_tok.isKeyword("fnc"):
                expr, error = self.fnc_def_stmt()
            else:
                expr, error = self.expr()
            if error: return None, error
            if isinstance(node, ArrayAccessNode):
                return ArrayAssignNode(node, expr, Range.merge(node.range, expr.range)), None
            else:
                return VarAssignNode(tok, expr, Range.merge(tok.range, expr.range), id_type), None
        return node, None
  
    def expr_list(self):
        args = []
        expr, error = self.expr()
        if error: return None, error
        args.append(expr)
        while self.state.current_tok.type == TokType.COMMA:
            self.state.advance()
            expr, error = self.expr()
            if error: return None, error
            args.append(expr)
        return args, None


    def expr_value(self):
        tok = self.state.current_tok
        if tok.type == TokType.NUM:
            self.state.advance()
            return NumNode(tok, tok.range), None
        elif tok.type == TokType.STR:
            self.state.advance()
            return StrNode(tok, tok.range), None
        elif tok.type == TokType.LPAR:
            self.state.advance()
            exp, error = self.expr()
            if error: return None, error
            if self.state.current_tok.type == TokType.RPAR:
                self.state.advance()
                return exp, None
            return None, SyntaxError(self.state.current_tok.range,  'Expected \')\'')
        elif tok.type == TokType.LBRACKET:
            self.state.advance()
            list = []
            if self.state.current_tok.type != TokType.RBRACKET:
                list, error = self.expr_list()
                if error: return None, error
                if self.state.current_tok.type != TokType.RBRACKET:
                    return None, SyntaxError(self.state.current_tok.range,  'Expected \']\'')
            end_range = self.state.current_tok.range
            self.state.advance()
            return ArrayNode(list, Range.merge(tok.range, end_range)), None
        return None, SyntaxError(tok.range, f"Expected an expression value before '{tok}'")


    def composite_type(self):
        from buildchain.typechecker import arrayType, strToType
        if self.state.current_tok.inKeywordList(("num", "bool", "str", "void")):
            type = strToType(self.state.current_tok.value)
            self.state.advance()
            while self.state.current_tok.type == TokType.LBRACKET:
                self.state.advance()
                type = arrayType(type)
                if self.state.current_tok.type != TokType.RBRACKET:
                    return None, SyntaxError(self.state.current_tok.range, "Expected ']'")
                self.state.advance()
            return type, None
        else:
            return None, SyntaxError(self.state.current_tok.range, 'Expected type definition')

    def num_op(self, func_a, toks, func_b=None):
        if func_b == None:
            func_b = func_a
        left_node, error = func_a()
        if error: return None, error
        while self.state.current_tok.type in toks or (self.state.current_tok.type, self.state.current_tok.value) in toks:
            op_tok = self.state.current_tok
            self.state.advance()
            right_node, error = func_b()
            if error: return None, error
            left_node = NumOpNode(left_node, op_tok, right_node, Range.merge(left_node.range, right_node.range))
        return left_node, None

        