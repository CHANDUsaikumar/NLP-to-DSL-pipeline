"""
End-to-end demonstration script.

This script is designed to work when executed either as a module
    python -m nl_dsl_strategy.src.demo
or directly as a script
    python nl_dsl_strategy/src/demo.py

It adapts imports accordingly to avoid the "attempted relative import"
error when run directly.
"""

from __future__ import annotations

import os
import sys
import pandas as pd
import json
from dataclasses import is_dataclass, asdict

# Resolve imports for both package and script execution modes
if __package__ is None or __package__ == "":
    # Running as a script: import modules via the package name so that
    # their relative imports continue to work.
    import importlib
    # Ensure the parent of the package root is on sys.path
    _SRC_DIR = os.path.dirname(os.path.abspath(__file__))
    _PKG_ROOT = os.path.dirname(_SRC_DIR)
    _PARENT = os.path.dirname(_PKG_ROOT)
    if _PARENT not in sys.path:
        sys.path.insert(0, _PARENT)
    _PKG = "nl_dsl_strategy.src"

    nl_parser = importlib.import_module(f"{_PKG}.nl_parser")  # type: ignore
    _dsl_mod = importlib.import_module(f"{_PKG}.dsl_lexer_parser")  # type: ignore
    parse_dsl = getattr(_dsl_mod, "parse_dsl")  # type: ignore
    DSLParseError = getattr(_dsl_mod, "DSLParseError")  # type: ignore
    _codegen_mod = importlib.import_module(f"{_PKG}.codegen")  # type: ignore
    generate_signals = getattr(_codegen_mod, "generate_signals")  # type: ignore
    _bt_mod = importlib.import_module(f"{_PKG}.backtest")  # type: ignore
    run_backtest = getattr(_bt_mod, "run_backtest")  # type: ignore
else:
        # Running as a module: use relative imports
        from . import nl_parser               # import module, not specific function
        from .dsl_lexer_parser import parse_dsl, DSLParseError
        from .codegen import generate_signals
        from .backtest import run_backtest


# Robust imports whether run as module or script
try:
    from . import nl_parser, dsl_lexer_parser, codegen, backtest
except Exception:
    import nl_parser, dsl_lexer_parser, codegen, backtest  # type: ignore

# Small embedded OHLCV sample (20 rows)
dates = pd.date_range("2024-01-01", periods=20, freq="D")
df = pd.DataFrame({
    "open":  [100, 101, 102, 103, 104, 103, 102, 101, 100, 101, 102, 103, 104, 105, 104, 103, 102, 103, 104, 105],
    "high":  [101, 102, 103, 104, 105, 104, 103, 102, 101, 102, 103, 104, 105, 106, 105, 104, 103, 104, 105, 106],
    "low":   [99,  100, 101, 102, 103, 102, 101, 100, 99,  100, 101, 102, 103, 104, 103, 102, 101, 102, 103, 104],
    "close": [100, 102, 101, 103, 104, 103, 102, 101, 100, 102, 103, 104, 105, 104, 103, 102, 101, 103, 104, 105],
    "volume":[1000,1200,1100,1300,1250,1200,1150,1100,1050,1400,1500,1550,1600,1580,1570,1500,1450,1490,1520,1550],
}, index=dates)

examples = [
    "Buy when the close price is above the 20-day moving average and volume is above 1 million.",
    "Enter when price crosses above yesterday's high.",
    "Exit when RSI(14) is below 30.",
    "Trigger entry when volume increases by more than 30 percent compared to last week.",
]


def build_example_df() -> pd.DataFrame:
    data = [
        ("2023-01-01", 100, 105, 99, 103, 900000),
        ("2023-01-02", 103, 108, 101, 107, 1200000),
        ("2023-01-03", 107, 110, 106, 109, 1300000),
        ("2023-01-04", 109, 112, 108, 111, 900000),
        ("2023-01-05", 111, 115, 110, 114, 1500000),
        ("2023-01-06", 114, 118, 113, 117, 1600000),
        ("2023-01-07", 117, 119, 116, 118, 1400000),
        ("2023-01-08", 118, 121, 117, 120, 1700000),
        ("2023-01-09", 120, 122, 119, 121, 1800000),
        ("2023-01-10", 121, 125, 120, 124, 1900000),
    ]
    df = pd.DataFrame(
        data,
        columns=["date", "open", "high", "low", "close", "volume"],
    )
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    return df


def main():
    nl_input = (
        "Buy when the close price is above the 3-day moving average and "
        "volume is above 1000000. "
        "Exit when RSI(14) is below 30."
    )

    print("=== Natural Language Input ===")
    print(f"{nl_input}\n")

    # 1) NL → structured JSON + DSL using nl_parser module directly
    try:
        structured = nl_parser.parse_natural_language(nl_input)
        dsl_text = nl_parser.structured_to_dsl(structured)
    except nl_parser.NLParseError as e:
        print("Error while parsing natural language:", e)
        return

    print("=== Structured JSON ===")
    print(structured, "\n")

    print("=== Generated DSL ===")
    print(dsl_text, "\n")

    # 2) DSL → AST
    try:
        strategy_ast = parse_dsl(dsl_text)
    except DSLParseError as e:
        print("Error while parsing DSL:", e)
        return

    print("=== Parsed Strategy AST ===")
    print("Entry AST type:", type(strategy_ast.entry).__name__)
    print("Exit  AST type:", type(strategy_ast.exit).__name__)
    print()

    # 3) AST → signals over sample data
    df = build_example_df()
    print("=== Sample OHLCV Data ===")
    print(df.head(), "\n")

    signals = generate_signals(strategy_ast, df)
    print("=== Generated Signals (head) ===")
    print(signals.head(), "\n")

    # 4) Backtest
    trades, stats = run_backtest(df, signals)

    print("=== Backtest Result ===")
    print(f"Total Return: {stats['total_return_pct']:.2f}%")
    print(f"Max Drawdown: {stats['max_drawdown_pct']:.2f}%")
    print(f"Trades: {stats['num_trades']}")
    print("Entry/Exit Log:")
    for t in trades:
        print(
            f"- Enter: {t.entry_date.date()} at {t.entry_price}, "
            f"Exit: {t.exit_date.date()} at {t.exit_price}, "
            f"PnL: {t.pnl:.2f} ({t.return_pct * 100:.2f}%)"
        )

    for i, nl in enumerate(examples, 1):
        print("=" * 80)
        print(f"Example {i}")
        print("Natural Language Input:")
        print(nl)
        print()

        # NL -> Structured JSON, DSL
        structured, dsl = nl_parser.nl_to_structured_and_dsl(nl)
        print("Generated Structured JSON:")
        print(json.dumps(structured, indent=2))
        print()

        print("Generated DSL:")
        print(dsl)
        print()

        # DSL -> AST
        try:
            strategy = dsl_lexer_parser.parse_dsl(dsl)
            ast_repr = asdict(strategy) if is_dataclass(strategy) else repr(strategy)
            print("Parsed AST:")
            print(ast_repr)
        except Exception as e:
            print("Parsed AST: ERROR")
            print(repr(e))
            print()
            continue  # move to next example if parsing fails

        print()

        # AST -> Signals -> Backtest
        try:
            signals = codegen.generate_signals(strategy, df)
            trades, stats = backtest.run_backtest(df, signals)
        except Exception as e:
            print("Backtest Result: ERROR")
            print(repr(e))
            print()
            continue

        # Report
        print("Backtest Result:")
        total_ret = stats.get("total_return_pct", 0.0)
        mdd = stats.get("max_drawdown_pct", 0.0)
        ntrades = stats.get("num_trades", 0)
        print(f"  Total Return: {total_ret:.4f} ({total_ret*100:.2f}%)")
        print(f"  Max Drawdown: {mdd:.4f} ({mdd*100:.2f}%)")
        print(f"  Trades Count: {ntrades}")
        print()

        print("Entry/Exit Log:")
        if trades:
            for t in trades:
                print(f"  Entry {t['entry_date']} @ {t['entry_price']:.2f}  "
                      f"Exit {t['exit_date']} @ {t['exit_price']:.2f}  "
                      f"PnL {t['pnl']:.2f}  Ret {t['return_pct']*100:.2f}%")
        else:
            print("  No trades executed.")
        print()


if __name__ == "__main__":
    main()
