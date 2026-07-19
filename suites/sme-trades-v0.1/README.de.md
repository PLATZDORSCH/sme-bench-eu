# SME Trades v0.1

| Feld | Wert |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite-ID** | `sme-trades-v0.1` |
| **Fälle** | 14 (7 DE/EN-Paare) |
| **Sprachen** | `de-DE`, `en-GB` |
| **Rolle** | Test-Suite Handwerk/Bau; Teil von **SME Full** |

Längere Fixtures: Aufmaß-Mails, Materialbestellungen, Handwerkerrechnungen, Baustellenkommunikation.

## Task-Typen

| Pair ID | Task-Typ |
| --- | --- |
| tr-invoice-001 | invoice_extraction |
| tr-order-001 | order_extraction |
| tr-missing-001 | missing_information |
| tr-support-001 | support_routing |
| tr-grounded-001 | grounded_qa |
| tr-meeting-001 | meeting_actions |
| tr-process-quote-001 | process_readiness |

## Verwendung

```bash
uv run sme-bench validate suites/sme-trades-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-trades-v0.1 --output runs/trades-v01
```

Standard-Ranking ohne `--suite` = SME Full (enthält diese Test-Suite).
