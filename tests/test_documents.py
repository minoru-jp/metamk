"""Checks for the documentation system.

* The Japanese canonical documents under ``devdocs/canonical_documents/`` are in
  sync with the canonical sources (nobody edited a generated file by hand).
* The English documents at the top level have the same structure as the
  Japanese canonical documents they are translated from.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_DOCUMENTS = ROOT / "devdocs" / "canonical_documents"
CONTEXT_FILE = ROOT / "devdocs" / "config" / "context.json"
NOTICE_FILE = ROOT / "devdocs" / "config" / "notice.toml"

# (document, canonical source module, rendered with realization context?)
DOCUMENTS = [
    ("README.md", "devdocs.canonical_sources.readme", True),
    ("STATUS.md", "devdocs.canonical_sources.status", True),
    ("CHANGELOG.md", "devdocs.canonical_sources.changelog", False),
]
DOCUMENT_IDS = [name for name, _, _ in DOCUMENTS]

# These documents use ``heading="identity"``: their section headings are
# identifiers (STATUS_001, V0_1_0, ...) and must not be translated. The H1 title
# of every document is translated.
IDENTITY_HEADING_DOCUMENTS = {"STATUS.md", "CHANGELOG.md"}


# --- Canonical documents are in sync with the canonical sources ------------


@pytest.mark.parametrize(
    ("name", "module", "uses_context"), DOCUMENTS, ids=DOCUMENT_IDS
)
def test_canonical_document_is_in_sync_with_its_source(
    tmp_path, require_tool, name, module, uses_context
):
    require_tool("shikumi-devdoc")
    command = [
        "shikumi-devdoc",
        "render",
        "document",
        module,
        "-o",
        str(tmp_path),
        "--notice",
        str(NOTICE_FILE.relative_to(ROOT)),
        "--translation-source",
    ]
    if uses_context:
        command += ["--context", CONTEXT_FILE.read_text(encoding="utf-8")]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    generated = (tmp_path / name).read_text(encoding="utf-8")
    committed = (CANONICAL_DOCUMENTS / name).read_text(encoding="utf-8")
    assert generated == committed, (
        f"{name} is out of date. Regenerate it from its canonical source."
    )


# --- English documents have the same structure as the Japanese ones --------


def _strip_generation_header(text: str) -> str:
    return re.sub(r"\A<!--.*?-->\s*", "", text, flags=re.DOTALL)


@dataclass
class Section:
    """Structure of one Markdown section (wording is deliberately not kept)."""

    level: int
    heading: str = field(default="", compare=False)
    paragraphs: int = 0
    bullets: int = 0
    table_rows: int = 0
    metadata: list[str] = field(default_factory=list)
    code_blocks: list[str] = field(default_factory=list)


_METADATA = re.compile(
    r"^(title|kind|condition|version|released on): |^(Added|Changed|Removed):$"
)


def _outline(text: str) -> list[Section]:
    """Split a Markdown document at its headings and describe each section."""
    sections = [Section(level=0)]
    in_code, code_lines, in_paragraph = False, [], False
    for line in text.splitlines():
        section = sections[-1]
        if line.startswith("```"):
            if in_code:
                section.code_blocks.append("\n".join(code_lines))
                code_lines = []
            in_code, in_paragraph = not in_code, False
        elif in_code:
            code_lines.append(line)
        elif heading := re.match(r"^(#+) ", line):
            sections.append(
                Section(level=len(heading.group(1)), heading=line[heading.end() :])
            )
            in_paragraph = False
        elif not line.strip():
            in_paragraph = False
        elif line.startswith("|"):
            section.table_rows += 1
            in_paragraph = False
        elif line.startswith("- "):
            section.bullets += 1
            in_paragraph = False
        elif metadata := _METADATA.match(line):
            section.metadata.append(metadata.group(0))
            in_paragraph = False
        elif line.startswith(">") and not line.startswith("> [!"):
            continue  # continuation of the NOTE admonition
        elif not in_paragraph:
            section.paragraphs += 1
            in_paragraph = True
    return sections


def _inline_code(text: str) -> set[str]:
    without_blocks = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    return set(re.findall(r"`([^`\n]+)`", without_blocks))


def _urls(text: str) -> set[str]:
    return set(re.findall(r"\]\((https?://[^)]+)\)", text))


@pytest.mark.parametrize("name", DOCUMENT_IDS)
def test_english_document_has_the_structure_of_the_japanese_one(name):
    japanese = _strip_generation_header(
        (CANONICAL_DOCUMENTS / name).read_text(encoding="utf-8")
    )
    english = (ROOT / name).read_text(encoding="utf-8")

    ja_outline, en_outline = _outline(japanese), _outline(english)
    assert len(ja_outline) == len(en_outline), "number of sections differs"
    for index, (ja, en) in enumerate(zip(ja_outline, en_outline, strict=True)):
        assert ja == en, f"section #{index} differs in structure"
        if name in IDENTITY_HEADING_DOCUMENTS and ja.level >= 2:
            assert ja.heading == en.heading, f"section #{index} heading was changed"

    assert _inline_code(japanese) == _inline_code(english)
    assert _urls(japanese) == _urls(english)


def test_no_generation_header_leaks_into_published_documents():
    for name in DOCUMENT_IDS:
        published = (ROOT / name).read_text(encoding="utf-8")
        assert "<!--" not in published
        assert "shikumi-devdoc:translation-metadata" not in published


def test_generation_header_is_present_in_canonical_documents():
    for name in DOCUMENT_IDS:
        canonical = (CANONICAL_DOCUMENTS / name).read_text(encoding="utf-8")
        assert canonical.startswith("<!--")


# --- The realization context must agree with pyproject.toml ----------------


def test_realization_context_matches_pyproject():
    """context.json supplies the version and Python range shown in the documents."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    context = json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))["project"]
    assert context["name"] == project["name"]
    assert context["version"] == project["version"]
    assert context["requires-python"] == project["requires-python"]
