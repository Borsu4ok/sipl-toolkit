from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Const:
    value: int | bool


@dataclass(frozen=True)
class Deref:
    name: str


@dataclass(frozen=True)
class Sup:
    function: str
    args: tuple[Term, ...]


@dataclass(frozen=True)
class AS:
    name: str
    arg: Term


@dataclass(frozen=True)
class Comp:
    parts: tuple[Term, ...]


@dataclass(frozen=True)
class Group:
    inner: Term


@dataclass(frozen=True)
class IF:
    cond: Term
    then_branch: Term
    else_branch: Term


@dataclass(frozen=True)
class WH:
    cond: Term
    body: Term


@dataclass(frozen=True)
class Id:
    pass


Term = Const | Deref | Sup | AS | Comp | Group | IF | WH | Id


def strip_groups(term: Term) -> Term:
    while isinstance(term, Group):
        term = term.inner
    return term


def term_to_dict(term: Term) -> dict[str, Any]:
    if isinstance(term, Const):
        return {"type": "Const", "value": term.value}
    if isinstance(term, Deref):
        return {"type": "Deref", "name": term.name}
    if isinstance(term, Sup):
        return {
            "type": "Sup",
            "arity": len(term.args),
            "function": term.function,
            "args": [term_to_dict(a) for a in term.args],
        }
    if isinstance(term, AS):
        return {"type": "AS", "name": term.name, "arg": term_to_dict(term.arg)}
    if isinstance(term, Comp):
        return {"type": "Comp", "parts": [term_to_dict(p) for p in term.parts]}
    if isinstance(term, Group):
        return {"type": "Group", "inner": term_to_dict(term.inner)}
    if isinstance(term, IF):
        return {
            "type": "IF",
            "cond": term_to_dict(term.cond),
            "then": term_to_dict(term.then_branch),
            "else": term_to_dict(term.else_branch),
        }
    if isinstance(term, WH):
        return {"type": "WH", "cond": term_to_dict(term.cond), "body": term_to_dict(term.body)}
    return {"type": "Id"}
