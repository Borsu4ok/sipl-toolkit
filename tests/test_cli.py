from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import EXAMPLES
from sipl.cli import EXIT_IO, EXIT_OK, EXIT_RUNTIME, EXIT_STEP_LIMIT, EXIT_SYNTAX, EXIT_USAGE, main

POWER = str(EXAMPLES / "valid" / "power.sipl")
LOOP = str(EXAMPLES / "valid" / "infinite_loop.sipl")
BAD = str(EXAMPLES / "invalid" / "equals_instead_of_assign.sipl")


def run_json(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, dict]:
    code = main([*argv, "--json"])
    return code, json.loads(capsys.readouterr().out)


def test_check_ok(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check", POWER]) == EXIT_OK
    assert "R, X, Y" in capsys.readouterr().out


def test_check_syntax_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check", BAD]) == EXIT_SYNTAX
    err = capsys.readouterr().err
    assert "equals_instead_of_assign.sipl:2:5: error[SYNTAX]" in err


def test_check_json_contract(capsys: pytest.CaptureFixture[str]) -> None:
    code, payload = run_json(capsys, "check", BAD)
    assert code == EXIT_SYNTAX
    assert payload["schema_version"] == 1
    assert payload["command"] == "check"
    assert payload["ok"] is False
    diagnostic = payload["diagnostics"][0]
    assert diagnostic["code"] == "SYNTAX"
    assert diagnostic["span"]["line"] == 2 and diagnostic["span"]["column"] == 5


def test_run(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", POWER, "--set", "X=5", "--set", "Y=2"]) == EXIT_OK
    assert "R = 25" in capsys.readouterr().out


def test_run_json_with_state(capsys: pytest.CaptureFixture[str]) -> None:
    code, payload = run_json(capsys, "run", POWER, "--state", '{"X": 2, "Y": 3}')
    assert code == EXIT_OK
    assert payload["ok"] is True
    assert payload["result"]["state"] == {"R": 8, "X": 2, "Y": 0}


def test_run_runtime_error(capsys: pytest.CaptureFixture[str]) -> None:
    code, payload = run_json(capsys, "run", POWER, "--set", "X=5")
    assert code == EXIT_RUNTIME
    assert payload["diagnostics"][0]["code"] == "UNDEFINED_VARIABLE"


def test_run_step_limit(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", LOOP, "--max-steps", "100"]) == EXIT_STEP_LIMIT
    assert "STEP_LIMIT" in capsys.readouterr().err


@pytest.mark.parametrize("bad", [["--set", "X"], ["--set", "1X=2"], ["--state", "[1]"], ["--state", "{bad"]])
def test_bad_state_arguments(capsys: pytest.CaptureFixture[str], bad: list[str]) -> None:
    assert main(["run", POWER, *bad]) == EXIT_USAGE
    assert "USAGE" in capsys.readouterr().err


def test_usage_error() -> None:
    with pytest.raises(SystemExit) as info:
        main(["unknown"])
    assert info.value.code == EXIT_USAGE


def test_missing_file(capsys: pytest.CaptureFixture[str]) -> None:
    code, payload = run_json(capsys, "check", "no_such_file.sipl")
    assert code == EXIT_IO
    assert payload["diagnostics"][0]["code"] == "IO"


def test_trace(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["trace", POWER, "--set", "X=2", "--set", "Y=1"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "condition_checked" in out and "R: 1 -> 2" in out


def test_trace_json(capsys: pytest.CaptureFixture[str]) -> None:
    code, payload = run_json(capsys, "trace", POWER, "--set", "X=2", "--set", "Y=1")
    assert code == EXIT_OK
    events = payload["result"]["events"]
    assert events[0]["kind"] == "start" and events[-1]["kind"] == "finish"
    assert payload["result"]["final"]["state"]["R"] == 2


def test_trace_json_on_error(capsys: pytest.CaptureFixture[str]) -> None:
    code, payload = run_json(capsys, "trace", LOOP, "--max-steps", "5")
    assert code == EXIT_STEP_LIMIT
    assert payload["result"]["events"][-1]["kind"] == "error"


def test_trace_text_on_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["trace", LOOP, "--max-steps", "3"]) == EXIT_STEP_LIMIT
    captured = capsys.readouterr()
    assert "error" in captured.out and "STEP_LIMIT" in captured.err


def test_parse(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["parse", POWER]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["type"] == "Program"
    assert main(["parse", POWER, "--format", "pretty"]) == EXIT_OK
    assert capsys.readouterr().out.startswith("begin\n  R := 1;")
    code, payload = run_json(capsys, "parse", POWER)
    assert payload["result"]["ast"]["body"]["type"] == "Seq"


def test_tree_formats(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    assert main(["tree", POWER, "--course-names"]) == EXIT_OK
    assert "Крона" in capsys.readouterr().out
    assert main(["tree", POWER, "--format", "json"]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["tree"]["label"] == "program"
    out = tmp_path / "tree.dot"
    assert main(["tree", POWER, "--format", "dot", "-o", str(out)]) == EXIT_OK
    assert out.read_text(encoding="utf-8").startswith('digraph "power"')
    assert main(["tree", POWER, "--ast"]) == EXIT_OK
    assert 'label="Program"' in capsys.readouterr().out
    assert main(["tree", POWER, "--ast", "--format", "json"]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["type"] == "Program"
    code, payload = run_json(capsys, "tree", POWER)
    assert payload["result"]["crown"].startswith("begin R := 1 ;")


@pytest.mark.skipif(shutil.which("dot") is None, reason="graphviz not installed")
def test_tree_svg(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    out = tmp_path / "tree.svg"
    assert main(["tree", POWER, "--format", "svg", "-o", str(out)]) == EXIT_OK
    assert "<svg" in out.read_text(encoding="utf-8")
    assert main(["tree", POWER, "--ast", "--format", "svg"]) == EXIT_OK
    assert "<svg" in capsys.readouterr().out


def test_tree_svg_without_graphviz(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert main(["tree", POWER, "--format", "svg"]) == EXIT_IO
    assert "GRAPHVIZ" in capsys.readouterr().err


def test_write_output_failure(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    target = tmp_path / "missing" / "x.dot"
    assert main(["tree", POWER, "--format", "dot", "-o", str(target)]) == EXIT_IO


def test_term(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["term", POWER, "--format", "plain"]) == EXIT_OK
    assert capsys.readouterr().out.strip() == (
        "AS^R(1) · WH(S^2(gr, Y⇒, 0), AS^R(S^2(mult, R⇒, X⇒)) · AS^Y(S^2(sub, Y⇒, 1)))"
    )
    assert main(["term", POWER, "--steps", "--format", "ascii"]) == EXIT_OK
    assert "NS_Stm_Wh" in capsys.readouterr().out
    assert main(["term", POWER, "--format", "json"]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["type"] == "Comp"
    code, payload = run_json(capsys, "term", POWER)
    assert payload["result"]["term_ascii"].startswith("AS^R(1) . WH")
    assert payload["result"]["derivation"][0]["rule"] == "NS_Prog"


def test_eval(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["eval", POWER, "--set", "X=5", "--set", "Y=2"]) == EXIT_OK
    out = capsys.readouterr().out
    assert "AF_WH" in out and "R ↦ 25" in out
    assert main(["eval", POWER, "--set", "X=5", "--set", "Y=2", "--quiet"]) == EXIT_OK
    assert capsys.readouterr().out.splitlines()[0] == "R = 25"


def test_eval_undefined(capsys: pytest.CaptureFixture[str]) -> None:
    code, payload = run_json(capsys, "eval", POWER, "--set", "X=5")
    assert code == EXIT_RUNTIME
    assert payload["ok"] is False
    assert payload["result"]["defined"] is False
    assert main(["eval", LOOP, "--max-steps", "50"]) == EXIT_STEP_LIMIT
    assert "невизначений" in capsys.readouterr().err


def test_grammar(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["grammar"]) == EXIT_OK
    assert "program: BEGIN seq END" in capsys.readouterr().out
    code, payload = run_json(capsys, "grammar")
    assert "while_stmt" in payload["result"]["grammar"]


def test_stdin(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    import io

    monkeypatch.setattr(sys, "stdin", io.StringIO("begin X := 2 * 21 end"))
    assert main(["run", "-"]) == EXIT_OK
    assert "X = 42" in capsys.readouterr().out


def test_module_entrypoint() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "sipl", "run", POWER, "--set", "X=3", "--set", "Y=3", "--json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert json.loads(completed.stdout)["result"]["state"]["R"] == 27
