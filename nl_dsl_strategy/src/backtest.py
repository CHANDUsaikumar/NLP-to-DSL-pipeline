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


def run_backtest(df, signals, position_size: float = 1.0):
  """
        Execute a simple long-only backtest over df using 'signals' with boolean 'entry' and 'exit' columns.

        Rules:
          - Enter when entry becomes True and no current position.
          - Exit when exit becomes True and in a position.
          - Trade price = df['close'] at the signal row.
          - PnL = exit_price - entry_price, return_pct = pnl / entry_price

        Returns:
          (trades_list, stats_dict)

        trades_list: list of dicts:
          {
            'entry_date': pd.Timestamp,
            'exit_date': pd.Timestamp,
            'entry_price': float,
            'exit_price': float,
            'pnl': float,
            'return_pct': float
          }

        stats_dict:
          {
            'total_return_pct': float,
            'max_drawdown_pct': float,
            'num_trades': int
          }
  """
  import pandas as pd

  position = 0
  entry_date = None
  entry_price = None
  trades = []

  equity = []
  cumulative_equity = 1.0
  equity_index = []

  for idx in df.index:
    entry_sig = bool(signals.loc[idx, 'entry'])
    exit_sig = bool(signals.loc[idx, 'exit'])
    close_price = float(df.loc[idx, 'close'])

    # Entry
    if entry_sig and position == 0:
      position = 1
      entry_date = pd.Timestamp(idx)
      entry_price = close_price

    # Exit
    if exit_sig and position == 1:
      position = 0
      exit_date = pd.Timestamp(idx)
      exit_price = close_price
      pnl = float(exit_price - entry_price)
      ret_pct = float(pnl / entry_price) if entry_price else 0.0

      trades.append(Trade(
        entry_date=entry_date,
        exit_date=exit_date,
        entry_price=float(entry_price),
        exit_price=float(exit_price),
        pnl=float(pnl),
        return_pct=float(ret_pct),
      ))

      cumulative_equity *= (1.0 + ret_pct * position_size)

    equity.append(float(cumulative_equity))
    equity_index.append(idx)

  equity_series = pd.Series(equity, index=equity_index)
  peak = equity_series.cummax()
  drawdown = (equity_series / peak) - 1.0
  max_drawdown_pct = float(drawdown.min()) if len(drawdown) else 0.0
  total_return_pct = float((cumulative_equity - 1.0) * 100.0)
  max_drawdown_pct *= 100.0
  num_trades = int(len(trades))

  stats = {
    'total_return_pct': total_return_pct,
    'max_drawdown_pct': max_drawdown_pct,
    'num_trades': num_trades,
  }

  return trades, stats


# Module provides run_backtest(df, signals) and Trade dataclass; no top-level execution.
