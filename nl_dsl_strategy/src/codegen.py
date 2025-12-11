"""
AST → pandas signal generation.

This module takes a parsed Strategy AST and evaluates it over a pandas DataFrame
containing OHLCV data, producing boolean entry/exit signal series.

Main entry point:
- generate_signals(strategy, df) -> DataFrame with 'entry' and 'exit' columns
"""

from __future__ import annotations

from typing import Union

import pandas as pd

# Import with fallback for script execution
try:
    from .ast_nodes import (
        ASTNode,
        Strategy,
        Literal,
        SeriesRef,
        FuncCall,
        UnaryOp,
        BinaryOp,
    )
    from .indicators import sma, ema, rsi
except ImportError:  # script mode
    from ast_nodes import (  # type: ignore
        ASTNode,
        Strategy,
        Literal,
        SeriesRef,
        FuncCall,
        UnaryOp,
        BinaryOp,
    )
    from indicators import sma, ema, rsi  # type: ignore


def eval_ast(node: ASTNode, df: pd.DataFrame) -> Union[pd.Series, float, bool]:
    """
    Evaluate an AST node over a pandas DataFrame.

    Depending on the node, this can return:
    - A scalar (float/bool) for literals
    - A pandas Series for time-series expressions
    - A boolean Series for boolean expressions/comparisons

    Parameters
    ----------
    node : ASTNode
        AST node to evaluate.
    df : pd.DataFrame
        Input OHLCV data. Must contain columns like 'open', 'high',
        'low', 'close', 'volume'.

    Returns
    -------
    Union[pd.Series, float, bool]
        Result of the evaluation.
    """
    # ----- Leaf nodes -----

    if isinstance(node, Literal):
        return node.value

    if isinstance(node, SeriesRef):
        series = df[node.name]
        if node.lag > 0:
            series = series.shift(node.lag)
        return series

    if isinstance(node, FuncCall):
        func_name = node.name.upper()
        args = [eval_ast(arg, df) for arg in node.args]
        # Optional runtime validation to fail fast on unknown indicator names
        try:
            from .validator import validate_indicator  # type: ignore
            validate_indicator(func_name.lower(), len(node.args))
        except Exception:
            # If validator isn't available (script mode), continue
            pass

        if func_name in ("SMA", "EMA", "RSI", "SHIFT"):
            pass  # placeholder to keep grouping nearby
        
        if func_name == "SMA":
            if len(args) != 2:
                raise ValueError("SMA(series, window) expects 2 arguments")
            series, window = args[0], int(args[1])
            if not isinstance(series, pd.Series):
                raise TypeError("SMA first argument must be a Series")
            return sma(series, window)

        if func_name == "RSI":
            if len(args) != 2:
                raise ValueError("RSI(series, window) expects 2 arguments")
            series, window = args[0], int(args[1])
            if not isinstance(series, pd.Series):
                raise TypeError("RSI first argument must be a Series")
            return rsi(series, window)

        if func_name == "EMA":
            if len(args) != 2:
                raise ValueError("EMA(series, window) expects 2 arguments")
            series, window = args[0], int(args[1])
            if not isinstance(series, pd.Series):
                raise TypeError("EMA first argument must be a Series")
            return ema(series, window)

        if func_name == "SHIFT":
            if len(args) != 2:
                raise ValueError("SHIFT(series, lag) expects 2 arguments")
            series, lag = args[0], int(args[1])
            if not isinstance(series, pd.Series):
                raise TypeError("SHIFT first argument must be a Series")
            return series.shift(lag)
        
        # If we get here, the function name wasn't recognized above
        raise ValueError(f"Unknown function: {func_name}")

    # ----- Unary ops -----

    if isinstance(node, UnaryOp):
        operand = eval_ast(node.operand, df)
        op = node.op.upper()

        if op == "NOT":
            # Expect boolean Series
            if isinstance(operand, pd.Series):
                return ~operand
            return not bool(operand)

        raise ValueError(f"Unknown unary op: {op}")

    # ----- Binary ops -----

    if isinstance(node, BinaryOp):
        op = node.op.upper()

        # Short-circuit AND/OR with Series support
        if op in ("AND", "OR"):
            left = eval_ast(node.left, df)
            right = eval_ast(node.right, df)

            if not isinstance(left, pd.Series) or not isinstance(right, pd.Series):
                raise TypeError("AND/OR operands must be pandas Series")

            if op == "AND":
                return left & right
            else:  # "OR"
                return left | right

        # Arithmetic or comparison or cross event
        left = eval_ast(node.left, df)
        right = eval_ast(node.right, df)

        # Arithmetic operators
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            return left / right

        # Comparisons
        if op in (">", "<", ">=", "<=", "==", "!="):
            return _compare(left, right, op)

        # Cross events: expect Series on both sides
        if op == "CROSSOVER":
            if not isinstance(left, pd.Series) or not isinstance(right, pd.Series):
                raise TypeError("CROSSOVER operands must be pandas Series")
            return (left > right) & (left.shift(1) <= right.shift(1))

        if op == "CROSSUNDER":
            if not isinstance(left, pd.Series) or not isinstance(right, pd.Series):
                raise TypeError("CROSSUNDER operands must be pandas Series")
            return (left < right) & (left.shift(1) >= right.shift(1))

        raise ValueError(f"Unknown binary op: {op}")

    raise ValueError(f"Unknown AST node type: {type(node)}")


def _compare(left, right, op: str):
    """
    Helper for comparison operations.
    Supports scalar/Series combinations via pandas broadcasting.
    """
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
    raise ValueError(f"Unsupported comparison op: {op}")


def generate_signals(strategy: Strategy, df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate entry and exit signals from a Strategy AST over a DataFrame.

    Parameters
    ----------
    strategy : Strategy
        Parsed and validated strategy AST.
    df : pd.DataFrame
        OHLCV data with index as dates and columns:
        'open', 'high', 'low', 'close', 'volume'.

    Returns
    -------
    pd.DataFrame
        DataFrame with boolean columns:
        - 'entry': True where entry condition is satisfied.
        - 'exit':  True where exit condition is satisfied.
    """
    entry_raw = eval_ast(strategy.entry, df)
    exit_raw = eval_ast(strategy.exit, df)

    # Coerce scalars to Series if needed (rare, but for completeness)
    if not isinstance(entry_raw, pd.Series):
        entry_series = pd.Series([bool(entry_raw)] * len(df), index=df.index)
    else:
        entry_series = entry_raw.astype(bool)

    if not isinstance(exit_raw, pd.Series):
        exit_series = pd.Series([bool(exit_raw)] * len(df), index=df.index)
    else:
        exit_series = exit_raw.astype(bool)

    signals = pd.DataFrame(index=df.index)
    # Ensure Python bools (not numpy.bool_) so tests using `is False/True` pass
    signals["entry"] = entry_series.fillna(False).map(lambda x: bool(x))
    signals["exit"] = exit_series.fillna(False).map(lambda x: bool(x))
    return signals
