from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from sipl.errors import DivisionByZeroError, SiplError, SiplRuntimeError, StepLimitExceeded, UndefinedVariableError
from sipl.operations import format_state
from sipl.semantics.render import UNICODE, Style, render
from sipl.semantics.terms import AS, IF, WH, Comp, Const, Deref, Group, Id, Sup, Term

DEFAULT_MAX_STEPS = 10_000

_ARITH = {
    "add": lambda a, b: a + b,
    "sub": lambda a, b: a - b,
    "mult": lambda a, b: a * b,
}
_REL = {
    "eq": lambda a, b: a == b,
    "gr": lambda a, b: a > b,
    "gre": lambda a, b: a >= b,
    "ls": lambda a, b: a < b,
    "lse": lambda a, b: a <= b,
    "neq": lambda a, b: a != b,
}
_BOOL = {
    "or": lambda a, b: a or b,
    "and": lambda a, b: a and b,
}


@dataclass(frozen=True)
class RuleApplication:
    depth: int
    rule: str
    text: str
    state: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {"depth": self.depth, "rule": self.rule, "text": self.text, "state": dict(self.state)}

    def format(self) -> str:
        return f"{'  ' * self.depth}{self.rule}: {self.text}"


@dataclass
class EvaluationResult:
    defined: bool
    state: dict[str, int] | None
    reason: str | None = None
    code: str | None = None
    steps: list[RuleApplication] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "defined": self.defined,
            "state": dict(sorted(self.state.items())) if self.state is not None else None,
            "reason": self.reason,
            "code": self.code,
            "rules": [s.to_dict() for s in self.steps],
        }


class TermEvaluator:
    def __init__(self, max_steps: int = DEFAULT_MAX_STEPS, style: Style = UNICODE) -> None:
        self.max_steps = max_steps
        self.style = style
        self.steps: list[RuleApplication] = []
        self._applications = 0
        self._state_counter = 0
        self._depth = 0

    def _new_state_name(self) -> str:
        name = f"st{self._state_counter}"
        self._state_counter += 1
        return name

    def _log(self, rule: str, text: str, state: dict[str, int]) -> None:
        self.steps.append(RuleApplication(self._depth, rule, text, dict(state)))

    def _tick(self) -> None:
        self._applications += 1
        if self._applications > self.max_steps:
            raise StepLimitExceeded(
                f"Перевищено ліміт застосувань правил ({self.max_steps}); "
                "значення WH на цьому стані вважаємо невизначеним"
            )

    def r(self, term: Term) -> str:
        return render(term, self.style)

    def evaluate(self, term: Term, state: Mapping[str, int]) -> EvaluationResult:
        self.steps = []
        self._applications = 0
        self._state_counter = 0
        st = dict(state)
        name = self._new_state_name()
        self._log("INIT", f"{name} = {format_state(st)}", st)
        try:
            final, final_name = self.apply(term, st, name)
        except SiplError as error:
            self._log("UNDEFINED", error.message, st)
            return EvaluationResult(False, None, error.message, error.code, self.steps)
        self._log("RESULT", f"{final_name} = {format_state(final)}", final)
        return EvaluationResult(True, final, None, None, self.steps)

    def apply(self, term: Term, st: dict[str, int], name: str) -> tuple[dict[str, int], str]:
        if isinstance(term, Group):
            return self.apply(term.inner, st, name)
        if isinstance(term, Id):
            self._tick()
            self._log("AF_ID", f"id({name}) = {name}", st)
            return st, name
        if isinstance(term, AS):
            self._tick()
            value, explanation = self.explain(term.arg, st, name)
            new_state = dict(st)
            new_state[term.name] = value
            new_name = self._new_state_name()
            self._log(
                "AF_AS",
                f"{self.r(term)}({name}) = {name}∇[{term.name} ↦ {explanation}] = "
                f"{format_state(new_state)} = {new_name}",
                new_state,
            )
            return new_state, new_name
        if isinstance(term, Comp):
            self._tick()
            self._log(
                "AF_SEQ",
                f"({self.r(term)})({name}): композиція з {len(term.parts)} функцій, застосовуємо зліва направо",
                st,
            )
            self._depth += 1
            current, current_name = st, name
            for part in term.parts:
                current, current_name = self.apply(part, current, current_name)
            self._depth -= 1
            return current, current_name
        if isinstance(term, IF):
            self._tick()
            value, explanation = self.explain(term.cond, st, name)
            branch = "перша (then)" if value else "друга (else)"
            self._log("AF_IF", f"{self.r(term.cond)}({name}) = {explanation} ⇒ виконуємо {branch} гілку", st)
            self._depth += 1
            result = self.apply(term.then_branch if value else term.else_branch, st, name)
            self._depth -= 1
            return result
        if isinstance(term, WH):
            iteration = 0
            current, current_name = st, name
            while True:
                self._tick()
                value, explanation = self.explain(term.cond, current, current_name)
                if not value:
                    self._log(
                        "AF_WH",
                        f"{self.r(term.cond)}({current_name}) = {explanation} ⇒ цикл завершено "
                        f"після {iteration} ітерацій, результат {current_name}",
                        current,
                    )
                    return current, current_name
                iteration += 1
                self._log(
                    "AF_WH",
                    f"{self.r(term.cond)}({current_name}) = {explanation} ⇒ ітерація {iteration}",
                    current,
                )
                self._depth += 1
                current, current_name = self.apply(term.body, current, current_name)
                self._depth -= 1
        raise SiplRuntimeError(f"Терм {self.r(term)} не є біномінативною функцією (не застосовний до стану)")

    def value(self, term: Term, st: dict[str, int]) -> Any:
        if isinstance(term, Const):
            return term.value
        if isinstance(term, Deref):
            if term.name not in st:
                raise UndefinedVariableError(
                    f"{term.name}⇒ не визначена на стані {format_state(st)}: {term.name} ∉ dom(st)"
                )
            return st[term.name]
        if isinstance(term, Sup):
            args = [self.value(a, st) for a in term.args]
            return self.call(term.function, args)
        if isinstance(term, Group):
            return self.value(term.inner, st)
        raise SiplRuntimeError(f"Терм {self.r(term)} не є номінативною функцією-значенням")

    def call(self, function: str, args: list[Any]) -> Any:
        if function == "neg":
            return not args[0]
        if function in _ARITH:
            return _ARITH[function](*args)
        if function in ("div", "mod"):
            if args[1] == 0:
                raise DivisionByZeroError(f"{function}({args[0]}, 0) не визначена")
            q, m = divmod(args[0], args[1])
            return q if function == "div" else m
        if function in _REL:
            return _REL[function](*args)
        if function in _BOOL:
            return _BOOL[function](*args)
        raise SiplRuntimeError(f"Невідома базова функція {function}")

    def explain(self, term: Term, st: dict[str, int], name: str) -> tuple[Any, str]:
        result = self.value(term, st)
        shown = str(result).lower() if isinstance(result, bool) else str(result)
        if isinstance(term, Sup):
            args = [self.value(a, st) for a in term.args]
            shown_args = ", ".join(str(a).lower() if isinstance(a, bool) else str(a) for a in args)
            return result, f"{term.function}({shown_args}) = {shown}"
        if isinstance(term, Deref):
            return result, f"{name}({term.name}) = {shown}"
        return result, shown


def evaluate(
    term: Term,
    state: Mapping[str, int],
    max_steps: int = DEFAULT_MAX_STEPS,
    style: Style = UNICODE,
) -> EvaluationResult:
    return TermEvaluator(max_steps, style).evaluate(term, state)
