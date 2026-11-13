from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any


@dataclass(frozen=True)
class SourceSpan:
    line: int
    column: int
    end_line: int
    end_column: int

    def to_dict(self) -> dict[str, int]:
        return {
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column,
        }

    def __str__(self) -> str:
        return f"{self.line}:{self.column}-{self.end_line}:{self.end_column}"

    def contains(self, line: int, column: int) -> bool:
        start = (self.line, self.column)
        end = (self.end_line, self.end_column)
        return start <= (line, column) < end


def _span() -> Any:
    return field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class Num:
    value: int
    span: SourceSpan | None = _span()


@dataclass(frozen=True)
class Var:
    name: str
    span: SourceSpan | None = _span()


@dataclass(frozen=True)
class BinOp:
    op: str
    left: AExpr
    right: AExpr
    span: SourceSpan | None = _span()


@dataclass(frozen=True)
class BoolConst:
    value: bool
    span: SourceSpan | None = _span()


@dataclass(frozen=True)
class Compare:
    op: str
    left: AExpr
    right: AExpr
    span: SourceSpan | None = _span()


@dataclass(frozen=True)
class BoolOp:
    op: str
    left: BExpr
    right: BExpr
    span: SourceSpan | None = _span()


@dataclass(frozen=True)
class Not:
    operand: BExpr
    span: SourceSpan | None = _span()


@dataclass(frozen=True)
class Assign:
    target: str
    expr: AExpr
    span: SourceSpan | None = _span()


@dataclass(frozen=True)
class Seq:
    statements: tuple[Stmt, ...]
    span: SourceSpan | None = _span()


@dataclass(frozen=True)
class If:
    cond: BExpr
    then_branch: Stmt
    else_branch: Stmt
    span: SourceSpan | None = _span()


@dataclass(frozen=True)
class While:
    cond: BExpr
    body: Stmt
    span: SourceSpan | None = _span()


@dataclass(frozen=True)
class Block:
    body: Stmt
    span: SourceSpan | None = _span()


@dataclass(frozen=True)
class Skip:
    span: SourceSpan | None = _span()


@dataclass(frozen=True)
class Program:
    body: Stmt
    span: SourceSpan | None = _span()


AExpr = Num | Var | BinOp
BExpr = BoolConst | Compare | BoolOp | Not
Stmt = Assign | Seq | If | While | Block | Skip
Node = AExpr | BExpr | Stmt | Program

ARITH_OPS = ("+", "-", "*", "div", "mod")
REL_OPS = ("=", ">", ">=", "<", "<=", "!=")
BOOL_OPS = ("or", "and")


def to_dict(node: Any) -> Any:
    if isinstance(node, tuple):
        return [to_dict(item) for item in node]
    if not hasattr(node, "__dataclass_fields__") or isinstance(node, SourceSpan):
        return node
    result: dict[str, Any] = {"type": type(node).__name__}
    for f in fields(node):
        value = getattr(node, f.name)
        if f.name == "span":
            result["span"] = value.to_dict() if value is not None else None
        else:
            result[f.name] = to_dict(value)
    return result


def children(node: Node) -> list[Node]:
    result: list[Node] = []
    for f in fields(node):
        if f.name == "span":
            continue
        value = getattr(node, f.name)
        if isinstance(value, tuple):
            result.extend(value)
        elif hasattr(value, "__dataclass_fields__"):
            result.append(value)
    return result


def walk(node: Node) -> list[Node]:
    result = [node]
    for child in children(node):
        result.extend(walk(child))
    return result


def variables(node: Node) -> set[str]:
    names: set[str] = set()
    for item in walk(node):
        if isinstance(item, Var):
            names.add(item.name)
        elif isinstance(item, Assign):
            names.add(item.target)
    return names
