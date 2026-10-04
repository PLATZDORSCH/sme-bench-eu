# sme-tools-v0.1

| Field | Value |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite ID** | `sme-tools-v0.1` |
| **Cases** | 52 (26 DE/EN pairs) |
| **Languages** | `de-DE`, `en-GB` |
| **Role** | Tool-use pack; part of **SME Full** from content 0.13.0, crowded variants in 0.14.0, schema-heavy calls in 0.15.0 |

ERP stock, booking, CRM, tickets, refund policy, negatives, hallucinations, four crowded-namespace pairs, plus wide signatures, nested objects, line-item arrays, enum literals and optional-field omission.

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
| tools-wide-customer-001 | wide_signature |
| tools-wide-offer-001 | wide_signature |
| tools-nested-address-001 | nested_argument |
| tools-array-order-001 | array_argument |
| tools-array-timesheet-001 | array_argument |
| tools-enum-ticket-001 | enum_literal |
| tools-enum-date-001 | enum_literal |
| tools-omit-update-001 | optional_omission |
| tools-date-arith-001 | date_arithmetic |
| tools-unit-convert-001 | unit_conversion |

## Usage

```bash
uv run sme-bench validate suites/sme-tools-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-tools-v0.1 --output runs/sme-tools-v0.1
```
