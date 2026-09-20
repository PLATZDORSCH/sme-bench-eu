# sme-agentic-v0.1

| Field | Value |
| --- | --- |
| **Status** | released (`review_status: approved`) |
| **Suite ID** | `sme-agentic-v0.1` |
| **Cases** | 32 (16 DE/EN pairs) |
| **Languages** | `de-DE`, `en-GB` |
| **Role** | Live tool-loop pack; part of **SME Full** from content 0.14.0 |

16 DE/EN pairs: contact/order chains, 429 and file recovery, exactly-once side effects, authorized writes, pagination.

## Task types

| Pair ID | Task type |
| --- | --- |
| agentic-chain-email-001 | tool_chain |
| agentic-chain-order-001 | tool_chain |
| agentic-recover-429-001 | error_recovery |
| agentic-recover-file-001 | error_recovery |
| agentic-once-room-001 | exactly_once |
| agentic-once-mail-001 | exactly_once |
| agentic-auth-event-001 | authorize_write |
| agentic-auth-refund-001 | authorize_write |
| agentic-page-invoices-001 | pagination |
| agentic-page-customers-001 | pagination |
| agentic-chain-event-001 | tool_chain |
| agentic-recover-iban-001 | error_recovery |
| agentic-once-ticket-001 | exactly_once |
| agentic-auth-mail-001 | authorize_write |
| agentic-chain-crm-001 | tool_chain |
| agentic-page-digest-001 | pagination |

## Usage

```bash
uv run sme-bench validate suites/sme-agentic-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-agentic-v0.1 --output runs/sme-agentic-v0.1
```
