# Семантика SIPL

## Побудова терму (SEM-01)

`sipl.semantics.build_term(program)` рекурсивно обходить AST і застосовує правила практикуму:

| Правило | Синтаксис | Терм |
|---|---|---|
| NS_Prog | `begin S end` | `sem_S(S)` |
| NS_Stm_As | `x := a` | `AS^x(sem_A(a))` |
| NS_Stm_Seq | `S1; S2` | `sem_S(S1) · sem_S(S2)` |
| NS_Stm_If | `if b then S1 else S2` | `IF(sem_B(b), sem_S(S1), sem_S(S2))` |
| NS_Stm_Wh | `while b do S` | `WH(sem_B(b), sem_S(S))` |
| NS_Stm_BE | `begin S end` | `(sem_S(S))` |
| NS_Stm_skip | `skip` | `id` |
| NS_A_Num | `n` | `n̄` |
| NS_A_Var | `x` | `x⇒` |
| NS_A_Add/Sub/Mult | `a1 + a2` … | `S^2(add/sub/mult, sem_A(a1), sem_A(a2))` |
| NS_B_eq / NS_B_gr | `a1 = a2`, `a1 > a2` | `S^2(eq/gr, …)` |
| NS_B_or | `b1 ∨ b2` | `S^2(or, sem_B(b1), sem_B(b2))` |
| NS_B_neg | `¬b` | `S^1(neg, sem_B(b))` |

Дужки `(a)`, `(b)` (NS_A_Par, NS_B_Par) зникають ще в AST. Композиція `·` асоціативна, тому `S1; S2; S3` дає плаский терм `f1 · f2 · f3`. Дужки навколо блоку виводяться, лише коли блок стоїть усередині композиції.

`--steps` друкує дерево застосованих правил (спадний обхід, як у прикладі практикуму).

## Обчислення терму (SEM-02)

`sipl.semantics.evaluate(term, state)` реалізує формули:

| Формула | Зміст |
|---|---|
| AF_S | `S^n(f, g1..gn)(st) = f(g1(st), …, gn(st))` |
| AF_AS | `AS^x(fa)(st) = st∇[x ↦ fa(st)]` |
| AF_SEQ | `(fs1 · fs2)(st) = fs2(fs1(st))` |
| AF_IF | `IF(fb, fs1, fs2)(st) = fs1(st)`, якщо `fb(st) = true`, інакше `fs2(st)` |
| AF_WH | `WH(fb, fs)(st) = st_n`, де `st_{i+1} = fs(st_i)`, `fb(st_i) = true` для `i < n`, `fb(st_n) = false` |
| AF_DNM | `x⇒(st) = st(x)` |
| AF_ID | `id(st) = st` |

Невизначеність результату виникає, якщо:

1. `x ∉ dom(st)` для деякого `x⇒` (часткова функція розіменування);
2. `div`/`mod` на нуль;
3. не знайдено `n` для AF_WH у межах ліміту застосувань правил.

Пункт 3 — апроксимація: ліміт показує, що цикл не завершився за N кроків, але не доводить нескінченності (проблема зупинки нерозв'язна).

## Узгодженість двох семантик

Інтерпретатор (`sipl.interpreter`) — операційна семантика над AST; `evaluate` — денотаційна над термом. Тест `test_term_semantics_agrees_with_interpreter` перевіряє, що на всіх прикладах обидві дають однаковий кінцевий стан.
