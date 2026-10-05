"""Consumer-side typing contract.

Checked with ``basedpyright -p tests/typing`` (standard mode, 0 errors required).
The point is that a type checker must see the phase blocks as blocks that do
*not* swallow exceptions: names assigned inside a block stay "bound" afterwards.
"""

from __future__ import annotations

import asyncio
from typing import Literal

from metamk import Mk, phase_of


def example() -> int:
    with Mk.PREPARE:
        data = {"x": 1, "y": 2}

    with Mk.MAIN:
        result = data["x"] + data["y"]

    with Mk.VERIFY:
        assert result == 3

    return result  # must not be reported as "possibly unbound"


async def async_example() -> int:
    with Mk.PREPARE:
        await asyncio.sleep(0)
        data = [1, 2, 3]

    with Mk.MAIN:
        await asyncio.sleep(0)
        total = sum(data)

    with Mk.VERIFY:
        assert total == 6

    return total


def phase_name_of(
    error: BaseException,
) -> Literal["PREPARE", "MAIN", "VERIFY"] | None:
    return phase_of(error)


def aliases() -> None:
    PREPARE, MAIN, VERIFY = Mk.PREPARE, Mk.MAIN, Mk.VERIFY
    with PREPARE:
        data = [1, 2, 3]
    with MAIN:
        total = sum(data)
    with VERIFY:
        assert total == 6
