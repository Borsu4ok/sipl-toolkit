from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, NoReturn

from sipl import __version__
from sipl.ast import Program, to_dict, variables
from sipl.errors import Diagnostic, SiplError, SiplSyntaxError, StepLimitExceeded
from sipl.interpreter import DEFAULT_MAX_STEPS, TraceRecorder, run
from sipl.parser import build_ast, grammar_text, parse, parse_tree
from sipl.printer import format_program
from sipl.semantics import STYLES, build_term_with_steps, evaluate, render, term_to_dict
from sipl.visualization import ast_to_dot, crown, dot_to_svg, from_lark, leaf_text, to_dot, to_text

SCHEMA_VERSION = 1

EXIT_OK = 0
EXIT_SYNTAX = 1
EXIT_USAGE = 2
EXIT_RUNTIME = 3
EXIT_STEP_LIMIT = 4
EXIT_IO = 5

_ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(-?[0-9]+)$")


class CliFailure(Exception):
    def __init__(self, exit_code: int, diagnostic: Diagnostic) -> None:
        super().__init__(diagnostic.message)
        self.exit_code = exit_code
        self.diagnostic = diagnostic


def _usage(message: str) -> CliFailure:
    return CliFailure(EXIT_USAGE, Diagnostic("error", "USAGE", message))


def _io(message: str) -> CliFailure:
    return CliFailure(EXIT_IO, Diagnostic("error", "IO", message))


def _read_source(path: str) -> tuple[str, str]:
    if path == "-":
        return sys.stdin.read(), "<stdin>"
    try:
        return Path(path).read_text(encoding="utf-8"), path
    except OSError as error:
        raise _io(f"Не вдалося прочитати {path}: {error.strerror}") from None


def _parse_state(assignments: Sequence[str], state_json: str | None) -> dict[str, int]:
    state: dict[str, int] = {}
    if state_json:
        try:
            loaded = json.loads(state_json)
        except json.JSONDecodeError as error:
            raise _usage(f"Некоректний JSON у --state: {error.msg}") from None
        if not isinstance(loaded, dict) or not all(
            isinstance(k, str) and isinstance(v, int) and not isinstance(v, bool) for k, v in loaded.items()
        ):
            raise _usage('--state має бути об\'єктом {"X": ціле, ...}')
        state.update(loaded)
    for item in assignments:
        match = _ASSIGNMENT.match(item.strip())
        if not match:
            raise _usage(f"Некоректне значення --set {item!r}; формат NAME=INT")
        state[match.group(1)] = int(match.group(2))
    return state


def _exit_code(error: SiplError) -> int:
    if isinstance(error, SiplSyntaxError):
        return EXIT_SYNTAX
    if isinstance(error, StepLimitExceeded):
        return EXIT_STEP_LIMIT
    return EXIT_RUNTIME


def _envelope(command: str, ok: bool, result: Any, diagnostics: list[Diagnostic]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "ok": ok,
        "result": result,
        "diagnostics": [d.to_dict() for d in diagnostics],
    }


def _emit_json(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _write_output(text: str, output: str | None) -> None:
    if output:
        try:
            Path(output).write_text(text, encoding="utf-8")
        except OSError as error:
            raise _io(f"Не вдалося записати {output}: {error.strerror}") from None
    else:
        sys.stdout.write(text if text.endswith("\n") else text + "\n")


def _load_program(args: argparse.Namespace) -> tuple[Program, str, str]:
    source, filename = _read_source(args.file)
    return parse(source), source, filename


def cmd_parse(args: argparse.Namespace) -> dict[str, Any]:
    program, _, _ = _load_program(args)
    if args.format == "pretty":
        _write_output(format_program(program), None)
    elif not args.json:
        _write_output(json.dumps(to_dict(program), ensure_ascii=False, indent=2), None)
    return {"ast": to_dict(program)}


def cmd_check(args: argparse.Namespace) -> dict[str, Any]:
    program, _, filename = _load_program(args)
    names = sorted(variables(program))
    if not args.json:
        print(f"{filename}: синтаксично коректна програма; змінні: {', '.join(names) or '—'}")
    return {"valid": True, "variables": names}


def cmd_run(args: argparse.Namespace) -> dict[str, Any]:
    program, _, _ = _load_program(args)
    state = _parse_state(args.set, args.state)
    result = run(program, state, args.max_steps)
    if not args.json:
        for name in sorted(result.state):
            print(f"{name} = {result.state[name]}")
    return result.to_dict()


def cmd_trace(args: argparse.Namespace) -> dict[str, Any]:
    program, _, _ = _load_program(args)
    state = _parse_state(args.set, args.state)
    recorder = TraceRecorder()
    try:
        result = run(program, state, args.max_steps, [recorder])
    except SiplError as error:
        if not args.json:
            for event in recorder.events:
                print(event.format())
        error.trace = recorder.to_list()
        raise
    if not args.json:
        for event in recorder.events:
            print(event.format())
    return {"final": result.to_dict(), "events": recorder.to_list()}


def cmd_tree(args: argparse.Namespace) -> dict[str, Any]:
    source, filename = _read_source(args.file)
    lark_tree = parse_tree(source)
    if args.ast:
        program = build_ast(lark_tree)
        dot = ast_to_dot(program, Path(filename).stem)
        payload: dict[str, Any] = {"ast": to_dict(program)}
        if args.format == "json":
            text = json.dumps(payload["ast"], ensure_ascii=False, indent=2)
        elif args.format == "svg":
            text = _svg(dot)
        else:
            text = dot
    else:
        root = from_lark(lark_tree, args.course_names)
        payload = {"tree": root.to_dict(), "crown": leaf_text(root)}
        if args.format == "json":
            text = json.dumps(payload, ensure_ascii=False, indent=2)
        elif args.format == "dot":
            text = to_dot(root, Path(filename).stem)
        elif args.format == "svg":
            text = _svg(to_dot(root, Path(filename).stem))
        else:
            text = to_text(root) + "\n\nКрона (обхід листків зліва направо):\n" + crown(root)
    if not args.json:
        _write_output(text, args.output)
    return payload


def _svg(dot: str) -> str:
    try:
        return dot_to_svg(dot)
    except RuntimeError as error:
        raise CliFailure(EXIT_IO, Diagnostic("error", "GRAPHVIZ", str(error))) from None


def cmd_term(args: argparse.Namespace) -> dict[str, Any]:
    program, _, _ = _load_program(args)
    term, steps = build_term_with_steps(program)
    style = STYLES["unicode" if args.format == "json" else args.format]
    if not args.json:
        if args.format == "json":
            _write_output(json.dumps(term_to_dict(term), ensure_ascii=False, indent=2), None)
        else:
            if args.steps:
                for step in steps:
                    print(step.format(style))
                print()
            print(render(term, style))
    return {
        "term": render(term, style),
        "term_ascii": render(term, STYLES["ascii"]),
        "tree": term_to_dict(term),
        "derivation": [s.to_dict(style) for s in steps],
    }


def cmd_eval(args: argparse.Namespace) -> dict[str, Any]:
    program, _, _ = _load_program(args)
    state = _parse_state(args.set, args.state)
    term, _ = build_term_with_steps(program)
    style = STYLES[args.style]
    result = evaluate(term, state, args.max_steps, style)
    if not args.json:
        if not args.quiet:
            print(render(term, style))
            print()
            for step in result.steps:
                print(step.format())
        if result.defined and result.state is not None:
            if args.quiet:
                for name in sorted(result.state):
                    print(f"{name} = {result.state[name]}")
        else:
            print(f"Результат невизначений: {result.reason}", file=sys.stderr)
    payload = result.to_dict()
    payload["term"] = render(term, style)
    if not result.defined:
        code = EXIT_STEP_LIMIT if result.code == "STEP_LIMIT" else EXIT_RUNTIME
        raise _UndefinedResult(code, payload, Diagnostic("error", result.code or "UNDEFINED", result.reason or ""))
    return payload


class _UndefinedResult(Exception):
    def __init__(self, exit_code: int, payload: dict[str, Any], diagnostic: Diagnostic) -> None:
        super().__init__(diagnostic.message)
        self.exit_code = exit_code
        self.payload = payload
        self.diagnostic = diagnostic


def cmd_grammar(args: argparse.Namespace) -> dict[str, Any]:
    text = grammar_text()
    if not args.json:
        _write_output(text, None)
    return {"grammar": text}


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"{self.prog}: помилка: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="sipl", description="Інструменти для мови SIPL")
    parser.add_argument("--version", action="version", version=f"sipl {__version__}")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)

    def add(name: str, help_text: str, handler: Any, with_file: bool = True) -> argparse.ArgumentParser:
        p = sub.add_parser(name, help=help_text, description=help_text)
        if with_file:
            p.add_argument("file", help="шлях до .sipl файлу або '-' для stdin")
        p.add_argument("--json", action="store_true", help="структурований JSON-вивід")
        p.set_defaults(handler=handler)
        return p

    def add_state(p: argparse.ArgumentParser, default_steps: int) -> None:
        p.add_argument("--set", action="append", default=[], metavar="NAME=INT", help="початкове значення змінної")
        p.add_argument("--state", metavar="JSON", help='початковий стан, напр. \'{"X": 5, "Y": 2}\'')
        p.add_argument("--max-steps", type=int, default=default_steps, help="ліміт кроків виконання")

    p = add("parse", "побудувати AST", cmd_parse)
    p.add_argument("--format", choices=["json", "pretty"], default="json")

    add("check", "перевірити синтаксичну коректність", cmd_check)

    p = add("run", "виконати програму", cmd_run)
    add_state(p, DEFAULT_MAX_STEPS)

    p = add("trace", "виконати програму з покроковим trace", cmd_trace)
    add_state(p, DEFAULT_MAX_STEPS)

    p = add("tree", "дерево синтаксичного виводу або AST", cmd_tree)
    p.add_argument("--format", choices=["text", "json", "dot", "svg"], default="text")
    p.add_argument("--ast", action="store_true", help="показати AST замість дерева виводу")
    p.add_argument("--course-names", action="store_true", help="мітки як у БНФ курсу: <оператор>, <вираз>, ...")
    p.add_argument("-o", "--output", help="файл для запису результату")

    p = add("term", "побудувати семантичний терм", cmd_term)
    p.add_argument("--format", choices=["unicode", "plain", "ascii", "latex", "json"], default="unicode")
    p.add_argument("--steps", action="store_true", help="показати застосовані правила NS_*")

    p = add("eval", "обчислити семантичний терм на стані", cmd_eval)
    add_state(p, 10_000)
    p.add_argument("--style", choices=["unicode", "plain", "ascii"], default="unicode")
    p.add_argument("--quiet", action="store_true", help="лише кінцевий стан")

    add("grammar", "показати граматику Lark", cmd_grammar, with_file=False)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command
    try:
        result = args.handler(args)
    except SiplError as error:
        diagnostic = error.diagnostic()
        if args.json:
            payload = _envelope(command, False, None, [diagnostic])
            if error.trace is not None:
                payload["result"] = {"events": error.trace}
            _emit_json(payload)
        else:
            print(diagnostic.format(getattr(args, "file", "<input>")), file=sys.stderr)
        return _exit_code(error)
    except _UndefinedResult as undefined:
        if args.json:
            _emit_json(_envelope(command, False, undefined.payload, [undefined.diagnostic]))
        return undefined.exit_code
    except CliFailure as failure:
        if args.json:
            _emit_json(_envelope(command, False, None, [failure.diagnostic]))
        else:
            print(failure.diagnostic.format(getattr(args, "file", "<input>")), file=sys.stderr)
        return failure.exit_code
    if args.json:
        _emit_json(_envelope(command, True, result, []))
    return EXIT_OK


def entrypoint() -> NoReturn:
    sys.exit(main())


if __name__ == "__main__":
    entrypoint()
