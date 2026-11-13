from __future__ import annotations

import pytest

from sipl.ast import (
    Assign,
    BinOp,
    Block,
    BoolConst,
    BoolOp,
    Compare,
    If,
    Not,
    Num,
    Seq,
    Skip,
    SourceSpan,
    Var,
    While,
    to_dict,
    variables,
    walk,
)
from sipl.errors import SiplSyntaxError
from sipl.parser import parse


def body(source: str):
    return parse(source).body


def test_power_ast(power_source: str) -> None:
    program = parse(power_source)
    assert program.body == Seq(
        (
            Assign("R", Num(1)),
            While(
                Compare(">", Var("Y"), Num(0)),
                Block(
                    Seq(
                        (
                            Assign("R", BinOp("*", Var("R"), Var("X"))),
                            Assign("Y", BinOp("-", Var("Y"), Num(1))),
                        )
                    )
                ),
            ),
        )
    )


def test_spans_point_to_source(power_source: str) -> None:
    program = parse(power_source)
    loop = program.body.statements[1]
    assert loop.span == SourceSpan(3, 3, 7, 6)
    assert loop.cond.span == SourceSpan(3, 9, 3, 14)
    lines = power_source.splitlines()
    assert lines[2][loop.cond.span.column - 1 : loop.cond.span.end_column - 1] == "Y > 0"


def test_every_node_has_span(power_source: str) -> None:
    for node in walk(parse(power_source)):
        assert node.span is not None, node


def test_multiplication_binds_tighter() -> None:
    stmt = body("begin X := 1 + 2 * 3 end")
    assert stmt == Assign("X", BinOp("+", Num(1), BinOp("*", Num(2), Num(3))))


def test_subtraction_is_left_associative() -> None:
    stmt = body("begin X := 10 - 3 - 2 end")
    assert stmt == Assign("X", BinOp("-", BinOp("-", Num(10), Num(3)), Num(2)))


def test_parentheses_override_precedence() -> None:
    stmt = body("begin X := (1 + 2) * 3 end")
    assert stmt == Assign("X", BinOp("*", BinOp("+", Num(1), Num(2)), Num(3)))


def test_negative_literal() -> None:
    assert body("begin X := -1 end") == Assign("X", Num(-1))
    assert body("begin X := Y - -1 end") == Assign("X", BinOp("-", Var("Y"), Num(-1)))
    assert body("begin X := Y-1 end") == Assign("X", BinOp("-", Var("Y"), Num(1)))


def test_boolean_precedence() -> None:
    stmt = body("begin if not X = 1 or Y > 2 and true then skip else skip end")
    assert isinstance(stmt, If)
    assert stmt.cond == BoolOp(
        "or",
        Not(Compare("=", Var("X"), Num(1))),
        BoolOp("and", Compare(">", Var("Y"), Num(2)), BoolConst(True)),
    )


def test_unicode_operators_are_normalized() -> None:
    stmt = body("begin if ¬(X = 0) ∨ X ≥ 1 ∧ false then X := X – 1 else X := X × 2 end")
    assert isinstance(stmt, If)
    assert stmt.cond == BoolOp(
        "or",
        Not(Compare("=", Var("X"), Num(0))),
        BoolOp("and", Compare(">=", Var("X"), Num(1)), BoolConst(False)),
    )
    assert stmt.then_branch == Assign("X", BinOp("-", Var("X"), Num(1)))
    assert stmt.else_branch == Assign("X", BinOp("*", Var("X"), Num(2)))


def test_while_binds_tighter_than_sequence() -> None:
    stmt = body("begin while X > 0 do X := X - 1; Y := 1 end")
    assert isinstance(stmt, Seq)
    assert isinstance(stmt.statements[0], While)
    assert stmt.statements[1] == Assign("Y", Num(1))


def test_skip_and_nested_blocks() -> None:
    stmt = body("begin skip; begin begin skip end end end")
    assert stmt == Seq((Skip(), Block(Block(Skip()))))


def test_identifiers_may_contain_keywords_as_prefix() -> None:
    stmt = body("begin divisor := 1; endX := 2; dot := 3 end")
    assert variables(parse("begin divisor := endX end")) == {"divisor", "endX"}
    assert isinstance(stmt, Seq)


def test_comments_are_ignored() -> None:
    assert body("// header\nbegin X := 1 // tail\nend") == Assign("X", Num(1))


def test_to_dict_is_json_ready(power_source: str) -> None:
    data = to_dict(parse(power_source))
    assert data["type"] == "Program"
    assert data["body"]["type"] == "Seq"
    assert data["span"] == {"line": 1, "column": 1, "end_line": 8, "end_column": 4}


@pytest.mark.parametrize(
    ("source", "line", "column", "fragment"),
    [
        ("begin X = 1 end", 1, 9, "':='"),
        ("begin\n  X := 1;\nend", 3, 1, "'end'"),
        ("begin X := 1", 1, 13, "кінець"),
        ("", 1, 1, "Порожня"),
        ("begin X := 1 end end", 1, 18, "кінець програми"),
    ],
)
def test_syntax_error_positions(source: str, line: int, column: int, fragment: str) -> None:
    with pytest.raises(SiplSyntaxError) as info:
        parse(source)
    assert info.value.span is not None
    assert (info.value.span.line, info.value.span.column) == (line, column)
    assert fragment in info.value.message
    assert info.value.diagnostic().to_dict()["code"] == "SYNTAX"


def test_span_contains() -> None:
    span = SourceSpan(2, 3, 2, 8)
    assert span.contains(2, 3)
    assert not span.contains(2, 8)
    assert str(span) == "2:3-2:8"
