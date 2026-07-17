# SME Financial v0.1

| | |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite ID** | `sme-financial-v0.1` |
| **Cases** | 14 (7 DE/EN pairs) |
| **Languages** | `de-DE`, `en-GB` |
| **Role** | Accounting/finance domain pack; part of **SME Full** |

Supplier invoices, expenses, VAT policies, payment reminders, and financial rounding.

## Task types

| Pair ID | Task type |
| --- | --- |
| fi-invoice-001 | invoice_extraction |
| fi-csv-001 | csv_analysis |
| fi-missing-001 | missing_information |
| fi-support-001 | support_routing |
| fi-grounded-001 | grounded_qa |
| fi-reply-001 | customer_reply |
| fi-meeting-001 | meeting_actions |

## Usage

```bash
uv run sme-bench validate suites/sme-financial-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-financial-v0.1 --output runs/financial-v01
```

Standard ranking without `--suite` = SME Full (includes this pack).
