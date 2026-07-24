# Changelog

## Unreleased

## 0.7.3

### Benchmark (SME Full content 0.8.0)

- Repeat outcomes now distinguish reliable (3/3), mostly successful (2/3), unreliable (1/3), and failed (0/3) cases in summaries, JSON rates (`failed_task_rate`), and failure reports
- SME Rank uses proportional attempt pass rate instead of treating 1/3 and 2/3 like 0/3
- Reasoning-only token-exhausted completions are retained as diagnostics but no longer shown or scored as final output
- Scoring fingerprints include scoring-spec version 0.5.0; model inputs are unchanged and existing runs remain regradable
- Compatibility manifest: [`regrade-0.8.0-baseline.json`](suites/compatibility/regrade-0.8.0-baseline.json)

### Tool 0.7.3

- Persist provider `finish_reason` in attempts and CSV reports
- Add reliability buckets (including 0/3) to summaries, reports, comparison output, and leaderboard
- Local website leaderboard shows a Thinking badge for thinking/reasoning runs

## 0.7.2

### Benchmark (SME Full content 0.7.0)

- Negated English refusal phrases such as `unable to promise/guarantee` no longer trigger critical forbidden-term failures
- Token-subset action matching accepts conservative English third-person forms (`send`/`sends`, `update`/`updates`)
- Reservation identifiers tolerate separated hash punctuation and extracted prices ignore terminal sentence punctuation
- Scoring fingerprints include scoring-spec version 0.4.0; all 196 inputs are unchanged and existing 0.6.0 runs are safely regradable
- Compatibility manifest: [`regrade-0.7.0-baseline.json`](suites/compatibility/regrade-0.7.0-baseline.json)

### Tool 0.7.2

- Persist scoring-spec version 0.4.0 in fresh, regraded, and merged run metadata

## 0.7.1

### Benchmark (SME Full content 0.6.0)

- Neutral PII output contracts for `de/en-pii-detection-001/002`; answer-like examples no longer contradict each case-specific expected label set
- PII-002 explicitly scopes detection to the forwarded CRM note, excluding unrelated mail headers and signatures
- Exactly four changed inputs; all model configurations require a selective 12-request delta before comparison
- Compatibility manifest: [`regrade-0.6.0-baseline.json`](suites/compatibility/regrade-0.6.0-baseline.json)

### Tool 0.7.1

- Regression coverage prevents answer-like PII label examples from returning

## 0.7.0

### Benchmark (SME Full content 0.5.0)

- Structural scoring contracts after GPT-5.4 audit: `must_pass` gates, broader process paraphrases, clarified SKU/PII/support prompts
- Exactly **14 input-changed cases** (PII-003, trades orders 001/002, eight support-001 pairs); remaining 182 inputs unchanged
- Trades order goldens use article codes without the `SKU` label; prefixed forms remain aliases
- Support rubrics make same-day / "today" asks explicitly `urgent`; adjacent priority credit stays partial-only via `must_pass`
- Missing-information `set_equality` is `must_pass` so schema points cannot override an incomplete field set
- Compatibility manifest: [`regrade-0.5.0-baseline.json`](suites/compatibility/regrade-0.5.0-baseline.json)

### Tool 0.7.0

- ScorerSpec `must_pass`: failed required scorers block a full pass while still allowing partial credit
- CLI `--task-ids` for selective delta runs; selection stored in `metadata.filters.task_ids`
- `merge-run` now rescores all merged attempts against the current suite before writing reports
- Historical helper script `scripts/rerun_changed_cases.sh` for selective OpenAI/Qwen deltas (superseded by CLI `run --task-ids` + `merge-run`; script removed from the tree)

## 0.6.3

### Benchmark (SME Full content 0.4.3)

- Structural scoring contracts for recurring false negatives (no input changes; still 196 cases)
- Meeting actions use `token_subset` matching: required task keywords may appear with filler words in any order
- Logistics process readiness scores `next_step` via action+phone regex contracts, not free-text equality
- Logistics order goldens use source size/colour form (`mittel/braun`, `medium/brown`) and accept colour-only aliases
- Compatibility manifest: [`regrade-0.4.3-baseline.json`](suites/compatibility/regrade-0.4.3-baseline.json)

### Tool 0.6.3

- `set_equality` supports `token_subset` key/match mode for deterministic multi-token concepts
- Leaderboard shows all present runs; status badges only (`regraded`, `ersetzt`/`superseded`, invalid)

## 0.6.2

### Benchmark (SME Full content 0.4.2)

- Patch release after Qwen 35B run audit: correct 39 clear false negatives, 12 overly harsh order scores, and 24 adjacent-priority false passes without changing inputs or case count
- Meeting actions and logistics process readiness accept confirmed, controlled paraphrases
- German grounded QA and order extraction accept equivalent currency/colour wording
- Complete customer replies may be concise (10 words / one sentence); required facts and forbidden-claim checks remain unchanged
- Trades orders now expect the exact source SKU including the written `SKU ` prefix
- Adjacent support priorities receive partial credit without crossing the 0.85 pass threshold
- Compatibility manifest: [`regrade-0.4.2-baseline.json`](suites/compatibility/regrade-0.4.2-baseline.json)

### Tool 0.6.2

- Case-migration tooling applies the 0.4.2 scorer and alias policy idempotently

## 0.6.1

### Benchmark (SME Full content 0.4.1)

- Patch release after Qwen 0.8B run audit: fix clear false positives/negatives without changing case count (still 196)
- Logistics process readiness now scores `next_step` + `missing`, not only `ready`
- Prompt-injection cases require exact `price` string (currency/format), not bare numerals
- Meeting task matching accepts confirmed paraphrases (`substring` + aliases); hospitality grounded alias `25 EUR`
- `forbidden_terms`: negated enumerations like „keine weiteren Zusagen (… bereits bezahlt)“ no longer false-critical
- Payment-reminder replies reject invented hold conditions (`will not process the payment` / missing confirmation claims)
- Compatibility manifest: [`regrade-0.4.1-baseline.json`](suites/compatibility/regrade-0.4.1-baseline.json)

### Tool 0.6.1

- `report --rescore` now hard-fails when the suite cannot be loaded, attempt task ids are unknown, or input fingerprints diverge
- Failure-report copy aligned with the real `unreliable` classifier; suite catalogue links point to `suites/*/CASES.md`

## 0.6.0

### Benchmark (SME Full content 0.4.0)

- **196 cases** in SME Full (72 Core + curated domain noise/edge variants; corridor ~180–210, no forced 324 quota)
- The 40 added domain variants passed pair review, deterministic golden checks, and representative calibration with GPT-5.6 Luna and GLM-5.2 Thinking
- Domain packs: noise `002` for grounded/order/meeting/reply families; edge `003` for grounded only (5 domains)
- Core `002` fixtures wrapped with realistic email/thread noise (inputs changed vs 0.3.0 for those cases)
- Safe expansion script never overwrites source fixtures; collisions abort hard
- Compatibility manifests: [`regrade-0.2.0-baseline.json`](suites/compatibility/regrade-0.2.0-baseline.json), [`regrade-0.3.0-baseline.json`](suites/compatibility/regrade-0.3.0-baseline.json), [`regrade-0.4.0-baseline.json`](suites/compatibility/regrade-0.4.0-baseline.json)

### Tool 0.6.0

- **`sme-bench merge-run`**: merge compatible partial runs; target must cover the current task-id set with matching input fingerprints
- Leaderboard filters by `suite_version` (default: explicitly released line); marks regraded/merged/invalid runs and excludes invalid runs from official ranking

## 0.5.0

### Benchmark (SME Full content 0.3.0)

- Restored load-bearing **156-case** baseline after isolating the broken 324-case expansion draft
- Scorer-only hardening (no input changes vs content 0.2.0): meetings `set_equality` + `key_aliases`, orders `variant` + field aliases, grounded QA answer field + citation `exact_set`, customer replies `text_structure` + claim-mode forbidden terms, IBAN `iban_used` normalization
- Localized grounded expecteds (`14 Tage`, `19%`, unicode range normalize)
- Positive scorer weights renormalized to 1.0; duplicate scorers removed; migration script idempotent
- Hard suite audits: duplicate scorers, weight sum, fingerprint uniqueness, variant message divergence, shared fixtures, DE/EN pair coverage

### Tool 0.5.0 / scoring

- Weighted pass semantics restored: pass iff weighted score ≥ threshold and no critical failure (`all_positive_passed` removed so `adjacent_credit` works)
- Citations: `exact_set` / duplicates / `max_count` are score-effective
- `json_fields`: controlled `text` / `percent` / `range` normalization (no semantic similarity)
- `forbidden_terms`: `mode=claims` + improved negation handling
- `sme-bench regrade` / `compat-report` / `fingerprints`; golden adversarial tests for Qwen false-negative patterns
- Invalid calibration run `qwen3.5-0.8b-new` documented under `runs/.invalid/` (exclude from leaderboards)

## 0.4.0

### Docs

- Terminology: **task packs** → **test suites** (README, authoring, versioning, suite READMEs)
- Example custom suite [`suites/demo-v0.1`](suites/demo-v0.1) (draft, not in SME Full)
- Default token budget / timeout and gpt-oss `reasoning_effort` example (README EN/DE);
  mid-CoT truncation symptom documented

### Benchmark

- Prompt-injection / secret cases: `expected` now includes `price` (as in the
  fixture) so success/failure reports match the schema and prompt; scoring
  unchanged (`json_fields` still checks `action`/`safe`, price via `contains`)

### Tool

- Strip leaked chain-of-thought from model `content` (Qwen-style thinking dumps /
  `<think>` blocks) before scoring; store CoT in `reasoning_text` when present
- Thinking split prefers post-delimiter answer (no mid-CoT JSON fishing); JSON
  ranking uses payload size so prompt anti-examples do not win
- `report --rescore` re-derives answers from stored `reasoning_text` when needed
- Default `--max-tokens-min 8192` and `--timeout 300` for all runs (disable floor
  with `--max-tokens-min 0`); avoids truncating reasoning models on short suite budgets
- Failure reports: mixed Pass + Hard-Fail cases are labelled **unzuverlässig** /
  **unreliable** (not blanket *fehlgeschlagen*); Reliable Pass / Rank unchanged

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
- Core + domain packs (trades, ecommerce, financial, hospitality, logistics, chains)
- Deterministic scorers with weighted pass / partial / critical gates
- DE/EN pair coverage and suite validation

### Tool

- CLI: `run`, `validate`, `report`, `catalog`
- OpenAI-compatible async client, repeats, resume, rich reports
