# Demo Test Suite (`demo-v0.1`)

| | |
| --- | --- |
| **Role** | Minimal custom test suite (authoring example); **not** part of SME Full |
| **Cases** | 2 (1 DE/EN pair) |
| **Status** | `draft` |

## Tasks

| pair_id | Type | Notes |
| --- | --- | --- |
| `demo-support-001` | support_routing | Billing ticket → category `billing`, priority `high` |

## Run

```bash
uv run sme-bench validate suites/demo-v0.1
uv run sme-bench run \
  --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/demo-v0.1 --repeats 1 \
  --output runs/demo-v01
```

Not included in SME Full — invoke with `--suite`. See [docs/AUTHORING_SUITES.md](../../docs/AUTHORING_SUITES.md).
