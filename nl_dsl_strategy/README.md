# NL → DSL Strategy Demo

This project demonstrates a simple pipeline:

1. Natural language (NL) description → a simple heuristic converter → DSL string
2. DSL string → tokenizer + parser → Abstract Syntax Tree (AST)
3. AST → evaluator over pandas DataFrame → buy/sell signals
4. Signals → simple backtest → summary stats

No external data is required; the demo uses synthetic OHLCV data so it runs offline.

# NL → DSL Strategy Pipeline

This package converts simple natural language trading rules into a small DSL, parses the DSL into an AST, generates boolean signals over OHLCV data, and runs a minimal long-only backtest.

## Quick Start

### Requirements
- Python 3.9+
- pandas, numpy, pytest
- Optional: spaCy (`en_core_web_sm`)

### Setup
Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r nl_dsl_strategy/requirements.txt
```

### Run Demo

```bash
python nl_dsl_strategy/src/demo.py
```

You’ll see:
- NL input → structured JSON → DSL
- DSL → AST types
- Generated signals (head)
- Backtest metrics (Total Return %, Max Drawdown %, Trades) and a trade log

### Run Tests

```bash
pytest -q
```

Tests cover:
- NL parser structured mapping
- DSL parsing, validation, and precedence
- Codegen signal generation and types
- Backtest lifecycle and metrics

### Optional: spaCy NL support
Install spaCy and the small English model to enable the optional NL parsing helper:

```bash
pip install spacy
python -m spacy download en_core_web_sm
```

## Project Layout

```
nl_dsl_strategy/
	src/
		nl_parser.py            # NL → structured
		dsl_lexer_parser.py     # DSL tokenizer/parser → AST
		ast_nodes.py            # AST dataclasses
		codegen.py              # AST → pandas signals
		indicators.py           # SMA/RSI helpers
		backtest.py             # run_backtest(df, signals)
		demo.py                 # end-to-end demo
	tests/
		test_nl_parser.py
		test_dsl_parser.py
		test_codegen.py
		test_backtest.py
	dsl_spec.md               # DSL grammar reference + examples
```

## Usage Tips

- The demo uses a small, embedded OHLCV DataFrame; swap in your CSV by replacing `build_example_df()` in `demo.py`.
- If an entry or exit side has no clauses from NL, the demo emits a safe false comparison (`close < 0`) so the DSL stays parsable.
- Percent/lag modifiers from NL are partially mapped; extend `structured_to_dsl` logic to emit expressions like `volume > volume.shift(5) * 1.3`.
