# SME Chains & Security v0.1

| | |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite ID** | `sme-chains-v0.1` |
| **Cases** | 14 (7 DE/EN pairs) |
| **Languages** | `de-DE`, `en-GB` |
| **Role** | Process-chains + critical security domain pack; part of **SME Full** |

Multi-step process decisions plus IBAN swap, PII exfiltration, and secret-leak scenarios.

## Task types

| Pair ID | Task type | Risk |
| --- | --- | --- |
| chain-invoice-001 | process_next_step | high |
| chain-fulfill-001 | process_next_step | high |
| chain-escalate-001 | process_next_step | high |
| chain-book-001 | process_next_step | high |
| sec-iban-001 | payment_integrity | critical |
| sec-pii-001 | pii_detection | critical |
| sec-secret-001 | prompt_injection | critical |

## Usage

```bash
uv run sme-bench validate suites/sme-chains-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-chains-v0.1 --output runs/chains-v01
```

Standard ranking without `--suite` = SME Full (includes this pack).
