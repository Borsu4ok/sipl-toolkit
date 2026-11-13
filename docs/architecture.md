# Архітектура

```
source.sipl
   │  parser.parse_tree      (Lark Earley, propagate_positions, keep_all_tokens)
   ▼
parse tree ───────────────► visualization.from_lark → text / JSON / DOT / SVG   (VIS-01)
   │  parser.build_ast
   ▼
AST (ast.py, SourceSpan) ─► printer (форматування)
   │                 │
   │                 └────► semantics.build_term → Term ─► semantics.evaluate(term, st)   (SEM-01, SEM-02)
   ▼
interpreter.Interpreter(listeners=[TraceRecorder]) → ExecutionResult + TraceEvent[]        (CORE-03, CORE-04)
   ▼
cli.py: parse | check | run | trace | tree | term | eval → text або JSON-конверт            (CORE-05)
```

Принципи:

1. Мова «живе» в бібліотеці `sipl`; CLI і VS Code extension — лише клієнти.
2. Парсер один: і дерево виводу, і AST будуються з одного Lark-дерева, тому позиції однакові на всіх рівнях.
3. Базові функції (`add`, `gr`, …) визначені в `operations.py` один раз і використовуються інтерпретатором.
4. Помилки — винятки з `SourceSpan`, перетворювані на `Diagnostic` для JSON.
5. Trace — спостерігач (listener): інтерпретатор не знає, хто слухає події, тому той самий потік подій придатний для CLI, debugger чи візуалізатора.
