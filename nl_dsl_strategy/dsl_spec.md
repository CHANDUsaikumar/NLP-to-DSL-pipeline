# DSL Specification

A compact language for defining trading entry/exit rules on time-series data.

## Grammar (informal)

- Strategy: one or more rules separated by `;`
- Rule: `BUY WHEN` Expr | `SELL WHEN` Expr
- Expr: Term (`AND`|`OR` Term)*
- Term: Factor (CompareOp Factor | CrossOp Factor)? | `NOT` Term | `(` Expr `)`
- CompareOp: `<` | `>` | `<=` | `>=` | `==` | `!=`
- CrossOp: `CROSSOVER` | `CROSSUNDER`
- Factor: IndicatorCall | SeriesRef | Number
- IndicatorCall: NAME `(` args `)`
- SeriesRef: `open` | `high` | `low` | `close` | `volume`

## Supported Indicators

- `SMA(series, period)` — Simple moving average
- `EMA(series, period)` — Exponential moving average
- `RSI(series, period)` — Relative Strength Index (default period 14)

## Examples

- Golden/death cross with RSI filter:

```
BUY WHEN SMA(close, 50) CROSSOVER SMA(close, 200) AND RSI(close, 14) < 70;
SELL WHEN SMA(close, 50) CROSSUNDER SMA(close, 200) OR RSI(close, 14) > 80
```

- Mean reversion on RSI:

```
BUY WHEN RSI(close, 14) < 30;
SELL WHEN RSI(close, 14) > 50
```
