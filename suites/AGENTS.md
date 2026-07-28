# Agent brief: create a SME-Bench suite

Use this when a coding agent should author or extend a **custom test suite**.

## Source of truth

Full guide (schema, scorers, fairness, pitfalls):

- English: [`docs/AUTHORING_SUITES.md`](../docs/AUTHORING_SUITES.md)
- German: [`docs/AUTHORING_SUITES.de.md`](../docs/AUTHORING_SUITES.de.md)

Minimal template: [`demo-v0.1/`](demo-v0.1/)  
Larger domain example: [`sme-trades-v0.1/`](sme-trades-v0.1/)

## Non-negotiables

- Deterministic scorers only — no LLM-as-a-Judge.
- Every case in **both** `cases/de-DE/` and `cases/en-GB/` with shared `pair_id`.
- Message body: either `content` **or** `fixture`, never both/neither.
- Paths stay inside the suite root; fixtures/schemas are relative to that root.
- Synthetic / anonymized data only — no real secrets or PII.
- Custom suites are **not** part of SME Full; run with `--suite suites/<id>`.

## Workflow

1. Create `suites/<id>/` with `suite.yaml`, `cases/de-DE/`, `cases/en-GB/`, plus `fixtures/` / `schemas/` as needed.
2. Copy structure from `demo-v0.1` or a domain suite; adapt prompts, expected JSON, scorers.
3. Pair DE/EN: same `task_type`, `difficulty`, comparable positive weight sums (Δ ≤ 0.05).
4. At least one scorer with `weight > 0`. Use `critical: true` only for hard fails.
5. Validate: `uv run sme-bench validate suites/<id>`
6. Smoke: `uv run sme-bench run --base-url … --model … --suite suites/<id> --repeats 1 --output runs/<id>-smoke`
7. Optional catalog: `uv run sme-bench catalog --suite suites/<id> --output suites/<id>/CASES.md`
8. Leave `review_status: draft` until a human approves.

## Do not

- Invent scorer types not documented in AUTHORING_SUITES.
- Put absolute paths or files outside the suite tree into case YAML.
- Merge custom suites into SME Full / official leaderboard without an explicit project decision.
