from __future__ import annotations

import pytest

from conftest import EXAMPLES
from sipl.errors import DivisionByZeroError, StepLimitExceeded, UndefinedVariableError
from sipl.interpreter import EVENT_KINDS, Interpreter, TraceRecorder, run
from sipl.parser import parse


def program(name: str):
    return parse((EXAMPLES / "valid" / f"{name}.sipl").read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("name", "state", "expected"),
    [
        ("power", {"X": 5, "Y": 2}, {"R": 25}),
        ("power", {"X": 2, "Y": 10}, {"R": 1024}),
        ("power", {"X": 7, "Y": 0}, {"R": 1}),
        ("geometric_sum_3", {"N": 3}, {"S": 40}),
        ("geometric_sum_3", {"N": 0}, {"S": 1}),
        ("geometric_sum_2", {"N": 3}, {"S": 15}),
        ("division", {"X": 7, "Y": 4}, {"R": 1, "X": 3}),
        ("factorial", {"N": 5}, {"F": 120}),
        ("fibonacci", {"N": 10}, {"A": 55}),
        ("gcd", {"A": 48, "B": 18}, {"A": 6, "B": 6}),
        ("max", {"X": 3, "Y": 9}, {"M": 9}),
        ("max", {"X": 4, "Y": 4}, {"M": 4}),
        ("parity", {"N": 5}, {"E": 0}),
        ("parity", {"N": 4}, {"E": 1}),
        ("skip_and_blocks", {}, {"X": 9, "Y": 10}),
        ("precedence", {}, {"A": 7, "B": 9, "C": 5, "D": 1}),
        ("divmod", {"X": -7, "Y": 2}, {"Q": -4, "M": 1}),
    ],
)
def test_examples(name: str, state: dict[str, int], expected: dict[str, int]) -> None:
    result = run(program(name), state)
    for key, value in expected.items():
        assert result.state[key] == value


def test_input_state_is_not_mutated() -> None:
    state = {"X": 2, "Y": 3}
    run(program("power"), state)
    assert state == {"X": 2, "Y": 3}


def test_step_limit() -> None:
    with pytest.raises(StepLimitExceeded) as info:
        run(program("infinite_loop"), {}, max_steps=500)
    assert info.value.span is not None
    assert info.value.code == "STEP_LIMIT"


def test_invalid_step_limit() -> None:
    with pytest.raises(ValueError):
        Interpreter(max_steps=0)


def test_undefined_variable_has_span() -> None:
    with pytest.raises(UndefinedVariableError) as info:
        run(parse("begin\n  R := Z + 1\nend"), {})
    assert info.value.span is not None
    assert (info.value.span.line, info.value.span.column) == (2, 8)


def test_division_by_zero() -> None:
    with pytest.raises(DivisionByZeroError):
        run(program("divmod"), {"X": 1, "Y": 0})


def test_or_evaluates_both_operands_like_superposition() -> None:
    with pytest.raises(UndefinedVariableError):
        run(parse("begin if 1 = 1 or Z = 0 then X := 1 else X := 2 end"), {})


def test_trace_events() -> None:
    recorder = TraceRecorder()
    result = run(program("power"), {"X": 5, "Y": 2}, listeners=[recorder])
    kinds = [event.kind for event in recorder.events]
    assert kinds[0] == "start"
    assert kinds[-1] == "finish"
    assert set(kinds) <= set(EVENT_KINDS)
    changes = [(e.data["name"], e.data["old"], e.data["new"]) for e in recorder.events if e.kind == "variable_changed"]
    assert changes == [("R", None, 1), ("R", 1, 5), ("Y", 2, 1), ("R", 5, 25), ("Y", 1, 0)]
    checks = [e.data["value"] for e in recorder.events if e.kind == "condition_checked"]
    assert checks == [True, True, False]
    befores = [e for e in recorder.events if e.kind == "before_statement"]
    afters = [e for e in recorder.events if e.kind == "after_statement"]
    assert len(befores) == len(afters)
    assert all(e.span is not None for e in befores)
    assert recorder.events[-1].state == result.state
    assert [e.index for e in recorder.events] == list(range(len(recorder.events)))


def test_trace_serialization_and_format() -> None:
    recorder = TraceRecorder()
    run(program("max"), {"X": 1, "Y": 2}, listeners=[recorder])
    data = recorder.to_list()
    assert data[0]["kind"] == "start"
    assert {"index", "step", "kind", "node", "text", "span", "state", "data"} <= set(data[1])
    lines = [e.format() for e in recorder.events]
    assert any("condition_checked" in line and "false" in line for line in lines)
    assert any("M: None -> 2" in line for line in lines)


def test_error_event_is_emitted() -> None:
    recorder = TraceRecorder()
    with pytest.raises(UndefinedVariableError):
        run(parse("begin X := Y end"), {}, listeners=[recorder])
    assert recorder.events[-1].kind == "error"
    assert recorder.events[-1].data["code"] == "UNDEFINED_VARIABLE"
    assert "UNDEFINED_VARIABLE" in recorder.events[-1].format()
