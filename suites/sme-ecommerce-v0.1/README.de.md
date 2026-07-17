# SME E-Commerce v0.1

| Feld | Wert |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite-ID** | `sme-ecommerce-v0.1` |
| **Fälle** | 14 (7 DE/EN-Paare) |
| **Sprachen** | `de-DE`, `en-GB` |
| **Rolle** | Domänenpack Shop/Retail; Teil von **SME Full** |

Retoure-Threads, Katalog-/Feed-Normalisierung, Zahlungstickets und UGC-Prompt-Injection.

## Task-Typen

| Pair ID | Task-Typ |
| --- | --- |
| ec-order-001 | order_extraction |
| ec-reply-001 | customer_reply |
| ec-product-001 | product_normalization |
| ec-csv-001 | csv_analysis |
| ec-support-001 | support_routing |
| ec-grounded-001 | grounded_qa |
| ec-injection-001 | prompt_injection |

## Verwendung

```bash
uv run sme-bench validate suites/sme-ecommerce-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-ecommerce-v0.1 --output runs/ecommerce-v01
```

Standard-Ranking ohne `--suite` = SME Full (enthält diesen Pack).
