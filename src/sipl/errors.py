from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sipl.ast import SourceSpan


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    message: str
    span: SourceSpan | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "span": self.span.to_dict() if self.span else None,
        }

    def format(self, filename: str = "<input>") -> str:
        where = f"{filename}:{self.span.line}:{self.span.column}" if self.span else filename
        return f"{where}: {self.severity}[{self.code}]: {self.message}"


class SiplError(Exception):
    code = "SIPL"

    def __init__(self, message: str, span: SourceSpan | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.span = span
        self.trace: list[dict[str, Any]] | None = None

    def diagnostic(self) -> Diagnostic:
        return Diagnostic("error", self.code, self.message, self.span)


class SiplSyntaxError(SiplError):
    code = "SYNTAX"


class SiplRuntimeError(SiplError):
    code = "RUNTIME"


class UndefinedVariableError(SiplRuntimeError):
    code = "UNDEFINED_VARIABLE"


class DivisionByZeroError(SiplRuntimeError):
    code = "DIVISION_BY_ZERO"


class StepLimitExceeded(SiplRuntimeError):
    code = "STEP_LIMIT"
