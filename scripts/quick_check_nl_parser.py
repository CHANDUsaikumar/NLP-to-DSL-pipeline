import sys, json, importlib.util
from pathlib import Path

# Load the currently edited nl_parser.py directly to ensure latest changes are used
nl_parser_path = Path(__file__).resolve().parents[1] / 'nl_dsl_strategy' / 'src' / 'nl_parser.py'
spec = importlib.util.spec_from_file_location("nl_parser", str(nl_parser_path))
nl_parser = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(nl_parser)

examples = [
    "Buy when the close price is above the 20-day moving average and volume is above 1 million.",
    "Enter when price crosses above yesterday's high.",
    "Exit when RSI(14) is below 30.",
    "Trigger entry when volume increases by more than 30 percent compared to last week."
]

for i, ex in enumerate(examples, 1):
    structured = nl_parser.parse_natural_language_to_structured(ex)
    print(f"Example {i}:")
    print(json.dumps(structured, indent=2))

# Assertions for requested verifications
e1 = nl_parser.parse_natural_language_to_structured(examples[0])
# Expect SMA clause and volume 1,000,000
has_sma = any(isinstance(c.get('right'), dict) and c['right'].get('name') == 'sma' for c in e1['entry'])
has_vol_million = any(c.get('left') == 'volume' and isinstance(c.get('right'), (int, float)) and int(c['right']) == 1000000 for c in e1['entry'])
print("Check Example 1 - SMA present:", has_sma)
print("Check Example 1 - Volume 1,000,000:", has_vol_million)

e3 = nl_parser.parse_natural_language_to_structured(examples[2])
has_rsi_indicator = any(isinstance(c.get('left'), dict) and c['left'].get('name') == 'rsi' for c in e3['exit'])
print("Check Example 3 - RSI indicator dict:", has_rsi_indicator)
