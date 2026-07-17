# SME Financial v0.1

| | |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite-ID** | `sme-financial-v0.1` |
| **Fälle** | 14 (7 DE/EN-Paare) |
| **Sprachen** | `de-DE`, `en-GB` |
| **Rolle** | Domänenpack Buchhaltung/Finance; Teil von **SME Full** |

Lieferantenrechnungen, Spesen, MwSt-Richtlinien, Zahlungserinnerungen und Finanzrunden.

## Task-Typen

| Pair ID | Task-Typ |
| --- | --- |
| fi-invoice-001 | invoice_extraction |
| fi-csv-001 | csv_analysis |
| fi-missing-001 | missing_information |
| fi-support-001 | support_routing |
| fi-grounded-001 | grounded_qa |
| fi-reply-001 | customer_reply |
| fi-meeting-001 | meeting_actions |

## Verwendung

```bash
uv run sme-bench validate suites/sme-financial-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-financial-v0.1 --output runs/financial-v01
```

Standard-Ranking ohne `--suite` = SME Full (enthält diesen Pack).
