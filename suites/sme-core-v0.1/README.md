# SME Core v0.1

| | |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite-ID** | `sme-core-v0.1` |
| **Fälle** | 72 (36 DE/EN-Paare) |
| **Sprachen** | `de-DE`, `en-GB` |
| **Rolle** | Kernbenchmark; optionaler Teil von **SME Full** |

Cross-domain KMU-Aufgaben: Extraktion, Routing, Grounded QA, Security — branchenübergreifend.

## Varianten

| Variante | Fokus | Beispiele |
| --- | --- | --- |
| `*-001` | Basis | Klare E-Mails, Standardformate |
| `*-002` | Mehr Rauschen | Forwards, Chats, Alternativformate |
| `*-003` | Härtegrad / Sonderfälle | 7 % MwSt, Tie-Break, partielle PII |

## Task-Typen

| Task-Typ | Kategorie | Varianten |
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

## Herkunft

- `provenance.type: synthetic`
- Keine echten Personen-, Kunden- oder Firmendaten
- Namen, IBAN-ähnliche Strings und Domains sind demonstrativ (`example`, `demo.test`)

## Verwendung

```bash
# Nur Core
uv run sme-bench validate suites/sme-core-v0.1
uv run sme-bench catalog suites/sme-core-v0.1
uv run sme-bench run \
  --base-url "$BASE_URL" \
  --model "$MODEL" \
  --suite suites/sme-core-v0.1 \
  --output runs/core-v01

# Standard-Ranking: Full (Core + Domänen), kein --suite nötig
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" --output runs/full
```

## Grenzen

- Freitext: deterministische Scorer (Pflichtinhalte / Verbote), kein LLM-as-Judge
- Keine branchenspezifische Rechtsberatung
- Domänenspezifische Härte liegt in den Domain-Packs (Trades, Financial, …)
