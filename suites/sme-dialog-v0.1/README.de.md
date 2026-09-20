# sme-dialog-v0.1

| Feld | Wert |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite-ID** | `sme-dialog-v0.1` |
| **Fälle** | 16 (8 DE/EN-Paare) |
| **Sprachen** | `de-DE`, `en-GB` |
| **Rolle** | Multi-Turn-Dialog-Pack; Teil von **SME Full** ab Inhalt 0.13.0 |

Revisionen, Rückfrage, Eskalation, Widerspruch, verpasster Rückruf, Mehrfachanliegen, Beschwerdeton.

## Task-Typen

| Pair-ID | Task-Typ |
| --- | --- |
| dialog-qty-revise-001 | order_revision |
| dialog-address-001 | order_revision |
| dialog-clarify-001 | clarification |
| dialog-escalate-001 | escalation |
| dialog-contradict-001 | contradiction |
| dialog-callback-001 | callback_followup |
| dialog-multi-issue-001 | multi_issue |
| dialog-complaint-001 | complaint_tone |

## Nutzung

```bash
uv run sme-bench validate suites/sme-dialog-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-dialog-v0.1 --output runs/sme-dialog-v0.1
```
