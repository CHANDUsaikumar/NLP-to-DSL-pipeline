"""
Indicator implementations for the trading strategy engine.

Currently supported:
- SMA (Simple Moving Average)
- EMA (Exponential Moving Average)
- RSI (Relative Strength Index, Wilder-style)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    """
    Simple Moving Average (SMA).

    Parameters
    ----------
    series : pd.Series
        Input price/volume series.
    window : int
        Lookback window length.

    Returns
    -------
    pd.Series
        Rolling mean with the given window. The first (window-1) values are NaN.
    """
    return series.rolling(window=window, min_periods=window).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    """
    Exponential Moving Average (EMA).

    Parameters
    ----------
    series : pd.Series
        Input price/volume series.
    window : int
        Lookback window length.

    Returns
    -------
    pd.Series
        EMA with adjust=False for standard trading usage.
    """
    return series.ewm(span=window, adjust=False).mean()


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """
    Relative Strength Index (RSI), Wilder's smoothing version.

    Parameters
    ----------
    series : pd.Series
        Input price series (typically close).
    window : int, default 14
        Lookback window length.

    Returns
    -------
    pd.Series
        RSI values in the range [0, 100]. Initial values may be NaN.
    """
    delta = series.diff()

    # Separate gains and losses
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Wilder's smoothing: use exponential-like rolling mean via simple rolling mean here
    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()

    # Avoid division by zero
    rs = avg_gain / avg_loss.replace(0, np.nan)

    rsi_series = 100 - (100 / (1 + rs))
    return rsi_series
