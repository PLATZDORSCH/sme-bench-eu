# SME Expert v0.1

| Field | Value |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite ID** | `sme-expert-v0.1` |
| **Cases** | 20 (10 DE/EN pairs) |
| **Languages** | `de-DE`, `en-GB` |
| **Role** | Very hard multi-step pack; part of **SME Full** from content 0.12.0 |

Skonto reconciliation, mixed VAT plus deposit, cash-flow weeks, policy chains, revision threads, dunning, PII forwards, agent injection, IBAN fraud, three-year TCO.

## Task types

| Pair ID | Task type |
| --- | --- |
| exp-reconcile-001 | payment_reconciliation |
| exp-vat-deposit-001 | invoice_extraction |
| exp-cashflow-001 | csv_analysis |
| exp-policy-chain-001 | grounded_qa |
| exp-order-thread-001 | order_extraction |
| exp-dunning-001 | process_readiness |
| exp-pii-forward-001 | pii_detection |
| exp-injection-agent-001 | prompt_injection |
| exp-iban-fraud-001 | payment_integrity |
| exp-offer-tco-001 | offer_comparison |

## Usage

```bash
uv run sme-bench validate suites/sme-expert-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-expert-v0.1 --output runs/expert-v01
```
