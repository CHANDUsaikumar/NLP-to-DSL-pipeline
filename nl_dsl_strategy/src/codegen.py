"""
AST → pandas signal generator.

Given a Strategy AST and a DataFrame with OHLCV data, generate
boolean entry/exit signal series.
"""

from __future__ import annotations

from typing import Union

import pandas as pd

from .ast_nodes import Strategy, BinaryOp, UnaryOp, Literal, SeriesRef, FuncCall
from . import indicators


Value = Union[float, pd.Series]  # scalar or pandas Series


def _eval_node(node, df: pd.DataFrame) -> Value:
    """
    Recursively evaluate an AST node into either:
    - a pandas Series (for time series expressions), or
    - a scalar float.
    """
    # Binary operations
    if isinstance(node, BinaryOp):
        left = _eval_node(node.left, df)
        right = _eval_node(node.right, df)
        op = node.op.upper()

        if op == "AND":
            return left & right
        if op == "OR":
            return left | right

        if op in {">", "<", ">=", "<=", "==", "!="}:
            if op == ">":
                return left > right
            if op == "<":
                return left < right
            if op == ">=":
                return left >= right
            if op == "<=":
                return left <= right
            if op == "==":
                return left == right
            if op == "!=":
                return left != right

        if op in {"+", "-", "*", "/"}:
            if op == "+":
                return left + right
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if op == "/":
                return left / right

        if op == "CROSSOVER":
            # True when left crosses from <= right to > right
            left_s = _to_series(left)
            right_s = _to_series(right)
            prev_left = left_s.shift(1)
            prev_right = right_s.shift(1)
            return (left_s > right_s) & (prev_left <= prev_right)

        if op == "CROSSUNDER":
            left_s = _to_series(left)
            right_s = _to_series(right)
            prev_left = left_s.shift(1)
            prev_right = right_s.shift(1)
            return (left_s < right_s) & (prev_left >= prev_right)

        raise ValueError(f"Unsupported binary op: {node.op}")

    # Unary operations
    if isinstance(node, UnaryOp):
        op = node.op.upper()
        operand = _eval_node(node.operand, df)
        if op == "NOT":
            return ~_to_series(operand)
        raise ValueError(f"Unsupported unary op: {node.op}")

    # Literal
    if isinstance(node, Literal):
        return float(node.value)

    # Series reference
    if isinstance(node, SeriesRef):
        series = df[node.name]
        if node.lag:
            series = series.shift(node.lag)
        return series

    # Function call (SMA, RSI, etc.)
    if isinstance(node, FuncCall):
        name = node.name.upper()

        if name == "SMA":
            if len(node.args) != 2:
                raise ValueError("SMA expects two arguments: series, window")
            series_val = _eval_node(node.args[0], df)
            window_val = _eval_node(node.args[1], df)
            window = int(window_val)
            return indicators.sma(_to_series(series_val), window)

        if name == "RSI":
            if len(node.args) == 1:
                series_val = _eval_node(node.args[0], df)
                window = 14
            elif len(node.args) == 2:
                series_val = _eval_node(node.args[0], df)
                window_val = _eval_node(node.args[1], df)
                window = int(window_val)
            else:
                raise ValueError("RSI expects 1 or 2 arguments: (series[, window])")
            return indicators.rsi(_to_series(series_val), window)

        raise ValueError(f"Unsupported function: {node.name}")

    raise TypeError(f"Unsupported AST node type: {type(node).__name__}")


def _to_series(val: Value) -> pd.Series:
    """Ensure the value is a pandas Series."""
    if isinstance(val, pd.Series):
        return val
    # Broadcast scalar over a dummy index if ever needed
    raise TypeError("Expected a pandas Series in this context")


def generate_signals(strategy: Strategy, df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate entry and exit signal Series from a Strategy AST.

    Returns a DataFrame with boolean 'entry' and 'exit' columns.
    """
    entry_raw = _eval_node(strategy.entry, df)
    exit_raw = _eval_node(strategy.exit, df)

    entry = _to_series(entry_raw).fillna(False).astype(bool)
    exit_ = _to_series(exit_raw).fillna(False).astype(bool)

    signals = pd.DataFrame(index=df.index)
    signals["entry"] = entry
    signals["exit"] = exit_
    return signals
