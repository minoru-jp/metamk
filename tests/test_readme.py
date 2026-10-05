"""README examples are executable and match the generated output.

The English README at the top level is a translation of the Japanese canonical
document under ``devdocs/canonical_documents/``. Code and output blocks must be
identical in both, and the Python examples must actually run.
"""

from __future__ import annotations

import asyncio
import inspect
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "devdocs" / "canonical_documents" / "README.md"
PUBLISHED = ROOT / "README.md"

_FENCE = re.compile(r"^```(\w+)\n(.*?)^```", re.DOTALL | re.MULTILINE)


def blocks(path: Path, language: str) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [m.group(2) for m in _FENCE.finditer(text) if m.group(1) == language]


PYTHON_BLOCKS = blocks(PUBLISHED, "python")


@pytest.mark.parametrize("language", ["python", "text", "bash"])
def test_published_blocks_match_the_canonical_document(language):
    published = blocks(PUBLISHED, language)
    assert published, f"no {language} blocks found"
    assert published == blocks(CANONICAL, language)


@pytest.mark.parametrize(
    "code", PYTHON_BLOCKS, ids=[f"block{i}" for i in range(len(PYTHON_BLOCKS))]
)
def test_python_examples_run(code):
    namespace: dict[str, object] = {"__name__": "readme_example"}
    # Intentional: the code comes from this repository's own README.
    exec(compile(code, "<README example>", "exec"), namespace)  # noqa: S102
    for name, value in list(namespace.items()):
        if name.startswith("test_") and callable(value):
            if inspect.iscoroutinefunction(value):
                asyncio.run(value())
            else:
                value()


def test_failure_output_matches_the_readme(tmp_path):
    quickstart = PYTHON_BLOCKS[0]
    failing = quickstart.replace("assert result == 3", "assert result == 4")
    assert failing != quickstart

    test_file = tmp_path / "test_failing.py"
    test_file.write_text(failing, encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "--color=no"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1, completed.stdout
    output = [line.rstrip() for line in completed.stdout.splitlines()]
    for expected in blocks(PUBLISHED, "text")[0].splitlines():
        assert expected.rstrip() in output
