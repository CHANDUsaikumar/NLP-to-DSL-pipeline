Quick NL → DSL examples

Run each example end-to-end using the CLI with the bundled sample data.

Prereqs
- Install deps: `pip install -r nl_dsl_strategy/requirements.txt`
- Use sample CSV: `scripts/sample_data.csv`

Examples

1) EMA crossover with RSI filter
- NL: 20 EMA crosses above 50 EMA and RSI(14) below 70
- DSL: ENTRY: CROSSOVER(EMA(close, 20), EMA(close, 50)) AND RSI(close, 14) < 70 EXIT: FALSE
- Run NL
  ```zsh
  python scripts/run_strategy.py --csv scripts/sample_data.csv --nl "20 EMA crosses above 50 EMA and RSI(14) below 70" --mark-to-market
  ```
- Run DSL
  ```zsh
  python scripts/run_strategy.py --csv scripts/sample_data.csv --dsl "ENTRY: CROSSOVER(EMA(close, 20), EMA(close, 50)) AND RSI(close, 14) < 70 EXIT: FALSE" --mark-to-market
  ```

2) MACD crosses below its signal
- NL: MACD crosses below its signal
- DSL: ENTRY: CROSSUNDER(MACD(close, 12, 26, 9), MACD_SIGNAL(close, 12, 26, 9)) EXIT: FALSE
- Run NL
  ```zsh
  python scripts/run_strategy.py --csv scripts/sample_data.csv --nl "MACD crosses below its signal" --mark-to-market
  ```
- Run DSL
  ```zsh
  python scripts/run_strategy.py --csv scripts/sample_data.csv --dsl "ENTRY: CROSSUNDER(MACD(close, 12, 26, 9), MACD_SIGNAL(close, 12, 26, 9)) EXIT: FALSE" --mark-to-market
  ```

3) Price breaks above upper Bollinger Band (20, 2)
- NL: Price breaks above upper Bollinger Band (20, 2)
- DSL: ENTRY: close > BBUPPER(close, 20, 2) EXIT: FALSE
- Run NL
  ```zsh
  python scripts/run_strategy.py --csv scripts/sample_data.csv --nl "Price breaks above upper Bollinger Band (20, 2)" --mark-to-market
  ```
- Run DSL
  ```zsh
  python scripts/run_strategy.py --csv scripts/sample_data.csv --dsl "ENTRY: close > BBUPPER(close, 20, 2) EXIT: FALSE" --mark-to-market
  ```

4) Volume above 1 million with positive 3-bar shift
- NL: Volume above 1 million and last 3 days close is above price
- DSL: ENTRY: volume > 1M AND SHIFT(close, 3) > close EXIT: FALSE
- Run NL
  ```zsh
  python scripts/run_strategy.py --csv scripts/sample_data.csv --nl "Volume above 1 million and last 3 days close is above price" --mark-to-market
  ```
- Run DSL
  ```zsh
  python scripts/run_strategy.py --csv scripts/sample_data.csv --dsl "ENTRY: volume > 1M AND SHIFT(close, 3) > close EXIT: FALSE" --mark-to-market
  ```

Notes
- If an NL phrase isn’t recognized, use the DSL equivalent directly.
- You can add `--export-signals signals.csv` to inspect generated signals.