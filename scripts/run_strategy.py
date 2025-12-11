#!/usr/bin/env python3
"""
CLI runner: Load a CSV of OHLCV data, parse an NL string to DSL, generate signals, and run a backtest.

Usage:
  python scripts/run_strategy.py --csv path/to/data.csv --nl "Buy when close > SMA(20) ..."

CSV requirements:
  - Must have columns: open, high, low, close, volume
  - Index will be set to a 'date' column if present; otherwise, row numbers will be used
"""

from __future__ import annotations

import argparse
import sys
import os
import pandas as pd


def _ensure_src_on_path():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    src = os.path.join(root, 'nl_dsl_strategy', 'src')
    if src not in sys.path:
        sys.path.insert(0, src)


def main():
    _ensure_src_on_path()
    from nl_parser import parse_natural_language_to_structured, structured_to_dsl
    from dsl_lexer_parser import parse_dsl, DSLParseError
    from codegen import generate_signals
    from backtest import run_backtest

    parser = argparse.ArgumentParser(description="Run NL→DSL→backtest on a CSV dataset")
    parser.add_argument('--csv', required=True, help='Path to CSV with columns: date(optional), open, high, low, close, volume')
    parser.add_argument('--nl', required=True, help='Natural language strategy description')
    parser.add_argument('--position-size', type=float, default=1.0, help='Position size multiplier (default: 1.0)')
    args = parser.parse_args()

    # Load data
    df = pd.read_csv(args.csv)
    # Normalize columns
    cols_lower = {c: c.lower() for c in df.columns}
    df.rename(columns=cols_lower, inplace=True)
    if 'date' in df.columns:
        try:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
        except Exception:
            pass

    # Basic column check
    required = {'open', 'high', 'low', 'close', 'volume'}
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"ERROR: CSV is missing required columns: {missing}")
        sys.exit(1)

    # NL → structured → DSL
    structured = parse_natural_language_to_structured(args.nl)
    dsl_text = structured_to_dsl(structured)
    print("=== NL input ===")
    print(args.nl)
    print()
    print("=== Structured JSON ===")
    import json
    print(json.dumps(structured, indent=2))
    print()
    print("=== DSL ===")
    print(dsl_text)
    print()

    # DSL → AST
    try:
        strategy = parse_dsl(dsl_text)
    except DSLParseError as e:
        print("ERROR: DSL parsing failed:", e)
        sys.exit(2)

    # AST → signals → backtest
    signals = generate_signals(strategy, df)
    trades, stats = run_backtest(df, signals, position_size=args.position_size)

    # Report
    print("=== Backtest Metrics ===")
    print(f"Total Return: {stats.get('total_return_pct', 0.0):.2f}%")
    print(f"Max Drawdown: {stats.get('max_drawdown_pct', 0.0):.2f}%")
    print(f"Trades: {stats.get('num_trades', 0)}")
    if trades:
        print("=== Trades ===")
        for t in trades:
            print(f"Enter {t.entry_date} @ {t.entry_price:.2f} | Exit {t.exit_date} @ {t.exit_price:.2f} | PnL {t.pnl:.2f} ({t.return_pct*100:.2f}%)")


if __name__ == '__main__':
    main()
