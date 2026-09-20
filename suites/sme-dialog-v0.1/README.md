# sme-dialog-v0.1

| Field | Value |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite ID** | `sme-dialog-v0.1` |
| **Cases** | 16 (8 DE/EN pairs) |
| **Languages** | `de-DE`, `en-GB` |
| **Role** | Multi-turn dialog pack; part of **SME Full** from content 0.13.0 |

Revisions, clarification, escalation, contradiction, missed callback, multi-issue, complaint tone.

## Task types

| Pair ID | Task type |
| --- | --- |
| dialog-qty-revise-001 | order_revision |
| dialog-address-001 | order_revision |
| dialog-clarify-001 | clarification |
| dialog-escalate-001 | escalation |
| dialog-contradict-001 | contradiction |
| dialog-callback-001 | callback_followup |
| dialog-multi-issue-001 | multi_issue |
| dialog-complaint-001 | complaint_tone |

## Usage

```bash
uv run sme-bench validate suites/sme-dialog-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-dialog-v0.1 --output runs/sme-dialog-v0.1
```
