from __future__ import annotations

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
from sipl.operations import function_name
from sipl.printer import format_aexpr, format_bexpr, format_stmt_inline
from sipl.semantics.render import UNICODE, Style, render
from sipl.semantics.terms import AS, IF, WH, Comp, Const, Deref, Group, Id, Sup, Term

ARITH_RULES = {"+": "NS_A_Add", "-": "NS_A_Sub", "*": "NS_A_Mult", "div": "NS_A_Div", "mod": "NS_A_Mod"}
REL_RULES = {
    "=": "NS_B_eq",
    ">": "NS_B_gr",
    ">=": "NS_B_gre",
    "<": "NS_B_ls",
    "<=": "NS_B_lse",
    "!=": "NS_B_neq",
}
BOOL_RULES = {"or": "NS_B_or", "and": "NS_B_and"}


@dataclass(frozen=True)
class DerivationStep:
    depth: int
    rule: str
    function: str
    source: str
    term: Term
    span: SourceSpan | None

    def format(self, style: Style = UNICODE) -> str:
        indent = "  " * self.depth
        return f"{indent}{self.rule}: {self.function}({self.source}) = {render(self.term, style)}"

    def to_dict(self, style: Style = UNICODE) -> dict[str, Any]:
        return {
            "depth": self.depth,
            "rule": self.rule,
            "function": self.function,
            "source": self.source,
            "term": render(self.term, style),
            "span": self.span.to_dict() if self.span else None,
        }


class TermBuilder:
    def __init__(self) -> None:
        self.steps: list[DerivationStep] = []
        self._depth = 0

    def _record(self, rule: str, function: str, source: str, span: SourceSpan | None) -> int:
        self.steps.append(DerivationStep(self._depth, rule, function, source, Id(), span))
        self._depth += 1
        return len(self.steps) - 1

    def _finish(self, index: int, term: Term) -> Term:
        self._depth -= 1
        old = self.steps[index]
        self.steps[index] = DerivationStep(old.depth, old.rule, old.function, old.source, term, old.span)
        return term

    def program(self, program: Program) -> Term:
        index = self._record("NS_Prog", "sem_P", "begin " + format_stmt_inline(program.body) + " end", program.span)
        return self._finish(index, self.stmt(program.body))

    def stmt(self, stmt: Stmt) -> Term:
        source = format_stmt_inline(stmt)
        if isinstance(stmt, Assign):
            index = self._record("NS_Stm_As", "sem_S", source, stmt.span)
            return self._finish(index, AS(stmt.target, self.aexpr(stmt.expr)))
        if isinstance(stmt, Seq):
            index = self._record("NS_Stm_Seq", "sem_S", source, stmt.span)
            return self._finish(index, Comp(tuple(self.stmt(s) for s in stmt.statements)))
        if isinstance(stmt, If):
            index = self._record("NS_Stm_If", "sem_S", source, stmt.span)
            term = IF(self.bexpr(stmt.cond), self.stmt(stmt.then_branch), self.stmt(stmt.else_branch))
            return self._finish(index, term)
        if isinstance(stmt, While):
            index = self._record("NS_Stm_Wh", "sem_S", source, stmt.span)
            return self._finish(index, WH(self.bexpr(stmt.cond), self.stmt(stmt.body)))
        if isinstance(stmt, Block):
            index = self._record("NS_Stm_BE", "sem_S", source, stmt.span)
            return self._finish(index, Group(self.stmt(stmt.body)))
        if isinstance(stmt, Skip):
            index = self._record("NS_Stm_skip", "sem_S", source, stmt.span)
            return self._finish(index, Id())
        raise TypeError(f"Unknown statement {stmt!r}")

    def aexpr(self, expr: AExpr) -> Term:
        source = format_aexpr(expr)
        if isinstance(expr, Num):
            index = self._record("NS_A_Num", "sem_A", source, expr.span)
            return self._finish(index, Const(expr.value))
        if isinstance(expr, Var):
            index = self._record("NS_A_Var", "sem_A", source, expr.span)
            return self._finish(index, Deref(expr.name))
        if isinstance(expr, BinOp):
            index = self._record(ARITH_RULES[expr.op], "sem_A", source, expr.span)
            term = Sup(function_name(expr.op), (self.aexpr(expr.left), self.aexpr(expr.right)))
            return self._finish(index, term)
        raise TypeError(f"Unknown arithmetic node {expr!r}")

    def bexpr(self, expr: BExpr) -> Term:
        source = format_bexpr(expr)
        if isinstance(expr, BoolConst):
            index = self._record("NS_B_const", "sem_B", source, expr.span)
            return self._finish(index, Const(expr.value))
        if isinstance(expr, Compare):
            index = self._record(REL_RULES[expr.op], "sem_B", source, expr.span)
            term = Sup(function_name(expr.op), (self.aexpr(expr.left), self.aexpr(expr.right)))
            return self._finish(index, term)
        if isinstance(expr, BoolOp):
            index = self._record(BOOL_RULES[expr.op], "sem_B", source, expr.span)
            term = Sup(function_name(expr.op), (self.bexpr(expr.left), self.bexpr(expr.right)))
            return self._finish(index, term)
        if isinstance(expr, Not):
            index = self._record("NS_B_neg", "sem_B", source, expr.span)
            return self._finish(index, Sup("neg", (self.bexpr(expr.operand),)))
        raise TypeError(f"Unknown boolean node {expr!r}")


def build_term(program: Program) -> Term:
    return TermBuilder().program(program)


def build_term_with_steps(program: Program) -> tuple[Term, list[DerivationStep]]:
    builder = TermBuilder()
    term = builder.program(program)
    return term, builder.steps
