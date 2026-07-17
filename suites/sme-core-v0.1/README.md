# SME Core v0.1

| | |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite ID** | `sme-core-v0.1` |
| **Cases** | 72 (36 DE/EN pairs) |
| **Languages** | `de-DE`, `en-GB` |
| **Role** | Core benchmark; optional part of **SME Full** |

Cross-domain SME tasks: extraction, routing, grounded QA, security — across industries.

## Variants

| Variant | Focus | Examples |
| --- | --- | --- |
| `*-001` | Baseline | Clear emails, standard formats |
| `*-002` | More noise | Forwards, chats, alternative formats |
| `*-003` | Hard / edge cases | 7 % VAT, tie-break, partial PII |

## Task types

| Task type | Category | Variants |
| --- | --- | --- |
| invoice_extraction | document_extraction | 001–003 |
| order_extraction | sales_operations | 001–003 |
| support_routing | customer_service | 001–003 |
| missing_information | sales_operations | 001–003 |
| customer_reply | customer_service | 001–003 |
| offer_comparison | sales_operations | 001–003 |
| product_normalization | commerce | 001–003 |
| csv_analysis | data_analysis | 001–003 |
| meeting_actions | meeting_operations | 001–003 |
| grounded_qa | grounded_qa | 001–003 |
| pii_detection | privacy_security | 001–003 |
| prompt_injection | privacy_security | 001–003 |

## Provenance

- `provenance.type: synthetic`
- No real personal, customer, or company data
- Names, IBAN-like strings, and domains are illustrative (`example`, `demo.test`)

## Usage

```bash
# Core only
uv run sme-bench validate suites/sme-core-v0.1
uv run sme-bench catalog suites/sme-core-v0.1
uv run sme-bench run \
  --base-url "$BASE_URL" \
  --model "$MODEL" \
  --suite suites/sme-core-v0.1 \
  --output runs/core-v01

# Standard ranking: Full (Core + domains), no --suite needed
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" --output runs/full
```

## Limitations

- Free text: deterministic scorers (required content / prohibitions), no LLM-as-a-Judge
- No industry-specific legal advice
- Domain-specific difficulty lives in the domain packs (Trades, Financial, …)
