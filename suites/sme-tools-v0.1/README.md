# sme-tools-v0.1

| Field | Value |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite ID** | `sme-tools-v0.1` |
| **Cases** | 32 (16 DE/EN pairs) |
| **Languages** | `de-DE`, `en-GB` |
| **Role** | Tool-use pack; part of **SME Full** from content 0.13.0, crowded variants in 0.14.0 |

ERP stock, booking, CRM, tickets, refund policy, negatives, hallucinations, plus four crowded-namespace pairs.

## Task types

| Pair ID | Task type |
| --- | --- |
| tools-stock-001 | stock_lookup |
| tools-booking-001 | appointment_booking |
| tools-crm-001 | crm_update |
| tools-ticket-001 | ticket_create |
| tools-refund-001 | refund_policy |
| tools-none-thanks-001 | no_tool_needed |
| tools-none-policy-001 | no_tool_needed |
| tools-none-calc-001 | no_tool_needed |
| tools-halluc-iban-001 | tool_hallucination |
| tools-halluc-email-001 | tool_hallucination |
| tools-turn-stock-001 | tool_result_answer |
| tools-turn-booking-001 | tool_result_answer |
| tools-stock-001-crowded | toolset_crowded |
| tools-booking-001-crowded | toolset_crowded |
| tools-crm-001-crowded | toolset_crowded |
| tools-refund-001-crowded | toolset_crowded |

## Usage

```bash
uv run sme-bench validate suites/sme-tools-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-tools-v0.1 --output runs/sme-tools-v0.1
```
