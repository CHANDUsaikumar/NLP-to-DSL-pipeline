import json

from nl_dsl_strategy.src.nl_parser import parse_natural_language_to_structured, structured_to_dsl


def roundtrip(nl: str):
    structured = parse_natural_language_to_structured(nl)
    dsl = structured_to_dsl(structured)
    return structured, dsl


def test_ma_synonyms_and_volume_million():
    nl = "Buy when the close price is above the 20-day moving average and volume is above 1 million. Exit when RSI(14) is below 30."
    structured, dsl = roundtrip(nl)
    # Check structured contains SMA and volume threshold
    entry = structured.get("entry", [])
    assert any(isinstance(c.get("right"), dict) and c["right"].get("name") == "sma" for c in entry)
    assert any(c.get("left") == "volume" and c.get("operator") == ">" and c.get("right") == 1000000 for c in entry)
    assert "ENTRY:" in dsl and "EXIT:" in dsl


def test_cross_above_below_phrase():
    nl = "Enter when the price crosses above yesterday's high. Exit when RSI(14) is above 70."
    structured, dsl = roundtrip(nl)
    # Expect modifiers with cross and lag in structured
    entry = structured.get("entry", [])
    assert any(c.get("modifiers", {}).get("cross") for c in entry)
    # DSL should include CROSSOVER and SHIFT(..., 1)
    assert "CROSSOVER" in dsl
    assert "SHIFT(" in dsl


def test_ema_mapping():
    nl = "Buy when the price is above the 50-day EMA."
    structured, dsl = roundtrip(nl)
    entry = structured.get("entry", [])
    assert any(isinstance(c.get("right"), dict) and c["right"].get("name") == "ema" for c in entry)
    assert "EMA(" in dsl


def test_macd_vs_signal_and_histogram():
    nl = "Enter when MACD is above the signal. Exit when MACD histogram is below 0."
    structured, dsl = roundtrip(nl)
    entry = structured.get("entry", [])
    exit_ = structured.get("exit", [])
    assert any(isinstance(c.get("left"), dict) and c["left"]["name"] == "macd" for c in entry)
    assert any(isinstance(c.get("right"), dict) and c["right"]["name"] == "macd_signal" for c in entry)
    assert any(isinstance(c.get("left"), dict) and c["left"]["name"] == "macd_hist" and c.get("operator") == "<" for c in exit_)
    assert "MACD(" in dsl and "MACD_SIGNAL(" in dsl and "MACD_HIST(" in dsl


def test_bollinger_band_upper_lower():
    nl = "Buy when price is above upper Bollinger Band (20, 2) and sell when price is below lower Bollinger Band."
    structured, dsl = roundtrip(nl)
    entry = structured.get("entry", [])
    exit_ = structured.get("exit", [])
    assert any(isinstance(c.get("right"), dict) and c["right"].get("name") == "bbupper" for c in entry)
    assert any(isinstance(c.get("right"), dict) and c["right"].get("name") == "bblower" for c in exit_)
    assert "BBUPPER(" in dsl and "BBLOWER(" in dsl


def test_cross_synonyms_and_breaks():
    nl = "Enter when the price crossed over yesterday's high or breaks below yesterday's low."
    structured, dsl = roundtrip(nl)
    entry = structured.get("entry", [])
    assert any(c.get("modifiers", {}).get("cross") for c in entry)
    # OR connective should be preserved in DSL
    assert " OR " in dsl


def test_or_and_precedence_documented():
    # Ensure the DSL preserves order of connectors for "A or B and C"
    nl = "Buy when close is above 10 or volume is above 1k and RSI(14) is below 30."
    structured, dsl = roundtrip(nl)
    # We expect connectors in order; we don't enforce grouping here, just presence and order tokens
    assert "OR" in dsl and "AND" in dsl


def test_percent_and_last_week():
    nl = "Buy when volume increases by more than 25 percent compared to last week."
    structured, dsl = roundtrip(nl)
    entry = structured.get("entry", [])
    assert any(c.get("modifiers", {}).get("percent") == 0.25 for c in entry)
    assert any(c.get("modifiers", {}).get("lag") == 5 for c in entry)
    assert "* 1.25" in dsl
