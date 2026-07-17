# SME Logistics v0.1

| | |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite ID** | `sme-logistics-v0.1` |
| **Cases** | 14 (7 DE/EN pairs) |
| **Languages** | `de-DE`, `en-GB` |
| **Role** | Logistics/warehouse domain pack; part of **SME Full** |

Freight invoices, order picking, shipping SLAs, delay tickets, and dispatch readiness.

## Task types

| Pair ID | Task type |
| --- | --- |
| lo-invoice-001 | invoice_extraction |
| lo-order-001 | order_extraction |
| lo-missing-001 | missing_information |
| lo-support-001 | support_routing |
| lo-csv-001 | csv_analysis |
| lo-grounded-001 | grounded_qa |
| lo-process-001 | process_readiness |

## Usage

```bash
uv run sme-bench validate suites/sme-logistics-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-logistics-v0.1 --output runs/logistics-v01
```

Standard ranking without `--suite` = SME Full (includes this pack).
