from __future__ import annotations

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
    Node,
    Not,
    Num,
    Program,
    Seq,
    Skip,
    Stmt,
    Var,
    While,
)

_ARITH_PRECEDENCE = {"+": 1, "-": 1, "*": 2, "div": 2, "mod": 2}
_BOOL_PRECEDENCE = {"or": 1, "and": 2}


def format_aexpr(expr: AExpr, parent: int = 0, right_side: bool = False) -> str:
    if isinstance(expr, Num):
        return str(expr.value)
    if isinstance(expr, Var):
        return expr.name
    precedence = _ARITH_PRECEDENCE[expr.op]
    text = f"{format_aexpr(expr.left, precedence)} {expr.op} {format_aexpr(expr.right, precedence, True)}"
    if precedence < parent or (right_side and precedence == parent):
        return f"({text})"
    return text


def format_bexpr(expr: BExpr, parent: int = 0, right_side: bool = False) -> str:
    if isinstance(expr, BoolConst):
        return "true" if expr.value else "false"
    if isinstance(expr, Compare):
        return f"{format_aexpr(expr.left)} {expr.op} {format_aexpr(expr.right)}"
    if isinstance(expr, Not):
        inner = format_bexpr(expr.operand, 3)
        if isinstance(expr.operand, Compare):
            inner = f"({inner})"
        return f"not {inner}"
    precedence = _BOOL_PRECEDENCE[expr.op]
    text = f"{format_bexpr(expr.left, precedence)} {expr.op} {format_bexpr(expr.right, precedence, True)}"
    if precedence < parent or (right_side and precedence == parent):
        return f"({text})"
    return text


def format_stmt_inline(stmt: Stmt) -> str:
    if isinstance(stmt, Assign):
        return f"{stmt.target} := {format_aexpr(stmt.expr)}"
    if isinstance(stmt, Skip):
        return "skip"
    if isinstance(stmt, Seq):
        return "; ".join(format_stmt_inline(s) for s in stmt.statements)
    if isinstance(stmt, Block):
        return f"begin {format_stmt_inline(stmt.body)} end"
    if isinstance(stmt, If):
        return (
            f"if {format_bexpr(stmt.cond)} then {format_stmt_inline(stmt.then_branch)} "
            f"else {format_stmt_inline(stmt.else_branch)}"
        )
    return f"while {format_bexpr(stmt.cond)} do {format_stmt_inline(stmt.body)}"


def format_header(stmt: Stmt) -> str:
    if isinstance(stmt, If):
        return f"if {format_bexpr(stmt.cond)} then …"
    if isinstance(stmt, While):
        return f"while {format_bexpr(stmt.cond)} do …"
    if isinstance(stmt, Block):
        return "begin … end"
    if isinstance(stmt, Seq):
        return f"{len(stmt.statements)} оператори через ';'"
    return format_stmt_inline(stmt)


def format_program(program: Program, indent: str = "  ") -> str:
    lines = ["begin"]
    _format_seq_lines(program.body, 1, indent, lines)
    lines.append("end")
    return "\n".join(lines) + "\n"


def _format_seq_lines(stmt: Stmt, level: int, indent: str, lines: list[str]) -> None:
    items = stmt.statements if isinstance(stmt, Seq) else (stmt,)
    for index, item in enumerate(items):
        _format_stmt_lines(item, level, indent, lines)
        if index < len(items) - 1:
            lines[-1] += ";"


def _format_stmt_lines(stmt: Stmt, level: int, indent: str, lines: list[str]) -> None:
    pad = indent * level
    if isinstance(stmt, Block):
        lines.append(f"{pad}begin")
        _format_seq_lines(stmt.body, level + 1, indent, lines)
        lines.append(f"{pad}end")
    elif isinstance(stmt, If):
        lines.append(f"{pad}if {format_bexpr(stmt.cond)} then")
        _format_stmt_lines(stmt.then_branch, level + 1, indent, lines)
        lines.append(f"{pad}else")
        _format_stmt_lines(stmt.else_branch, level + 1, indent, lines)
    elif isinstance(stmt, While):
        lines.append(f"{pad}while {format_bexpr(stmt.cond)} do")
        _format_stmt_lines(stmt.body, level + 1, indent, lines)
    elif isinstance(stmt, Seq):
        lines.append(f"{pad}begin")
        _format_seq_lines(stmt, level + 1, indent, lines)
        lines.append(f"{pad}end")
    else:
        lines.append(pad + format_stmt_inline(stmt))


def describe(node: Node) -> str:
    if isinstance(node, Program):
        return "program"
    if isinstance(node, (Num, Var, BinOp)):
        return format_aexpr(node)
    if isinstance(node, (BoolConst, Compare, BoolOp, Not)):
        return format_bexpr(node)
    return format_header(node)
