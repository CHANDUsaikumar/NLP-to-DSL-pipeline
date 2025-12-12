"""
AST node definitions for the trading strategy DSL.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Union


class ASTNode:
    """Base class for all AST nodes."""
    pass


@dataclass
class Strategy(ASTNode):
    """
    Top-level strategy node.

    Represents the full strategy with entry and exit boolean expressions.
    """
    entry: ASTNode
    exit: ASTNode


@dataclass
class BinaryOp(ASTNode):
    """
    Binary operation node.

    Examples:
        close > SMA(close, 20)
        volume > 1_000_000
        expr1 AND expr2
        expr1 OR expr2
        CROSSOVER(close, SMA(close, 20))
    """
    left: ASTNode
    op: str
    right: ASTNode


@dataclass
class UnaryOp(ASTNode):
    """
    Unary operation node.

    Currently used for logical NOT.
    """
    op: str
    operand: ASTNode


@dataclass
class Literal(ASTNode):
    """
    Numeric literal, e.g. 1000000, 30.5, etc.
    """
    value: float


@dataclass
class SeriesRef(ASTNode):
    """
    Reference to a time series column with optional lag.

    Examples:
        close       -> name='close', lag=0
        high[1]     -> name='high', lag=1
        volume[5]   -> name='volume', lag=5
    """
    name: str
    lag: int = 0


@dataclass
class FuncCall(ASTNode):
    """
    Function call node.

    Used for indicators and other expressions.

    Examples:
        SMA(close, 20)
        RSI(close, 14)
    """
    name: str
    args: List[ASTNode]

ASTChild = Union[Strategy, BinaryOp, UnaryOp, Literal, SeriesRef, FuncCall]
