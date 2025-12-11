# tests/test_dsl_parser.py

import pytest

from src.dsl_lexer_parser import parse_dsl, DSLParseError
from src.ast_nodes import Strategy, BinaryOp, SeriesRef, FuncCall


def test_parse_simple_entry_exit():
    dsl = """
    ENTRY: close > SMA(close, 3) AND volume > 1000000
    EXIT:  RSI(close, 14) < 30
    """

    strategy = parse_dsl(dsl)
    assert isinstance(strategy, Strategy)

    # Entry and exit should be AST nodes
    assert strategy.entry is not None
    assert strategy.exit is not None

    # Entry should be a BinaryOp (AND) at the top
    assert isinstance(strategy.entry, BinaryOp)
    assert strategy.entry.op == "AND"

    # Left side of AND: close > SMA(...)
    left = strategy.entry.left
    assert isinstance(left, BinaryOp)
    assert left.op == ">"
    assert isinstance(left.left, SeriesRef)
    assert left.left.name == "close"
    assert isinstance(left.right, FuncCall)
    assert left.right.name == "SMA"

    # Exit: RSI(close,14) < 30
    exit_node = strategy.exit
    assert isinstance(exit_node, BinaryOp)
    assert exit_node.op == "<"
    assert isinstance(exit_node.left, FuncCall)
    assert exit_node.left.name == "RSI"


def test_invalid_series_name_raises():
    # 'price' is not in VALID_SERIES {"open","high","low","close","volume"}
    bad_dsl = """
    ENTRY: price > 100
    EXIT:  close < 90
    """
    with pytest.raises(DSLParseError):
        parse_dsl(bad_dsl)


def test_crossover_parsing():
    dsl = """
    ENTRY: close CROSSOVER SMA(close, 5)
    EXIT:  close < SMA(close, 3)
    """

    strategy = parse_dsl(dsl)
    entry = strategy.entry
    assert isinstance(entry, BinaryOp)
    assert entry.op == "CROSSOVER"
    assert isinstance(entry.left, SeriesRef)
    assert entry.left.name == "close"
    assert isinstance(entry.right, FuncCall)
    assert entry.right.name == "SMA"
