# tests/test_backtest.py

import sys
from pathlib import Path
import pandas as pd

# Ensure package path for tests when running from repo root
sys.path.append(str(Path(__file__).resolve().parents[1] / 'nl_dsl_strategy' / 'src'))
from backtest import run_backtest


def test_backtest_single_trade():
    # Construct a tiny dataset where we know exactly what should happen:
    # - Entry on day 2
    # - Exit on day 4
    data = [
        ("2023-01-01", 100),
        ("2023-01-02", 110),  # entry here
        ("2023-01-03", 115),
        ("2023-01-04", 120),  # exit here
    ]
    df = pd.DataFrame(data, columns=["date", "close"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")

    # Signals: entry True at index 1, exit True at index 3
    signals = pd.DataFrame(index=df.index)
    signals["entry"] = [False, True, False, False]
    signals["exit"] = [False, False, False, True]

    trades, stats = run_backtest(df, signals, position_size=1.0)

    # Exactly one trade
    assert len(trades) == 1
    t = trades[0]

    assert t.entry_price == 110
    assert t.exit_price == 120
    assert t.pnl == 10  # 120 - 110
    assert abs(t.return_pct - (10 / 110)) < 1e-9

    # Stats sanity
    assert stats["num_trades"] == 1
    # Total return should match PnL / starting_notional * 100
    assert abs(stats["total_return_pct"] - (10 / 110) * 100) < 1e-6
