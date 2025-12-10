# NL → DSL Strategy Demo

This project demonstrates a simple pipeline:

1. Natural language (NL) description → a simple heuristic converter → DSL string
2. DSL string → tokenizer + parser → Abstract Syntax Tree (AST)
3. AST → evaluator over pandas DataFrame → buy/sell signals
4. Signals → simple backtest → summary stats

No external data is required; the demo uses synthetic OHLCV data so it runs offline.

## Quick start

Create a virtual environment (optional), install requirements, and run the demo:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m nl_dsl_strategy.src.demo
```

You can pass a DSL string directly:

```bash
python -m nl_dsl_strategy.src.demo --dsl "BUY WHEN SMA(close, 20) CROSSOVER SMA(close, 50); SELL WHEN SMA(close, 20) CROSSUNDER SMA(close, 50)"
```

Or try a simple NL phrase:

```bash
python -m nl_dsl_strategy.src.demo --nl "buy when 20 sma crosses above 50 sma and rsi below 70"
```

## DSL quick reference

See `dsl_spec.md` for the informal grammar and examples.

## Notes

- The NL converter is intentionally minimal; it's just to make the demo end-to-end.
- The backtester executes orders at the next bar's close to avoid lookahead.
