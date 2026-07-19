# Contributing to SME-Bench

Thanks for your interest in improving SME-Bench! Contributions of new cases,
suites, scorers, fixes, and docs are welcome.

## Development setup

Requirements: Python ≥ 3.11 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras --dev
```

## Quality gates

Please make sure these pass before opening a pull request:

```bash
uv run ruff check .
uv run mypy src
uv run pytest
```

CI runs the same checks on Python 3.11 and 3.12.

## Authoring suites and cases

New benchmark cases or suites must follow **[docs/AUTHORING_SUITES.md](docs/AUTHORING_SUITES.md)**.
Key rules:

- Deterministic scorers only — no LLM-as-a-Judge.
- Provide DE/EN pairs via a shared `pair_id`.
- Fixtures must be **synthetic or anonymized**; never commit real secrets or PII.
- Validate before submitting: `uv run sme-bench validate suites/<id>`

## Versioning and releases

See **[docs/VERSIONING.md](docs/VERSIONING.md)** (Deutsch: [VERSIONING.de.md](docs/VERSIONING.de.md)).

Summary:

- **Harness bugfixes** that do not change scores → patch release (same content line).
- **Prompt, case, fixture, expected, weights, or score-changing scorer fixes** → new version; runs are not comparable across content versions without an explicit label.
- Publish via annotated Git tags and [GitHub Releases](https://github.com/PLATZDORSCH/sme-bench-eu/releases); keep [`CHANGELOG.md`](CHANGELOG.md) in sync.

## Pull requests

1. Fork and create a feature branch.
2. Keep changes focused; update `CHANGELOG.md` when user-facing behaviour changes.
3. Add or update tests for code changes.
4. Ensure all quality gates pass.
5. Describe the motivation and scope in the PR description.
6. If the change affects benchmark scores or case content, call out the required version bump in the PR.

## Commit style

Small, focused commits with clear messages are preferred. Reference issues where
applicable (e.g. `Fixes #12`).

## Reporting bugs

Open an issue with reproduction steps, expected vs. actual behaviour, and
environment details (OS, Python version).

## License

By contributing, you agree that your contributions are licensed under the
[MIT License](LICENSE).
