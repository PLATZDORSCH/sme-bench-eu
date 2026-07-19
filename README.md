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

Copy `.env.example` to `.env` and fill in the keys you need. The CLI loads `.env` automatically. Use `--api-key-env` to select which variable to send (default: `OPENAI_API_KEY`). Local servers often accept any value or `EMPTY`.

```bash
cp .env.example .env
```

**The default run target is SME Full** (Core + all domain packs, ~156 cases × repeats).

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

Optional: enable Qwen-style thinking and raise the token budget so answers are not truncated mid-reasoning:

```bash
uv run sme-bench run \
  --base-url http://localhost:4000/v1 \
  --model qwen3.6-35b \
  --api-key-env LITELLM_API_KEY \
  --enable-thinking \
  --max-tokens-mult 8 \
  --save-reasoning \
  --output runs/litellm-qwen-thinking
```

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
| `sme-bench report …` | Rebuild reports from raw data (`summary\|failures\|success`.`de\|en`.md) |
| `sme-bench compare …` | Compare multiple runs |

## Metrics

- **Attempt Pass Rate:** passed attempts / all attempts (≥85 %, fully correct)
- **Attempt Partial Rate:** partially passed attempts (65–84 %, mostly correct)
- **Reliable Pass Rate:** cases that passed in *every* repeat / all cases
- **Critical Failure:** a critical scorer failed → effective score `0` for that attempt
- **SME Core Score:** mean of category-weighted effective scores × 100 (domain quality, no rate penalty)
- **SME Rank Score:** `SME Core × Reliable Pass × max(0, 1 − 5 × critical_rate) × max(0, 1 − 2 × partial_rate)` — primary leaderboard metric
- **Language gap:** pass/score difference `en-GB − de-DE` plus pair consistency

## Releases and versioning

Current release: **[v0.1.0](https://github.com/PLATZDORSCH/sme-bench-eu/releases/tag/v0.1.0)**.

Harness bugfixes stay on the same content line (patch). Prompt, case, or score-changing changes get a **new version** so leaderboard runs stay comparable. Details: **[docs/VERSIONING.md](docs/VERSIONING.md)**.

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
