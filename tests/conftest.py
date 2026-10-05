"""Shared pytest fixtures."""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable

import pytest


@pytest.fixture
def require_tool() -> Callable[[str], None]:
    """Return a function that makes a test depend on an external command.

    On a developer machine a missing tool skips the test. On CI (the ``CI``
    environment variable is set, as it is on GitHub Actions) a missing tool is a
    failure, so a check can never be silently skipped there.
    """

    def require(name: str) -> None:
        if shutil.which(name) is not None:
            return
        message = f"{name} is not installed"
        if os.environ.get("CI"):
            pytest.fail(message + " (required on CI)")
        pytest.skip(message)

    return require
