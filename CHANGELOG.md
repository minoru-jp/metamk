# metamk Changelog

Records the change history of `metamk` by version. Versions before `0.1.0` (`0.0.x`) used the old design and are not carried over into this changelog.

## V0_1_0

A redesign from scratch. It has no compatibility whatsoever with the old design `0.0.x`.

version: 0.1.0

released on: 2026-10-05

Added:

- Added `Mk.PREPARE`, `Mk.MAIN`, and `Mk.VERIFY`. They are `with` blocks that divide test code into prepare, target, and verify. When an exception passes through, they record the name of the phase it passed through on the exception and add the note `[metamk] failed in <phase>`. The exception is not swallowed or replaced and is re-raised as is.
- Added `phase_of(exc)`. It retrieves the phase name recorded on an exception. It follows the chain through the exception itself, `__cause__`, and `__context__` in that order.
- Added support for asynchronous code. Because `await` can be used inside a `with` block, no asynchronous-specific API is provided.
- Added GitHub Actions workflows: the reusable `checks.yml` (ruff, basedpyright, and pytest on Python 3.11 through 3.14), `ci.yml`, which runs on pushes and pull requests, and `release.yml`, which runs when a GitHub Release is published. `release.yml` publishes through PyPI Trusted Publishing only what has passed the checks, the tag and version match, and the verification of the distributions.
- Introduced a documentation system based on `shikumi-devdoc`. The canonical sources and canonical documents are written in Japanese under `devdocs/`, and the top-level README, STATUS, and CHANGELOG are published as their English translations.

Changed:

- Redesigned from scratch. The purpose is narrowed to "making the structure of a test explicit and leaving the failed phase on the exception", and the runtime machinery is kept to a minimum.
- Raised the supported Python to 3.11 or later. `BaseException.add_note()` is used to attach notes to exceptions.

Removed:

- Removed `Mark`, which validated phase order with a state machine, as well as `Phase`, `PhaseError`, and the hooks (`on_result`, `on_positive`, `on_negative`, `on_error_in_phase_block`, `on_phase_transition_error`).
- Removed the phases `invariant`, `setup`, `before`, `cleanup`, `after`, `final`, and `invoke`, and the corresponding `as_*_block`. The phases are narrowed to the three: PREPARE, MAIN, and VERIFY.
- Removed the call forms that accepted a function or an awaitable and evaluated its truthiness (`before`, `after`, `invariant`), and `MAIN(value)`, which accepted a value. The target code is now written not as a value but as a `with Mk.MAIN:` block.
- Removed the asynchronous-specific namespace `Mk.a`.
