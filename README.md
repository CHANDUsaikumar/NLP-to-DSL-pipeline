# NL → DSL Strategy Demo

This project demonstrates a simple pipeline:

1. Natural language (NL) description → a simple heuristic converter → DSL string
2. DSL string → tokenizer + parser → Abstract Syntax Tree (AST)
3. AST → evaluator over pandas DataFrame → buy/sell signals
4. Signals → simple backtest → summary stats

No external data is required; the demo uses synthetic OHLCV data so it runs offline.

# NL → DSL Strategy Pipeline

This package converts simple natural language trading rules into a small DSL, parses the DSL into an AST, generates boolean signals over OHLCV data, and runs a minimal long-only backtest.

## DSL Overview

Primitives
- Series: `open`, `high`, `low`, `close`, `volume`
- Literals: integers/floats, booleans (`TRUE`, `FALSE`), numeric suffixes `K` (×1,000) and `M` (×1,000,000) like `2K`, `1.5M`

Functions
- Moving averages: `SMA(series, period)`, `EMA(series, period)`
- Momentum: `RSI(series, period)`, `SHIFT(series, bars)`
- MACD: `MACD(series, fast, slow, signal)`, `MACD_SIGNAL(...)`, `MACD_HIST(...)`
- Bollinger Bands: `BBANDS(series, period, std)`, `BBUPPER(...)`, `BBLOWER(...)`
- Events: `CROSSOVER(left, right)`, `CROSSUNDER(left, right)`

Operators
- Arithmetic: `+`, `-`, `*`, `/`
- Comparisons: `>`, `>=`, `<`, `<=`, `==`, `!=`
- Logic: `AND`, `OR`, `NOT`

Precedence
- `NOT` > `AND` > `OR`; arithmetic and comparisons evaluate before logic. Use parentheses to group.

Examples
- `CROSSOVER(EMA(close, 20), EMA(close, 50)) AND RSI(close, 14) < 70`
- `close > BBUPPER(close, 20, 2) OR CROSSUNDER(MACD(close, 12, 26, 9), MACD_SIGNAL(close, 12, 26, 9))`
- `SHIFT(close, 5) >= 1.5M AND volume > 2M`

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

```zsh
# Run the built-in demo with synthetic OHLCV data
python nl_dsl_strategy/src/demo.py
```

What to expect:
- NL input is converted to structured JSON and then to DSL
- DSL is parsed into AST types and evaluated into boolean signals
- Backtest prints summary metrics: Total Return %, Max Drawdown %, Sharpe, Trades
- A compact trade log is shown for transparency

Troubleshooting:
- If Python can’t find dependencies, ensure your virtualenv is active and run `pip install -r nl_dsl_strategy/requirements.txt`.
- If spaCy is missing (optional), either install it or ignore related NL helpers; the demo runs without spaCy.

## CLI

Run end-to-end on a CSV:

```bash
python scripts/run_strategy.py --csv path/to/data.csv --nl "Buy when the close price is above the 20-day moving average and volume is above 1 million. Exit when RSI(14) is below 30."
```

Direct DSL input (bypass NL):

```bash
python scripts/run_strategy.py --csv path/to/data.csv --dsl "ENTRY: CROSSOVER(CLOSE, SMA(CLOSE, 50)) AND VOLUME > 1M EXIT: CROSSUNDER(CLOSE, SMA(CLOSE, 20))" --export-signals signals.csv
```

Backtest options:

- `--slippage-bps`: basis points applied to entry and exit (default 0)
- `--fee`: flat fee per trade in currency units (default 0)
- `--mark-to-market`: update equity each bar while in position for more granular drawdown/Sharpe (optional; default off)

Metrics include total return, max drawdown, trades, and Sharpe ratio.

Note on NL coverage:
- The NL converter is designed to support the documented examples and closely related patterns (e.g., EMA/MA crossovers, RSI thresholds, MACD/Bollinger phrases, AND/OR chaining).
- It does not attempt to parse every possible English phrasing. If a sentence isn’t recognized, use DSL directly.

### Accepted NL examples → DSL

- "20 EMA crosses above 50 EMA" → `CROSSOVER(EMA(close, 20), EMA(close, 50))`
- "RSI(14) below 30" → `RSI(close, 14) < 30`
- "MACD crosses below its signal" → `CROSSUNDER(MACD(close, 12, 26, 9), MACD_SIGNAL(close, 12, 26, 9))`
- "Price breaks above upper Bollinger Band (20, 2)" → `close > BBUPPER(close, 20, 2)`
- "Volume above 1 million" → `volume > 1M`
- "Last 5 days close above 100" (simplified) → `SHIFT(close, 5) > 100`

Tip: run NL vs DSL side-by-side
```zsh
# NL input
python scripts/run_strategy.py --csv scripts/sample_data.csv --nl "20 EMA crosses above 50 EMA and RSI(14) below 70" --mark-to-market

# Equivalent DSL (remember: provide ENTRY and EXIT clauses)
python scripts/run_strategy.py --csv scripts/sample_data.csv --dsl "ENTRY: CROSSOVER(EMA(close, 20), EMA(close, 50)) AND RSI(close, 14) < 70 EXIT: FALSE" --mark-to-market
```

### Run Tests

```zsh
# Run the entire test suite quietly
pytest -q

# Or run a single test file for faster iteration
pytest -q tests/test_dsl_parser.py

# Show detailed output when diagnosing failures
pytest -vv
```

Coverage:
- NL → structured mapping and DSL generation
- DSL tokenizer/parser correctness, validation, and operator precedence
- Codegen for indicators, crossovers, and boolean logic
- Backtest lifecycle, fees/slippage, and metrics (including mark-to-market option)

## Architecture overview

Layers (separation of concerns):
- NL mapping (`nl_parser.py`): Regex-first mapping of supported phrases to structured JSON and DSL; spaCy helpers optional.
- DSL parsing (`dsl_lexer_parser.py`, `ast_nodes.py`): Tokenizer + recursive descent → typed AST with precise errors (line/col/snippet).
- Code generation (`codegen.py`, `indicators.py`): AST evaluation over pandas; indicators and crossover logic; boolean broadcasting for AND/OR.
- Validation (`validator.py`): Centralized `VALID_SERIES`, `VALID_FUNCS`, and indicator arities (`ALLOWED_INDICATORS`).
- Backtest (`backtest.py`): Long-only lifecycle with slippage/fees and optional mark-to-market.

Data flow:
NL → structured → DSL → AST → signals → backtest → metrics

## Design contracts (inputs, outputs, invariants)

DSL parser
- Input: DSL string using documented functions/operators.
- Output: AST (`Strategy`, `FuncCall`, `SeriesRef`, `Literal`, `BinaryOp`, `UnaryOp`).
- Errors: include line/column and snippet; suggest nearest valid tokens when possible.

Codegen
- Input: AST + pandas DataFrame with columns `[open, high, low, close, volume]`.
- Output: pandas Series/frames of booleans and indicator values; entry/exit signals.
- Invariants: indices align; boolean logic broadcasts scalars; comparisons handle NaNs consistently (emit False where undefined).

Backtest
- Input: price/volume DataFrame + entry/exit signals; parameters (slippage bps, fee, mark-to-market).
- Output: summary metrics (return %, max drawdown %, Sharpe) and trade log.
- Invariants: trades honor signal order; equity monotonic between fills unless mark-to-market enabled.

### Optional: spaCy NL support
Install spaCy and the small English model to enable the optional NL parsing helper:

```bash
pip install spacy
python -m spacy download en_core_web_sm
```

## Project Layout

```
MANIFEST.in
pyproject.toml
README.md                     # Top-level docs (DSL overview, CLI, tests)
signals.csv                   # Optional output from CLI --export-signals

nl_dsl_strategy/
	README.md                 # Package-level README (overview + pointers)
	dsl_spec.md               # DSL grammar reference + examples
	requirements.txt          # Runtime/test dependencies
	src/
		__init__.py
		ast_nodes.py          # AST dataclasses
		backtest.py           # run_backtest(df, signals, mark_to_market)
		codegen.py            # AST → pandas signals (indicators, logic)
		demo.py               # End-to-end demo
		dsl_lexer_parser.py   # DSL tokenizer/parser → AST
		indicators.py         # SMA/EMA/RSI/MACD/BBANDS and helpers
		nl_parser.py          # NL → structured + DSL mapping
		nlp_spacy.py          # Optional spaCy helpers (if installed)
		validator.py          # Centralized VALID_SERIES/VALID_FUNCS/arities
	tests/
		conftest.py
		test_backtest.py
		test_codegen.py
		test_crossover_func.py
		test_dsl_parser.py
		test_indicators.py
		test_nl_mapping.py

scripts/
	quick_check_nl_parser.py  # Small NL parser sanity script
	run_strategy.py           # CLI runner for NL/DSL → signals → backtest
	sample_data.csv           # Example CSV for CLI runs
```

## Usage Tips

- The demo uses a small, embedded OHLCV DataFrame; swap in your CSV by replacing `build_example_df()` in `demo.py`.
- If an entry or exit side has no clauses from NL, the demo emits a safe false comparison (`close < 0`) so the DSL stays parsable.
- Percent/lag modifiers from NL are mapped; e.g., `volume > SHIFT(volume, 5) * 1.3`.

## DSL Cheatsheet

- Indicators: `SMA(series, window)`, `EMA(series, window)`, `RSI(series, window)`, `MACD(series, fast, slow, signal)`, `BBANDS(series, period, std)`
- Lag: `SHIFT(series, lag)`
- Cross events: `CROSSOVER` / `CROSSUNDER` as binary ops, or functions `CROSSOVER(seriesA, seriesB)` / `CROSSUNDER(seriesA, seriesB)`
- Numeric suffixes: literals like `1M` or `2K` are supported in DSL.
 - Bands/Signals helpers: `BBUPPER(series, period, std)`, `BBLOWER(series, period, std)`, `MACD_SIGNAL(series, fast, slow, signal)`, `MACD_HIST(series, fast, slow, signal)`

Examples:

- MA crossover: `ENTRY: CROSSOVER(CLOSE, SMA(CLOSE, 50)) EXIT: CROSSUNDER(CLOSE, SMA(CLOSE, 20))`
- RSI threshold: `ENTRY: RSI(CLOSE, 14) > 70 EXIT: RSI(CLOSE, 14) < 30`
- Mean reversion: `ENTRY: CLOSE < BBANDS(CLOSE, 20, 2.0) EXIT: CLOSE > BBANDS(CLOSE, 20, 2.0)`

## Design decisions

- Functions over properties: Indicators and temporal ops are functions (e.g., `SMA`, `RSI`, `SHIFT`) to keep grammar compact and parsing deterministic.
- Clear precedence: Boolean ops follow `NOT > AND > OR`, with parentheses for explicit grouping.
- Temporal semantics via `SHIFT`: Lag is represented uniformly, avoiding dotted offsets.
- Extensibility: Central `VALID_FUNCS` and validator hooks make adding indicators straightforward; helpers like `BBUPPER`/`MACD_SIGNAL` are thin wrappers over core functions.
- Ergonomics: Numeric suffixes (`1M`, `2K`) and crossover functions improve authoring symmetry with NL.

## Validator (centralized constants)

The validator defines canonical sets used by the parser and codegen:

- VALID_SERIES: `{open, high, low, close, volume}`
- VALID_FUNCS: `{SMA, EMA, RSI, SHIFT, MACD, BBANDS, BBUPPER, BBLOWER, MACD_SIGNAL, MACD_HIST, CROSSOVER, CROSSUNDER}`

Indicator arities are enforced by `ALLOWED_INDICATORS` (see `nl_dsl_strategy/src/validator.py`).
