"""The public API is exactly what the README describes."""

from __future__ import annotations

from pathlib import Path

import metamk
from metamk import Mk


def test_public_names():
    assert sorted(metamk.__all__) == ["Mk", "phase_of"]


def test_mk_exposes_exactly_the_three_phases():
    public = [name for name in vars(Mk) if not name.startswith("_")]
    assert public == ["PREPARE", "MAIN", "VERIFY"]


def test_typed_package_marker_is_present():
    assert (Path(metamk.__file__).parent / "py.typed").is_file()
