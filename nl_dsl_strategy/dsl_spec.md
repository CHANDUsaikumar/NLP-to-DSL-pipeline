# DSL Grammar and Examples

This document concisely describes the trading DSL and provides examples. The DSL maps to an AST which is evaluated over OHLCV data to produce entry/exit signals.

## Program Structure

Strategies have two clauses:
- ENTRY: <boolean-expression>
- EXIT:  <boolean-expression>

Example skeleton:
```
ENTRY: <expr>
EXIT:  <expr>
```

## Lexical Elements

- Identifiers: uppercase in DSL; series names are stored lowercase internally.
- Literals: integers, floats, booleans `TRUE`/`FALSE`.
- Numeric suffixes: `K` (×1,000), `M` (×1,000,000), e.g., `2K`, `1.5M`.
- Parentheses: `(` `)` for grouping.
- Brackets: `[` `]` for lag indexing on series (optional).

## Series

Available series (DataFrame columns): `open`, `high`, `low`, `close`, `volume`.

Lag indexing (optional):
- `CLOSE[5]` means close shifted by 5 bars.

## Functions

- Moving Averages: `SMA(series, period)`, `EMA(series, period)`
- Momentum: `RSI(series, period)`, `SHIFT(series, bars)`
- MACD family: `MACD(series, fast, slow, signal)`, `MACD_SIGNAL(series, fast, slow, signal)`, `MACD_HIST(series, fast, slow, signal)`
- Bollinger Bands: `BBANDS(series, period, std)`, `BBUPPER(series, period, std)`, `BBLOWER(series, period, std)`
- Events: `CROSSOVER(left, right)`, `CROSSUNDER(left, right)`

Notes:
- `MACD` returns the MACD line; use `MACD_SIGNAL` / `MACD_HIST` for signal and histogram.
- `BBANDS` returns the middle band; use `BBUPPER` / `BBLOWER` for upper/lower.

## Operators and Precedence

- Arithmetic: `+`, `-`, `*`, `/`
- Comparisons: `>`, `>=`, `<`, `<=`, `==`, `!=`
- Logic: `AND`, `OR`, `NOT`

Precedence (highest → lowest):
1. Parentheses `(...)`
2. Arithmetic `*` `/` then `+` `-`
3. Comparisons `>` `>=` `<` `<=` `==` `!=`
4. NOT
5. AND
6. OR

Arithmetic and comparisons are evaluated before logical operators. Use parentheses to override.

One-line BNF (informal):

```
program   := "ENTRY:" bool_expr "\n" "EXIT:" bool_expr
bool_expr := or_expr
or_expr   := and_expr { "OR" and_expr }
and_expr  := not_expr { "AND" not_expr }
not_expr  := [ "NOT" ] comparison
comparison:= arith { ("<"|"<="|">"|">="|"=="|"!=") arith | ("CROSSOVER"|"CROSSUNDER") arith }
arith     := term { ("+"|"-") term }
term      := factor { ("*"|"/") factor }
factor    := NUMBER [SUFFIX] | TRUE | FALSE | IDENT [ "[" NUMBER "]" ] | IDENT "(" args ")" | "(" bool_expr ")"
args      := [ bool_expr { "," bool_expr } ]
```

## Examples

### 1) EMA crossover with RSI filter
```
ENTRY: CROSSOVER(EMA(close, 20), EMA(close, 50)) AND RSI(close, 14) < 70
EXIT:  FALSE
```

### 2) Bollinger breakout
```
ENTRY: close > BBUPPER(close, 20, 2)
EXIT:  close < BBANDS(close, 20, 2)
```

### 3) MACD signal cross under
```
ENTRY: CROSSUNDER(MACD(close, 12, 26, 9), MACD_SIGNAL(close, 12, 26, 9))
EXIT:  FALSE
```

### 4) Volume filter with shift
```
ENTRY: volume > 1M AND SHIFT(close, 3) > 0
EXIT:  FALSE
```

### 5) Parentheses and precedence
```
ENTRY: NOT (RSI(close, 14) > 70 AND close > SMA(close, 50)) OR volume > 2K
EXIT:  FALSE
```

## Error Reporting

- Parser errors include line and column with a small snippet context.
- Unknown series or functions may suggest closest valid names.

## Validation

- Series and function names are validated against centralized sets (`VALID_SERIES`, `VALID_FUNCS`).
- Indicator arities are enforced (`ALLOWED_INDICATORS`). See `nl_dsl_strategy/src/validator.py`.

## Design Intent

The DSL favors correctness and clarity. It is compact, deterministic, and maps cleanly to an AST for evaluation over pandas.
