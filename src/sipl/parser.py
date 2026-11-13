from __future__ import annotations

import re
from collections.abc import Iterable
from functools import lru_cache
from importlib.resources import files

from lark import Lark, Token, Tree
from lark.exceptions import UnexpectedCharacters, UnexpectedEOF, UnexpectedInput, UnexpectedToken

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
from sipl.errors import SiplSyntaxError

TERMINAL_NAMES = {
    "BEGIN": "'begin'",
    "END": "'end'",
    "IF": "'if'",
    "THEN": "'then'",
    "ELSE": "'else'",
    "WHILE": "'while'",
    "DO": "'do'",
    "SKIP": "'skip'",
    "TRUE": "'true'",
    "FALSE": "'false'",
    "OR": "'or'",
    "AND": "'and'",
    "NOT": "'not'",
    "ASSIGN": "':='",
    "SEMI": "';'",
    "LPAR": "'('",
    "RPAR": "')'",
    "ADDOP": "'+' або '-'",
    "MULOP": "'*', 'div' або 'mod'",
    "RELOP": "оператор порівняння",
    "NAME": "ім'я змінної",
    "INT": "число",
}

OP_ALIASES = {
    "–": "-",
    "−": "-",
    "×": "*",
    "∗": "*",
    "≥": ">=",
    "≤": "<=",
    "≠": "!=",
    "∨": "or",
    "∧": "and",
    "¬": "not",
}


_LEXEME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|-?[0-9]+|:=|>=|<=|!=|\S")


def grammar_text() -> str:
    return files("sipl").joinpath("grammar/sipl.lark").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _lark() -> Lark:
    return Lark(
        grammar_text(),
        start="start",
        parser="earley",
        propagate_positions=True,
        keep_all_tokens=True,
    )


def _expected(names: Iterable[object] | None) -> str:
    if not names:
        return ""
    readable = sorted({TERMINAL_NAMES.get(str(n), str(n)) for n in names})
    return "; очікувалось: " + ", ".join(readable)


def _end_position(source: str) -> tuple[int, int]:
    lines = source.split("\n")
    return len(lines), len(lines[-1]) + 1


def _syntax_error(error: UnexpectedInput, source: str) -> SiplSyntaxError:
    if isinstance(error, UnexpectedEOF):
        line, column = _end_position(source)
        message = "Неочікуваний кінець програми" + _expected(error.expected)
        return SiplSyntaxError(message, SourceSpan(line, column, line, column))
    if isinstance(error, UnexpectedCharacters):
        line, column = error.line, error.column
        pos = error.pos_in_stream if error.pos_in_stream is not None else len(source)
        if pos >= len(source):
            message = "Неочікуваний кінець програми" + _expected(error.allowed)
            return SiplSyntaxError(message, SourceSpan(line, column, line, column))
        match = _LEXEME.match(source, pos)
        lexeme = match.group(0) if match else source[pos]
        expected = _expected(error.allowed) or "; очікувався кінець програми"
        message = f"Неочікуване {lexeme!r}" + expected
        return SiplSyntaxError(message, SourceSpan(line, column, line, column + len(lexeme)))
    if isinstance(error, UnexpectedToken):
        token = error.token
        if token.type == "$END":
            line, column = _end_position(source)
            return SiplSyntaxError(
                "Неочікуваний кінець програми" + _expected(error.expected),
                SourceSpan(line, column, line, column),
            )
        end_line = token.end_line or token.line or 1
        end_column = token.end_column or (token.column or 1) + 1
        return SiplSyntaxError(
            f"Неочікувана лексема {str(token)!r}" + _expected(error.expected),
            SourceSpan(token.line or 1, token.column or 1, end_line, end_column),
        )
    return SiplSyntaxError(str(error))


def parse_tree(source: str) -> Tree[Token]:
    if not source.strip():
        raise SiplSyntaxError("Порожня програма; очікувалось 'begin'", SourceSpan(1, 1, 1, 1))
    try:
        return _lark().parse(source)
    except UnexpectedInput as error:
        raise _syntax_error(error, source) from None


def parse(source: str) -> Program:
    return build_ast(parse_tree(source))


def build_ast(tree: Tree[Token]) -> Program:
    return _Builder().program(_subtrees(tree)[0] if tree.data == "start" else tree)


def tree_span(tree: Tree[Token]) -> SourceSpan | None:
    meta = tree.meta
    if getattr(meta, "empty", True):
        return None
    return SourceSpan(meta.line, meta.column, meta.end_line, meta.end_column)


def token_span(token: Token) -> SourceSpan:
    line = token.line or 1
    column = token.column or 1
    return SourceSpan(line, column, token.end_line or line, token.end_column or column + len(token))


def _subtrees(tree: Tree[Token]) -> list[Tree[Token]]:
    return [c for c in tree.children if isinstance(c, Tree)]


def _tokens(tree: Tree[Token]) -> list[Token]:
    return [c for c in tree.children if isinstance(c, Token)]


def _op(token: Token) -> str:
    return OP_ALIASES.get(str(token), str(token))


class _Builder:
    def program(self, tree: Tree[Token]) -> Program:
        return Program(self.seq(_subtrees(tree)[0]), tree_span(tree))

    def seq(self, tree: Tree[Token]) -> Stmt:
        items: list[Stmt] = []
        node = tree
        while True:
            subs = _subtrees(node)
            if len(subs) == 2:
                items.append(self.stmt(subs[1]))
                node = subs[0]
            else:
                items.append(self.stmt(subs[0]))
                break
        items.reverse()
        if len(items) == 1:
            return items[0]
        return Seq(tuple(items), tree_span(tree))

    def stmt(self, tree: Tree[Token]) -> Stmt:
        inner = _subtrees(tree)[0]
        span = tree_span(inner)
        subs = _subtrees(inner)
        kind = inner.data
        if kind == "assign":
            return Assign(self.name(subs[0]), self.aexpr(subs[1]), span)
        if kind == "if_stmt":
            return If(self.bexpr(subs[0]), self.stmt(subs[1]), self.stmt(subs[2]), span)
        if kind == "while_stmt":
            return While(self.bexpr(subs[0]), self.stmt(subs[1]), span)
        if kind == "block":
            return Block(self.seq(subs[0]), span)
        if kind == "skip_stmt":
            return Skip(span)
        raise SiplSyntaxError(f"Невідомий вид оператора: {kind}", span)

    def name(self, tree: Tree[Token]) -> str:
        return str(_tokens(tree)[0])

    def aexpr(self, tree: Tree[Token]) -> AExpr:
        subs = _subtrees(tree)
        span = tree_span(tree)
        if tree.data in ("aexpr", "term"):
            if len(subs) == 2:
                op = _op(_tokens(tree)[0])
                return BinOp(op, self.aexpr(subs[0]), self.aexpr(subs[1]), span)
            return self.aexpr(subs[0])
        if tree.data == "factor":
            return self.aexpr(subs[0])
        if tree.data == "num":
            return Num(int(str(_tokens(tree)[0])), span)
        if tree.data == "var":
            return Var(self.name(tree), span)
        raise SiplSyntaxError(f"Невідомий вид виразу: {tree.data}", span)

    def bexpr(self, tree: Tree[Token]) -> BExpr:
        subs = _subtrees(tree)
        toks = _tokens(tree)
        span = tree_span(tree)
        if tree.data in ("bexpr", "bterm"):
            if len(subs) == 2:
                return BoolOp(_op(toks[0]), self.bexpr(subs[0]), self.bexpr(subs[1]), span)
            return self.bexpr(subs[0])
        if tree.data == "bfactor":
            first = toks[0].type if toks and tree.children[0] is toks[0] else None
            if first == "NOT":
                return Not(self.bexpr(subs[0]), span)
            if first == "TRUE":
                return BoolConst(True, span)
            if first == "FALSE":
                return BoolConst(False, span)
            if first == "LPAR":
                return self.bexpr(subs[0])
            return Compare(_op(toks[0]), self.aexpr(subs[0]), self.aexpr(subs[1]), span)
        raise SiplSyntaxError(f"Невідомий вид умови: {tree.data}", span)
