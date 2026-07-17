# Changelog

## 0.1.0

- **SME Full** is the default `sme-bench run` target (~156 cases: Core + all domain packs)
- `--suite PATH` runs a single pack (e.g. Core alone)
- Renamed former `sme-core-v0.2` → **`sme-core-v0.1`** (72 cases); removed legacy 24-case Core
- All released packs versioned consistently as **v0.1**
- Domain packs: Trades, E-Commerce, Financial, Hospitality, Logistics, Chains
- Root and suite READMEs rewritten as the source for a future website
- Bilingual run reports: `summary.de.md` / `summary.en.md`, `failures.de.md` /
  `failures.en.md`, `success.de.md` / `success.en.md`
- Partial grade, fairness scorers (`forbidden_terms` fields/`exclude_fields`, citations normalisation,
  order `keys`), `catalog`, `report --rescore`
- Test suite rework: split unit tests, parametrized scorers, coverage gate (≥76 %), E2E for
  `compare`, `list`, invalid-suite validation, and seed determinism

## Earlier history

Prior MVP and Core v0.2 development notes lived under interim changelog sections; the
public version line is now aligned on **0.1.0** for Core, Domains, and Full.
