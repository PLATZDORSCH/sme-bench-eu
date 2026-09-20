# SME Advanced v0.1

| Field | Value |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite ID** | `sme-advanced-v0.1` |
| **Cases** | 36 (18 DE/EN pairs) |
| **Languages** | `de-DE`, `en-GB` |
| **Role** | Hard multi-step pack; part of **SME Full** from content 0.11.0 |

Reconciliation, mixed VAT, policy exceptions, revision threads, weekend due dates, dual IBAN, and over-refusal injection.

## Task types

| Pair ID | Task type |
| --- | --- |
| adv-reconcile-001 | payment_reconciliation |
| adv-csv-001 | csv_analysis |
| adv-invoice-thread-001 | invoice_extraction |
| adv-vat-split-001 | invoice_extraction |
| adv-policy-001 | grounded_qa |
| adv-conflict-001 | grounded_qa |
| adv-order-revision-001 | order_extraction |
| adv-order-revision-002 | order_extraction |
| adv-deadline-001 | process_readiness |
| adv-chain-precond-001 | process_next_step |
| adv-pii-001 | pii_detection |
| adv-injection-001 | prompt_injection |
| adv-injection-002 | prompt_injection |
| adv-iban-002 | payment_integrity |
| adv-support-multi-001 | support_routing |
| adv-offer-001 | offer_comparison |
| adv-meeting-001 | meeting_actions |
| adv-missing-001 | missing_information |

## Usage

```bash
uv run sme-bench validate suites/sme-advanced-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-advanced-v0.1 --output runs/advanced-v01
```
