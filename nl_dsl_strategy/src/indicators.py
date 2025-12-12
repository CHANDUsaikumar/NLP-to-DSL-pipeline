"""
Indicator implementations for the trading strategy engine.

Currently supported:
- SMA (Simple Moving Average)
- EMA (Exponential Moving Average)
- RSI (Relative Strength Index, Wilder-style)
- MACD (Moving Average Convergence Divergence)
- BBANDS (Bollinger Bands)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = [
    "sma",
    "ema",
    "rsi",
    "macd",
    "bbands",
    "bbupper",
    "bblower",
    "macd_signal",
    "macd_hist",
]


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


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Moving Average Convergence Divergence (MACD).

    Parameters
    ----------
    series : pd.Series
        Input price series (typically close).
    fast : int, default 12
        Fast EMA span.
    slow : int, default 26
        Slow EMA span.
    signal : int, default 9
        Signal line EMA span of the MACD line.

    Returns
    -------
    (macd_line, signal_line, histogram) : tuple of pd.Series
        macd_line = EMA(fast) - EMA(slow)
        signal_line = EMA(macd_line, signal)
        histogram = macd_line - signal_line
    """
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def bbands(series: pd.Series, period: int = 20, std: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Bollinger Bands.

    Parameters
    ----------
    series : pd.Series
        Input price series (typically close).
    period : int, default 20
        SMA lookback window.
    std : float, default 2.0
        Standard deviation multiplier.

    Returns
    -------
    (upper, middle, lower) : tuple of pd.Series
        Upper band = SMA(period) + std * rolling_std
        Middle band = SMA(period)
        Lower band = SMA(period) - std * rolling_std
    """
    mid = sma(series, period)
    rolling_std = series.rolling(window=period, min_periods=period).std(ddof=0)
    upper = mid + std * rolling_std
    lower = mid - std * rolling_std
    return upper, mid, lower


def bbupper(series: pd.Series, period: int = 20, std: float = 2.0) -> pd.Series:
    upper, _mid, _lower = bbands(series, period=period, std=std)
    return upper


def bblower(series: pd.Series, period: int = 20, std: float = 2.0) -> pd.Series:
    _upper, _mid, lower = bbands(series, period=period, std=std)
    return lower


def macd_signal(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
    _macd_line, signal_line, _hist = macd(series, fast=fast, slow=slow, signal=signal)
    return signal_line


def macd_hist(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.Series:
    macd_line, signal_line, hist = macd(series, fast=fast, slow=slow, signal=signal)
    return hist
