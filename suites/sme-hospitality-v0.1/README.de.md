# SME Hospitality v0.1

| Feld | Wert |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite-ID** | `sme-hospitality-v0.1` |
| **Fälle** | 14 (7 DE/EN-Paare) |
| **Sprachen** | `de-DE`, `en-GB` |
| **Rolle** | Domänenpack Gastro/Hotel; Teil von **SME Full** |

Catering-Bestellungen, Reservierungen, Gästetickets, F&B-Umsatz und Hausregeln.

## Task-Typen

| Pair ID | Task-Typ |
| --- | --- |
| ho-order-001 | order_extraction |
| ho-reply-001 | customer_reply |
| ho-missing-001 | missing_information |
| ho-support-001 | support_routing |
| ho-csv-001 | csv_analysis |
| ho-grounded-001 | grounded_qa |
| ho-meeting-001 | meeting_actions |

## Verwendung

```bash
uv run sme-bench validate suites/sme-hospitality-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-hospitality-v0.1 --output runs/hospitality-v01
```

Standard-Ranking ohne `--suite` = SME Full (enthält diesen Pack).
