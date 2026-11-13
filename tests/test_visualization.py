from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from conftest import EXAMPLES, VALID
from sipl.parser import parse, parse_tree
from sipl.visualization import ast_to_dot, crown, dot_to_svg, from_lark, leaf_text, leaves, to_dot, to_text

LEXEME = re.compile(r"//[^\n]*|:=|>=|<=|!=|-?[0-9]+|[A-Za-z_][A-Za-z0-9_]*|\S")


def tokens(source: str) -> list[str]:
    result = []
    for match in LEXEME.finditer(source):
        if not match.group(0).startswith("//"):
            result.append(match.group(0))
    return result


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.stem)
def test_crown_reproduces_program(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    root = from_lark(parse_tree(source))
    assert leaf_text(root).split() == tokens(source) or "".join(leaf_text(root).split()) == "".join(tokens(source))


def test_power_crown_matches_practicum() -> None:
    root = from_lark(parse_tree((EXAMPLES / "valid" / "power.sipl").read_text(encoding="utf-8")), course_names=True)
    assert crown(root) == (
        "1 begin 2 R 3 := 4 1 5 ; 6 while 7 Y 8 > 9 0 10 do 11 begin 12 R 13 := 14 R 15 * 16 X "
        "17 ; 18 Y 19 := 20 Y 21 - 22 1 23 end 24 end"
    )


def test_course_names_collapse_chains() -> None:
    root = from_lark(parse_tree("begin X := Y end"), course_names=True)
    assert root.label == "<програма>"
    stmt = root.children[1]
    assert stmt.label == "<оператор>"
    assert [c.label for c in stmt.children] == ["<змінна>", ":=", "<вираз>"]
    assert stmt.children[2].children[0].label == "<змінна>"


def test_leaves_have_spans_linked_to_source() -> None:
    source = "begin\n  X := 10\nend"
    root = from_lark(parse_tree(source))
    lines = source.split("\n")
    for leaf in leaves(root):
        span = leaf.span
        assert span is not None
        assert lines[span.line - 1][span.column - 1 : span.end_column - 1] == leaf.label


def test_text_json_dot() -> None:
    root = from_lark(parse_tree("begin skip end"))
    text = to_text(root)
    assert text.splitlines()[0].startswith("program")
    assert "└── 3. 'end'" in text
    data = json.loads(json.dumps(root.to_dict()))
    assert data["kind"] == "nonterminal"
    assert data["children"][0] == {
        "id": 1,
        "kind": "terminal",
        "label": "begin",
        "rule": "BEGIN",
        "span": {"line": 1, "column": 1, "end_line": 1, "end_column": 6},
        "leaf_index": 1,
    }
    dot = to_dot(root, "demo")
    assert dot.startswith('digraph "demo"')
    assert 'label="begin"' in dot and "n0 -> n1;" in dot
    assert 'tooltip="1:1-1:6"' in dot


def test_ast_dot() -> None:
    dot = ast_to_dot(parse("begin while X > 0 do X := X - 1 end"))
    assert 'label="Program"' in dot
    assert "While\\nwhile X > 0 do …" in dot
    assert "Compare\\n>" in dot


@pytest.mark.skipif(shutil.which("dot") is None, reason="graphviz not installed")
def test_svg() -> None:
    svg = dot_to_svg(to_dot(from_lark(parse_tree("begin skip end"))))
    assert "<svg" in svg and "skip" in svg


def test_svg_without_graphviz(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError):
        dot_to_svg("digraph {}")
