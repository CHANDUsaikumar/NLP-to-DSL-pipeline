
"""
DSL lexer and parser for the trading strategy language.

This module supports both package and script import contexts by attempting
relative imports first and falling back to absolute imports when needed.
"""

import re
from dataclasses import dataclass

# Import AST nodes with fallback for script execution
try:  # package import
    from .ast_nodes import (
        Strategy,
        BinaryOp,
        UnaryOp,
        Literal,
        SeriesRef,
        FuncCall,
    )
except ImportError:  # script import fallback
    from ast_nodes import (  # type: ignore
        Strategy,
        BinaryOp,
        UnaryOp,
        Literal,
        SeriesRef,
        FuncCall,
    )


class DSLParseError(Exception):
    """Raised when DSL parsing or validation fails."""
    pass


# ==============
# Tokenizer
# ==============

TOKEN_SPEC = [
    ("NUMBER",   r'\d+(\.\d+)?'),
    ("IDENT",    r'[A-Za-z_][A-Za-z0-9_]*'),
    ("GE",       r'>='),
    ("LE",       r'<='),
    ("EQ",       r'=='),
    ("NE",       r'!='),
    ("GT",       r'>'),
    ("LT",       r'<'),
    ("LBRACK",   r'\['),
    ("RBRACK",   r'\]'),
    ("LPAREN",   r'\('),
    ("RPAREN",   r'\)'),
    ("COMMA",    r','),
    ("COLON",    r':'),
    ("PLUS",     r'\+'),
    ("MINUS",    r'-'),
    ("TIMES",    r'\*'),
    ("DIV",      r'/'),
    ("NEWLINE",  r'\n'),
    ("SKIP",     r'[ \t\r]+'),
    ("MISMATCH", r'.'),
]

TOK_REGEX = '|'.join('(?P<%s>%s)' % pair for pair in TOKEN_SPEC)


@dataclass
class Token:
    type: str
    value: str


def tokenize(code: str):
    """
    Convert DSL text into a list of tokens.

    Identifiers are uppercased to make keywords case-insensitive.
    """
    tokens = []
    for mo in re.finditer(TOK_REGEX, code):
        kind = mo.lastgroup
        value = mo.group()
        if kind == "NUMBER":
            tokens.append(Token("NUMBER", value))
        elif kind == "IDENT":
            tokens.append(Token("IDENT", value.upper()))
        elif kind in ("NEWLINE", "SKIP"):
            continue
        elif kind == "MISMATCH":
            raise DSLParseError(f"Unexpected character: {value!r}")
        else:
            tokens.append(Token(kind, value))
    return tokens


# ==============
# Parser
# ==============

class Parser:
    """
    Recursive descent parser.
    """

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def advance(self):
        tok = self.peek()
        if tok is None:
            raise DSLParseError("Unexpected end of input")
        self.pos += 1
        return tok

    def expect(self, type_, value=None):
        tok = self.peek()
        if tok is None:
            raise DSLParseError(f"Expected {type_} but got EOF")
        if tok.type != type_:
            raise DSLParseError(f"Expected {type_} but got {tok.type}")
        if value is not None and tok.value != value:
            raise DSLParseError(f"Expected {value} but got {tok.value}")
        self.pos += 1
        return tok

    # --- entry point ---

    def parse_strategy(self):
        self.expect("IDENT", "ENTRY")
        self.expect("COLON")
        entry_expr = self.parse_bool_expr()

        self.expect("IDENT", "EXIT")
        self.expect("COLON")
        exit_expr = self.parse_bool_expr()

        if self.peek() is not None:
            raise DSLParseError("Extra tokens after EXIT expression")

        return Strategy(entry=entry_expr, exit=exit_expr)

    # --- boolean expressions ---

    def parse_bool_expr(self):
        return self.parse_or_expr()

    def parse_or_expr(self):
        node = self.parse_and_expr()
        while True:
            tok = self.peek()
            if tok and tok.type == "IDENT" and tok.value == "OR":
                self.advance()
                right = self.parse_and_expr()
                node = BinaryOp(left=node, op="OR", right=right)
            else:
                break
        return node

    def parse_and_expr(self):
        node = self.parse_not_expr()
        while True:
            tok = self.peek()
            if tok and tok.type == "IDENT" and tok.value == "AND":
                self.advance()
                right = self.parse_not_expr()
                node = BinaryOp(left=node, op="AND", right=right)
            else:
                break
        return node

    def parse_not_expr(self):
        tok = self.peek()
        if tok and tok.type == "IDENT" and tok.value == "NOT":
            self.advance()
            operand = self.parse_not_expr()
            return UnaryOp(op="NOT", operand=operand)
        return self.parse_comparison()

    # --- comparisons & arithmetic ---

    def parse_comparison(self):
        left = self.parse_arith_expr()
        tok = self.peek()
        if tok is None:
            return left

        if tok.type in ("GT", "LT", "GE", "LE", "EQ", "NE"):
            op_map = {
                "GT": ">",
                "LT": "<",
                "GE": ">=",
                "LE": "<=",
                "EQ": "==",
                "NE": "!=",
            }
            op = op_map[tok.type]
            self.advance()
            right = self.parse_arith_expr()
            return BinaryOp(left=left, op=op, right=right)

        if tok.type == "IDENT" and tok.value in ("CROSSOVER", "CROSSUNDER"):
            op = tok.value
            self.advance()
            right = self.parse_arith_expr()
            return BinaryOp(left=left, op=op, right=right)

        return left

    def parse_arith_expr(self):
        node = self.parse_term()
        while True:
            tok = self.peek()
            if tok and tok.type in ("PLUS", "MINUS"):
                op = tok.value
                self.advance()
                right = self.parse_term()
                node = BinaryOp(left=node, op=op, right=right)
            else:
                break
        return node

    def parse_term(self):
        node = self.parse_factor()
        while True:
            tok = self.peek()
            if tok and tok.type in ("TIMES", "DIV"):
                op = tok.value
                self.advance()
                right = self.parse_factor()
                node = BinaryOp(left=node, op=op, right=right)
            else:
                break
        return node

    def parse_factor(self):
        tok = self.peek()
        if tok is None:
            raise DSLParseError("Unexpected EOF in factor")

        if tok.type == "NUMBER":
            self.advance()
            return Literal(value=float(tok.value))

        if tok.type == "IDENT":
            ident = tok.value
            self.advance()
            next_tok = self.peek()

            # function call IDENT(...)
            if next_tok and next_tok.type == "LPAREN":
                self.advance()  # consume '('
                args = []
                if self.peek() and self.peek().type != "RPAREN":
                    args.append(self.parse_bool_expr())
                    while self.peek() and self.peek().type == "COMMA":
                        self.advance()
                        args.append(self.parse_bool_expr())
                self.expect("RPAREN")
                return FuncCall(name=ident, args=args)

            # series reference IDENT[NUMBER]?
            lag = 0
            if self.peek() and self.peek().type == "LBRACK":
                self.advance()  # '['
                lag_tok = self.expect("NUMBER")
                lag = int(float(lag_tok.value))
                self.expect("RBRACK")

            # store series names in lowercase to match DataFrame columns
            return SeriesRef(name=ident.lower(), lag=lag)

        if tok.type == "LPAREN":
            self.advance()
            node = self.parse_bool_expr()
            self.expect("RPAREN")
            return node

        raise DSLParseError(f"Unexpected token in factor: {tok.type} {tok.value!r}")


# ==============
# Validation & public API
# ==============

VALID_SERIES = {"open", "high", "low", "close", "volume"}
VALID_FUNCS = {"SMA", "RSI"}


def validate_strategy(strategy: Strategy):
    """
    Validate that all series and functions are known.
    """

    def walk(node):
        if isinstance(node, BinaryOp):
            walk(node.left)
            walk(node.right)
        elif isinstance(node, UnaryOp):
            walk(node.operand)
        elif isinstance(node, SeriesRef):
            if node.name not in VALID_SERIES:
                raise DSLParseError(f"Unknown series: {node.name}")
        elif isinstance(node, FuncCall):
            if node.name not in VALID_FUNCS:
                raise DSLParseError(f"Unknown function: {node.name}")
            for a in node.args:
                walk(a)
        elif isinstance(node, Literal):
            return
        elif isinstance(node, Strategy):
            walk(node.entry)
            walk(node.exit)
        else:
            return

    walk(strategy)


def parse_dsl(dsl_text: str) -> Strategy:
    """
    Parse DSL text into a Strategy AST and validate it.
    """
    tokens = tokenize(dsl_text)
    parser = Parser(tokens)
    strategy = parser.parse_strategy()
    validate_strategy(strategy)
    return strategy
