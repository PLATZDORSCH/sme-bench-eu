# SME-Bench

SME-Bench evaluates language models on **realistic tasks from small and medium-sized enterprises (SMEs)** in German and English — not on general knowledge or multiple-choice quizzes.

It measures separately:

- domain quality
- reliability across repeats
- critical failures (hallucinations, data leaks, unauthorised actions)
- DE/EN language parity
- format and process compliance
- performance (TTFR, TTFT, latency, tokens/s)
- optionally cost efficiency (token cost)

There is **no composite score**. The headline number is the share of passed attempts; it always appears together with its 95 % interval, the number of unsolved and critical cases, the language comparison, and performance metrics.

## Installation

Requires Python ≥ 3.11 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras --dev
```

## Quick start

Copy `.env.example` to `.env` and fill in the keys you need. The CLI loads `.env` automatically. Use `--api-key-env` to select which variable to send (default: `OPENAI_API_KEY`). Local servers often accept any value or `EMPTY`.

```bash
cp .env.example .env
```

**The default run target is SME Full** (Core + domain packs + Advanced + Expert + Tools + Dialog + Long-Context + Agentic, 284 cases × 2 repeats).

### Ollama

```bash
uv run sme-bench doctor \
  --base-url http://localhost:11434/v1 \
  --model qwen3.6:27b \
  --api-key-env OPENAI_API_KEY

uv run sme-bench run \
  --base-url http://localhost:11434/v1 \
  --model qwen3.6:27b \
  --api-key-env OPENAI_API_KEY \
  --output runs/ollama-qwen3.6-27b
```

### LM Studio

LM Studio’s local server is OpenAI-compatible (default port `1234`):

```bash
uv run sme-bench doctor \
  --base-url http://localhost:1234/v1 \
  --model local-model \
  --api-key-env OPENAI_API_KEY

uv run sme-bench run \
  --base-url http://localhost:1234/v1 \
  --model local-model \
  --api-key-env OPENAI_API_KEY \
  --output runs/lmstudio
```

Use the model id shown in LM Studio (loaded model / API name).

### OpenAI

```bash
uv run sme-bench doctor \
  --base-url https://api.openai.com/v1 \
  --model gpt-4o-mini \
  --api-key-env OPENAI_API_KEY

uv run sme-bench run \
  --base-url https://api.openai.com/v1 \
  --model gpt-4o-mini \
  --api-key-env OPENAI_API_KEY \
  --output runs/gpt-4o-mini
```

### Nebius

```bash
uv run sme-bench doctor \
  --base-url https://api.tokenfactory.nebius.com/v1 \
  --model zai-org/GLM-5.2 \
  --api-key-env NEBIUS_API_KEY

uv run sme-bench run \
  --base-url https://api.tokenfactory.nebius.com/v1 \
  --model zai-org/GLM-5.2 \
  --api-key-env NEBIUS_API_KEY \
  --extra-body-file examples/extra-body-glm-no-thinking.json \
  --output runs/glm-5.2
```

By default every run uses `--max-tokens-min 8192` and `--timeout 300`. Suite tasks
often allow only ~150–400 completion tokens; that truncates reasoning mid-CoT
(gpt-oss, Qwen thinking, Nemotron, …). You pay for tokens actually generated —
the floor is a ceiling. Disable with `--max-tokens-min 0` if you need the raw
suite budgets.

When a thinking model exhausts its token budget before emitting a final answer,
the chain-of-thought is kept in `reasoning_text` for diagnostics and is **not**
scored or shown as `output_text`. Provider `finish_reason` is stored on each
attempt (and in `attempts.csv`) when the API reports it.

Reasoning via `reasoning_effort` (gpt-oss / GPT-5.x style):

```bash
uv run sme-bench run \
  --base-url https://api.tokenfactory.nebius.com/v1 \
  --model openai/gpt-oss-120b \
  --api-key-env NEBIUS_API_KEY \
  --extra-body-file examples/extra-body-gpt54-reasoning.json \
  --save-reasoning \
  --output runs/gpt-oss-120b-thinking
```

### LiteLLM / vLLM

Any OpenAI-compatible proxy (LiteLLM, vLLM, …):

```bash
uv run sme-bench doctor \
  --base-url http://localhost:4000/v1 \
  --model qwen3.6-35b \
  --api-key-env LITELLM_API_KEY

uv run sme-bench run \
  --base-url http://localhost:4000/v1 \
  --model qwen3.6-35b \
  --api-key-env LITELLM_API_KEY \
  --output runs/litellm-qwen
```

Optional: enable Qwen-style thinking (`chat_template_kwargs`). Token floor and
timeout already default as above. Prefer `--save-reasoning` so leaked thinking
stays inspectable:

```bash
uv run sme-bench run \
  --base-url http://localhost:4000/v1 \
  --model qwen3.6-35b \
  --api-key-env LITELLM_API_KEY \
  --enable-thinking \
  --save-reasoning \
  --output runs/litellm-qwen-thinking
```

Override only if needed (e.g. `--max-tokens-min 4096` or `--timeout 180`).
Do not rely on `--max-tokens-mult 8` alone — short tasks still truncated at
1200–2800 completion tokens in practice without the floor.

### Core only

```bash
uv run sme-bench run \
  --base-url http://localhost:11434/v1 \
  --model qwen3.6:27b \
  --api-key-env OPENAI_API_KEY \
  --suite suites/sme-core-v0.1 \
  --output runs/core
```

## CLI commands

| Command | Purpose |
| --- | --- |
| `sme-bench doctor` | Check reachability, streaming, usage |
| `sme-bench list --suite …` | List cases, languages, pairs |
| `sme-bench validate …` | Check suite, fixtures, scorers, pairing |
| `sme-bench run …` | Run the benchmark (**default: Full**) |
| `sme-bench catalog …` | Generate `CASES.md` — documentation for all cases |
| `sme-bench report …` | Rebuild reports from raw data (`summary\|failures\|success`.`de\|en`.md); `--rescore` in memory only |
| `sme-bench regrade SOURCE --output TARGET` | Non-destructive re-score into a new run directory |
| `sme-bench merge-run BASE --delta … -o …` | Merge a full base run with selective `--task-ids` deltas and rescore |
| `sme-bench compat-report SOURCE` | Show regrade vs rerun-required tasks |
| `sme-bench fingerprints --suite …` | Export legacy input-fingerprint manifest |
| `sme-bench compare …` | Compare multiple runs |

Use `--task-ids id1,id2` on `run` for selective deltas when only some inputs changed.

Concurrency and scheduling: see **[docs/RUNNING.md](docs/RUNNING.md)**. On a
server endpoint `--concurrency 4` is the usual speed-up. llama.cpp needs
`--parallel N --cont-batching` and `n_ctx ≥ N × 32768` or stay at concurrency 1.

## What the score means

SME-Bench is a **readiness test**, not a ranking contest. Cases represent work a model must handle in an SME office. High scores mean the model is fit for that work; 100 % on a task type stays on purpose as a regression guard. Harder differentiation belongs in a separate expert pack, not in the standard pack.

| Suitability | When |
| --- | --- |
| **suitable** | Passed ≥ 95 %, no case with a critical failure, language compliance 100 % (when measured) |
| **partly suitable** | Passed ≥ 85 %; a critical case or a language break caps a run here even above 95 % |
| **not suitable** | Passed below 85 % |
| **inconclusive** | Coverage below 95 % — the run is not fully comparable |

The table is sorted by **Passed**. There is no composite score: every column is a share or a count you can check against the per-run report.

## Metrics

- **Passed:** share of graded attempts that passed (score ≥ 0.85, no critical failure, no failed must-pass check), averaged per case. Infrastructure errors and excluded capability probes are not graded and do not count against the model
- **95 % interval:** bootstrap interval of Passed, resampling DE/EN case pairs (2000 draws, fixed seed). Overlapping intervals mean the gap between two models is not reliable
- **Unsolved cases:** cases that did not pass in every repeat
- **Critical cases:** cases with at least one critical failure (a critical scorer failed → effective score `0` for that attempt)
- **Unstable cases:** cases where the repeats disagreed. With `temperature: 0` and 2 repeats this is a weak signal, not a reliability measurement
- **Coverage:** graded attempts / planned attempts
- **Suitability:** `suitable` / `partly suitable` / `not suitable` / `inconclusive`, see above. Internal keys in `summary.json`: `ready` / `supervised` / `not_recommended` / `inconclusive`
- **Attempt Partial Rate** and **mean partial-credit score:** report-only detail (partial = 65–84 %, or ≥ 85 % with a failed must-pass check)
- **Language gap:** pass/score difference `en-GB − de-DE` plus pair consistency
- **Language compliance:** share of attempts answered in the case language (`—` for runs graded before content 0.9.0)
- **Format-only failure rate:** content scorers passed but format/language scorers failed
- **TTFT cold / TTFA:** first-token time on `repeat_index == 0`, and time to first *answer* token (not reasoning)
- Performance numbers are measured **under the benchmark load** (default concurrency 1). For pp/tg sweeps, prefix-cache, and concurrency scaling use [llama-benchy](https://github.com/eugr/llama-benchy).

### Scoring normalisation

Scoring is deterministic and never uses an LLM judge. Before matching, every scorer folds typographic Unicode variants onto their ASCII equivalents on **both** sides of the comparison: non-breaking hyphen (U+2011), en/em dash, minus sign, narrow no-break space (U+202F), soft hyphen, zero-width characters, and typographic quotes. A model that writes an order number as `#W‑55021` therefore scores the same as one that writes `#W-55021`. Regex *patterns* are exempt so character classes such as `[\u2010-\u2015]` keep working; only the scanned text is folded.

### Language compliance

A German case answered in English is unusable in practice, so every case states its answer language in the prompt and carries a `language` scorer with `weight: 0` and `must_pass: true`. A language break therefore leaves the partial-credit score untouched but blocks the attempt from passing, which lowers Passed and caps suitability at partly suitable.

The check counts function words that are unambiguous for one language and fails only when the wrong language leads by two markers. It deliberately abstains when the evidence is thin, because German business answers legitimately carry English loanwords and structured values. Consequence worth knowing: a short English phrase without function words (`update inventory`) is not detected. That threshold is validated against every case's own expected answer — a stricter setting would fail cases against their own reference. JSON keys are never scanned, and cases whose `reason` field quotes a refused English payload exclude that field, the same way `forbidden_terms` already does.

## Releases and versioning

Current release: **v0.14.0** (harness) with SME Full content **0.16.1** (284 DE/EN cases) and scoring-spec **0.10.0**. Harness 0.11 adds a live mock-tool loop, completion rate, a `tool_choice=required` probe, and crowded-namespace deltas. Harness 0.11.2 displays the score as SME Readiness Score and adds a readiness tier. Harness 0.12.0 / spec 0.9.0 add `absent_fields` and the `tool_calls` expected form for schema-heavy tool calls. Content 0.14.x adds `sme-agentic-v0.1` and crowded variants in Tools; 0.14.1 closes specification gaps; 0.14.2 disambiguates `dialog-clarify-001`; 0.15.0 adds wide signatures, nested and array arguments, enum literals, and optional-field omission to Tools; 0.15.1 disambiguates callback, policy-chain and TCO discount; 0.15.2 states the digest format and supplies the email content in Agentic. Spec 0.9.1 matches numeric forbidden terms as whole numbers (`0 EUR` no longer fires inside `1200 EUR`); regrade earlier runs. Content 0.16.0 retires 14 redundant domain pairs and adds six harder tool-call pairs (284 cases). Content 0.16.1 keeps IBAN `action` enums as `accept`/`reject` even in German cases. Spec 0.10.0 adds `trace_calls.same_turn` and `forbidden`. Harness 0.14.0 schedules longest-first when `--concurrency` is greater than 1.

Harness bugfixes stay on the same content line (patch). Prompt, case, or score-changing changes get a **new version** so published comparison runs stay comparable. Details: **[docs/VERSIONING.md](docs/VERSIONING.md)**.

## Test suites

All cases on a released content line have `review_status: approved`. Folder ids stay `*-v0.1`; the current suite version is **0.16.1**.

| Name | Path | Content | Cases |
| --- | --- | --- | --- |
| **SME Full** | *(virtual)* | Standard readiness pack: Core + domains + Advanced + Expert + Tools + Dialog + Long-Context + Agentic | 284 |
| **SME Core v0.1** | `suites/sme-core-v0.1` | Discriminating core tasks (DE/EN) | 42 |
| **SME Trades v0.1** | `suites/sme-trades-v0.1` | Trades/construction | 12 |
| **SME E-Commerce v0.1** | `suites/sme-ecommerce-v0.1` | Shop/retail | 16 |
| **SME Financial v0.1** | `suites/sme-financial-v0.1` | Accounting/finance | 10 |
| **SME Hospitality v0.1** | `suites/sme-hospitality-v0.1` | Food service/hotel | 10 |
| **SME Logistics v0.1** | `suites/sme-logistics-v0.1` | Logistics/warehouse | 10 |
| **SME Chains v0.1** | `suites/sme-chains-v0.1` | Process chains + security/PII | 4 |
| **SME Advanced v0.1** | `suites/sme-advanced-v0.1` | Multi-step hard cases | 36 |
| **SME Expert v0.1** | `suites/sme-expert-v0.1` | Very hard multi-step cases | 20 |
| **SME Tools v0.1** | `suites/sme-tools-v0.1` | Tool use, negatives, hallucinations, crowded namespace, schema-heavy calls | 52 |
| **SME Dialog v0.1** | `suites/sme-dialog-v0.1` | Multi-turn customer threads | 16 |
| **SME Long Context v0.1** | `suites/sme-longctx-v0.1` | 8k–24k token needles | 16 |
| **SME Agentic v0.1** | `suites/sme-agentic-v0.1` | Live tool loops: chains, recovery, exactly-once, auth, parallel/branch | 40 |

Details for each test suite live in `suites/<id>/README.md` (basis for the future website).

### Full vs. a single test suite

```bash
export BASE_URL=http://localhost:11434/v1
export MODEL=qwen3.6:27b
export OPENAI_API_KEY=EMPTY

# Default: Full
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" --output runs/full

# Optional: Core only
uv run sme-bench validate suites/sme-core-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-core-v0.1 --output runs/core

# Optional: a single domain test suite
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-financial-v0.1 --output runs/financial
```

Included in the Full run: `sme-core-v0.1`, `sme-trades-v0.1`, `sme-ecommerce-v0.1`, `sme-financial-v0.1`, `sme-hospitality-v0.1`, `sme-logistics-v0.1`, `sme-chains-v0.1`, `sme-advanced-v0.1`, `sme-expert-v0.1`, `sme-tools-v0.1`, `sme-dialog-v0.1`, `sme-longctx-v0.1`, `sme-agentic-v0.1`.

Custom example (not in Full): [`suites/demo-v0.1`](suites/demo-v0.1) — run with `--suite suites/demo-v0.1`.

## Authoring your own test suite

A custom suite lets you test models on **your** workflows — ticket categories,
invoice fields, approval rules, and similar — with the same transparent,
deterministic scoring as SME Full. You see which model is reliable on your
tasks, not only on the published comparison.

Full guide (layout, case schema, scorers, fairness):
**[docs/AUTHORING_SUITES.md](docs/AUTHORING_SUITES.md)**.
For coding agents: short brief in **[`suites/AGENTS.md`](suites/AGENTS.md)**
(points to the same guide). Minimal template: [`suites/demo-v0.1`](suites/demo-v0.1).

### Why a custom suite?

- You own the ground truth and scorers — no LLM-as-a-Judge.
- DE/EN pairs, repeats, and critical fails work like the Full benchmark.
- Custom suites are **not** auto-merged into the SME Full comparison; run them
  explicitly with `--suite`.

### How to proceed

1. **Create a folder** under `suites/<my-suite-v0.1>/` with `suite.yaml`,
   `cases/de-DE/`, `cases/en-GB/`, and optionally `fixtures/` and `schemas/`.
2. **Write cases** as YAML: system/user prompt (inline or via fixture),
   expected output, and scorers (e.g. `json_fields`, `contains`,
   `classification`, `forbidden_terms`).
3. **Pair languages**: the same task in DE and EN with a shared `pair_id`,
   matching `task_type`, and comparable scorer weights.
4. **Validate**: `uv run sme-bench validate suites/<my-suite-v0.1>`.
5. **Smoke-run** with one repeat, then a full run with `--repeats 2`.

```bash
# Try the demo suite
uv run sme-bench validate suites/demo-v0.1
uv run sme-bench run \
  --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/demo-v0.1 --repeats 1 \
  --output runs/demo-smoke

# Your suite
uv run sme-bench validate suites/my-suite-v0.1
uv run sme-bench run \
  --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/my-suite-v0.1 \
  --output runs/my-suite
```

### Typical layout

```text
suites/my-suite-v0.1/
├── suite.yaml
├── cases/de-DE/…yaml
├── cases/en-GB/…yaml
├── fixtures/          # optional input texts
└── schemas/           # optional for json_schema scorers
```

Notes:

- Each message uses either `content` **or** `fixture` (not both).
- Fixture paths are relative to the suite root and must stay inside the suite.
- At least one scorer with `weight > 0`; use `critical: true` only for hard
  business rules (e.g. forbidden commitments).
- Keep `review_status: draft` until review; use `approved` for released packs.

Optional catalog:
`uv run sme-bench catalog --suite suites/my-suite-v0.1 --output suites/my-suite-v0.1/CASES.md`.

## Privacy and limitations

- Local-first, no telemetry.
- No API keys in logs or result files.
- No LLM-as-a-Judge; free text is graded on required content, forbidden statements, and structure.

## Development

```bash
uv run ruff check .
uv run mypy src
uv run pytest --cov=sme_bench --cov-report=term-missing
```

CI runs ruff, mypy, suite validation, README example-path checks, and pytest with
coverage (gate ≥76 %) on Python 3.11 and 3.12.

### Test layout

| Path | Scope |
| --- | --- |
| `tests/unit/test_models.py` | Pydantic models |
| `tests/unit/test_utils.py` | Path safety, JSON extraction, redaction |
| `tests/unit/test_scorers.py` | All deterministic scorers (parametrised) |
| `tests/unit/test_scoring.py` | Thresholds, critical failures |
| `tests/unit/test_statistics.py` | Aggregation, language parity, TPS |
| `tests/unit/test_reporters.py` | Markdown/JSON reports, dashboard |
| `tests/unit/test_task_loader.py` | Full benchmark load, resume keys |
| `tests/unit/test_pricing.py` | Token cost estimation |
| `tests/unit/test_client.py` | HTTP client, streaming, retries |
| `tests/integration/test_e2e.py` | CLI end-to-end (run, compare, list, validate, determinism) |
