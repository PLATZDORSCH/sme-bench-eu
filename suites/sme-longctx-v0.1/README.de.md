# sme-longctx-v0.1

| Feld | Wert |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite-ID** | `sme-longctx-v0.1` |
| **Fälle** | 16 (8 DE/EN-Paare) |
| **Sprachen** | `de-DE`, `en-GB` |
| **Rolle** | Long-Context-Pack; Teil von **SME Full** ab Inhalt 0.13.0 |

Umsatz-/Bestands-CSV, Vertragskündigung und Haftung, Preis- und Genehmigungsthreads, Meeting-Owner.

## Task-Typen

| Pair-ID | Task-Typ |
| --- | --- |
| longctx-sales-csv-001 | csv_analysis |
| longctx-stock-csv-001 | csv_analysis |
| longctx-notice-001 | contract_qa |
| longctx-liability-001 | contract_qa |
| longctx-price-thread-001 | thread_qa |
| longctx-approval-001 | thread_qa |
| longctx-invoice-policy-001 | csv_analysis |
| longctx-meeting-001 | meeting_actions |

## Nutzung

```bash
uv run sme-bench validate suites/sme-longctx-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-longctx-v0.1 --output runs/sme-longctx-v0.1
```
