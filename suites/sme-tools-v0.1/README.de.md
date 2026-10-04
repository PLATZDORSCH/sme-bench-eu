# sme-tools-v0.1

| Feld | Wert |
| --- | --- |
| **Status** | freigegeben (`review_status: approved`) |
| **Suite-ID** | `sme-tools-v0.1` |
| **Fälle** | 52 (26 DE/EN-Paare) |
| **Sprachen** | `de-DE`, `en-GB` |
| **Rolle** | Tool-Use-Pack; Teil von **SME Full** ab Inhalt 0.13.0, Crowded-Varianten in 0.14.0, Schema-Aufrufe in 0.15.0 |

ERP-Bestand, Termin, CRM, Ticket, Erstattung, Negativfälle, Halluzinationen, vier Crowded-Namespace-Paare plus breite Signaturen, verschachtelte Objekte, Positions-Arrays, Enum-Literale und Weglassen optionaler Felder.

## Aufgabentypen

| Pair-ID | Aufgabentyp |
| --- | --- |
| tools-stock-001 | stock_lookup |
| tools-booking-001 | appointment_booking |
| tools-crm-001 | crm_update |
| tools-ticket-001 | ticket_create |
| tools-refund-001 | refund_policy |
| tools-none-thanks-001 | no_tool_needed |
| tools-none-policy-001 | no_tool_needed |
| tools-none-calc-001 | no_tool_needed |
| tools-halluc-iban-001 | tool_hallucination |
| tools-halluc-email-001 | tool_hallucination |
| tools-turn-stock-001 | tool_result_answer |
| tools-turn-booking-001 | tool_result_answer |
| tools-stock-001-crowded | toolset_crowded |
| tools-booking-001-crowded | toolset_crowded |
| tools-crm-001-crowded | toolset_crowded |
| tools-refund-001-crowded | toolset_crowded |
| tools-wide-customer-001 | wide_signature |
| tools-wide-offer-001 | wide_signature |
| tools-nested-address-001 | nested_argument |
| tools-array-order-001 | array_argument |
| tools-array-timesheet-001 | array_argument |
| tools-enum-ticket-001 | enum_literal |
| tools-enum-date-001 | enum_literal |
| tools-omit-update-001 | optional_omission |
| tools-date-arith-001 | date_arithmetic |
| tools-unit-convert-001 | unit_conversion |
