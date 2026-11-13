from __future__ import annotations

from dataclasses import dataclass

from sipl.semantics.terms import AS, IF, WH, Comp, Const, Deref, Group, Id, Sup, Term

OVERLINE = "̅"


@dataclass(frozen=True)
class Style:
    name: str
    deref: str
    comp: str
    nabla: str

    def const(self, value: int | bool) -> str:
        text = str(value).lower() if isinstance(value, bool) else str(value)
        if self.name == "unicode":
            return "".join(ch + OVERLINE for ch in text)
        if self.name == "latex":
            return f"\\overline{{{text}}}"
        return text

    def sup(self, arity: int) -> str:
        if self.name == "latex":
            return f"S^{{{arity}}}"
        return f"S^{arity}"

    def assign(self, name: str) -> str:
        if self.name == "latex":
            return f"AS^{{{name}}}"
        return f"AS^{name}"

    def keyword(self, word: str) -> str:
        if self.name == "latex":
            return f"\\mathit{{{word}}}"
        return word


UNICODE = Style("unicode", "⇒", " · ", "∇")
PLAIN = Style("plain", "⇒", " · ", "∇")
ASCII = Style("ascii", "=>", " . ", "#")
LATEX = Style("latex", "\\Rightarrow", " \\cdot ", "\\nabla")

STYLES = {"unicode": UNICODE, "plain": PLAIN, "ascii": ASCII, "latex": LATEX}


def render(term: Term, style: Style = UNICODE, in_comp: bool = False) -> str:
    if isinstance(term, Const):
        return style.const(term.value)
    if isinstance(term, Deref):
        return f"{term.name}{style.deref}"
    if isinstance(term, Sup):
        args = ", ".join(render(a, style) for a in term.args)
        return f"{style.sup(len(term.args))}({style.keyword(term.function)}, {args})"
    if isinstance(term, AS):
        return f"{style.assign(term.name)}({render(term.arg, style)})"
    if isinstance(term, Comp):
        return style.comp.join(render(p, style, True) for p in term.parts)
    if isinstance(term, Group):
        inner = render(term.inner, style, in_comp)
        if in_comp and isinstance(term.inner, (Comp, Group)):
            return f"({inner})"
        return inner
    if isinstance(term, IF):
        return (
            f"{style.keyword('IF')}({render(term.cond, style)}, "
            f"{render(term.then_branch, style)}, {render(term.else_branch, style)})"
        )
    if isinstance(term, WH):
        return f"{style.keyword('WH')}({render(term.cond, style)}, {render(term.body, style)})"
    if isinstance(term, Id):
        return style.keyword("id")
    raise TypeError(f"Unknown term {term!r}")
