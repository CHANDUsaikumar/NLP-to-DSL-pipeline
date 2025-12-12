
"""
DSL lexer and parser for the trading strategy language.

This module supports both package and script import contexts by attempting
relative imports first and falling back to absolute imports when needed.
"""

from __future__ import annotations

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
    from .validator import validate_field_name, validate_indicator, VALID_SERIES, VALID_FUNCS
except ImportError:  # script import fallback
    from ast_nodes import (  # type: ignore
        Strategy,
        BinaryOp,
        UnaryOp,
        Literal,
        SeriesRef,
        FuncCall,
    )
    from validator import validate_field_name, validate_indicator, VALID_SERIES, VALID_FUNCS  # type: ignore


class DSLParseError(Exception):
    """Raised when DSL parsing or validation fails, with optional position info."""

    def __init__(self, message: str, position: int | None = None, line: int | None = None, col: int | None = None):
        self.position = position
        self.line = line
        self.col = col
        if line is not None and col is not None:
            super().__init__(f"{message} (line {line}, col {col})")
        else:
            super().__init__(message)


# ==============
# Tokenizer
# ==============

TOKEN_SPEC = [
    ("NUMBER", r"\d+(\.\d+)?"),
    ("SUFFIX", r"\b[KkMm]\b"),
    ("TRUE", r"\bTRUE\b"),
    ("FALSE", r"\bFALSE\b"),
    ("IDENT", r"[A-Za-z_][A-Za-z0-9_]*"),
    ("PERCENT", r"%|percent"),
    ("DAY", r"\bday\b"),
    ("CROSS", r"\bcross(?:es)?\b"),
    ("ABOVE", r"\babove\b"),
    ("BELOW", r"\bbelow\b"),
    ("GE", r">="),
    ("LE", r"<="),
    ("EQ", r"=="),
    ("NE", r"!="),
    ("GT", r">"),
    ("LT", r"<"),
    ("LBRACK", r"\["),
    ("RBRACK", r"\]"),
    ("LPAREN", r"\("),
    ("RPAREN", r"\)"),
    ("COMMA", r","),
    ("COLON", r":"),
    ("PLUS", r"\+"),
    ("MINUS", r"-"),
    ("TIMES", r"\*"),
    ("DIV", r"/"),
    ("NEWLINE", r"\n"),
    ("SKIP", r"[ \t\r]+"),
    ("MISMATCH", r"."),
]

TOK_REGEX = "|".join("(?P<%s>%s)" % pair for pair in TOKEN_SPEC)


@dataclass
class Token:
    type: str
    value: str
    line: int | None = None
    col: int | None = None


def tokenize(code: str):
    """Convert DSL text into a list of tokens; identifiers are uppercased."""
    tokens: list[Token] = []
    for mo in re.finditer(TOK_REGEX, code):
        kind = mo.lastgroup
        value = mo.group()
        start = mo.start()
        # compute line/col
        line = code.count("\n", 0, start) + 1
        last_newline = code.rfind("\n", 0, start)
        col = (start - last_newline) if last_newline != -1 else (start + 1)
        if kind == "NUMBER":
            tokens.append(Token("NUMBER", value, line=line, col=col))
        elif kind == "IDENT":
            tokens.append(Token("IDENT", value.upper(), line=line, col=col))
        elif kind == "SUFFIX":
            tokens.append(Token("SUFFIX", value.upper(), line=line, col=col))
        elif kind in ("NEWLINE", "SKIP"):
            continue
        elif kind == "MISMATCH":
            raise DSLParseError(f"Unexpected character: {value!r}", position=start, line=line, col=col)
        else:
            tokens.append(Token(kind, value, line=line, col=col))
    return tokens


# ==============
# Parser
# ==============

class Parser:
    """Recursive descent parser."""

    def __init__(self, tokens: list[Token], source_text: str | None = None):
        self.tokens = tokens
        self.pos = 0
        self.source_text = source_text or ""

    def peek(self) -> Token | None:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def advance(self) -> Token:
        tok = self.peek()
        if tok is None:
            snippet = self._snippet()
            raise DSLParseError(f"Unexpected end of input. Near: {snippet}")
        self.pos += 1
        return tok

    def expect(self, type_: str, value: str | None = None) -> Token:
        tok = self.peek()
        if tok is None:
            snippet = self._snippet()
            raise DSLParseError(f"Expected {type_} but got EOF. Near: {snippet}")
        if tok.type != type_:
            ctx = []
            for i in range(self.pos, min(self.pos + 5, len(self.tokens))):
                t = self.tokens[i]
                ctx.append(f"{t.type}:{t.value}")
            snippet = self._snippet()
            loc = f" (line {tok.line}, col {tok.col})" if tok.line is not None and tok.col is not None else ""
            raise DSLParseError(
                f"Expected {type_} but got {tok.type} ({tok.value}){loc}. Context: {' '.join(ctx)}. Near: {snippet}"
            )
        if value is not None and tok.value != value:
            ctx = []
            for i in range(self.pos, min(self.pos + 5, len(self.tokens))):
                t = self.tokens[i]
                ctx.append(f"{t.type}:{t.value}")
            snippet = self._snippet()
            loc = f" (line {tok.line}, col {tok.col})" if tok.line is not None and tok.col is not None else ""
            raise DSLParseError(
                f"Expected {value} but got {tok.value}{loc}. Context: {' '.join(ctx)}. Near: {snippet}"
            )
        self.pos += 1
        return tok

    def _snippet(self, radius: int = 20) -> str:
        """Return a small slice of source text around an estimated position based on tokens consumed."""
        if not self.source_text:
            return "(no snippet)"
        try:
            approx = sum(len(t.value) for t in self.tokens[: self.pos])
            start = max(0, approx - radius)
            end = min(len(self.source_text), approx + radius)
            snip = self.source_text[start:end].replace("\n", " ")
            return f"...{snip}..."
        except Exception:
            return "(no snippet)"

    # --- entry point ---

    def parse_strategy(self) -> Strategy:
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
            # support numeric suffixes like 1M, 2K
            nxt = self.peek()
            if nxt and nxt.type == "SUFFIX":
                self.advance()
                base = float(tok.value)
                mul = 1_000_000.0 if nxt.value.upper() == "M" else 1_000.0
                return Literal(value=base * mul)
            return Literal(value=float(tok.value))

        if tok.type == "TRUE":
            self.advance()
            return Literal(value=1.0)

        if tok.type == "FALSE":
            self.advance()
            return Literal(value=0.0)

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
                # Validate indicator name and arity (number of args), with suggestion
                try:
                    validate_indicator(ident.lower(), len(args))
                except ValueError as e:
                    # Suggest closest function name
                    try:
                        valid = VALID_FUNCS
                        import difflib
                        suggestion = difflib.get_close_matches(ident, list(valid), n=1)
                        if suggestion:
                            raise DSLParseError(f"{str(e)}. Did you mean {suggestion[0]}?")
                    except Exception:
                        raise DSLParseError(str(e))
                return FuncCall(name=ident, args=args)

            # series reference IDENT[NUMBER]?
            lag = 0
            if self.peek() and self.peek().type == "LBRACK":
                self.advance()  # '['
                lag_tok = self.expect("NUMBER")
                lag = int(float(lag_tok.value))
                self.expect("RBRACK")

            # store series names in lowercase to match DataFrame columns
            series_name = ident.lower()
            try:
                validate_field_name(series_name)
            except ValueError as e:
                # Suggest closest series name
                try:
                    import difflib
                    suggestion = difflib.get_close_matches(series_name, list(VALID_SERIES), n=1)
                    if suggestion:
                        raise DSLParseError(f"{str(e)}. Did you mean {suggestion[0]}?")
                except Exception:
                    raise DSLParseError(str(e))
            return SeriesRef(name=series_name, lag=lag)

        if tok.type == "LPAREN":
            self.advance()
            node = self.parse_bool_expr()
            self.expect("RPAREN")
            return node

        raise DSLParseError(f"Unexpected token in factor: {tok.type} {tok.value!r}")


# ==============
# Validation & public API
# ==============

# Use centralized sets from validator


def validate_strategy(strategy: Strategy):
    """Validate that all series and functions are known."""

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
    """Parse DSL text into a Strategy AST and validate it."""
    tokens = tokenize(dsl_text)
    parser = Parser(tokens, source_text=dsl_text)
    strategy = parser.parse_strategy()
    validate_strategy(strategy)
    return strategy
