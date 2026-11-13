from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from sipl.ast import (
    AExpr,
    Assign,
    BExpr,
    BinOp,
    Block,
    BoolConst,
    BoolOp,
    Compare,
    If,
    Not,
    Num,
    Program,
    Seq,
    Skip,
    SourceSpan,
    Stmt,
    Var,
    While,
)
from sipl.errors import SiplError, StepLimitExceeded, UndefinedVariableError
from sipl.interpreter.events import (
    AFTER_STATEMENT,
    BEFORE_STATEMENT,
    CONDITION_CHECKED,
    ERROR,
    FINISH,
    START,
    VARIABLE_CHANGED,
    Listener,
    TraceEvent,
)
from sipl.operations import apply_arith, apply_bool, apply_rel
from sipl.printer import describe, format_bexpr

DEFAULT_MAX_STEPS = 100_000

State = dict[str, int]


@dataclass(frozen=True)
class ExecutionResult:
    state: State
    steps: int

    def to_dict(self) -> dict[str, Any]:
        return {"state": dict(sorted(self.state.items())), "steps": self.steps}


class Interpreter:
    def __init__(
        self,
        max_steps: int = DEFAULT_MAX_STEPS,
        listeners: Iterable[Listener] = (),
    ) -> None:
        if max_steps <= 0:
            raise ValueError("max_steps має бути додатним")
        self.max_steps = max_steps
        self.listeners = list(listeners)
        self.steps = 0
        self._event_index = 0
        self._state: State = {}

    def run(self, program: Program, state: Mapping[str, int] | None = None) -> ExecutionResult:
        self.steps = 0
        self._event_index = 0
        self._state = dict(state or {})
        self._emit(START, None, None, None)
        try:
            self.exec_stmt(program.body)
        except SiplError as error:
            self._emit(
                ERROR,
                None,
                None,
                error.span,
                {"code": error.code, "message": error.message},
            )
            raise
        self._emit(FINISH, None, None, program.span)
        return ExecutionResult(dict(self._state), self.steps)

    def _emit(
        self,
        kind: str,
        node: str | None,
        text: str | None,
        span: SourceSpan | None,
        data: dict[str, Any] | None = None,
    ) -> None:
        if not self.listeners:
            return
        event = TraceEvent(
            index=self._event_index,
            step=self.steps,
            kind=kind,
            node=node,
            text=text,
            span=span,
            state=dict(self._state),
            data=data or {},
        )
        self._event_index += 1
        for listener in self.listeners:
            listener(event)

    def _tick(self, span: SourceSpan | None) -> None:
        self.steps += 1
        if self.steps > self.max_steps:
            raise StepLimitExceeded(
                f"Перевищено ліміт кроків ({self.max_steps}); можливо, цикл не завершується",
                span,
            )

    def exec_stmt(self, stmt: Stmt) -> None:
        if isinstance(stmt, Seq):
            for item in stmt.statements:
                self.exec_stmt(item)
            return
        if isinstance(stmt, Block):
            self.exec_stmt(stmt.body)
            return
        self._tick(stmt.span)
        name = type(stmt).__name__
        self._emit(BEFORE_STATEMENT, name, describe(stmt), stmt.span)
        if isinstance(stmt, Assign):
            old = self._state.get(stmt.target)
            value = self.eval_aexpr(stmt.expr)
            self._state[stmt.target] = value
            self._emit(
                VARIABLE_CHANGED,
                name,
                describe(stmt),
                stmt.span,
                {"name": stmt.target, "old": old, "new": value},
            )
        elif isinstance(stmt, Skip):
            pass
        elif isinstance(stmt, If):
            branch = self._check(stmt.cond, "if")
            self.exec_stmt(stmt.then_branch if branch else stmt.else_branch)
        elif isinstance(stmt, While):
            iteration = 0
            while self._check(stmt.cond, "while", iteration):
                iteration += 1
                self.exec_stmt(stmt.body)
                self._tick(stmt.span)
        self._emit(AFTER_STATEMENT, name, describe(stmt), stmt.span)

    def _check(self, cond: BExpr, owner: str, iteration: int | None = None) -> bool:
        value = self.eval_bexpr(cond)
        data: dict[str, Any] = {"value": value, "owner": owner}
        if iteration is not None:
            data["iteration"] = iteration
        self._emit(CONDITION_CHECKED, type(cond).__name__, format_bexpr(cond), cond.span, data)
        return value

    def eval_aexpr(self, expr: AExpr) -> int:
        if isinstance(expr, Num):
            return expr.value
        if isinstance(expr, Var):
            if expr.name not in self._state:
                raise UndefinedVariableError(
                    f"Змінна {expr.name} не має значення в поточному стані "
                    f"(функція розіменування {expr.name}⇒ не визначена)",
                    expr.span,
                )
            return self._state[expr.name]
        if isinstance(expr, BinOp):
            left = self.eval_aexpr(expr.left)
            right = self.eval_aexpr(expr.right)
            return apply_arith(expr.op, left, right, expr.span)
        raise TypeError(f"Unknown arithmetic node {expr!r}")

    def eval_bexpr(self, expr: BExpr) -> bool:
        if isinstance(expr, BoolConst):
            return expr.value
        if isinstance(expr, Compare):
            left = self.eval_aexpr(expr.left)
            right = self.eval_aexpr(expr.right)
            return apply_rel(expr.op, left, right, expr.span)
        if isinstance(expr, Not):
            return not self.eval_bexpr(expr.operand)
        if isinstance(expr, BoolOp):
            left = self.eval_bexpr(expr.left)
            right = self.eval_bexpr(expr.right)
            return apply_bool(expr.op, left, right, expr.span)
        raise TypeError(f"Unknown boolean node {expr!r}")


def run(
    program: Program,
    state: Mapping[str, int] | None = None,
    max_steps: int = DEFAULT_MAX_STEPS,
    listeners: Iterable[Listener] = (),
) -> ExecutionResult:
    return Interpreter(max_steps, listeners).run(program, state)
