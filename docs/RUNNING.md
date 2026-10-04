# Running SME-Bench

Default target is SME Full (284 cases × 2 repeats). Content pruning in 0.16.0
saves only a few percent of wall time. The real lever is `--concurrency` plus
longest-first scheduling (harness 0.14.0).

## Server endpoints (Atlas, vLLM, LiteLLM)

```bash
uv run sme-bench run \
  --base-url https://atlas.example/v1 \
  --model qwen3.8-27b \
  --concurrency 4 \
  --output runs/qwen-full
```

Concurrency 4 typically cuts a 55-minute sequential Qwen run to about 15–20
minutes. The runner still scores temperature-0 tasks independently; only the
start order changes.

## llama.cpp

Use concurrency greater than 1 only if the server was started with matching
parallel slots and a large enough context:

```bash
llama-server --parallel 4 --cont-batching --ctx-size 131072
```

`n_ctx` must be at least `N × 32768`. Long-Context cases send ~28k prompt
tokens; a 32k context shared across four slots will fail those tasks. Without
`--parallel N --cont-batching`, keep `--concurrency 1`.

## Scheduling

| `--concurrency` | Order |
| --- | --- |
| 1 | Seeded shuffle (historical default) |
| > 1 | Longest-first (Expert, Advanced, Long-Context, Agentic, then the rest) |

Results do not change. A long Expert attempt no longer sits idle at the end of
a parallel window.
