"""Behavior guarantees of the phase blocks (README: "Behavior guarantees")."""

from __future__ import annotations

import asyncio
import pickle
import threading
import traceback

import pytest

from metamk import Mk, phase_of

PHASES = [
    pytest.param("PREPARE", Mk.PREPARE, id="PREPARE"),
    pytest.param("MAIN", Mk.MAIN, id="MAIN"),
    pytest.param("VERIFY", Mk.VERIFY, id="VERIFY"),
]


def note(name: str) -> str:
    return f"[metamk] failed in {name}"


# --- "When the block ends normally, nothing happens." ---------------------


@pytest.mark.parametrize(("name", "phase"), PHASES)
def test_normal_exit_does_nothing(name, phase):
    with phase:
        value = 1
    assert value == 1


# --- "(1) the phase name is recorded and (2) the note is added" ------------


@pytest.mark.parametrize(("name", "phase"), PHASES)
def test_records_phase_name_and_adds_note(name, phase):
    error = ValueError("boom")
    with pytest.raises(ValueError) as info, phase:
        raise error
    assert phase_of(error) == name
    assert error.__notes__ == [note(name)]
    assert info.value is error


def test_notes_added_by_others_are_kept():
    error = ValueError("boom")
    error.add_note("added by the user")
    with pytest.raises(ValueError), Mk.MAIN:
        raise error
    assert error.__notes__ == ["added by the user", note("MAIN")]


# --- "re-raised as is: not swallowed or replaced, traceback not changed" ---


def test_exception_is_neither_replaced_nor_wrapped():
    error = KeyError("k")
    with pytest.raises(KeyError) as info, Mk.PREPARE:
        raise error
    assert info.value is error
    assert error.args == ("k",)
    assert error.__cause__ is None
    assert error.__context__ is None


def test_traceback_has_no_metamk_frame():
    def target():
        with Mk.MAIN:
            raise ValueError("boom")

    with pytest.raises(ValueError) as info:
        target()
    frames = traceback.extract_tb(info.value.__traceback__)
    assert [frame.name for frame in frames] == [
        "test_traceback_has_no_metamk_frame",
        "target",
    ]


# --- "only the innermost phase is recorded, and the note is added once" ----


def test_nested_blocks_record_only_the_innermost_phase_once():
    with pytest.raises(KeyError) as info, Mk.VERIFY, Mk.MAIN:
        raise KeyError("k")
    assert phase_of(info.value) == "MAIN"
    assert info.value.__notes__ == [note("MAIN")]


# --- "the record remains the first phase" ----------------------------------


def test_same_exception_object_keeps_the_first_phase():
    error = RuntimeError("r")
    for phase in (Mk.PREPARE, Mk.VERIFY):
        with pytest.raises(RuntimeError), phase:
            raise error
    assert phase_of(error) == "PREPARE"
    assert error.__notes__ == [note("PREPARE")]


# --- "Everything that inherits from BaseException is covered" --------------


@pytest.mark.parametrize(
    "error",
    [
        KeyboardInterrupt(),
        SystemExit(1),
        GeneratorExit(),
        asyncio.CancelledError(),
        ExceptionGroup("group", [ValueError("inner")]),
    ],
    ids=lambda error: type(error).__name__,
)
def test_every_base_exception_is_covered(error):
    with pytest.raises(type(error)), Mk.MAIN:
        raise error
    assert phase_of(error) == "MAIN"


# --- "Failing to record does not prevent the original exception" -----------


def test_failing_add_note_does_not_hide_the_original_exception():
    class NoteFails(Exception):
        def add_note(self, note: str) -> None:
            raise RuntimeError("add_note failed")

    error = NoteFails("original")
    with pytest.raises(NoteFails) as info, Mk.MAIN:
        raise error
    assert info.value is error


def test_unusable_notes_attribute_does_not_hide_the_original_exception():
    error = ValueError("original")
    error.__notes__ = "not a list"  # makes add_note() fail
    with pytest.raises(ValueError) as info, Mk.MAIN:
        raise error
    assert info.value is error


# --- "It holds no state" ---------------------------------------------------


def test_order_and_count_of_phases_are_not_checked():
    for phase in (Mk.VERIFY, Mk.MAIN, Mk.MAIN, Mk.PREPARE, Mk.MAIN):
        with phase:
            pass


def test_instances_are_shared_safely_between_threads():
    barrier = threading.Barrier(3)
    errors: dict[str, ValueError] = {}

    def worker(name, phase):
        error = ValueError(name)
        try:
            with phase:
                barrier.wait(timeout=5)  # all threads are inside a block at once
                raise error
        except ValueError:
            pass
        errors[name] = error

    threads = [
        threading.Thread(target=worker, args=(name, phase))
        for name, phase in (
            ("PREPARE", Mk.PREPARE),
            ("MAIN", Mk.MAIN),
            ("VERIFY", Mk.VERIFY),
        )
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert set(errors) == {"PREPARE", "MAIN", "VERIFY"}
    for name, error in errors.items():
        assert phase_of(error) == name
        assert error.__notes__ == [note(name)]


# --- "Phases cannot be used as decorators" ---------------------------------


def test_phases_are_not_callable():
    for phase in (Mk.PREPARE, Mk.MAIN, Mk.VERIFY):
        assert not callable(phase)


def test_phases_cannot_decorate_functions():
    with pytest.raises(TypeError):

        @Mk.MAIN
        def decorated():
            pass


# --- Not promised by the README, but valuable: the record survives pickling,
# --- e.g. when pytest-xdist sends an exception between processes.


def test_record_survives_pickling():
    error = ValueError("boom")
    with pytest.raises(ValueError), Mk.MAIN:
        raise error
    restored = pickle.loads(pickle.dumps(error))
    assert phase_of(restored) == "MAIN"
    assert restored.__notes__ == [note("MAIN")]
