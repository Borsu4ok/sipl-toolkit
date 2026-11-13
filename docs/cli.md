# CLI та JSON-контракт

## Конверт відповіді (`--json`)

```json
{
  "schema_version": 1,
  "command": "run",
  "ok": true,
  "result": { },
  "diagnostics": [ ]
}
```

| Поле | Тип | Опис |
|---|---|---|
| `schema_version` | int | версія контракту; змінюється лише при несумісних змінах |
| `command` | string | `parse`, `check`, `run`, `trace`, `tree`, `term`, `eval`, `grammar` |
| `ok` | bool | `true` ⇔ код завершення 0 |
| `result` | object / null | залежить від команди |
| `diagnostics` | array | список `Diagnostic` |

## Diagnostic

```json
{
  "severity": "error",
  "code": "SYNTAX",
  "message": "Неочікуване '='; очікувалось: ':='",
  "span": { "line": 2, "column": 5, "end_line": 2, "end_column": 6 }
}
```

Коди: `SYNTAX`, `RUNTIME`, `UNDEFINED_VARIABLE`, `DIVISION_BY_ZERO`, `STEP_LIMIT`, `USAGE`, `IO`, `GRAPHVIZ`. Рядки й колонки нумеруються з 1, `end_column` не включається.

## `result` за командами

| Команда | `result` |
|---|---|
| `parse` | `{"ast": Node}` |
| `check` | `{"valid": true, "variables": [..]}` |
| `run` | `{"state": {..}, "steps": int}` |
| `trace` | `{"final": {"state", "steps"}, "events": [TraceEvent]}`; при помилці — `{"events": [...]}` |
| `tree` | `{"tree": PTNode, "crown": string}` або `{"ast": Node}` з `--ast` |
| `term` | `{"term", "term_ascii", "tree", "derivation": [..]}` |
| `eval` | `{"defined", "state", "reason", "code", "rules": [..], "term"}` |

## TraceEvent

```json
{
  "index": 7,
  "step": 3,
  "kind": "variable_changed",
  "node": "Assign",
  "text": "R := R * X",
  "span": { "line": 5, "column": 5, "end_line": 5, "end_column": 15 },
  "state": { "R": 5, "X": 5, "Y": 2 },
  "data": { "name": "R", "old": 1, "new": 5 }
}
```

`kind` ∈ `start`, `before_statement`, `after_statement`, `variable_changed`, `condition_checked`, `finish`, `error`. `state` — знімок стану після події.
