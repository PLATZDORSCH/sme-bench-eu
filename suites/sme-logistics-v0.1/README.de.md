# SME Logistics v0.1

| Feld | Wert |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite-ID** | `sme-logistics-v0.1` |
| **Fälle** | 14 (7 DE/EN-Paare) |
| **Sprachen** | `de-DE`, `en-GB` |
| **Rolle** | Domänenpack Logistik/Lager; Teil von **SME Full** |

Frachtrechnungen, Kommissionierung, Versand-SLA, Verspätungstickets und Dispatch-Readiness.

## Task-Typen

| Pair ID | Task-Typ |
| --- | --- |
| lo-invoice-001 | invoice_extraction |
| lo-order-001 | order_extraction |
| lo-missing-001 | missing_information |
| lo-support-001 | support_routing |
| lo-csv-001 | csv_analysis |
| lo-grounded-001 | grounded_qa |
| lo-process-001 | process_readiness |

## Verwendung

```bash
uv run sme-bench validate suites/sme-logistics-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-logistics-v0.1 --output runs/logistics-v01
```

Standard-Ranking ohne `--suite` = SME Full (enthält diesen Pack).
