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
    from .indicators import sma, ema, rsi, macd, bbands, bbupper, bblower, macd_signal, macd_hist
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
    from indicators import sma, ema, rsi, macd, bbands, bbupper, bblower, macd_signal, macd_hist  # type: ignore


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

        if func_name in ("SMA", "EMA", "RSI", "SHIFT", "MACD", "BBANDS", "BBUPPER", "BBLOWER", "MACD_SIGNAL", "MACD_HIST", "CROSSOVER", "CROSSUNDER"):
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

        if func_name == "MACD":
            # MACD(series, fast=12, slow=26, signal=9) → returns macd_line
            # To use signal or histogram, users can construct via auxiliary functions in future.
            # For now, expose the macd line directly when called.
            if len(args) < 1 or len(args) > 4:
                raise ValueError("MACD(series, fast=12, slow=26, signal=9) expects 1-4 arguments")
            series = args[0]
            if not isinstance(series, pd.Series):
                raise TypeError("MACD first argument must be a Series")
            fast = int(args[1]) if len(args) >= 2 else 12
            slow = int(args[2]) if len(args) >= 3 else 26
            signal = int(args[3]) if len(args) >= 4 else 9
            macd_line, _signal_line, _hist = macd(series, fast=fast, slow=slow, signal=signal)
            return macd_line

        if func_name == "BBANDS":
            # BBANDS(series, period=20, std=2.0) → returns middle band for direct comparisons
            # To use upper/lower explicitly, add functions BBUPPER/BBLOWER in future.
            if len(args) < 1 or len(args) > 3:
                raise ValueError("BBANDS(series, period=20, std=2.0) expects 1-3 arguments")
            series = args[0]
            if not isinstance(series, pd.Series):
                raise TypeError("BBANDS first argument must be a Series")
            period = int(args[1]) if len(args) >= 2 else 20
            std = float(args[2]) if len(args) >= 3 else 2.0
            _upper, middle, _lower = bbands(series, period=period, std=std)
            return middle

        if func_name == "BBUPPER":
            if len(args) < 1 or len(args) > 3:
                raise ValueError("BBUPPER(series, period=20, std=2.0) expects 1-3 arguments")
            series = args[0]
            if not isinstance(series, pd.Series):
                raise TypeError("BBUPPER first argument must be a Series")
            period = int(args[1]) if len(args) >= 2 else 20
            std = float(args[2]) if len(args) >= 3 else 2.0
            return bbupper(series, period=period, std=std)

        if func_name == "BBLOWER":
            if len(args) < 1 or len(args) > 3:
                raise ValueError("BBLOWER(series, period=20, std=2.0) expects 1-3 arguments")
            series = args[0]
            if not isinstance(series, pd.Series):
                raise TypeError("BBLOWER first argument must be a Series")
            period = int(args[1]) if len(args) >= 2 else 20
            std = float(args[2]) if len(args) >= 3 else 2.0
            return bblower(series, period=period, std=std)

        if func_name == "MACD_SIGNAL":
            if len(args) < 1 or len(args) > 4:
                raise ValueError("MACD_SIGNAL(series, fast=12, slow=26, signal=9) expects 1-4 arguments")
            series = args[0]
            if not isinstance(series, pd.Series):
                raise TypeError("MACD_SIGNAL first argument must be a Series")
            fast = int(args[1]) if len(args) >= 2 else 12
            slow = int(args[2]) if len(args) >= 3 else 26
            signal = int(args[3]) if len(args) >= 4 else 9
            return macd_signal(series, fast=fast, slow=slow, signal=signal)

        if func_name == "MACD_HIST":
            if len(args) < 1 or len(args) > 4:
                raise ValueError("MACD_HIST(series, fast=12, slow=26, signal=9) expects 1-4 arguments")
            series = args[0]
            if not isinstance(series, pd.Series):
                raise TypeError("MACD_HIST first argument must be a Series")
            fast = int(args[1]) if len(args) >= 2 else 12
            slow = int(args[2]) if len(args) >= 3 else 26
            signal = int(args[3]) if len(args) >= 4 else 9
            return macd_hist(series, fast=fast, slow=slow, signal=signal)

        if func_name in ("CROSSOVER", "CROSSUNDER"):
            if len(args) != 2:
                raise ValueError(f"{func_name}(seriesA, seriesB) expects 2 arguments")
            left, right = args
            if not isinstance(left, pd.Series) or not isinstance(right, pd.Series):
                raise TypeError(f"{func_name} operands must be pandas Series")
            if func_name == "CROSSOVER":
                return (left > right) & (left.shift(1) <= right.shift(1))
            else:
                return (left < right) & (left.shift(1) >= right.shift(1))
        
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

            # Optional scalar broadcasting for convenience
            if isinstance(left, bool):
                left = pd.Series([left] * len(df), index=df.index)
            if isinstance(right, bool):
                right = pd.Series([right] * len(df), index=df.index)

            if not isinstance(left, pd.Series) or not isinstance(right, pd.Series):
                raise TypeError("AND/OR operands must be pandas Series or booleans")

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
