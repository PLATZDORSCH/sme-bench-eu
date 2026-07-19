# Demo-Test-Suite (`demo-v0.1`)

| | |
| --- | --- |
| **Rolle** | Minimale Custom-Test-Suite (Authoring-Beispiel); **nicht** Teil von SME Full |
| **Cases** | 2 (1 DE/EN-Paar) |
| **Status** | `draft` |

## Tasks

| pair_id | Typ | Hinweise |
| --- | --- | --- |
| `demo-support-001` | support_routing | Billing-Ticket → category `billing`, priority `high` |

## Ausführen

```bash
uv run sme-bench validate suites/demo-v0.1
uv run sme-bench run \
  --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/demo-v0.1 --repeats 1 \
  --output runs/demo-v01
```

Nicht in SME Full — mit `--suite` starten. Siehe [docs/AUTHORING_SUITES.de.md](../../docs/AUTHORING_SUITES.de.md).
