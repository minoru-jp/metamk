"""Asynchronous code (README: "Asynchronous code")."""

from __future__ import annotations

import asyncio

from metamk import Mk, phase_of


def test_await_works_inside_the_blocks():
    async def scenario():
        with Mk.PREPARE:
            await asyncio.sleep(0)
            data = [1, 2, 3]
        with Mk.MAIN:
            await asyncio.sleep(0)
            total = sum(data)
        with Mk.VERIFY:
            await asyncio.sleep(0)
            assert total == 6
        return total

    assert asyncio.run(scenario()) == 6


def test_failure_after_an_await_is_recorded():
    async def scenario():
        error = ValueError("boom")
        try:
            with Mk.MAIN:
                await asyncio.sleep(0)
                raise error
        except ValueError:
            pass
        return error

    error = asyncio.run(scenario())
    assert phase_of(error) == "MAIN"
    assert error.__notes__ == ["[metamk] failed in MAIN"]


def test_concurrent_tasks_share_the_same_instances():
    async def task(delay, phase):
        error = ValueError("boom")
        try:
            with phase:
                await asyncio.sleep(delay)
                raise error
        except ValueError:
            pass
        return error

    async def scenario():
        return await asyncio.gather(
            task(0.03, Mk.PREPARE), task(0.02, Mk.MAIN), task(0.01, Mk.VERIFY)
        )

    errors = asyncio.run(scenario())
    assert [phase_of(error) for error in errors] == ["PREPARE", "MAIN", "VERIFY"]
    assert all(len(error.__notes__) == 1 for error in errors)


def test_timeout_converts_the_exception_but_phase_of_still_finds_main():
    async def scenario():
        try:
            async with asyncio.timeout(0.01):
                with Mk.MAIN:
                    await asyncio.sleep(10)
        except TimeoutError as error:
            return error
        raise AssertionError("timeout did not occur")

    error = asyncio.run(scenario())
    assert isinstance(error, TimeoutError)
    assert phase_of(error) == "MAIN"


def test_cancellation_is_recorded():
    async def scenario():
        started = asyncio.Event()

        async def worker():
            with Mk.MAIN:
                started.set()
                await asyncio.sleep(10)

        task = asyncio.create_task(worker())
        await started.wait()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError as error:
            return error
        raise AssertionError("task was not cancelled")

    assert phase_of(asyncio.run(scenario())) == "MAIN"


def test_exception_in_a_task_group_child_is_recorded_on_the_leaf():
    async def scenario():
        async def child():
            with Mk.MAIN:
                await asyncio.sleep(0)
                raise ValueError("child")

        leaves = []
        try:
            async with asyncio.TaskGroup() as group:
                group.create_task(child())
        except* ValueError as group_error:
            leaves = list(group_error.exceptions)
        return leaves

    leaves = asyncio.run(scenario())
    assert [phase_of(leaf) for leaf in leaves] == ["MAIN"]
