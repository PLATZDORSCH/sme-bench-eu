# SME Expert v0.1

| Feld | Wert |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite-ID** | `sme-expert-v0.1` |
| **Fälle** | 20 (10 DE/EN-Paare) |
| **Sprachen** | `de-DE`, `en-GB` |
| **Rolle** | Sehr harte Mehrschritt-Suite; Teil von **SME Full** ab Inhalt 0.12.0 |

Skonto-Abstimmung, gemischte MwSt plus Anzahlung, Cashflow-Wochen, Policy-Ketten, Änderungsmails, Mahnung, PII in Weiterleitungen, Agent-Injection, IBAN-Betrug, Drei-Jahres-TCO.

## Task-Typen

| Pair ID | Task-Typ |
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

## Verwendung

```bash
uv run sme-bench validate suites/sme-expert-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-expert-v0.1 --output runs/expert-v01
```
