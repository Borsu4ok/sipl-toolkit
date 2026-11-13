from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any

from lark import Token, Tree

from sipl.ast import Node, Program, SourceSpan, children
from sipl.parser import token_span, tree_span
from sipl.printer import describe

COURSE_NAMES = {
    "program": "<програма>",
    "seq": "<оператор>",
    "stmt": "<оператор>",
    "assign": "<оператор>",
    "if_stmt": "<оператор>",
    "while_stmt": "<оператор>",
    "block": "<оператор>",
    "skip_stmt": "<оператор>",
    "aexpr": "<вираз>",
    "term": "<вираз>",
    "factor": "<вираз>",
    "bexpr": "<умова>",
    "bterm": "<умова>",
    "bfactor": "<умова>",
    "var": "<змінна>",
    "num": "<число>",
}


@dataclass
class PTNode:
    id: int
    label: str
    rule: str | None
    kind: str
    span: SourceSpan | None
    children: list[PTNode] = field(default_factory=list)
    leaf_index: int | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "rule": self.rule,
            "span": self.span.to_dict() if self.span else None,
        }
        if self.kind == "terminal":
            result["leaf_index"] = self.leaf_index
        else:
            result["children"] = [c.to_dict() for c in self.children]
        return result


def from_lark(tree: Tree[Token], course_names: bool = False) -> PTNode:
    counter = [0]
    leaves = [0]

    def visit(item: Tree[Token] | Token) -> PTNode:
        node_id = counter[0]
        counter[0] += 1
        if isinstance(item, Token):
            leaves[0] += 1
            return PTNode(node_id, str(item), item.type, "terminal", token_span(item), [], leaves[0])
        rule = str(item.data)
        label = COURSE_NAMES.get(rule, rule) if course_names else rule
        node = PTNode(node_id, label, rule, "nonterminal", tree_span(item))
        node.children = [visit(child) for child in item.children]
        if course_names and len(node.children) == 1:
            only = node.children[0]
            if only.kind == "nonterminal" and only.label == node.label:
                return only
        return node

    root = tree
    if tree.data == "start" and len(tree.children) == 1 and isinstance(tree.children[0], Tree):
        root = tree.children[0]
    return visit(root)


def leaves(node: PTNode) -> list[PTNode]:
    if node.kind == "terminal":
        return [node]
    result: list[PTNode] = []
    for child in node.children:
        result.extend(leaves(child))
    return result


def crown(node: PTNode) -> str:
    return " ".join(f"{leaf.leaf_index} {leaf.label}" for leaf in leaves(node))


def leaf_text(node: PTNode) -> str:
    return " ".join(leaf.label for leaf in leaves(node))


def to_text(node: PTNode) -> str:
    lines: list[str] = []

    def visit(item: PTNode, prefix: str, last: bool, root: bool) -> None:
        span = f"  [{item.span}]" if item.span else ""
        if item.kind == "terminal":
            text = f"{item.leaf_index}. '{item.label}'{span}"
        else:
            text = f"{item.label}{span}"
        if root:
            lines.append(text)
            child_prefix = ""
        else:
            lines.append(prefix + ("└── " if last else "├── ") + text)
            child_prefix = prefix + ("    " if last else "│   ")
        for index, child in enumerate(item.children):
            visit(child, child_prefix, index == len(item.children) - 1, False)

    visit(node, "", True, True)
    return "\n".join(lines)


def _dot_label(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def to_dot(node: PTNode, title: str = "parse_tree") -> str:
    lines = [
        f'digraph "{_dot_label(title)}" {{',
        '  graph [ordering=out, fontname="DejaVu Sans"];',
        '  node [fontname="DejaVu Sans", fontsize=11];',
        "  edge [arrowhead=none];",
    ]

    def visit(item: PTNode) -> None:
        span = str(item.span) if item.span else "-"
        if item.kind == "terminal":
            lines.append(
                f'  n{item.id} [label="{_dot_label(item.label)}", shape=box, style="rounded,filled", '
                f'fillcolor="#e8f1ff", xlabel="{item.leaf_index}", tooltip="{span}", id="pt{item.id}"];'
            )
        else:
            lines.append(
                f'  n{item.id} [label="{_dot_label(item.label)}", shape=ellipse, '
                f'tooltip="{_dot_label(item.rule or "")} {span}", id="pt{item.id}"];'
            )
        for child in item.children:
            visit(child)
            lines.append(f"  n{item.id} -> n{child.id};")

    visit(node)
    lines.append("}")
    return "\n".join(lines) + "\n"


def ast_to_dot(program: Program, title: str = "ast") -> str:
    lines = [
        f'digraph "{_dot_label(title)}" {{',
        '  graph [ordering=out, fontname="DejaVu Sans"];',
        '  node [fontname="DejaVu Sans", fontsize=11, shape=box, style=rounded];',
    ]
    counter = [0]

    def visit(item: Node) -> int:
        node_id = counter[0]
        counter[0] += 1
        span = str(item.span) if item.span else "-"
        detail = _ast_detail(item)
        label = type(item).__name__ + (f"\\n{_dot_label(detail)}" if detail else "")
        lines.append(f'  a{node_id} [label="{label}", tooltip="{span}", id="ast{node_id}"];')
        for child in children(item):
            child_id = visit(child)
            lines.append(f"  a{node_id} -> a{child_id};")
        return node_id

    visit(program)
    lines.append("}")
    return "\n".join(lines) + "\n"


def _ast_detail(node: Node) -> str:
    for attr in ("op", "target", "name", "value"):
        if hasattr(node, attr):
            value = getattr(node, attr)
            return str(value).lower() if isinstance(value, bool) else str(value)
    if type(node).__name__ in ("If", "While", "Block", "Seq", "Assign"):
        return describe(node)
    return ""


def dot_to_svg(dot: str) -> str:
    executable = shutil.which("dot")
    if executable is None:
        raise RuntimeError("Graphviz не встановлено: потрібна команда 'dot' (sudo apt install graphviz)")
    completed = subprocess.run(
        [executable, "-Tsvg"],
        input=dot.encode("utf-8"),
        capture_output=True,
        check=True,
    )
    return completed.stdout.decode("utf-8")
