from __future__ import annotations

from pathlib import Path

import pytest

from conftest import VALID
from sipl.parser import parse
from sipl.printer import describe, format_program


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.stem)
def test_format_roundtrip(path: Path) -> None:
    program = parse(path.read_text(encoding="utf-8"))
    formatted = format_program(program)
    assert parse(formatted) == program
    assert format_program(parse(formatted)) == formatted


def test_minimal_parentheses() -> None:
    program = parse("begin X := (1 + 2) * 3; Y := 10 - (3 - 2); Z := (1 * 2) + 3 end")
    assert format_program(program) == "begin\n  X := (1 + 2) * 3;\n  Y := 10 - (3 - 2);\n  Z := 1 * 2 + 3\nend\n"


def test_describe() -> None:
    program = parse("begin while X > 0 do X := X - 1 end")
    assert describe(program) == "program"
    assert describe(program.body) == "while X > 0 do …"
