# metamk Project Status

Describes the current state of `metamk` and notices about the future from the current point of view.
Past state changes are not retained; user-facing changes that actually occurred are the responsibility of the CHANGELOG.

## STATUS_001

The current development stage is Alpha. The current public version is `0.1.0`, a redesign from scratch.

title: Development stage

## STATUS_002

The supported Python range is `>=3.11`. This is because `BaseException.add_note()`, which is used to attach notes to exceptions, was introduced in 3.11.

title: Supported Python

## STATUS_003

The design of `metamk` is described in the README. The README is the basis for the implementation, and the implementation follows the README's description. If the README and the implementation disagree, the README's description is reviewed first, not the implementation.

The implementation follows the README's description. The README's code examples and output examples, each item of the behavior guarantees, and the public names are verified by the tests in `tests/`.

title: Design and implementation

## STATUS_004

The `0.0.x` versions already published on PyPI use the old design and are not compatible with `0.1.0`. The old design's `Mk` / `Mark` and their phases, hooks, and asynchronous layer have not been carried over. See the CHANGELOG for details of the changes.

title: Relationship to 0.0.x

## STATUS_005

Documents are managed with `shikumi-devdoc`. The canonical sources are in `devdocs/canonical_sources/` and the canonical documents generated from them are in `devdocs/canonical_documents/`; both are written in Japanese. The README, STATUS, and CHANGELOG at the top level of the repository are published documents that translate those canonical documents into English. Translation is not a feature of `shikumi-devdoc`; it is handled by this repository's publication workflow. The canonical documents are generated with the optional dependency `docs` (`shikumi-devdoc`).

title: Documentation system

## STATUS_006

Development uses ruff for formatting and linting, basedpyright for type checking, and pytest for testing. ruff is pinned to `0.16.10` and basedpyright to `1.40.2`, declared as the optional dependencies `lint` and `typecheck` respectively. pytest is declared as `test` with `>=8.0`. None of them is a runtime dependency.

title: Development tools

## STATUS_007

`ruff format --check .`, `ruff check .`, `basedpyright`, `basedpyright -p tests/typing`, and `pytest` are all clean. `src/metamk` is checked with basedpyright's default settings (recommended), and the consumer-side typing contract (names assigned inside a `with` block must not be reported as "possibly unbound") is checked in standard mode under `tests/typing`; both report 0 errors / 0 warnings.

Because publication through the release workflow requires all checks to succeed, the published version has passed every check, including pytest on Python 3.11 through 3.14.

title: Quality checks

## STATUS_008

Distribution is through PyPI, and the source repository is public on [GitHub](https://github.com/minoru-jp/metamk).

GitHub Actions quality checks are consolidated in the reusable `checks.yml`. It runs the ruff format check and lint, basedpyright (for `src/metamk` and `tests/typing`), and pytest on Python 3.11 through 3.14. On CI a missing tool is treated as a failure rather than a reason to skip a test.

The normal CI (`ci.yml`) calls these shared checks on pushes and pull requests to `main`, and also builds the wheel and sdist and verifies them with `scripts/check_dist.py`. The verification covers that the wheel contents are as expected, that there are no runtime dependencies, `twine check --strict`, and installing into a separate virtual environment to confirm that it works.

When a GitHub Release is published, the release workflow (`release.yml`) first runs the same shared checks. Only if all of them succeed does it confirm that the tag matches `v<project version>` and that the CHANGELOG has an entry for that version, build and verify the wheel and sdist, and publish only those verified artifacts through PyPI Trusted Publishing. No PyPI API token is stored.

References to GitHub Actions are pinned to commit SHAs and updated by Dependabot.

Registering the Trusted Publisher on PyPI and creating the `pypi` environment on GitHub are settings outside the repository. `0.1.0` was published through this release workflow.

title: Distribution and CI status

## NOTICE_001

A mechanism that reflects the phase name recorded on an exception in pytest reports (such as distinguishing error from failure) is not provided at present. The phase name can be retrieved mechanically with `phase_of()`, but how to integrate with pytest has not been decided.

title: pytest integration is undecided

kind: General

condition: Until the direction of the integration is decided.

## NOTICE_002

Between `0.1.0` and 1.0, the public API may change without notice.

title: API stability before 1.0

kind: General

condition: Until the first major version is released.
