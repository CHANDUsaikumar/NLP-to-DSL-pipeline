import pandas as pd
import numpy as np
from nl_dsl_strategy.src.dsl_lexer_parser import parse_dsl
from nl_dsl_strategy.src.codegen import generate_signals


def build_df(n=10):
    dates = pd.date_range("2020-01-01", periods=n, freq="D")
    close = pd.Series(np.linspace(100, 110, n), index=dates)
    df = pd.DataFrame({
        "open": close.values,
        "high": close.values + 1,
        "low": close.values - 1,
        "close": close.values,
        "volume": np.ones(n) * 1_000
    }, index=dates)
    return df


def test_indicators_nan_on_short_windows():
    df = build_df(5)
    # Small windows can produce leading NaNs; ensure comparisons yield False where undefined
    dsl = "ENTRY: EMA(close, 5) > SMA(close, 5) EXIT: FALSE"
    ast = parse_dsl(dsl)
    signals = generate_signals(ast, df)
    # Leading entries may be False due to NaNs; no exceptions should be thrown
    assert "entry" in signals
    assert signals["entry"].dtype == bool


def test_macd_and_bbands_defined_types():
    df = build_df(30)
    dsl = (
        "ENTRY: MACD(close, 12, 26, 9) > MACD_SIGNAL(close, 12, 26, 9) AND "
        "close < BBLOWER(close, 20, 2) EXIT: FALSE"
    )
    ast = parse_dsl(dsl)
    signals = generate_signals(ast, df)
    assert "entry" in signals and signals["entry"].dtype == bool
