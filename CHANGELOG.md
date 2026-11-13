# Changelog

Формат: [Keep a Changelog](https://keepachangelog.com/uk/1.1.0/), версії: [SemVer](https://semver.org/lang/uk/).

## [0.5.0] - РРРР-ММ-ДД

### Added
- Семантичні терми SIPL у нотації курсу (`AS^x`, `S^n`, `·`, `IF`, `WH`, `id`) з поясненням застосованих правил `NS_*` (SEM-01).
- Обчислення семантичного терму на стані з trace формул `AF_*` і явною невизначеністю (SEM-02).
- Команди `sipl term` та `sipl eval`.

## [0.4.0] - РРРР-ММ-ДД

### Added
- Дерево синтаксичного виводу: text, JSON, DOT, SVG; крона з нумерацією листків; мітки метазмінних курсу (VIS-01).
- DOT/SVG для AST (`sipl tree --ast`).

## [0.3.0] - РРРР-ММ-ДД

### Added
- CLI `parse`, `check`, `run`, `trace` зі стабільним JSON-конвертом (`schema_version: 1`) і кодами завершення (CORE-05).
- Подієва модель виконання: `start`, `before_statement`, `after_statement`, `variable_changed`, `condition_checked`, `finish`, `error` (CORE-04).

## [0.2.0] - РРРР-ММ-ДД

### Added
- Інтерпретатор SIPL зі станом змінних, лімітом кроків та діагностикою невизначених змінних (CORE-03).

## [0.1.0] - РРРР-ММ-ДД

### Added
- Граматика Lark, що відповідає БНФ курсу, 13 коректних і 14 некоректних прикладів (CORE-01).
- Парсер у власне типізоване AST з `SourceSpan` (CORE-02).
