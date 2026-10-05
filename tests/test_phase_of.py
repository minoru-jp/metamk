"""phase_of() (README: "Retrieving the phase name")."""

from __future__ import annotations

import pytest

from metamk import Mk, phase_of


def recorded(phase, message="recorded"):
    """Return an exception that has passed through ``phase``."""
    error = ValueError(message)
    try:
        with phase:
            raise error
    except ValueError:
        pass
    return error


def test_returns_none_when_nothing_is_recorded():
    assert phase_of(ValueError("plain")) is None


@pytest.mark.parametrize("name", ["PREPARE", "MAIN", "VERIFY"])
def test_returns_the_recorded_phase_name(name):
    phase = getattr(Mk, name)
    assert phase_of(recorded(phase)) == name


def test_own_record_wins_over_the_chain():
    top = recorded(Mk.VERIFY)
    top.__cause__ = recorded(Mk.PREPARE)
    top.__context__ = recorded(Mk.MAIN)
    assert phase_of(top) == "VERIFY"


def test_cause_is_followed_before_context():
    top = ValueError("top")
    top.__cause__ = recorded(Mk.PREPARE)
    top.__context__ = recorded(Mk.VERIFY)
    assert phase_of(top) == "PREPARE"


def test_context_is_followed_when_there_is_no_cause():
    top = ValueError("top")
    top.__context__ = recorded(Mk.MAIN)
    assert phase_of(top) == "MAIN"


def test_chain_is_explored_depth_first():
    # top --cause--> middle --context--> PREPARE
    # top --context--> VERIFY
    # The cause's whole subtree is explored before the context.
    middle = ValueError("middle")
    middle.__context__ = recorded(Mk.PREPARE)
    top = ValueError("top")
    top.__cause__ = middle
    top.__context__ = recorded(Mk.VERIFY)
    assert phase_of(top) == "PREPARE"


def test_circular_chain_terminates():
    first, second = ValueError("first"), ValueError("second")
    first.__context__ = second
    second.__context__ = first
    assert phase_of(first) is None


def test_circular_chain_still_finds_a_record():
    first, second = ValueError("first"), recorded(Mk.MAIN)
    first.__context__ = second
    second.__context__ = first
    assert phase_of(first) == "MAIN"


@pytest.mark.parametrize("with_record", [False, True])
def test_very_long_chain_does_not_exhaust_the_recursion_limit(with_record):
    current = recorded(Mk.MAIN) if with_record else ValueError("bottom")
    for _ in range(5000):  # far beyond the default recursion limit
        wrapper = ValueError("wrapper")
        wrapper.__context__ = current
        current = wrapper
    assert phase_of(current) == ("MAIN" if with_record else None)
