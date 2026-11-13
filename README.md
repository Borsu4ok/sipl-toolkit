# SIPL Toolkit

![CI](https://github.com/Borsu4ok/sipl-toolkit/actions/workflows/ci.yml/badge.svg)

Набір інструментів для навчальної мови SIPL (курс «Теорія програмування»): граматика, парсер у типізоване AST, інтерпретатор із покроковим trace, CLI, дерево синтаксичного виводу, семантичні терми та їх обчислення на станах.  Виконав студент групи ТК-32 Слобожанін Нікіта

## Обрані завдання курсового проєкту

| ID | Завдання | Бали |
|---|---|---|
| CORE-01 | Формальна граматика (Lark), ≥10 позитивних і ≥10 негативних прикладів | 0.5 |
| CORE-02 | Парсер і типізоване AST з `SourceSpan` | 1.5 |
| CORE-03 | Інтерпретатор: стан, присвоювання, `;`, `if`, `while`, `begin/end`, `skip`, ліміт кроків | 2.0 |
| CORE-04 | Подієва модель виконання та trace (API + JSON) | 1.0 |
| CORE-05 | CLI `parse/check/run/trace` + JSON-режим | 1.0 |
| VIS-01 | Дерево синтаксичного виводу: text / JSON / DOT / SVG | 1.5 |
| SEM-01 | Побудова семантичного терму в нотації курсу | 2.0 |
| SEM-02 | Обчислення терму на стані з поясненням правил | 2.0 |
| REL-01 | CI: lint, type-check, тести, збірка | 0.5 |
| REL-02 | GitHub Releases + SemVer + CHANGELOG | 0.5 |
| | **Разом заявлено** | **12.5** (зараховується максимум 10) |

Додатково (поза заліком): VS Code extension з підсвічуванням у `vscode-sipl/`.

## Встановлення

Потрібні Python ≥ 3.10 і (для SVG) Graphviz.

```bash
sudo apt install graphviz
git clone https://github.com/Borsu4ok/sipl-toolkit.git
cd sipl-toolkit
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Швидкий старт

```bash
sipl check examples/valid/power.sipl
sipl run examples/valid/power.sipl --set X=5 --set Y=2
sipl trace examples/valid/power.sipl --set X=5 --set Y=2
sipl tree examples/valid/power.sipl --course-names
sipl tree examples/valid/power.sipl --format svg -o power.svg
sipl term examples/valid/power.sipl --steps
sipl eval examples/valid/power.sipl --set X=5 --set Y=2
```

Результат `sipl term`:

```
AS^R(1̅) · WH(S^2(gr, Y⇒, 0̅), AS^R(S^2(mult, R⇒, X⇒)) · AS^Y(S^2(sub, Y⇒, 1̅)))
```

## Команди CLI

| Команда | Що робить | Основні опції |
|---|---|---|
| `parse FILE` | AST у JSON або відформатований код | `--format json\|pretty` |
| `check FILE` | синтаксична перевірка | |
| `run FILE` | виконання | `--set X=5`, `--state '{"X":5}'`, `--max-steps N` |
| `trace FILE` | виконання з подіями | як у `run` |
| `tree FILE` | дерево виводу / AST | `--format text\|json\|dot\|svg`, `--ast`, `--course-names`, `-o` |
| `term FILE` | семантичний терм | `--format unicode\|plain\|ascii\|latex\|json`, `--steps` |
| `eval FILE` | обчислення терму на стані | `--set`, `--state`, `--max-steps`, `--style`, `--quiet` |
| `grammar` | вивести граматику | |

Будь-яка команда приймає `--json`, `FILE = -` читає зі stdin. Формат JSON і коди завершення — у [docs/cli.md](docs/cli.md).

| Код | Значення |
|---|---|
| 0 | успіх |
| 1 | синтаксична помилка |
| 2 | некоректні аргументи |
| 3 | помилка виконання / результат невизначений |
| 4 | перевищено ліміт кроків |
| 5 | помилка вводу-виводу (файл, Graphviz) |

## Архітектура

```
src/sipl/
├── grammar/sipl.lark      граматика
├── ast.py                 вузли AST + SourceSpan
├── parser.py              текст → parse tree (Lark) → AST
├── errors.py              Diagnostic та ієрархія помилок
├── operations.py          базові функції add/sub/mult/gr/eq/...
├── printer.py             AST → текст
├── interpreter/           виконання + події trace
├── semantics/             терми, правила NS_*, обчислення AF_*
├── visualization/         дерево виводу та AST: text/JSON/DOT/SVG
└── cli.py                 командний рядок
```

Детальніше: [docs/architecture.md](docs/architecture.md), [docs/grammar.md](docs/grammar.md), [docs/semantics.md](docs/semantics.md).

## Обмеження

- Ліміт кроків не розв'язує проблему зупинки: перевищення означає лише «не завершилось за N кроків», а не доведену нескінченність циклу.
- Значення змінних — необмежені цілі Python; `div`/`mod` — цілочислове ділення з округленням до −∞.
- Розширення поза БНФ курсу (`div`, `mod`, `>=`, `<`, `<=`, `!=`, `and`, `true`, `false`, коментарі `//`) описані в [docs/grammar.md](docs/grammar.md) і не змінюють семантику базової мови.

## Ліцензія

MIT
