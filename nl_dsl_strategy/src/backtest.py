"""
Simple backtest-style execution engine.

Assumptions:
- Long-only, single-position strategy (either flat or fully long 1 unit).
- Orders are executed at the close price of the bar where the signal occurs.
- No transaction costs, slippage, or partial fills.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import pandas as pd


@dataclass
class Trade:
    entry_date: Any
    exit_date: Any
    entry_price: float
    exit_price: float
    pnl: float
    return_pct: float


def run_backtest(
    df: pd.DataFrame,
    signals: pd.DataFrame,
    position_size: float = 1.0,
) -> Tuple[List[Trade], Dict[str, float]]:
    """
    Run a very simple backtest:

    - Start flat (no position).
    - When entry == True and flat → enter long at close.
    - When exit == True and long → exit at close.
    - Track PnL and a simple equity curve.

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV data with a DatetimeIndex and at least a 'close' column.
    signals : pd.DataFrame
        DataFrame with boolean columns 'entry' and 'exit'.
    position_size : float, default 1.0
        Notional number of units (shares/contracts) per trade.

    Returns
    -------
    trades : List[Trade]
        List of completed trades.
    stats : Dict[str, float]
        Dictionary with summary statistics:
        - total_return_pct
        - max_drawdown_pct
        - num_trades
    """
    trades: List[Trade] = []

    position = 0  # 0 = flat, 1 = long
    entry_price = None
    entry_date = None
    cash = 0.0

    equity_curve: List[float] = []
    starting_notional = None  # for return normalization

    for ts, row in df.iterrows():
        price = float(row["close"])
        entry_signal = bool(signals.loc[ts, "entry"])
        exit_signal = bool(signals.loc[ts, "exit"])

        # Entry logic
        if position == 0 and entry_signal:
            position = 1
            entry_price = price
            entry_date = ts
            if starting_notional is None:
                # Use first entry price * position size as baseline for return
                starting_notional = entry_price * position_size

        # Exit logic
        elif position == 1 and exit_signal:
            position = 0
            exit_price = price
            pnl = (exit_price - entry_price) * position_size
            ret = pnl / (entry_price * position_size)

            trades.append(
                Trade(
                    entry_date=entry_date,
                    exit_date=ts,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    pnl=pnl,
                    return_pct=ret,
                )
            )

            cash += pnl
            entry_price = None
            entry_date = None

        # Mark-to-market equity
        if position == 1 and entry_price is not None:
            unrealized = (price - entry_price) * position_size
            equity_curve.append(cash + unrealized)
        else:
            equity_curve.append(cash)

    equity_series = pd.Series(equity_curve, index=df.index)

    # Basic drawdown stats
    if len(equity_series) > 0:
        peak = equity_series.cummax()
        # Avoid division by zero: where peak == 0, drawdown is 0
        dd = pd.Series(0.0, index=equity_series.index)
        valid_peak = peak != 0
        dd[valid_peak] = (equity_series[valid_peak] - peak[valid_peak]) / peak[valid_peak]
        max_drawdown_pct = dd.min() * 100.0
    else:
        max_drawdown_pct = 0.0

    # Normalize total return to starting_notional if we ever traded
    if starting_notional is not None and starting_notional != 0:
        total_return_pct = (cash / starting_notional) * 100.0
    else:
        total_return_pct = 0.0

    stats = {
        "total_return_pct": float(total_return_pct),
        "max_drawdown_pct": float(max_drawdown_pct),
        "num_trades": len(trades),
    }

    return trades, stats
