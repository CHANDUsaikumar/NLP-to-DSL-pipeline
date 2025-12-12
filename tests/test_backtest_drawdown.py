import pandas as pd
import numpy as np
from nl_dsl_strategy.src.dsl_lexer_parser import parse_dsl
from nl_dsl_strategy.src.codegen import generate_signals
from nl_dsl_strategy.src.backtest import run_backtest


def build_df():
    # Construct a price series that rises then falls to force a drawdown
    dates = pd.date_range("2020-01-01", periods=6, freq="D")
    close = pd.Series([100, 110, 120, 115, 105, 90], index=dates)
    df = pd.DataFrame({
        "open": close.values,
        "high": close.values,
        "low": close.values,
        "close": close.values,
        "volume": np.ones(len(dates)) * 1000,
    }, index=dates)
    return df


def test_max_drawdown_numeric_assertion():
    df = build_df()
    # Simple always-in strategy to experience peak then drawdown
    dsl = "ENTRY: close > 0 EXIT: FALSE"
    ast = parse_dsl(dsl)
    signals = generate_signals(ast, df)
    trades, stats = run_backtest(df, signals, slippage_bps=0, fee_per_trade=0, mark_to_market=True)
    # Peak at 120, valley at 90 → drawdown = (90 - 120) / 120 = -25%
    # Drawdown is reported as a negative percentage (decline from peak)
    assert abs(stats["max_drawdown_pct"] - (-25.0)) < 1e-6
