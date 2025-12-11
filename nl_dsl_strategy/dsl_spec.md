# DSL Specification

A compact language for defining trading entry/exit rules on time-series data.

## Overview

- Two clauses: `ENTRY:` and `EXIT:`; each is a boolean expression.
- Supports comparisons, boolean operators, parentheses, and cross events.
- Series fields: `open`, `high`, `low`, `close`, `volume` (optional lag via `.shift(N)` in codegen-level mapping).

## Grammar (informal)

- Expr := Term (`AND` | `OR` Term)*
- Term := Factor | `NOT` Term | `(` Expr `)` | Factor CompareOp Factor | Factor CrossOp Factor
- CompareOp := `<` | `>` | `<=` | `>=` | `==` | `!=`
- CrossOp := `CROSSOVER` | `CROSSUNDER`
- Factor := IndicatorCall | SeriesRef | Number
- IndicatorCall := NAME `(` args `)`
- SeriesRef := `open` | `high` | `low` | `close` | `volume`

Precedence (highest → lowest):
1. Parentheses
2. NOT
3. AND
4. OR

## Supported Indicators

- `SMA(series, period)` — Simple moving average
- `RSI(series, period)` — Relative Strength Index (default period 14)

## Examples

### Golden/death cross with RSI filter

```
ENTRY: SMA(close, 50) CROSSOVER SMA(close, 200) AND RSI(close, 14) < 70
EXIT:  SMA(close, 50) CROSSUNDER SMA(close, 200) OR RSI(close, 14) > 80
```

### Mean reversion on RSI

```
ENTRY: RSI(close, 14) < 30
EXIT:  RSI(close, 14) > 50
```

### Price above fast SMA and volume threshold

```
ENTRY: close > SMA(close, 3) AND volume > 1000000
EXIT:  RSI(close, 14) < 30
```

### Crossover example (yesterday’s high)

```
ENTRY: close CROSSOVER high
EXIT:  close < 0   # placeholder false expression when no exit clauses
```
