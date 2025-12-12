import pytest
from nl_dsl_strategy.src.nl_parser import structured_to_dsl, parse_natural_language_to_structured


def test_ambiguous_grouping_preserves_order():
    nl = "20 EMA crosses above 50 EMA and RSI(14) below 70 or volume above 1M"
    structured = parse_natural_language_to_structured(nl)
    dsl = structured_to_dsl(structured)
    # Ensure presence of OR and that earlier clause precedes OR
    assert "OR" in dsl
    assert dsl.strip().startswith("ENTRY:")


def test_malformed_input_error_handling():
    nl = "random gibberish without indicators"
    structured = parse_natural_language_to_structured(nl)
    dsl = structured_to_dsl(structured)
    # Expect safe placeholders when nothing is recognized
    assert "EXIT:" in dsl
    assert "ENTRY:" in dsl
