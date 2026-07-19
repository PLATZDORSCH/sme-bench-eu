# Suite authoring guide (for humans & coding agents)

How to create a **custom SME-Bench test suite**: directory layout, `suite.yaml`, case YAML, scorers, validation, and fairness rules.

Use an existing small test suite as a template: [`suites/sme-trades-v0.1`](../suites/sme-trades-v0.1) or the minimal example [`suites/demo-v0.1`](../suites/demo-v0.1).

---

## Goals

- Deterministic grading only (no LLM-as-a-Judge).
- Prefer DE/EN pairs via shared `pair_id`.
- Synthetic or anonymized fixtures only; never put real secrets or PII in the repo.
- Custom suites are **not** auto-merged into SME Full — run them with `--suite PATH`.

---

## Checklist (agent workflow)

1. Create `suites/<id>/` with `suite.yaml`, `cases/de-DE/`, `cases/en-GB/`, `fixtures/`, `schemas/` as needed.
2. Add cases as YAML; every message uses either `content` **or** `fixture` (not both, not neither).
3. **Author every case in both languages** — one file under `cases/de-DE/` and one under `cases/en-GB/`.
4. Fixture and schema paths are **relative to the suite root** and must stay inside that directory.
5. Pair DE/EN: same `pair_id`, same `task_type`, same `difficulty`, comparable positive scorer weight sums (Δ ≤ 0.05).
6. At least one scorer with `weight > 0`. Use `critical: true` only for hard fail conditions (effective score → 0).
7. Validate: `uv run sme-bench validate suites/<id>`
8. Smoke-run: `uv run sme-bench run --base-url … --model … --suite suites/<id> --repeats 1 --output runs/<id>-smoke`
9. Optional catalog: `uv run sme-bench catalog --suite suites/<id> --output suites/<id>/CASES.md`
10. Keep `review_status: draft` until human review; set `approved` only when ready to ship.

---

## Directory layout

```text
suites/my-domain-v0.1/
├── suite.yaml                 # required manifest
├── README.md                  # optional test-suite description
├── cases/
│   ├── de-DE/
│   │   └── de-xx-task-001.yaml
│   └── en-GB/
│       └── en-xx-task-001.yaml
├── fixtures/                  # input texts, CSVs, etc.
│   ├── de-….txt
│   └── en-….txt
└── schemas/                   # JSON Schema files for json_schema scorer
    └── ….schema.json
```

Naming conventions used in released test suites:

| Item | Pattern | Example |
| --- | --- | --- |
| Suite folder / `id` | `sme-<domain>-v0.1` | `sme-trades-v0.1` |
| Case `id` | `<lang-prefix>-<abbr>-<type>-<nnn>` | `de-tr-invoice-001` |
| `pair_id` | shared across languages | `tr-invoice-001` |
| Case file | mirrors `id` | `de-tr-invoice-001.yaml` |

---

## `suite.yaml`

```yaml
schema_version: "1.0"
id: my-domain-v0.1
name: My Domain Test Suite
version: 0.1.0
description: Short description of the domain and task mix
languages:
  - de-DE
  - en-GB
default_repeats: 3
default_pass_threshold: 0.85
default_partial_threshold: 0.65
case_globs:
  - cases/**/*.yaml
category_weights:
  document_extraction: 1.0
  customer_service: 1.0
  # … only categories you actually use
provenance:
  type: synthetic
  notes: "Custom test suite. Synthetic fixtures."
```

Notes:

- Case language must appear in `languages`.
- If a case omits thresholds, suite defaults apply (`pass` 0.85, `partial` 0.65).
- `partial_threshold` must be **strictly lower** than `pass_threshold`.

---

## Case YAML

### Required / common fields

| Field | Values / notes |
| --- | --- |
| `schema_version` | `"1.0"` |
| `id` | unique within the suite (and across Full if you ever merge) |
| `pair_id` | shared DE/EN id (strongly recommended) |
| `title` | short human title |
| `language` | `de-DE` or `en-GB` |
| `category` | e.g. `document_extraction`, `customer_service`, `grounded_qa`, … |
| `task_type` | free string; keep consistent within a pair |
| `difficulty` | `easy` \| `normal` \| `hard` |
| `risk` | `low` \| `medium` \| `high` \| `critical` |
| `review_status` | `draft` \| `reviewed` \| `approved` |
| `data_classification` | `synthetic` \| `anonymized` \| `confidential` |
| `tags` | list of strings |
| `messages` | list of `{role, content}` or `{role, fixture}` |
| `generation` | `max_tokens`, `temperature` (usually `0`), `response_format` |
| `expected` | ground truth for scorers (object, string, or list) |
| `scorers` | list of scorer specs |
| `pass_threshold` / `partial_threshold` | optional overrides |

`response_format`: `text` \| `json` \| `classification`.

### Always author cases as a DE + EN pair

Every custom case should exist in **both** German and English, coupled by a shared
`pair_id`. This keeps the suite comparable across languages (the validator warns on a
`pair_id` with fewer than two language variants and errors on inconsistent
`task_type` / `difficulty` / incomparable scorer weights).

Rules for a pair:

- **Same** `pair_id`, `task_type`, `difficulty`, and comparable positive scorer weight sums (Δ ≤ 0.05).
- **Different** `id` (language prefix), `language`, `title`, and usually the `fixture` (localised input).
- Structured `expected` values (categories, numbers, SKUs) are typically identical; localise only free-text content.
- Put each language under its own folder: `cases/de-DE/` and `cases/en-GB/`.

### Minimal example (classification) — full DE + EN pair

`cases/de-DE/de-xx-support-001.yaml`:

```yaml
schema_version: "1.0"
review_status: draft
data_classification: synthetic
id: de-xx-support-001
pair_id: xx-support-001
title: Ticket priorisieren
language: de-DE
category: customer_service
task_type: support_routing
difficulty: normal
risk: medium
tags: [custom, support]
messages:
  - role: system
    content: >-
      Classify the support ticket. Return JSON with category
      (one of [billing,shipping,technical,other]) and priority
      (one of [low,medium,high,urgent]). …
  - role: user
    fixture: fixtures/de-ticket.txt
generation:
  max_tokens: 120
  temperature: 0
  response_format: json
expected:
  category: technical
  priority: high
scorers:
  - type: json_schema
    weight: 0.2
    params:
      schema: schemas/support-routing.schema.json
  - type: classification
    weight: 0.5
    params:
      field: category
      expected: technical
      allowed: [billing, shipping, technical, other]
  - type: classification
    weight: 0.3
    params:
      field: priority
      expected: high
      allowed: [low, medium, high, urgent]
```

`cases/en-GB/en-xx-support-001.yaml` (same `pair_id`, localised `title`/`fixture`, identical structure):

```yaml
schema_version: "1.0"
review_status: draft
data_classification: synthetic
id: en-xx-support-001
pair_id: xx-support-001
title: Prioritise ticket
language: en-GB
category: customer_service
task_type: support_routing
difficulty: normal
risk: medium
tags: [custom, support]
messages:
  - role: system
    content: >-
      Classify the support ticket. Return JSON with category
      (one of [billing,shipping,technical,other]) and priority
      (one of [low,medium,high,urgent]). …
  - role: user
    fixture: fixtures/en-ticket.txt
generation:
  max_tokens: 120
  temperature: 0
  response_format: json
expected:
  category: technical
  priority: high
scorers:
  - type: json_schema
    weight: 0.2
    params:
      schema: schemas/support-routing.schema.json
  - type: classification
    weight: 0.5
    params:
      field: category
      expected: technical
      allowed: [billing, shipping, technical, other]
  - type: classification
    weight: 0.3
    params:
      field: priority
      expected: high
      allowed: [low, medium, high, urgent]
```

Copy richer patterns from released cases (invoice + numeric, orders + `set_equality`, grounded QA + `citations`, injection + `forbidden_terms`) — always in matching DE/EN pairs.

---

## Scorers

Each entry:

```yaml
- type: <name>
  weight: 0.5          # contribution to weighted score; 0 = check-only / often with critical
  critical: false      # if true and failed → critical_failure, effective score 0
  params: { … }
```

| Type | Typical use | Important `params` |
| --- | --- | --- |
| `json_schema` | Output matches JSON Schema file | `schema: schemas/….json` |
| `json_fields` | Exact/loose match on named fields vs `expected` | `fields`, optional `match`, `case_insensitive` |
| `numeric` | Float fields with tolerance | `fields`, `absolute_tolerance`, `relative_tolerance` |
| `classification` | Label in a field | `field`, `expected`, `allowed`, optional `scale` + `adjacent_credit` |
| `contains` | Required substrings in output | `terms` (or `required`): string or list of alternatives per slot; `mode: all\|any`, `case_insensitive` |
| `forbidden_terms` | Must not appear (often `critical: true`) | `terms`, optional `fields` / `exclude_fields`, `ignore_negated` |
| `set_equality` | Unordered lists (orders, line items) | `field`, `ignore_order`, optional `keys` (project dicts), `aliases` |
| `citations` | Citation ids must be in allow-list | `field`, `allowed`, `require_nonempty` |
| `exact_match` | Whole-string match | optional `expected`, `case_insensitive`, `normalize_whitespace` |
| `regex` | Pattern checks | `patterns`, optional `case_insensitive` |

### Fairness tips (avoid flaky fails)

- **System prompt:** name exact JSON keys and formats (`vat_rate` as decimal `0.19`, dates `YYYY-MM-DD`).
- **`forbidden_terms`:** use `fields` to only scan structured values, or `exclude_fields` (e.g. exclude `reason`) so free-text explanations do not false-trigger.
- **Orders / lists:** grade with `set_equality` + `keys: [sku, qty]` instead of full-object equality when extra keys are allowed.
- **Citations:** ids may appear as `SEC-A` or `[SEC-A]`; the scorer normalizes common forms.
- Weights of positive scorers should sum sensibly (often ≈ 1.0); pairs must stay comparable.

---

## Grading thresholds

| Grade | Default | Meaning |
| --- | --- | --- |
| Pass | ≥ 0.85 | fully correct attempt |
| Partial | 0.65–0.84 | mostly correct |
| Fail | < 0.65 | hard fail |
| Critical | critical scorer failed | attempt effective score 0 |

**Reliable pass** (reports): every repeat of a case passed. See root README Kennzahlen.

---

## Validation & run commands

```bash
# Structure, fixtures, scorers, pairing
uv run sme-bench validate suites/my-domain-v0.1

# List cases
uv run sme-bench list --suite suites/my-domain-v0.1

# Run only this suite (not Full)
uv run sme-bench run \
  --base-url "$BASE_URL" \
  --model "$MODEL" \
  --suite suites/my-domain-v0.1 \
  --languages de-DE,en-GB \
  --repeats 3 \
  --output runs/my-domain-v0.1

# Rebuild bilingual reports from an existing run
uv run sme-bench report runs/my-domain-v0.1 --format all
```

Validate fails on unknown scorer types, missing fixtures, path escapes, invalid YAML/Pydantic models, duplicate ids, language not in manifest, and incomparable pairs. Unpaired `pair_id` is a **warning**.

---

## Do / Don’t

**Do**

- Mirror an existing test suite for scorer + prompt style.
- Keep fixtures short enough to be reviewable; put long inputs in `fixtures/`.
- Document the test suite in `suites/<id>/README.md` (task table + how to run).
- Use `data_classification: synthetic` for made-up content.

**Don’t**

- Reference files outside the suite directory.
- Rely on model “judgment” in scorers.
- Put API keys, real customer data, or live credentials in fixtures.
- Expect a custom suite to appear in default Full until it is added to `FULL_SUITE_IDS` in `src/sme_bench/task_loader.py` (maintainers only).

---

## Adding to SME Full (maintainers)

Released test suites live under `suites/` and are listed in `FULL_SUITE_IDS`. Custom community suites usually stay separate and are invoked with `--suite`. Only maintainers should extend Full after review (`review_status: approved`, unique task ids, docs, changelog).

Changing prompts, fixtures, expected answers, or weights requires a **new content version** — see [VERSIONING.md](VERSIONING.md).

---

## Reference implementations

| Test suite | Why useful as a template |
| --- | --- |
| [`demo-v0.1`](../suites/demo-v0.1) | Minimal custom suite (2 cases, draft) |
| [`sme-trades-v0.1`](../suites/sme-trades-v0.1) | Compact domain test suite (14 cases) |
| [`sme-core-v0.1`](../suites/sme-core-v0.1) | Full task-type coverage |
| [`sme-chains-v0.1`](../suites/sme-chains-v0.1) | Process chains + security / PII / injection |

Models: `src/sme_bench/models.py` (`BenchmarkTask`, `SuiteManifest`, `ScorerSpec`).  
Loader / checks: `src/sme_bench/task_loader.py`.  
Scorer registry: `src/sme_bench/scorers/`.
