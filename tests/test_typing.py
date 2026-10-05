"""Consumer typing contract, checked with basedpyright when it is available."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_consumer_typing_contract(require_tool):
    require_tool("basedpyright")
    completed = subprocess.run(
        ["basedpyright", "-p", str(ROOT / "tests" / "typing")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout
    assert "0 errors, 0 warnings" in completed.stdout, completed.stdout
