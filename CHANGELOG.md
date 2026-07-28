# Changelog

## Unreleased

<!-- Add notes here; move into a version section at release. -->

## 0.7.11

### Scoring specification 0.6.3

- `forbidden_terms` with `ignore_negated` treats long existential refusals as safe: English `there is/are no …, or TERM` / German `es gibt kein…` list items, and post-negation `nicht erfüllen` / `nicht bestätigen` (and EN counterparts). Fixes false criticals when models correctly deny invented payment claims in a longer list or refusal clause
- Model inputs and suite content are unchanged (`suite_version` stays 0.10.3); existing 0.10.x runs are regradable

### Tool 0.7.11

- Package bump for scoring-spec 0.6.3

## 0.7.10

### Benchmark (SME Full content 0.10.3)

- Trades order prompts clarify that a colour/size named in the item text (e.g. "Sockelleiste weiß" / "white skirting") must be extracted as `variant`, not `none`
- **Input change** on `de/en-tr-order-001` and `de/en-tr-order-002` only — regrade of full 0.10.2 runs is blocked; use a 4-task delta run + `merge-run`
- Compatibility manifest: [`regrade-0.10.3-baseline.json`](suites/compatibility/regrade-0.10.3-baseline.json)

### Tool 0.7.10

- Package bump for content 0.10.3

## 0.7.9

### Scoring specification 0.6.2

- `forbidden_terms` with `ignore_negated` treats correlative refusals as safe: German `weder … noch` and English `neither … nor` (plus `weder`/`neither`/`nor` as negators). Fixes false criticals when models correctly refuse invented perks

### Benchmark (SME Full content 0.10.2)

- Order `variant` aliases: accept `black/95` and `schwarz/95` for expected `95/black` (fixture order is colour then length)
- Only scorer params / scorer semantics change for these; model inputs unchanged → regradable from 0.10.1
- Compatibility manifest: [`regrade-0.10.2-baseline.json`](suites/compatibility/regrade-0.10.2-baseline.json)

### Tool 0.7.9

- Package bump for scoring-spec 0.6.2 and content 0.10.2

## 0.7.8

### Benchmark (SME Full content 0.10.1)

- Hospitality booking replies accept guest-count as digit or word: `4` / `four` / `vier`. Models that write "four covers" or "vier Personen" were previously failed by a digit-only `contains` check
- Only scorer params change on four cases; model inputs are unchanged, so existing 0.10.x runs are regradable
- Compatibility manifest: [`regrade-0.10.1-baseline.json`](suites/compatibility/regrade-0.10.1-baseline.json)

### Tool 0.7.8

- Package bump for content 0.10.1

## 0.7.7

### Scoring specification 0.6.1

- The `citations` scorer extracts a leading bracketed section ID when a model pastes the whole policy line (`[V-1] Standardsteuersatz…` → `V-1`). Clean IDs and bare `[V-1]` forms stay accepted; wrong IDs and numeric placeholders such as `[1]` still fail
- Model inputs and suite content are unchanged (`suite_version` stays 0.10.0); existing 0.10.0 runs are regradable

### Tool 0.7.7

- Package bump for scoring-spec 0.6.1

## 0.7.6

### Benchmark (SME Full content 0.10.0)

- Grounded-QA system prompts no longer use `SEC-1` as the citation example shape. Domain packs use real IDs such as `R-2` / `H-2` / `L-2` / `V-2`, so the shared example was a misleading format cue that weaker models copied instead of citing the policy
- Example shape is now prefix-neutral: `{"answer":"…","citations":["ID-1"]}`. Core cases that genuinely use `SEC-*` IDs are unchanged in the policy body
- Only the 36 grounded-QA input fingerprints change. From content 0.9.0, use `sme-bench run --task-ids …` on those cases and `merge-run`; full reruns are only needed for models that still fail by inventing `SEC-*` on domain packs
- Compatibility manifest: [`regrade-0.10.0-baseline.json`](suites/compatibility/regrade-0.10.0-baseline.json)

### Tool 0.7.6

- Package bump for the content 0.10.0 line

## 0.7.5

### Benchmark (SME Full content 0.9.0)

- Every case now states its answer language in the prompt. Grading a German case against German expected values while the prompt never asked for German was a specification gap, and it produced failures that looked like scorer bugs
- New `language` scorer on all 196 cases with `weight: 0` and `must_pass: true`: a language break leaves the SME Core Score untouched but blocks the attempt from passing. Any positive weight would renormalise the other scorers and dilute real errors
- The check counts function words unambiguous for one language and fails only when the wrong language leads by two markers. The threshold is validated against every case's own expected answer; a stricter setting fails cases against their own reference. Short English phrases without function words (`update inventory`) stay undetected
- JSON keys are never scanned. Injection and security cases exclude `reason`, where a refusal legitimately quotes the English payload it refused, matching the existing `forbidden_terms` exclusion; offer comparison excludes the unscored `reasons` field whose canonical values are language-neutral tokens
- All 196 input fingerprints changed, so runs on content 0.8.0 or earlier require a **rerun**, not a regrade
- Compatibility manifest: [`regrade-0.9.0-baseline.json`](suites/compatibility/regrade-0.9.0-baseline.json)
- Known gap: the curated-candidate calibration in `calibration-0.4.0.json` is pinned to content 0.4.0 and needs a fresh run for 0.9.0; the calibrated candidate set is still verified against the shipped set

### Tool 0.7.5

- Add the `language` scorer with `expected`, `fields`, `exclude_fields`, and `margin` params
- Report `language_compliance_rate` in summaries, markdown and console reports, and `sme-bench compare`; it is `null` for runs graded before content 0.9.0 so an absent check is not read as total non-compliance
- Add `scripts/add_language_requirement.py` for the idempotent case migration

## 0.7.4

### Benchmark (SME Full content 0.8.0)

- Scorers fold typographic Unicode variants onto their ASCII equivalents before matching: non-breaking hyphen (U+2011), en/em dash, minus sign, narrow no-break space (U+202F), soft hyphen, zero-width characters, and typographic quotes
- Identifiers such as `#W-55021`, `RE-2026-1048`, and `R-8821` are now recognised when a model formats them with a non-breaking hyphen; 63 attempts across two runs were previously graded as missing terms although the identifier was present and correct
- `forbidden_terms` folds the same variants, so a critical gate can no longer be evaded with a typographic dash
- Model inputs and case content are unchanged: `suite_version` stays 0.8.0 and every existing run is regradable
- Scoring fingerprints include scoring-spec version 0.6.0
- Compatibility manifest: [`regrade-0.8.0-baseline.json`](suites/compatibility/regrade-0.8.0-baseline.json)

### Tool 0.7.4

- Add `normalize_typography` / `normalize_typography_deep` and apply them in `contains`, `forbidden_terms`, `regex`, `set_equality`, `json_fields`, `citations`, `exact_match`, and `classification`
- Regex *patterns* are exempt from folding so character classes such as `[\u2010-\u2015]` keep working; only the haystack is folded

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
