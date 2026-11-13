from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
VALID = sorted((EXAMPLES / "valid").glob("*.sipl"))
INVALID = sorted((EXAMPLES / "invalid").glob("*.sipl"))
GOLDEN = Path(__file__).resolve().parent / "golden"


@pytest.fixture
def power_source() -> str:
    return (EXAMPLES / "valid" / "power.sipl").read_text(encoding="utf-8")
