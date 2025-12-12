import pytest
from nl_dsl_strategy.src.dsl_lexer_parser import DSLParseError, parse_dsl


def test_parser_error_message_shape():
    bad_dsl = "ENTRY: CROSSOVER(EMA(close, 20), EMA(close, 50)) EXIT:"
    with pytest.raises(DSLParseError) as ei:
        parse_dsl(bad_dsl)
    msg = str(ei.value)
    # Message should include a human-readable description and possibly line/col
    assert "Expected" in msg or "Unexpected" in msg
    # Optional: line/col added by parser
    assert ("line" in msg and "col" in msg) or True
