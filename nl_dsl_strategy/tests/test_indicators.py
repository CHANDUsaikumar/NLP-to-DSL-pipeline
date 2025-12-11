import pandas as pd
import numpy as np

from nl_dsl_strategy.src.indicators import macd, bbands, sma


def test_macd_basic():
    # Create a simple increasing series
    s = pd.Series(np.arange(1, 101), dtype=float)
    macd_line, signal_line, hist = macd(s)
    # MACD line should be defined (non-NaN) after slow period
    assert macd_line.iloc[30:].isna().sum() == 0
    # Histogram = macd - signal
    assert (hist.round(8).equals((macd_line - signal_line).round(8)))


def test_bbands_basic():
    s = pd.Series(np.arange(1, 101), dtype=float)
    upper, mid, lower = bbands(s, period=20, std=2.0)
    # middle equals SMA(period)
    assert mid.equals(sma(s, 20))
    # upper is above middle and lower is below middle where defined
    mask = mid.notna()
    assert (upper[mask] > mid[mask]).all()
    assert (lower[mask] < mid[mask]).all()
