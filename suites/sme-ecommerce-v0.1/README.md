# SME E-Commerce v0.1

| | |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite ID** | `sme-ecommerce-v0.1` |
| **Cases** | 14 (7 DE/EN pairs) |
| **Languages** | `de-DE`, `en-GB` |
| **Role** | Shop/retail domain pack; part of **SME Full** |

Return threads, catalogue/feed normalisation, payment tickets, and UGC prompt injection.

## Task types

| Pair ID | Task type |
| --- | --- |
| ec-order-001 | order_extraction |
| ec-reply-001 | customer_reply |
| ec-product-001 | product_normalization |
| ec-csv-001 | csv_analysis |
| ec-support-001 | support_routing |
| ec-grounded-001 | grounded_qa |
| ec-injection-001 | prompt_injection |

## Usage

```bash
uv run sme-bench validate suites/sme-ecommerce-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-ecommerce-v0.1 --output runs/ecommerce-v01
```

Standard ranking without `--suite` = SME Full (includes this pack).
