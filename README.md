# metamk

`metamk` is a very small library that divides test code into three phases — **prepare (PREPARE), target (MAIN), and verify (VERIFY)** — and records, on an exception passing through, the phase in which it failed.

The division is written as `with` blocks, so the role of each part is clear just from reading the code. At runtime it does nothing. It does not change control flow, swallow exceptions, or replace them.

> [!NOTE]
> The current version `0.1.0` is a redesign from scratch. This README is the basis for the implementation. See [STATUS](https://github.com/minoru-jp/metamk/blob/main/STATUS.md) for the state of the implementation and [CHANGELOG](https://github.com/minoru-jp/metamk/blob/main/CHANGELOG.md) for the differences from earlier versions.

## What it aims to solve

A test body mixes three different kinds of code.

- Preparation for running the test target
- The thing you actually want to test (the call to the test target)
- Checking its result

When these are lined up without distinction, a failing test forces you to work out from the traceback and the code whether the preparation was faulty, the target is broken, or the expectation is wrong. A reader also cannot tell at a glance which line is the one that is "really being tested". pytest distinguishes failures in fixtures from failures in the test body, but not inside the test function.

`metamk` writes this distinction into the structure of the code and also leaves it on the failing exception.

## Minimal example

```python
from metamk import Mk


def test_example():
    with Mk.PREPARE:
        data = {"x": 1, "y": 2}

    with Mk.MAIN:
        result = data["x"] + data["y"]

    with Mk.VERIFY:
        assert result == 3
```

If an `assert` inside `with Mk.VERIFY:` fails (when `result == 4` is written in the example above), pytest's failure output gains a line like this:

```text
>           assert result == 4
E           assert 3 == 4
E           [metamk] failed in VERIFY
```

When an exception occurs in `PREPARE` or `MAIN`, the output likewise shows `failed in PREPARE` or `failed in MAIN`.

## The three phases

Each phase is defined not by its purpose but by its **position relative to MAIN**.

| Phase | Position | What a failure means |
| --- | --- | --- |
| `PREPARE` | Before MAIN. Establishes a state in which MAIN can run | The problem lies in the environment or in how the test is written, not in the test target |
| `MAIN` | The thing to be tested itself. One per test | The test target failed |
| `VERIFY` | After MAIN. Checks the result of MAIN | The target ran, but the result differs from the expectation |

The vocabulary is limited to three to leave as little room as possible for hesitation about which to use. `metamk` checks neither the order of phases nor the number of MAIN blocks. "One MAIN" and "PREPARE, MAIN, VERIFY in that order" are conventions and are not enforced.

### There is no cleanup phase

A `with` block does not change control flow, so if MAIN raises an exception, the following blocks are never reached. Giving a name such as `CLEANUP`, which suggests a section that "always runs", therefore could not satisfy that expectation. For cleanup, use pytest fixtures or `try` / `finally`.

## Behavior guarantees

A phase block (such as `with Mk.PREPARE:`) behaves as follows.

- When the block ends normally, nothing happens.
- When an exception passes through the block, (1) the name of the phase it passed through is recorded on the exception and (2) the note `[metamk] failed in <phase>` is added, and the exception is re-raised as is. It is not swallowed or replaced, and the traceback is not changed. The note is added with `BaseException.add_note()`.
- When an exception passes through multiple phases (for example, nested blocks), only the innermost phase is recorded, and the note is added only once.
- If the same exception object later passes through a different phase, the record remains the first phase.
- The kind of exception does not matter. Everything that inherits from `BaseException` is covered, including `asyncio.CancelledError`.
- If recording or adding the note fails, it does not prevent the original exception from being raised.
- It holds no state. It does not remember the order or number of phases or which phase it is currently in, and it checks none of them.

## Asynchronous code

`await` can be used inside a `with` block, so there is no separate API for asynchronous code (`async with` is not needed). `metamk` itself never awaits anything.

```python
import asyncio

from metamk import Mk


async def test_async_example():
    with Mk.PREPARE:
        await asyncio.sleep(0)
        data = [1, 2, 3]

    with Mk.MAIN:
        await asyncio.sleep(0)
        total = sum(data)

    with Mk.VERIFY:
        assert total == 6
```

Because it holds no state, using the same `Mk.MAIN` and the like concurrently from multiple tasks or threads does not cause interference.

Phases cannot be used as decorators. Providing a form that decorates a function in a straightforward way would exit the block as soon as the coroutine object is created for an asynchronous function, so nothing would be recorded.

## Retrieving the phase name

The phase name recorded on an exception can be retrieved with `phase_of()`. Use it when you want to handle it mechanically, such as in a pytest report, rather than reading the human-readable note.

```python
from metamk import Mk, phase_of

try:
    with Mk.MAIN:
        raise ValueError("boom")
except ValueError as e:
    assert phase_of(e) == "MAIN"
```

`phase_of(exc)` returns one of `"PREPARE"`, `"MAIN"`, or `"VERIFY"`, or `None` if nothing is recorded. If the exception itself has no record, it follows the chain through `__cause__` and then `__context__` and returns the first record found (it terminates even if the chain is circular).

The chain is followed because an exception may be converted into another exception. For example, when MAIN inside `asyncio.timeout()` times out, the `CancelledError` that passed through MAIN is converted to a `TimeoutError` outside. The converted exception carries no record, but the original exception remains in `__context__`, so `phase_of()` can return `"MAIN"`.

## Giving aliases

`Mk.PREPARE` and the others are plain attributes, so the caller can give them aliases.

```python
from metamk import Mk

PREPARE, MAIN, VERIFY = Mk.PREPARE, Mk.MAIN, Mk.VERIFY


def test_example():
    with PREPARE:
        data = [1, 2, 3]

    with MAIN:
        total = sum(data)

    with VERIFY:
        assert total == 6
```

The recorded phase names are `"PREPARE"`, `"MAIN"`, and `"VERIFY"` regardless of the alias.

## What it does not do

`metamk` does not do the following.

- Swallow, replace, or convert exceptions.
- Evaluate the truthiness of a result. How you write verification (such as `assert`) is up to you.
- Enforce the order or number of phases.
- Guarantee that cleanup is run.
- Provide hooks or configuration.
- Provide a pytest plugin (not provided at present; see [STATUS](https://github.com/minoru-jp/metamk/blob/main/STATUS.md)).

## Installation and requirements

```bash
pip install metamk
```

Python `>=3.11` is required. It uses only the standard library and has no external dependencies. It is provided with type annotations and ships the PEP 561 `py.typed` marker.

## Documentation

The documentation of this repository is managed with [shikumi-devdoc](https://github.com/minoru-jp/shikumi-devdoc). The canonical sources and the canonical documents generated from them are in `devdocs/` and are written in Japanese. The top-level published documents are English translations of those canonical documents.

- [STATUS](https://github.com/minoru-jp/metamk/blob/main/STATUS.md): current development status
- [CHANGELOG](https://github.com/minoru-jp/metamk/blob/main/CHANGELOG.md): change history

## License

MIT License. See [`LICENSE`](https://github.com/minoru-jp/metamk/blob/main/LICENSE).
