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
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--nl', help='Natural language strategy description')
    group.add_argument('--dsl', help='Direct DSL string (bypasses NL parsing)')
    parser.add_argument('--position-size', type=float, default=1.0, help='Position size multiplier (default: 1.0)')
    parser.add_argument('--slippage-bps', type=float, default=0.0, help='Slippage in basis points applied to entry/exit (default: 0)')
    parser.add_argument('--fee', type=float, default=0.0, help='Flat fee per trade in currency units (default: 0)')
    parser.add_argument('--export-signals', help='Path to export signals CSV (optional)')
    parser.add_argument("--mark-to-market", help="Update equity each bar while in position for more granular drawdown/Sharpe", action="store_true")
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

    # NL → structured → DSL or direct DSL
    if args.dsl:
        dsl_text = args.dsl
        print("=== DSL (provided) ===")
        print(dsl_text)
        print()
    else:
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
    trades, stats = run_backtest(
        df,
        signals,
        position_size=args.position_size,
        slippage_bps=args.slippage_bps,
        fee_per_trade=args.fee,
        mark_to_market=args.mark_to_market,
    )

    # Report
    print("=== Backtest Metrics ===")
    print(f"Total Return: {stats.get('total_return_pct', 0.0):.2f}%")
    print(f"Max Drawdown: {stats.get('max_drawdown_pct', 0.0):.2f}%")
    print(f"Trades: {stats.get('num_trades', 0)}")
    print(f"Sharpe: {stats.get('sharpe', 0.0):.2f}")
    if trades:
        print("=== Trades ===")
        for t in trades:
            print(f"Enter {t.entry_date} @ {t.entry_price:.2f} | Exit {t.exit_date} @ {t.exit_price:.2f} | PnL {t.pnl:.2f} ({t.return_pct*100:.2f}%)")

    # Optional export of signals
    if args.export_signals:
        out = pd.DataFrame({"entry": signals["entry"].astype(int), "exit": signals["exit"].astype(int)}, index=df.index)
        out.to_csv(args.export_signals)
        print(f"Signals exported to {args.export_signals}")


if __name__ == '__main__':
    main()
