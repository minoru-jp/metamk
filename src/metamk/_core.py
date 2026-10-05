"""Implementation of metamk.

The README is the reference for the behavior implemented here.
"""

from __future__ import annotations

from types import TracebackType
from typing import Final, Literal, final

PhaseName = Literal["PREPARE", "MAIN", "VERIFY"]

# The phase name is recorded in the exception's own ``__dict__`` under this key.
# It is an implementation detail: use ``phase_of()`` to read it. Because it lives
# in the instance dictionary, it survives pickling and copying of the exception.
_RECORD_KEY: Final = "_metamk_phase"

_PHASE_BY_NAME: Final[dict[str, PhaseName]] = {
    "PREPARE": "PREPARE",
    "MAIN": "MAIN",
    "VERIFY": "VERIFY",
}


def _record(exc: BaseException, name: PhaseName) -> None:
    """Record ``name`` on ``exc`` and add the note, unless already recorded.

    Never raises: failing to record must not hide the original exception.
    """
    try:
        attributes = exc.__dict__
        if _RECORD_KEY in attributes:
            return  # The innermost phase was recorded first and wins.
        attributes[_RECORD_KEY] = name
        exc.add_note(f"[metamk] failed in {name}")
    except Exception:  # noqa: BLE001
        # Deliberately broad: recording is best effort and must never hide
        # the exception that is already propagating.
        return


@final
class _Phase:
    """A phase block usable as ``with Mk.<NAME>:``.

    It holds no mutable state, so a single instance can be shared freely between
    tasks and threads. It is deliberately neither callable nor usable as a
    decorator.
    """

    __slots__ = ("_name",)

    def __init__(self, name: PhaseName) -> None:
        self._name: Final = name

    def __enter__(self) -> None:
        return None

    # The return type must be ``None`` (not ``bool``): a ``bool`` return type tells
    # type checkers that the block may swallow exceptions, which would make
    # variables assigned inside the block "possibly unbound" afterwards.
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc is not None:
            _record(exc, self._name)


@final
class Mk:
    """Namespace of the three phase blocks."""

    PREPARE: Final = _Phase("PREPARE")
    MAIN: Final = _Phase("MAIN")
    VERIFY: Final = _Phase("VERIFY")


def _recorded_phase(exc: BaseException) -> PhaseName | None:
    value: object = exc.__dict__.get(_RECORD_KEY)
    if isinstance(value, str):
        return _PHASE_BY_NAME.get(value)
    return None


def phase_of(exc: BaseException) -> PhaseName | None:
    """Return the phase recorded on ``exc``, or ``None`` if there is none.

    If ``exc`` itself carries no record, follow ``__cause__`` and then
    ``__context__`` (depth first) and return the first record found. The walk
    is iterative and remembers visited exceptions, so long or circular chains
    are handled.
    """
    seen: set[int] = set()
    pending: list[BaseException] = [exc]
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        phase = _recorded_phase(current)
        if phase is not None:
            return phase
        # Push ``__context__`` first so that ``__cause__`` is explored first.
        if current.__context__ is not None:
            pending.append(current.__context__)
        if current.__cause__ is not None:
            pending.append(current.__cause__)
    return None
