# Changelog

## Unreleased

### Docs

- Terminology: **task packs** → **test suites** (README, authoring, versioning, suite READMEs)
- Example custom suite [`suites/demo-v0.1`](suites/demo-v0.1) (draft, not in SME Full)

### Benchmark

- Prompt-injection / secret cases: `expected` now includes `price` (as in the
  fixture) so success/failure reports match the schema and prompt; scoring
  unchanged (`json_fields` still checks `action`/`safe`, price via `contains`)

### Tool

- Strip leaked chain-of-thought from model `content` (Qwen-style thinking dumps /
  `<think>` blocks) before scoring; store CoT in `reasoning_text` when present
- `extract_json_payload` tries all fences (prefer `json`), then the richest
  top-level JSON object — fixes false fails when CoT quotes source text in a fence
- `report --rescore` rewrites cleaned `output_text` (and fills `reasoning_text`)
  so existing thinking runs can be re-graded without a full re-run

## 0.3.0

### Ranking

- Partial-rate penalty in SME Rank Score reduced from `k=2` to `k=0.5` (milder tie-breaker; critical stays `k=5`)
- Formula: `Core × Reliable Pass × max(0, 1 − 5 × critical_rate) × max(0, 1 − 0.5 × partial_rate)`

## 0.2.0

### Benchmark

- `contains` scorer accepts alternative term groups (any match satisfies the group)
- Loosened payment-phrasing requirements in `en/de-customer-reply-003`
- Suite pack `version` fields and Full suite bumped to **0.2.0** (folder ids remain `*-v0.1`)
- Leaderboard results after rescore align with this content line

### Tool

- OpenAI client: `max_completion_tokens` for GPT-5/4o/4.1/o-series; omit `temperature` for GPT-5/o-series
- Ruff SIM103 cleanup in `forbidden_terms`

## 0.1.0

### Benchmark

- **SME Full** is the default `sme-bench run` target (~156 cases: Core + all domain packs)
- `--suite PATH` runs a single pack (e.g. Core alone)
- Renamed former `sme-core-v0.2` → **`sme-core-v0.1`** (72 cases); removed legacy 24-case Core
- All released packs versioned consistently as **v0.1**
- Domain packs: Trades, E-Commerce, Financial, Hospitality, Logistics, Chains
- Partial grade, fairness scorers (`forbidden_terms` fields/`exclude_fields`, citations normalisation,
  order `keys`), `catalog`, `report --rescore`
- Sharpened case prompts where existing runs showed format ambiguity (PII label strings, `missing` as array, invoice amounts as numbers, grounded citation IDs, missing-field semantics, exact SKUs, fulfill `address` token, trades support category)
- Fixed corrupted system prompts (YAML leakage into `content`); reformulated grounded prompts without naming wrong keys; removed meta annotations from missing-info fixtures; clarified product-normalization vocab mapping
- Grounded prompts: concrete JSON example shape; missing-info: clarify empty array semantics; product size mapping examples (`medium`→`M`)
- CLI `--enable-thinking` sets `chat_template_kwargs.enable_thinking=true` (Qwen/vLLM/LiteLLM); pair with `--max-tokens-mult` / `--max-tokens-min`
- Restored missing `.env` loader module used by the CLI

### Reports

- Bilingual run reports: `summary.de.md` / `summary.en.md`, `failures.de.md` /
  `failures.en.md`, `success.de.md` / `success.en.md`
- Case catalogue (`CASES.md`) generated in English
- **SME Rank Score** for leaderboard ordering: Core × Reliable Pass × critical (`k=5`) and partial (`k=2`) rate penalties; Core Score remains the unpenalised quality metric

### Documentation

- Root and suite READMEs in English and German
- **[docs/AUTHORING_SUITES.md](docs/AUTHORING_SUITES.md)** — guide for custom suites and DE/EN case pairs
- **[docs/VERSIONING.md](docs/VERSIONING.md)** — release policy (tool vs. benchmark content)

### Open source

- MIT License (Tim Dau, PLATZDORSCH Softwareentwicklung GmbH & Co. KG)
- GitHub: [PLATZDORSCH/sme-bench-eu](https://github.com/PLATZDORSCH/sme-bench-eu)
- CI workflow (ruff, mypy, pytest + coverage on Python 3.11/3.12)
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`
- Reproducible installs via committed `uv.lock`
- First GitHub Release: **v0.1.0**

### Tests

- Split unit tests into focused modules (models, utils, scorers, scoring, statistics, reporters, …)
- Parametrized scorer tests; coverage gate ≥76 % in CI
- E2E: `compare`, `list`, invalid-suite validation, seed determinism

## Earlier history

Prior MVP and Core v0.2 development notes lived under interim changelog sections; the
public version line is now aligned on **0.1.0** for Core, Domains, and Full.
