# SME Trades v0.1

| Field | Value |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite ID** | `sme-trades-v0.1` |
| **Cases** | 14 (7 DE/EN pairs) |
| **Languages** | `de-DE`, `en-GB` |
| **Role** | Trades/construction test suite; part of **SME Full** |

Longer fixtures: site-survey emails, material orders, contractor invoices, on-site communication.

## Task types

| Pair ID | Task type |
| --- | --- |
| tr-invoice-001 | invoice_extraction |
| tr-order-001 | order_extraction |
| tr-missing-001 | missing_information |
| tr-support-001 | support_routing |
| tr-grounded-001 | grounded_qa |
| tr-meeting-001 | meeting_actions |
| tr-process-quote-001 | process_readiness |

## Usage

```bash
uv run sme-bench validate suites/sme-trades-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-trades-v0.1 --output runs/trades-v01
```

Standard ranking without `--suite` = SME Full (includes this test suite).
