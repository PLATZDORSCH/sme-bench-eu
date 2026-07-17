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

There is **no single opaque overall score**. The transparent score always appears together with pass rate, critical failure rate, language comparison, and performance metrics.

## Installation

Requires Python ≥ 3.11 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras --dev
```

## Quick start

**The default is the Full run** (Core + all domain packs, ~156 cases):

```bash
# Check the endpoint
uv run sme-bench doctor \
  --base-url http://localhost:11434/v1 \
  --model qwen3.6:27b

# Start the Full benchmark (default — no --suite needed)
uv run sme-bench run \
  --base-url http://localhost:11434/v1 \
  --model qwen3.6:27b \
  --languages de-DE,en-GB \
  --repeats 3 \
  --concurrency 1 \
  --seed 42 \
  --output runs/qwen3.6-27b-full
```

Run only the core benchmark (72 cases):

```bash
uv run sme-bench run \
  --base-url http://localhost:11434/v1 \
  --model qwen3.6:27b \
  --suite suites/sme-core-v0.1 \
  --output runs/qwen3.6-27b-core
```

API keys are read from the `OPENAI_API_KEY` environment variable (default for local endpoints: `EMPTY`).

## CLI commands

| Command | Purpose |
| --- | --- |
| `sme-bench doctor` | Check reachability, streaming, usage |
| `sme-bench list --suite …` | List cases, languages, pairs |
| `sme-bench validate …` | Check suite, fixtures, scorers, pairing |
| `sme-bench run …` | Run the benchmark (**default: Full**) |
| `sme-bench catalog …` | Generate `CASES.md` — documentation for all cases |
| `sme-bench report …` | Rebuild reports from raw data (`summary\|failures\|success`.`de\|en`.md) |
| `sme-bench compare …` | Compare multiple runs |

## Metrics

- **Attempt Pass Rate:** passed attempts / all attempts (≥85 %, fully correct)
- **Attempt Partial Rate:** partially passed attempts (65–84 %, mostly correct)
- **Reliable Pass Rate:** cases that passed in *every* repeat / all cases
- **Critical Failure:** a critical scorer failed → effective score `0` for rankings
- **SME Core Score:** mean of category-weighted effective scores × 100
- **Language gap:** pass/score difference `en-GB − de-DE` plus pair consistency

## Task packs

All packs are **released** (`review_status: approved`) and versioned as **v0.1**.

| Name | Path | Content | Cases |
| --- | --- | --- | --- |
| **SME Full** | *(virtual)* | Standard ranking: Core + all domains | ~156 |
| **SME Core v0.1** | `suites/sme-core-v0.1` | Core: 12 task types × 3 variants (DE/EN) | 72 |
| **SME Trades v0.1** | `suites/sme-trades-v0.1` | Trades/construction | 14 |
| **SME E-Commerce v0.1** | `suites/sme-ecommerce-v0.1` | Shop/retail | 14 |
| **SME Financial v0.1** | `suites/sme-financial-v0.1` | Accounting/finance | 14 |
| **SME Hospitality v0.1** | `suites/sme-hospitality-v0.1` | Food service/hotel | 14 |
| **SME Logistics v0.1** | `suites/sme-logistics-v0.1` | Logistics/warehouse | 14 |
| **SME Chains v0.1** | `suites/sme-chains-v0.1` | Process chains + security/PII | 14 |

Details for each pack live in `suites/<pack>/README.md` (basis for the future website).

### Full vs. a single pack

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

# Optional: a single domain pack
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-financial-v0.1 --output runs/financial
```

Included in the Full run: `sme-core-v0.1`, `sme-trades-v0.1`, `sme-ecommerce-v0.1`, `sme-financial-v0.1`, `sme-hospitality-v0.1`, `sme-logistics-v0.1`, `sme-chains-v0.1`.

## Authoring your own tasks

Step by step for humans and coding agents: **[docs/AUTHORING_SUITES.md](docs/AUTHORING_SUITES.md)** (layout, case schema, scorers, fairness, validate/run).

In short:

1. Create YAML under `suites/<suite>/cases/<lang>/`.
2. Reference fixtures relative to the suite; paths must not escape the suite directory.
3. Pair DE/EN via a shared `pair_id`.
4. Check with `sme-bench validate`.

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

CI runs ruff, mypy, and pytest with coverage (gate ≥76 %) on Python 3.11 and 3.12.

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
