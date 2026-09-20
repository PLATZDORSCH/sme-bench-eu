# SME Chains & Security v0.1

| Feld | Wert |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite-ID** | `sme-chains-v0.1` |
| **Fälle** | 4 (2 DE/EN-Paare) |
| **Sprachen** | `de-DE`, `en-GB` |
| **Rolle** | Test-Suite Prozessketten + kritische Security; Teil von **SME Full** |

Mehrstufige Prozessentscheidungen sowie IBAN-Tausch und PII-Exfiltration.

## Task-Typen

| Pair ID | Task-Typ | Risiko |
| --- | --- | --- |
| chain-fulfill-001 | process_next_step | high |
| sec-pii-001 | pii_detection | critical |

## Verwendung

```bash
uv run sme-bench validate suites/sme-chains-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-chains-v0.1 --output runs/chains-v01
```

Standard-Ranking ohne `--suite` = SME Full (enthält diese Test-Suite).
