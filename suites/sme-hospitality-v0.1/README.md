# SME Hospitality v0.1

| Field | Value |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite ID** | `sme-hospitality-v0.1` |
| **Cases** | 14 (7 DE/EN pairs) |
| **Languages** | `de-DE`, `en-GB` |
| **Role** | Food service/hotel test suite; part of **SME Full** |

Catering orders, reservations, guest tickets, F&B revenue, and house rules.

## Task types

| Pair ID | Task type |
| --- | --- |
| ho-order-001 | order_extraction |
| ho-reply-001 | customer_reply |
| ho-missing-001 | missing_information |
| ho-support-001 | support_routing |
| ho-csv-001 | csv_analysis |
| ho-grounded-001 | grounded_qa |
| ho-meeting-001 | meeting_actions |

## Usage

```bash
uv run sme-bench validate suites/sme-hospitality-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-hospitality-v0.1 --output runs/hospitality-v01
```

Standard ranking without `--suite` = SME Full (includes this test suite).
