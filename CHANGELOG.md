# Changelog

## 0.1.0

### Benchmark

- **SME Full** is the default `sme-bench run` target (~156 cases: Core + all domain packs)
- `--suite PATH` runs a single pack (e.g. Core alone)
- Renamed former `sme-core-v0.2` → **`sme-core-v0.1`** (72 cases); removed legacy 24-case Core
- All released packs versioned consistently as **v0.1**
- Domain packs: Trades, E-Commerce, Financial, Hospitality, Logistics, Chains
- Partial grade, fairness scorers (`forbidden_terms` fields/`exclude_fields`, citations normalisation,
  order `keys`), `catalog`, `report --rescore`

### Reports

- Bilingual run reports: `summary.de.md` / `summary.en.md`, `failures.de.md` /
  `failures.en.md`, `success.de.md` / `success.en.md`
- Case catalogue (`CASES.md`) generated in English

### Documentation

- Root and suite READMEs in English (basis for a future website)
- **[docs/AUTHORING_SUITES.md](docs/AUTHORING_SUITES.md)** — guide for custom suites and DE/EN case pairs
- Cursor rule for suite authoring (`.cursor/rules/suite-authoring.mdc`)

### Open source

- MIT License (Tim Dau, PLATZDORSCH Softwareentwicklung GmbH & Co. KG)
- GitHub: [PLATZDORSCH/sme-bench-eu](https://github.com/PLATZDORSCH/sme-bench-eu)
- CI workflow (ruff, mypy, pytest + coverage on Python 3.11/3.12)
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`
- Reproducible installs via committed `uv.lock`

### Tests

- Split unit tests into focused modules (models, utils, scorers, scoring, statistics, reporters, …)
- Parametrized scorer tests; coverage gate ≥76 % in CI
- E2E: `compare`, `list`, invalid-suite validation, seed determinism

## Earlier history

Prior MVP and Core v0.2 development notes lived under interim changelog sections; the
public version line is now aligned on **0.1.0** for Core, Domains, and Full.
