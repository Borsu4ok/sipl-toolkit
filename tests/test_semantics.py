from __future__ import annotations

from pathlib import Path

import pytest

from conftest import EXAMPLES, GOLDEN, VALID
from sipl.parser import parse
from sipl.semantics import (
    AS,
    ASCII,
    LATEX,
    PLAIN,
    WH,
    Comp,
    Const,
    Deref,
    Group,
    Sup,
    build_term,
    build_term_with_steps,
    render,
    term_to_dict,
)

PRACTICUM_POWER = "AS^R(1) · WH(S^2(gr, Y⇒, 0), AS^R(S^2(mult, R⇒, X⇒)) · AS^Y(S^2(sub, Y⇒, 1)))"
PRACTICUM_DIVISION = "AS^R(0) · WH(S^2(gre, X⇒, Y⇒), AS^X(S^2(sub, X⇒, Y⇒)) · AS^R(S^2(add, R⇒, 1)))"


def term_of(name: str):
    return build_term(parse((EXAMPLES / "valid" / f"{name}.sipl").read_text(encoding="utf-8")))


def test_power_term_matches_practicum() -> None:
    assert render(term_of("power"), PLAIN) == PRACTICUM_POWER


def test_division_term_matches_practicum() -> None:
    assert render(term_of("division"), PLAIN) == PRACTICUM_DIVISION


def test_power_term_structure() -> None:
    term = term_of("power")
    assert term == Comp(
        (
            AS("R", Const(1)),
            WH(
                Sup("gr", (Deref("Y"), Const(0))),
                Group(
                    Comp(
                        (
                            AS("R", Sup("mult", (Deref("R"), Deref("X")))),
                            AS("Y", Sup("sub", (Deref("Y"), Const(1)))),
                        )
                    )
                ),
            ),
        )
    )


@pytest.mark.parametrize("path", VALID, ids=lambda p: p.stem)
def test_golden_terms(path: Path) -> None:
    expected = (GOLDEN / f"{path.stem}.term").read_text(encoding="utf-8").strip()
    assert render(build_term(parse(path.read_text(encoding="utf-8"))), PLAIN) == expected


def test_all_constructs() -> None:
    source = "begin skip; if not (X = 1) or true and X > 0 then X := 1 else begin X := 2; Y := 3 end end"
    term = build_term(parse(source))
    assert render(term, PLAIN) == (
        "id · IF(S^2(or, S^1(neg, S^2(eq, X⇒, 1)), S^2(and, true, S^2(gr, X⇒, 0))), AS^X(1), AS^X(2) · AS^Y(3))"
    )


def test_block_inside_composition_keeps_parentheses() -> None:
    term = build_term(parse("begin X := 1; begin Y := 2; Z := 3 end; skip end"))
    assert render(term, PLAIN) == "AS^X(1) · (AS^Y(2) · AS^Z(3)) · id"


def test_styles() -> None:
    term = term_of("power")
    assert "1̅" in render(term)
    assert render(term, ASCII).startswith("AS^R(1) . WH(S^2(gr, Y=>, 0)")
    latex = render(term, LATEX)
    assert latex.startswith("AS^{R}(\\overline{1}) \\cdot \\mathit{WH}")


def test_derivation_steps_follow_course_rules() -> None:
    _, steps = build_term_with_steps(parse((EXAMPLES / "valid" / "power.sipl").read_text(encoding="utf-8")))
    rules = [s.rule for s in steps]
    assert rules[:3] == ["NS_Prog", "NS_Stm_Seq", "NS_Stm_As"]
    assert {"NS_Stm_Wh", "NS_B_gr", "NS_Stm_BE", "NS_A_Mult", "NS_A_Sub", "NS_A_Var", "NS_A_Num"} <= set(rules)
    assert steps[0].depth == 0 and steps[1].depth == 1
    assert render(steps[0].term, PLAIN) == PRACTICUM_POWER
    assert steps[2].format(PLAIN) == "    NS_Stm_As: sem_S(R := 1) = AS^R(1)"
    assert steps[2].to_dict(PLAIN)["span"]["line"] == 2


def test_term_to_dict() -> None:
    data = term_to_dict(term_of("power"))
    assert data["type"] == "Comp"
    assert data["parts"][1]["type"] == "WH"
    assert data["parts"][1]["cond"] == {
        "type": "Sup",
        "arity": 2,
        "function": "gr",
        "args": [{"type": "Deref", "name": "Y"}, {"type": "Const", "value": 0}],
    }
