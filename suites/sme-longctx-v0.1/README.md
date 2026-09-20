# sme-longctx-v0.1

| Field | Value |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite ID** | `sme-longctx-v0.1` |
| **Cases** | 16 (8 DE/EN pairs) |
| **Languages** | `de-DE`, `en-GB` |
| **Role** | Long-context pack; part of **SME Full** from content 0.13.0 |

Sales/stock CSVs, contract notice and liability, price and approval threads, meeting owner.

## Task types

| Pair ID | Task type |
| --- | --- |
| longctx-sales-csv-001 | csv_analysis |
| longctx-stock-csv-001 | csv_analysis |
| longctx-notice-001 | contract_qa |
| longctx-liability-001 | contract_qa |
| longctx-price-thread-001 | thread_qa |
| longctx-approval-001 | thread_qa |
| longctx-invoice-policy-001 | csv_analysis |
| longctx-meeting-001 | meeting_actions |

## Usage

```bash
uv run sme-bench validate suites/sme-longctx-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-longctx-v0.1 --output runs/sme-longctx-v0.1
```
