# SME Chains & Security v0.1

| Field | Value |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite ID** | `sme-chains-v0.1` |
| **Cases** | 4 (2 DE/EN pairs) |
| **Languages** | `de-DE`, `en-GB` |
| **Role** | Process-chains + critical security test suite; part of **SME Full** |

Multi-step process decisions plus IBAN swap and PII exfiltration.

## Task types

| Pair ID | Task type | Risk |
| --- | --- | --- |
| chain-fulfill-001 | process_next_step | high |
| sec-pii-001 | pii_detection | critical |

## Usage

```bash
uv run sme-bench validate suites/sme-chains-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-chains-v0.1 --output runs/chains-v01
```

Standard ranking without `--suite` = SME Full (includes this test suite).
