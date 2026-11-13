from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sipl.ast import SourceSpan

START = "start"
BEFORE_STATEMENT = "before_statement"
AFTER_STATEMENT = "after_statement"
VARIABLE_CHANGED = "variable_changed"
CONDITION_CHECKED = "condition_checked"
FINISH = "finish"
ERROR = "error"

EVENT_KINDS = (
    START,
    BEFORE_STATEMENT,
    AFTER_STATEMENT,
    VARIABLE_CHANGED,
    CONDITION_CHECKED,
    FINISH,
    ERROR,
)


@dataclass(frozen=True)
class TraceEvent:
    index: int
    step: int
    kind: str
    node: str | None = None
    text: str | None = None
    span: SourceSpan | None = None
    state: dict[str, int] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "step": self.step,
            "kind": self.kind,
            "node": self.node,
            "text": self.text,
            "span": self.span.to_dict() if self.span else None,
            "state": dict(self.state),
            "data": dict(self.data),
        }

    def format(self) -> str:
        where = f"[{self.span.line}:{self.span.column}]" if self.span else "[-]"
        head = f"#{self.index:<4} step={self.step:<4} {self.kind:<17} {where:<9}"
        if self.kind == VARIABLE_CHANGED:
            return f"{head} {self.data['name']}: {self.data['old']} -> {self.data['new']}"
        if self.kind == CONDITION_CHECKED:
            return f"{head} {self.text} = {str(self.data['value']).lower()}"
        if self.kind in (FINISH, START):
            return f"{head} {_state(self.state)}"
        if self.kind == ERROR:
            return f"{head} {self.data.get('code')}: {self.data.get('message')}"
        return f"{head} {self.text}"


Listener = Callable[[TraceEvent], None]


class TraceRecorder:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    def __call__(self, event: TraceEvent) -> None:
        self.events.append(event)

    def to_list(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self.events]


def _state(state: dict[str, int]) -> str:
    return "{" + ", ".join(f"{k}={state[k]}" for k in sorted(state)) + "}"
