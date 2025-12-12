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


def run_backtest(df, signals, position_size: float = 1.0, slippage_bps: float = 0.0, fee_per_trade: float = 0.0, mark_to_market: bool = False):
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
  prev_close_in_position = None
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
      # apply slippage on entry
      entry_price = close_price * (1 + slippage_bps / 10000.0)
      prev_close_in_position = close_price  # baseline for mark-to-market

    # Exit
    if exit_sig and position == 1:
      position = 0
      exit_date = pd.Timestamp(idx)
      # apply slippage on exit (sell worse by bps)
      exit_price = close_price * (1 - slippage_bps / 10000.0)
      pnl = float(exit_price - entry_price)
      # include fee per trade (flat) proportional to entry price for percent terms
      fee_pct = (fee_per_trade / entry_price) if entry_price and fee_per_trade > 0 else 0.0
      ret_pct = float(pnl / entry_price) - fee_pct if entry_price else 0.0

      trades.append(Trade(
        entry_date=entry_date,
        exit_date=exit_date,
        entry_price=float(entry_price),
        exit_price=float(exit_price),
        pnl=float(pnl),
        return_pct=float(ret_pct),
      ))
      cumulative_equity *= (1.0 + ret_pct * position_size)
      prev_close_in_position = None

    # Optional mark-to-market equity update while holding
    if mark_to_market and position == 1 and prev_close_in_position is not None and not exit_sig:
      # Multiply equity by bar return scaled by position_size
      bar_ret = 0.0
      if prev_close_in_position != 0.0:
        bar_ret = (close_price / prev_close_in_position) - 1.0
      cumulative_equity *= (1.0 + bar_ret * position_size)
      prev_close_in_position = close_price

    equity.append(float(cumulative_equity))
    equity_index.append(idx)

  equity_series = pd.Series(equity, index=equity_index)
  peak = equity_series.cummax()
  drawdown = (equity_series / peak) - 1.0
  max_drawdown_pct = float(drawdown.min()) if len(drawdown) else 0.0
  total_return_pct = float((cumulative_equity - 1.0) * 100.0)
  max_drawdown_pct *= 100.0
  num_trades = int(len(trades))

  # Daily returns for Sharpe (assume equity sampled by row frequency)
  rets = equity_series.pct_change().fillna(0.0)
  if rets.std(ddof=0) > 0:
    sharpe = float((rets.mean() / rets.std(ddof=0)) * (252 ** 0.5))
  else:
    sharpe = 0.0

  stats = {
    'total_return_pct': total_return_pct,
    'max_drawdown_pct': max_drawdown_pct,
    'num_trades': num_trades,
    'sharpe': sharpe,
  }

  return trades, stats


# Module provides run_backtest(df, signals) and Trade dataclass; no top-level execution.
