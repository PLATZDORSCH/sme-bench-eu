# SME Chains & Security v0.1

| | |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite-ID** | `sme-chains-v0.1` |
| **Fälle** | 14 (7 DE/EN-Paare) |
| **Sprachen** | `de-DE`, `en-GB` |
| **Rolle** | Domänenpack Prozessketten + kritische Security; Teil von **SME Full** |

Mehrstufige Prozessentscheidungen sowie IBAN-Tausch, PII-Exfiltration und Secret-Leak-Szenarien.

## Task-Typen

| Pair ID | Task-Typ | Risiko |
| --- | --- | --- |
| chain-invoice-001 | process_next_step | high |
| chain-fulfill-001 | process_next_step | high |
| chain-escalate-001 | process_next_step | high |
| chain-book-001 | process_next_step | high |
| sec-iban-001 | payment_integrity | critical |
| sec-pii-001 | pii_detection | critical |
| sec-secret-001 | prompt_injection | critical |

## Verwendung

```bash
uv run sme-bench validate suites/sme-chains-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-chains-v0.1 --output runs/chains-v01
```

Standard-Ranking ohne `--suite` = SME Full (enthält diesen Pack).
