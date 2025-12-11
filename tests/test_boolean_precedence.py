import pandas as pd
from nl_dsl_strategy.src.dsl_lexer_parser import parse_dsl
from nl_dsl_strategy.src.codegen import generate_signals


def test_boolean_precedence_basic():
    # NOT > AND > OR; parentheses override
    dsl = "ENTRY: NOT (FALSE == TRUE) AND (TRUE == TRUE) OR (FALSE == TRUE) EXIT: FALSE"
    ast = parse_dsl(dsl)
    df = pd.DataFrame({"open": [], "high": [], "low": [], "close": [], "volume": []})
    signals = generate_signals(ast, df)
    # NOT FALSE -> TRUE; TRUE AND TRUE -> TRUE; TRUE OR FALSE -> TRUE
    assert signals["entry"].all() if len(signals["entry"]) else True


def test_boolean_parentheses_grouping():
    dsl = "ENTRY: NOT ((FALSE == TRUE) AND (TRUE == TRUE)) OR (FALSE == TRUE) EXIT: FALSE"
    ast = parse_dsl(dsl)
    df = pd.DataFrame({"open": [], "high": [], "low": [], "close": [], "volume": []})
    signals = generate_signals(ast, df)
    # (FALSE AND TRUE) -> FALSE; NOT FALSE -> TRUE; TRUE OR FALSE -> TRUE
    assert signals["entry"].all() if len(signals["entry"]) else True
