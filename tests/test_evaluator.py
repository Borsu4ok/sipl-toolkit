from __future__ import annotations

from pathlib import Path

import pytest

from conftest import EXAMPLES, VALID
from sipl.errors import SiplRuntimeError
from sipl.interpreter import run
from sipl.parser import parse
from sipl.semantics import IF, Comp, Const, Deref, build_term, evaluate
from sipl.semantics.evaluator import TermEvaluator

STATES = {
    "power": {"X": 3, "Y": 4},
    "geometric_sum_3": {"N": 4},
    "geometric_sum_2": {"N": 4},
    "division": {"X": 17, "Y": 5},
    "factorial": {"N": 6},
    "fibonacci": {"N": 7},
    "gcd": {"A": 21, "B": 14},
    "max": {"X": 1, "Y": -1},
    "parity": {"N": 7},
    "skip_and_blocks": {},
    "precedence": {},
    "divmod": {"X": 17, "Y": 5},
}


def load(name: str):
    return parse((EXAMPLES / "valid" / f"{name}.sipl").read_text(encoding="utf-8"))


def test_practicum_example_power() -> None:
    result = evaluate(build_term(load("power")), {"X": 5, "Y": 2})
    assert result.defined
    assert result.state == {"X": 5, "Y": 0, "R": 25}
    rules = [s.rule for s in result.steps]
    assert rules[0] == "INIT" and rules[-1] == "RESULT"
    assert rules.count("AF_WH") == 3
    assert rules.count("AF_AS") == 5
    texts = [s.text for s in result.steps if s.rule == "AF_WH"]
    assert "gr(2, 0) = true" in texts[0]
    assert "gr(0, 0) = false" in texts[-1]


def test_variant_19() -> None:
    result = evaluate(build_term(load("geometric_sum_3")), {"N": 3})
    assert result.state is not None and result.state["S"] == 40


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.stem)
def test_term_semantics_agrees_with_interpreter(path: Path) -> None:
    if path.stem not in STATES:
        pytest.skip("program without terminating input")
    program = parse(path.read_text(encoding="utf-8"))
    state = STATES[path.stem]
    operational = run(program, state).state
    denotational = evaluate(build_term(program), state)
    assert denotational.defined
    assert denotational.state == operational


def test_undefined_variable_makes_result_undefined() -> None:
    result = evaluate(build_term(load("power")), {"X": 2})
    assert not result.defined
    assert result.state is None
    assert result.code == "UNDEFINED_VARIABLE"
    assert "Y ∉ dom(st)" in (result.reason or "")
    assert result.to_dict()["defined"] is False


def test_nonterminating_loop_is_undefined() -> None:
    result = evaluate(build_term(load("infinite_loop")), {}, max_steps=200)
    assert not result.defined
    assert result.code == "STEP_LIMIT"


def test_division_by_zero_is_undefined() -> None:
    result = evaluate(build_term(load("divmod")), {"X": 3, "Y": 0})
    assert not result.defined
    assert result.code == "DIVISION_BY_ZERO"


def test_if_rule_and_identity() -> None:
    term = build_term(parse("begin if X > 0 then skip else X := 0 end"))
    result = evaluate(term, {"X": 5})
    assert [s.rule for s in result.steps] == ["INIT", "AF_IF", "AF_ID", "RESULT"]
    assert result.steps[1].format().startswith("AF_IF:")
    other = evaluate(term, {"X": -5})
    assert other.state == {"X": 0}


def test_value_term_is_not_applicable_to_state() -> None:
    result = evaluate(IF(Const(True), Deref("X"), Deref("X")), {"X": 1})
    assert not result.defined
    with pytest.raises(SiplRuntimeError):
        TermEvaluator().value(Comp(()), {})
