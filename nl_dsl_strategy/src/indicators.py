"""
Basic indicator helpers: SMA and RSI.
"""

import pandas as pd
import numpy as np


def sma(series: pd.Series, window: int) -> pd.Series:
    """Simple moving average."""
    return series.rolling(window).mean()


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """
    Relative Strength Index (RSI) using a simple Wilder-style smoothing.
    """
    delta = series.diff()

    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()

    rs = avg_gain / (avg_loss.replace(0, np.nan))
    rsi = 100 - (100 / (1 + rs))
    return rsi
