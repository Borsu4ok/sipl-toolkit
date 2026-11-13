from __future__ import annotations

from sipl.ast import SourceSpan
from sipl.errors import DivisionByZeroError, SiplRuntimeError

ARITH_FUNCTIONS = {
    "+": "add",
    "-": "sub",
    "*": "mult",
    "div": "div",
    "mod": "mod",
}

REL_FUNCTIONS = {
    "=": "eq",
    ">": "gr",
    ">=": "gre",
    "<": "ls",
    "<=": "lse",
    "!=": "neq",
}

BOOL_FUNCTIONS = {
    "or": "or",
    "and": "and",
    "not": "neg",
}

EXTENSION_OPERATORS = frozenset({"div", "mod", ">=", "<", "<=", "!=", "and"})


def apply_arith(op: str, left: int, right: int, span: SourceSpan | None = None) -> int:
    if op == "+":
        return left + right
    if op == "-":
        return left - right
    if op == "*":
        return left * right
    if op in ("div", "mod"):
        if right == 0:
            raise DivisionByZeroError(f"Ділення на нуль в операції {op}", span)
        quotient, remainder = divmod(left, right)
        return quotient if op == "div" else remainder
    raise SiplRuntimeError(f"Невідома арифметична операція {op}", span)


def apply_rel(op: str, left: int, right: int, span: SourceSpan | None = None) -> bool:
    if op == "=":
        return left == right
    if op == ">":
        return left > right
    if op == ">=":
        return left >= right
    if op == "<":
        return left < right
    if op == "<=":
        return left <= right
    if op == "!=":
        return left != right
    raise SiplRuntimeError(f"Невідома операція порівняння {op}", span)


def apply_bool(op: str, left: bool, right: bool, span: SourceSpan | None = None) -> bool:
    if op == "or":
        return left or right
    if op == "and":
        return left and right
    raise SiplRuntimeError(f"Невідома логічна операція {op}", span)


def function_name(op: str) -> str:
    for table in (ARITH_FUNCTIONS, REL_FUNCTIONS, BOOL_FUNCTIONS):
        if op in table:
            return table[op]
    raise KeyError(op)


def format_state(state: dict[str, int]) -> str:
    if not state:
        return "[]"
    return "[" + ", ".join(f"{name} ↦ {state[name]}" for name in sorted(state)) + "]"
