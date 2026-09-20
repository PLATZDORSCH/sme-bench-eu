# SME Advanced v0.1

| Feld | Wert |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite-ID** | `sme-advanced-v0.1` |
| **Fälle** | 36 (18 DE/EN-Paare) |
| **Sprachen** | `de-DE`, `en-GB` |
| **Rolle** | Harte Mehrschritt-Suite; Teil von **SME Full** ab Inhalt 0.11.0 |

Abstimmung, gemischte MwSt, Policy-Ausnahmen, Änderungsmails, Wochenend-Fälligkeit, Doppel-IBAN und Over-Refusal-Injection.

## Task-Typen

| Pair ID | Task-Typ |
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

## Verwendung

```bash
uv run sme-bench validate suites/sme-advanced-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-advanced-v0.1 --output runs/advanced-v01
```
