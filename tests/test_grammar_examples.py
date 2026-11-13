from __future__ import annotations

from pathlib import Path

import pytest

from conftest import INVALID, VALID
from sipl.errors import SiplSyntaxError
from sipl.parser import parse


def test_enough_examples() -> None:
    assert len(VALID) >= 10
    assert len(INVALID) >= 10


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.stem)
def test_valid_programs_parse(path: Path) -> None:
    program = parse(path.read_text(encoding="utf-8"))
    assert program.span is not None


@pytest.mark.parametrize("path", INVALID, ids=lambda p: p.stem)
def test_invalid_programs_are_rejected(path: Path) -> None:
    with pytest.raises(SiplSyntaxError) as info:
        parse(path.read_text(encoding="utf-8"))
    span = info.value.span
    assert span is not None
    assert span.line >= 1 and span.column >= 1
    assert info.value.message
