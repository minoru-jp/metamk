"""Build and verify the metamk release distributions.

Used by CI and by the release workflow; it can also be run locally::

    python -m pip install -e ".[dist]"
    python scripts/check_dist.py

What it does, in order:

1. (release only) checks that the release tag is ``v<project version>``;
2. checks that the CHANGELOG has an entry for the project version (and,
   for a release, that the entry has a release date);
3. builds one wheel and one sdist;
4. inspects both archives (exact wheel contents, metadata, sdist contents);
5. runs ``twine check --strict`` on them;
6. installs each artifact into a fresh virtual environment, runs ``pip check``
   and a smoke test from a neutral directory (so the source tree is not used).
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import venv
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"

# The wheel must contain exactly these package files (plus .dist-info). Adding a
# module to the package therefore requires updating this list on purpose.
EXPECTED_WHEEL_PACKAGE_FILES = {
    "metamk/__init__.py",
    "metamk/_core.py",
    "metamk/py.typed",
}

REQUIRED_SDIST_PATHS = {
    "src/metamk/__init__.py",
    "src/metamk/_core.py",
    "src/metamk/py.typed",
    "tests/test_phases.py",
    "tests/test_readme.py",
    "devdocs/canonical_sources/readme.py",
    "devdocs/canonical_documents/README.md",
    "README.md",
    "STATUS.md",
    "CHANGELOG.md",
    "LICENSE",
    "pyproject.toml",
    "scripts/check_dist.py",
}

FORBIDDEN_ARCHIVE_PARTS = {
    ".github",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
}

SMOKE_TEST = r"""
from importlib.resources import files
from pathlib import Path

import metamk
from metamk import Mk, phase_of

assert files("metamk").joinpath("py.typed").is_file(), "py.typed is missing"

error = ValueError("boom")
try:
    with Mk.MAIN:
        raise error
except ValueError:
    pass
assert phase_of(error) == "MAIN", phase_of(error)
assert error.__notes__ == ["[metamk] failed in MAIN"], error.__notes__

root = Path(r"__SOURCE_ROOT__").resolve()
installed_from = Path(metamk.__file__).resolve()
assert root not in installed_from.parents, f"imported from the source tree: {installed_from}"
print("smoke test passed:", installed_from)
"""


def _fail(message: str) -> None:
    raise SystemExit(f"check_dist: {message}")


def _run(
    args: list[str | os.PathLike[str]],
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
) -> None:
    command = [os.fspath(arg) for arg in args]
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def _project() -> dict[str, object]:
    with (ROOT / "pyproject.toml").open("rb") as file:
        return tomllib.load(file)["project"]


# --- 1 / 2: release tag and changelog --------------------------------------


def check_release_tag(tag: str, version: str) -> None:
    expected = f"v{version}"
    if tag != expected:
        _fail(
            f"release tag {tag!r} does not match project version {version!r}; "
            f"expected {expected!r}"
        )
    print(f"release tag {tag} matches project version {version}")


def check_changelog(version: str, *, require_release_date: bool) -> None:
    """The CHANGELOG must have an entry for ``version``.

    When publishing a release the entry must also carry its release date
    (``released on: YYYY-MM-DD``). Normal CI does not require the date, so that
    the entry for the next version can be started before it is released.
    """
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    sections = re.split(r"^## ", changelog, flags=re.MULTILINE)
    entry = next(
        (
            section
            for section in sections
            if re.search(rf"^version: {re.escape(version)}$", section, re.MULTILINE)
        ),
        None,
    )
    if entry is None:
        _fail(f"CHANGELOG.md has no entry for version {version}")
    if require_release_date and not re.search(
        r"^released on: \d{4}-\d{2}-\d{2}$", entry, re.MULTILINE
    ):
        _fail(
            f"the CHANGELOG.md entry for version {version} has no release date "
            "('released on: YYYY-MM-DD')"
        )


# --- 3: build --------------------------------------------------------------


def _build() -> tuple[Path, Path]:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    _run([sys.executable, "-m", "build", "--outdir", DIST])
    wheels = sorted(DIST.glob("*.whl"))
    sdists = sorted(DIST.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        _fail(f"expected one wheel and one sdist, found {wheels=} {sdists=}")
    return wheels[0], sdists[0]


# --- 4: archive inspection -------------------------------------------------


def _assert_no_forbidden_parts(names: list[str], *, archive: Path) -> None:
    bad = [n for n in names if FORBIDDEN_ARCHIVE_PARTS.intersection(Path(n).parts)]
    if bad:
        _fail(f"forbidden paths in {archive.name}: {bad[:20]}")


def check_wheel(wheel: Path, project: dict[str, object]) -> None:
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        _assert_no_forbidden_parts(names, archive=wheel)

        package_files = {n for n in names if ".dist-info/" not in n}
        if package_files != EXPECTED_WHEEL_PACKAGE_FILES:
            _fail(
                f"unexpected wheel contents in {wheel.name}: "
                f"extra={sorted(package_files - EXPECTED_WHEEL_PACKAGE_FILES)} "
                f"missing={sorted(EXPECTED_WHEEL_PACKAGE_FILES - package_files)}"
            )
        if not any(n.endswith(".dist-info/licenses/LICENSE") for n in names):
            _fail(f"LICENSE is not included in {wheel.name}")

        metadata_names = [n for n in names if n.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1:
            _fail(f"expected one METADATA in {wheel.name}, found {metadata_names}")
        metadata = archive.read(metadata_names[0]).decode("utf-8")

    fields: dict[str, list[str]] = {}
    for line in metadata.split("\n\n", 1)[0].splitlines():
        key, _, value = line.partition(": ")
        fields.setdefault(key, []).append(value)

    expectations = {
        "Name": [project["name"]],
        "Version": [project["version"]],
        "Requires-Python": [project["requires-python"]],
        "License-Expression": ["MIT"],
    }
    for key, expected in expectations.items():
        if fields.get(key) != expected:
            _fail(f"metadata {key}: expected {expected}, found {fields.get(key)}")

    # README promises "no external dependencies": only extras may require anything.
    runtime_requirements = [
        r for r in fields.get("Requires-Dist", []) if "extra ==" not in r
    ]
    if runtime_requirements:
        _fail(f"unexpected runtime dependencies: {runtime_requirements}")


def check_sdist(sdist: Path) -> None:
    with tarfile.open(sdist, "r:gz") as archive:
        names = archive.getnames()
    _assert_no_forbidden_parts(names, archive=sdist)
    # Every sdist member lives under one top-level directory (metamk-<version>/).
    # Compare the paths below it exactly: matching only on a suffix would let
    # devdocs/canonical_documents/README.md stand in for a missing README.md.
    relative_paths = {name.split("/", 1)[1] for name in names if "/" in name}
    missing = sorted(REQUIRED_SDIST_PATHS - relative_paths)
    if missing:
        _fail(f"missing required paths in {sdist.name}: {missing}")


# --- 5: twine --------------------------------------------------------------


def check_metadata_with_twine(wheel: Path, sdist: Path) -> None:
    _run([sys.executable, "-m", "twine", "check", "--strict", wheel, sdist])


# --- 6: installed smoke test ----------------------------------------------


def _venv_python(directory: Path) -> Path:
    bin_dir = directory / ("Scripts" if os.name == "nt" else "bin")
    return bin_dir / ("python.exe" if os.name == "nt" else "python")


def install_and_smoke_test(artifact: Path, *, work: Path, label: str) -> None:
    environment = work / f"{label}-env"
    venv.EnvBuilder(with_pip=True).create(environment)
    python = _venv_python(environment)
    _run([python, "-m", "pip", "install", artifact], cwd=work)
    _run([python, "-m", "pip", "check"], cwd=work)

    # Run from a neutral directory without PYTHONPATH so that the installed
    # package, not the source tree, is what gets imported.
    clean_env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    _run(
        [python, "-c", SMOKE_TEST.replace("__SOURCE_ROOT__", str(ROOT))],
        cwd=work,
        env=clean_env,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build and verify the metamk release distributions."
    )
    parser.add_argument(
        "--release-tag",
        help="Git tag of the release being published; must be v<project version>.",
    )
    parser.add_argument(
        "--archive-only",
        action="store_true",
        help="Inspect the built archives without installing them.",
    )
    args = parser.parse_args()

    project = _project()
    version = str(project["version"])

    if args.release_tag is not None:
        check_release_tag(args.release_tag, version)
    check_changelog(version, require_release_date=args.release_tag is not None)

    wheel, sdist = _build()
    check_wheel(wheel, project)
    check_sdist(sdist)
    check_metadata_with_twine(wheel, sdist)

    if not args.archive_only:
        with tempfile.TemporaryDirectory(prefix="metamk-dist-check-") as temp:
            work = Path(temp)
            install_and_smoke_test(wheel, work=work, label="wheel")
            install_and_smoke_test(sdist, work=work, label="sdist")

    print(f"release distributions verified: {wheel.name}, {sdist.name}")


if __name__ == "__main__":
    main()
