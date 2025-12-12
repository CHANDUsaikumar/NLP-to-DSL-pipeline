# tests/test_codegen.py

import sys
from pathlib import Path
import pandas as pd

# Ensure package path
sys.path.append(str(Path(__file__).resolve().parents[1] / 'nl_dsl_strategy' / 'src'))
from dsl_lexer_parser import parse_dsl
from codegen import generate_signals


def _build_small_df() -> pd.DataFrame:
    data = [
        ("2023-01-01", 100, 105, 99, 103, 900000),
        ("2023-01-02", 103, 108, 101, 107, 1200000),
        ("2023-01-03", 107, 110, 106, 109, 1300000),
        ("2023-01-04", 109, 112, 108, 111, 900000),
        ("2023-01-05", 111, 115, 110, 114, 1500000),
    ]
    df = pd.DataFrame(
        data,
        columns=["date", "open", "high", "low", "close", "volume"],
    )
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    return df


def test_generate_signals_basic():
    df = _build_small_df()

    # Simple strategy: entry when close > SMA(close, 2), exit when close < SMA(close, 2)
    dsl = """
    ENTRY: close > SMA(close, 2)
    EXIT:  close < SMA(close, 2)
    """

    strategy = parse_dsl(dsl)
    signals = generate_signals(strategy, df)

    # Signals DataFrame should have correct shape and columns
    assert list(signals.columns) == ["entry", "exit"]
    assert len(signals) == len(df)

    # Types: boolean
    assert signals["entry"].dtype == bool
    assert signals["exit"].dtype == bool

    # There should be at least one non-NaN / True entry signal after enough data points
    # (since SMA(2) becomes defined from the 2nd row)
    # Use equality for boolean comparison; pandas may return numpy.bool_
    assert signals["entry"].iloc[0] == False  # first row has no SMA
    # After second row, we may see some True's; just check that there are any True
    assert signals["entry"].any() or signals["exit"].any()


def test_generate_signals_with_ema():
    df = _build_small_df()

    # Strategy using EMA: entry when close > EMA(close, 3), exit when close < EMA(close, 3)
    dsl = """
    ENTRY: close > EMA(close, 3)
    EXIT:  close < EMA(close, 3)
    """

    strategy = parse_dsl(dsl)
    signals = generate_signals(strategy, df)

    # Signals DataFrame should have correct shape and columns
    assert list(signals.columns) == ["entry", "exit"]
    assert len(signals) == len(df)

    # Types: boolean
    assert signals["entry"].dtype == bool
    assert signals["exit"].dtype == bool

    # EMA(3) becomes defined from the 3rd row; first row should be False
    assert signals["entry"].iloc[0] == False
    # Ensure at least one signal appears by the end
    assert signals["entry"].any() or signals["exit"].any()


def test_generate_signals_macd_bbands_helpers():
    df = _build_small_df()

    # Use MACD line vs signal and BBUPPER/BBLOWER in pure DSL
    dsl = """
    ENTRY: MACD(close) > MACD_SIGNAL(close) AND close < BBUPPER(close, 20, 2)
    EXIT:  MACD(close) < MACD_SIGNAL(close) OR close > BBLOWER(close, 20, 2)
    """

    strategy = parse_dsl(dsl)
    signals = generate_signals(strategy, df)

    assert list(signals.columns) == ["entry", "exit"]
    assert len(signals) == len(df)
    assert signals["entry"].dtype == bool
    assert signals["exit"].dtype == bool
    # Ensure evaluation completes and returns booleans; no guarantee of a signal in tiny sample
    assert signals["entry"].isin([True, False]).all()
    assert signals["exit"].isin([True, False]).all()
