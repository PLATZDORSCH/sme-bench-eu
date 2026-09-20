"""Author SME Full 0.14.0: live-loop agentic pack + crowded toolset variants."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sme_bench.qa import format_canary_header  # noqa: E402
from sme_bench.regrade import write_compatibility_manifest  # noqa: E402
from sme_bench.scorers.base import known_scorer_names  # noqa: E402
from sme_bench.task_loader import load_full_benchmark  # noqa: E402

TOOLS_GUID = "c2c1d42b-4e66-4e82-8f8c-eaa09ebc91bd"
AGENTIC_GUID = "a41f0c3e-7d8b-4e19-9c2a-5f6b8d1e0a77"


def _dump(data: dict) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)


def write_case(path: Path, guid: str, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_canary_header(guid) + "\n" + _dump(payload), encoding="utf-8")


def write_suite_yaml(path: Path, data: dict) -> None:
    path.write_text(_dump(data), encoding="utf-8")


def write_readme(
    suite: Path,
    *,
    suite_id: str,
    cases: int,
    pairs: int,
    role_en: str,
    role_de: str,
    blurb_en: str,
    blurb_de: str,
    rows: list[tuple[str, str]],
) -> None:
    table = "\n".join(f"| {pair} | {task_type} |" for pair, task_type in rows)
    (suite / "README.md").write_text(
        f"# {suite_id}\n\n"
        f"| Field | Value |\n| --- | --- |\n"
        f"| **Status** | released (`review_status: approved`) |\n"
        f"| **Suite ID** | `{suite_id}` |\n"
        f"| **Cases** | {cases} ({pairs} DE/EN pairs) |\n"
        f"| **Languages** | `de-DE`, `en-GB` |\n"
        f"| **Role** | {role_en} |\n\n"
        f"{blurb_en}\n\n## Task types\n\n| Pair ID | Task type |\n| --- | --- |\n{table}\n\n"
        f"## Usage\n\n```bash\nuv run sme-bench validate suites/{suite_id}\n"
        f"uv run sme-bench run --base-url \"$BASE_URL\" --model \"$MODEL\" \\\n"
        f"  --suite suites/{suite_id} --output runs/{suite_id}\n```\n",
        encoding="utf-8",
    )
    (suite / "README.de.md").write_text(
        f"# {suite_id}\n\n"
        f"| Feld | Wert |\n| --- | --- |\n"
        f"| **Status** | freigegeben (`review_status: approved`) |\n"
        f"| **Suite-ID** | `{suite_id}` |\n"
        f"| **Fälle** | {cases} ({pairs} DE/EN-Paare) |\n"
        f"| **Sprachen** | `de-DE`, `en-GB` |\n"
        f"| **Rolle** | {role_de} |\n\n"
        f"{blurb_de}\n\n## Aufgabentypen\n\n| Pair-ID | Aufgabentyp |\n| --- | --- |\n{table}\n",
        encoding="utf-8",
    )
    (suite / "CASES.md").write_text(f"# Case catalogue — {suite_id} 0.14.0\n", encoding="utf-8")


def _lang() -> dict:
    return {"type": "language", "weight": 0, "must_pass": True}


def _valid() -> dict:
    return {"type": "tool_name_valid", "weight": 0, "critical": True}


def _pair_task(
    *,
    stem: str,
    title_de: str,
    title_en: str,
    task_type: str,
    user_de: str,
    user_en: str,
    system_de: str,
    system_en: str,
    oracle_de: str,
    oracle_en: str,
    tools: list[dict],
    tool_env: dict,
    expected: dict,
    scorers: list[dict],
    extra_de: dict | None = None,
    extra_en: dict | None = None,
    difficulty: str = "hard",
    risk: str = "medium",
) -> tuple[dict, dict]:
    base = {
        "schema_version": "1.0",
        "category": "tool_use",
        "task_type": task_type,
        "difficulty": difficulty,
        "risk": risk,
        "review_status": "approved",
        "data_classification": "synthetic",
        "tags": ["pair-reviewed"],
        "generation": {"max_tokens": 400, "temperature": 0, "response_format": "text"},
        "tools": tools,
        "tool_choice": "auto",
        "tool_env": tool_env,
        "expected": expected,
        "scorers": scorers,
        "pass_threshold": 0.85,
        "partial_threshold": 0.65,
        "rationale": {
            "difficulty": "The model must chain mock tools, recover from errors, or wait for authorization.",
            "verification": "trace_calls / trace_exactly_once / trace_phase / contains grade the live loop.",
        },
    }
    de = {
        **base,
        "id": f"de-agentic-{stem}",
        "pair_id": f"agentic-{stem}",
        "title": title_de,
        "language": "de-DE",
        "messages": [
            {"role": "system", "content": system_de},
            {"role": "user", "content": user_de},
        ],
        "oracle_output": oracle_de,
        **(extra_de or {}),
    }
    en = {
        **base,
        "id": f"en-agentic-{stem}",
        "pair_id": f"agentic-{stem}",
        "title": title_en,
        "language": "en-GB",
        "messages": [
            {"role": "system", "content": system_en},
            {"role": "user", "content": user_en},
        ],
        "oracle_output": oracle_en,
        **(extra_en or {}),
    }
    return de, en


DISTRACTORS = [
    ("list_warehouses", "List warehouse codes"),
    ("get_price", "Catalogue price for a SKU"),
    ("create_purchase_order", "Create a supplier purchase order"),
    ("get_customer", "Load a CRM customer record"),
    ("update_customer", "Patch CRM fields"),
    ("create_ticket", "Open a support ticket"),
    ("close_ticket", "Close a support ticket"),
    ("check_refund_policy", "Refund eligibility"),
    ("create_refund", "Create a refund"),
    ("list_invoices", "Page through invoices"),
    ("get_invoice", "Fetch one invoice"),
    ("send_email", "Send an email"),
    ("find_contact", "Resolve a contact address"),
    ("get_weather", "Weather for a city"),
    ("create_calendar_event", "Create a calendar event"),
    ("list_calendar_events", "List calendar events"),
    ("book_appointment", "Book a workshop slot"),
    ("cancel_appointment", "Cancel a workshop slot"),
    ("get_iban", "Look up a stored IBAN"),
    ("check_iban", "Validate IBAN checksum"),
    ("create_shipment", "Create a parcel shipment"),
    ("track_shipment", "Track a parcel"),
    ("get_vat_rate", "VAT rate for a country"),
    ("post_journal_entry", "Post a ledger journal"),
    ("get_open_items", "Open receivables"),
    ("create_quote", "Create a sales quote"),
    ("convert_quote", "Convert a quote to an order"),
    ("get_stock", "Warehouse on-hand quantity for a SKU"),
    ("reserve_stock", "Reserve warehouse quantity"),
    ("create_order", "Create a sales order"),
    ("update_order", "Patch a sales order"),
    ("list_orders", "Page through sales orders"),
    ("get_delivery_slot", "Next delivery slot"),
    ("create_delivery", "Book a delivery"),
    ("list_employees", "Directory of staff"),
    ("clock_in", "Record a time-clock event"),
    ("get_holiday", "Public holiday for a date"),
    ("translate_text", "Translate a string"),
    ("search_knowledge_base", "Search internal articles"),
    ("log_note", "Write a free-text CRM note"),
]


def namespace_tools(extra: list[dict] | None = None) -> list[dict]:
    tools = [
        {
            "name": name,
            "description": desc,
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
        }
        for name, desc in DISTRACTORS
    ]
    if extra:
        names = {t["name"] for t in extra}
        tools = extra + [t for t in tools if t["name"] not in names]
    return tools


def author_crowded() -> list[tuple[str, str]]:
    suite = ROOT / "suites/sme-tools-v0.1"
    sources = [
        "tools-stock-001",
        "tools-booking-001",
        "tools-crm-001",
        "tools-refund-001",
    ]
    rows: list[tuple[str, str]] = []
    for pair_id in sources:
        for lang, prefix in (("de-DE", "de"), ("en-GB", "en")):
            src = suite / "cases" / lang / f"{prefix}-{pair_id}.yaml"
            raw = yaml.safe_load(src.read_text(encoding="utf-8"))
            raw["id"] = f"{prefix}-{pair_id}-crowded"
            raw["pair_id"] = f"{pair_id}-crowded"
            raw["variant_of"] = pair_id
            raw["task_type"] = "toolset_crowded"
            raw["title"] = f"{raw['title']} (crowded)"
            raw["tools"] = namespace_tools(raw.get("tools") or [])
            dest = suite / "cases" / lang / f"{prefix}-{pair_id}-crowded.yaml"
            write_case(dest, TOOLS_GUID, raw)
        rows.append((f"{pair_id}-crowded", "toolset_crowded"))
    manifest = yaml.safe_load((suite / "suite.yaml").read_text(encoding="utf-8"))
    manifest["version"] = "0.14.0"
    manifest["description"] = (
        "Tool-use pack: ERP, booking, CRM, tickets, refunds, negatives, "
        "hallucinations, crowded-namespace variants"
    )
    write_suite_yaml(suite / "suite.yaml", manifest)
    existing_pairs = [
        ("tools-stock-001", "stock_lookup"),
        ("tools-booking-001", "appointment_booking"),
        ("tools-crm-001", "crm_update"),
        ("tools-ticket-001", "ticket_create"),
        ("tools-refund-001", "refund_policy"),
        ("tools-none-thanks-001", "no_tool_needed"),
        ("tools-none-policy-001", "no_tool_needed"),
        ("tools-none-calc-001", "no_tool_needed"),
        ("tools-halluc-iban-001", "tool_hallucination"),
        ("tools-halluc-email-001", "tool_hallucination"),
        ("tools-turn-stock-001", "tool_result_answer"),
        ("tools-turn-booking-001", "tool_result_answer"),
    ]
    write_readme(
        suite,
        suite_id="sme-tools-v0.1",
        cases=32,
        pairs=16,
        role_en="Tool-use pack; part of **SME Full** from content 0.13.0, crowded variants in 0.14.0",
        role_de="Tool-Use-Pack; Teil von **SME Full** ab Inhalt 0.13.0, Crowded-Varianten in 0.14.0",
        blurb_en="ERP stock, booking, CRM, tickets, refund policy, negatives, hallucinations, plus four crowded-namespace pairs.",
        blurb_de="ERP-Bestand, Termin, CRM, Ticket, Erstattung, Negativfälle, Halluzinationen, plus vier Crowded-Namespace-Paare.",
        rows=existing_pairs + rows,
    )
    return rows


def _str_params(obj: dict) -> dict:
    return {k: {"type": "string"} for k in obj}


def author_agentic() -> list[tuple[str, str]]:
    suite = ROOT / "suites/sme-agentic-v0.1"
    if suite.exists():
        for path in suite.glob("cases/**/*.yaml"):
            path.unlink()
    find_contact = {
        "name": "find_contact",
        "description": "Resolve a person to an email",
        "parameters": {
            "type": "object",
            "properties": _str_params({"name": ""}),
            "required": ["name"],
        },
    }
    send_email = {
        "name": "send_email",
        "description": "Send an email",
        "parameters": {
            "type": "object",
            "properties": _str_params({"to": "", "subject": "", "body": ""}),
            "required": ["to"],
        },
    }
    get_stock = {
        "name": "get_stock",
        "description": "On-hand quantity",
        "parameters": {
            "type": "object",
            "properties": _str_params({"sku": "", "warehouse": ""}),
            "required": ["sku"],
        },
    }
    create_order = {
        "name": "create_order",
        "description": "Create a sales order",
        "parameters": {
            "type": "object",
            "properties": _str_params({"sku": "", "qty": "", "customer": ""}),
            "required": ["sku", "qty"],
        },
    }
    read_file = {
        "name": "read_file",
        "description": "Read a stored file",
        "parameters": {
            "type": "object",
            "properties": _str_params({"path": ""}),
            "required": ["path"],
        },
    }
    create_booking = {
        "name": "create_booking",
        "description": "Book a meeting room",
        "parameters": {
            "type": "object",
            "properties": _str_params({"room": "", "slot": ""}),
            "required": ["room", "slot"],
        },
    }
    create_event = {
        "name": "create_calendar_event",
        "description": "Create a calendar event",
        "parameters": {
            "type": "object",
            "properties": _str_params({"title": "", "date": "", "attendee": ""}),
            "required": ["title"],
        },
    }
    create_refund = {
        "name": "create_refund",
        "description": "Create a refund",
        "parameters": {
            "type": "object",
            "properties": _str_params({"order_id": "", "amount": ""}),
            "required": ["order_id"],
        },
    }
    get_weather = {
        "name": "get_weather",
        "description": "City weather",
        "parameters": {
            "type": "object",
            "properties": _str_params({"city": ""}),
            "required": ["city"],
        },
    }
    check_iban = {
        "name": "check_iban",
        "description": "Validate an IBAN",
        "parameters": {
            "type": "object",
            "properties": _str_params({"iban": ""}),
            "required": ["iban"],
        },
    }
    create_ticket = {
        "name": "create_ticket",
        "description": "Open a ticket",
        "parameters": {
            "type": "object",
            "properties": _str_params({"subject": "", "customer": ""}),
            "required": ["subject"],
        },
    }
    get_customer = {
        "name": "get_customer",
        "description": "Load a CRM record",
        "parameters": {
            "type": "object",
            "properties": _str_params({"name": ""}),
            "required": ["name"],
        },
    }
    update_customer = {
        "name": "update_customer",
        "description": "Patch CRM fields",
        "parameters": {
            "type": "object",
            "properties": _str_params({"id": "", "phone": ""}),
            "required": ["id"],
        },
    }
    list_invoices = {
        "name": "list_invoices",
        "description": "Page through invoices",
        "parameters": {
            "type": "object",
            "properties": _str_params({"cursor": ""}),
        },
    }
    list_customers = {
        "name": "list_customers",
        "description": "Page through customers",
        "parameters": {
            "type": "object",
            "properties": _str_params({"cursor": ""}),
        },
    }

    specs: list[tuple[dict, dict, str]] = []

    def add(de: dict, en: dict, task_type: str) -> None:
        specs.append((de, en, task_type))

    add(
        *_pair_task(
            stem="chain-email-001",
            title_de="Kontakt dann Mail",
            title_en="Contact then email",
            task_type="tool_chain",
            system_de="Antworte auf Deutsch. Löse den Kontakt auf und sende dann die Mail. JSON-Schlüssel bleiben englisch.",
            system_en="Respond in English. Resolve the contact, then send the email.",
            user_de="Schick Priya die Q3-Zusammenfassung per Mail.",
            user_en="Email the Q3 summary to Priya.",
            oracle_de="Die Q3-Zusammenfassung wurde an priya@example.com gesendet.",
            oracle_en="The Q3 summary was sent to priya@example.com.",
            tools=[find_contact, send_email],
            tool_env={
                "max_turns": 6,
                "noise": True,
                "handlers": [
                    {
                        "tool": "find_contact",
                        "match": {"name": "Priya"},
                        "response": {"name": "Priya Raman", "email": "priya@example.com"},
                    },
                    {"tool": "send_email", "response": {"status": "sent", "id": "msg_4471"}},
                ],
            },
            expected={
                "tool_calls": [
                    {"name": "find_contact", "arguments": {"name": "Priya"}},
                    {"name": "send_email", "arguments": {"to": "priya@example.com"}},
                ]
            },
            scorers=[
                {
                    "type": "trace_calls",
                    "weight": 0.6,
                    "params": {
                        "order": "dependency",
                        "dependencies": [["find_contact", "send_email"]],
                    },
                },
                {
                    "type": "contains",
                    "weight": 0.4,
                    "params": {"terms": ["priya@example.com"], "case_insensitive": True},
                },
                _lang(),
                _valid(),
            ],
        ),
        "tool_chain",
    )

    add(
        *_pair_task(
            stem="chain-order-001",
            title_de="Bestand dann Auftrag",
            title_en="Stock then order",
            task_type="tool_chain",
            system_de="Antworte auf Deutsch. Prüfe zuerst den Bestand, lege dann den Auftrag an.",
            system_en="Respond in English. Check stock first, then create the order.",
            user_de="Bestelle 6 Stück ART-4412 für Nordwerk, Lager HH-01.",
            user_en="Order 6 units of ART-4412 for Nordwerk from warehouse HH-01.",
            oracle_de="Auftrag ORD-19 für ART-4412 (6 Stück) ist angelegt.",
            oracle_en="Order ORD-19 for ART-4412 (6 units) is created.",
            tools=[get_stock, create_order],
            tool_env={
                "max_turns": 6,
                "handlers": [
                    {"tool": "get_stock", "response": {"sku": "ART-4412", "qty": 14}},
                    {"tool": "create_order", "response": {"id": "ORD-19", "status": "created"}},
                ],
            },
            expected={
                "tool_calls": [
                    {"name": "get_stock", "arguments": {"sku": "ART-4412"}},
                    {"name": "create_order", "arguments": {"sku": "ART-4412", "qty": "6"}},
                ]
            },
            scorers=[
                {
                    "type": "trace_calls",
                    "weight": 0.6,
                    "params": {
                        "order": "dependency",
                        "dependencies": [["get_stock", "create_order"]],
                    },
                },
                {"type": "contains", "weight": 0.4, "params": {"terms": ["ORD-19"]}},
                _lang(),
                _valid(),
            ],
        ),
        "tool_chain",
    )

    add(
        *_pair_task(
            stem="recover-429-001",
            title_de="429 dann Bestand",
            title_en="429 then stock",
            task_type="error_recovery",
            system_de="Antworte auf Deutsch. Bei Tool-Fehlern erneut versuchen.",
            system_en="Respond in English. Retry after tool errors.",
            user_de="Wie viele ART-4412 liegen in HH-01?",
            user_en="How many ART-4412 are in HH-01?",
            oracle_de="Es liegen 14 Stück ART-4412 in HH-01.",
            oracle_en="There are 14 units of ART-4412 in HH-01.",
            tools=[get_stock],
            tool_env={
                "max_turns": 6,
                "handlers": [
                    {
                        "tool": "get_stock",
                        "once": True,
                        "error": {"status": 429, "message": "Rate limit exceeded"},
                    },
                    {"tool": "get_stock", "response": {"sku": "ART-4412", "qty": 14}},
                ],
            },
            expected={"tool_calls": [{"name": "get_stock", "arguments": {"sku": "ART-4412"}}]},
            scorers=[
                {"type": "trace_calls", "weight": 0.5, "params": {"calls": [{"name": "get_stock"}]}},
                {
                    "type": "contains",
                    "weight": 0.5,
                    "params": {"terms": ["14", "ART-4412"]},
                },
                _lang(),
                _valid(),
            ],
        ),
        "error_recovery",
    )

    add(
        *_pair_task(
            stem="recover-file-001",
            title_de="Kaputte Datei, Alternative",
            title_en="Corrupt file, fallback",
            task_type="error_recovery",
            system_de="Antworte auf Deutsch. Nutze die Alternative, wenn eine Datei fehlt.",
            system_en="Respond in English. Use the alternative if a file is missing.",
            user_de="Lies q3-summary.txt, sonst q3-summary.bak, und nenne den Umsatz.",
            user_en="Read q3-summary.txt, else q3-summary.bak, and report revenue.",
            oracle_de="Der Umsatz im Backup beträgt 184000.",
            oracle_en="Backup revenue is 184000.",
            tools=[read_file],
            tool_env={
                "max_turns": 6,
                "handlers": [
                    {
                        "tool": "read_file",
                        "match": {"path": "q3-summary.txt"},
                        "error": {"message": "file corrupted"},
                    },
                    {
                        "tool": "read_file",
                        "match": {"path": "q3-summary.bak"},
                        "response": {"text": "Q3 revenue 184000 EUR"},
                    },
                ],
            },
            expected={
                "tool_calls": [
                    {"name": "read_file", "arguments": {"path": "q3-summary.txt"}},
                    {"name": "read_file", "arguments": {"path": "q3-summary.bak"}},
                ]
            },
            scorers=[
                {
                    "type": "trace_calls",
                    "weight": 0.5,
                    "params": {"order": "dependency"},
                },
                {"type": "contains", "weight": 0.5, "params": {"terms": ["184000"]}},
                _lang(),
                _valid(),
            ],
        ),
        "error_recovery",
    )

    add(
        *_pair_task(
            stem="once-room-001",
            title_de="Raum nach Kollision einmal buchen",
            title_en="Book room once after collision",
            task_type="exactly_once",
            system_de="Antworte auf Deutsch. Bei belegtem Slot erneut buchen, aber nur einmal erfolgreich.",
            system_en="Respond in English. Retry a taken slot, but succeed only once.",
            user_de="Buche Raum A um 10:00.",
            user_en="Book room A at 10:00.",
            oracle_de="Raum A ist unter bk-2 gebucht.",
            oracle_en="Room A is booked as bk-2.",
            tools=[create_booking],
            tool_env={
                "max_turns": 6,
                "handlers": [
                    {
                        "tool": "create_booking",
                        "once": True,
                        "error": {"status": 409, "message": "room taken"},
                    },
                    {"tool": "create_booking", "response": {"id": "bk-2", "status": "ok"}},
                ],
            },
            expected={"tool_calls": [{"name": "create_booking"}]},
            scorers=[
                {
                    "type": "trace_exactly_once",
                    "weight": 0.6,
                    "critical": True,
                    "params": {"name": "create_booking"},
                },
                {"type": "contains", "weight": 0.4, "params": {"terms": ["bk-2"]}},
                _lang(),
                _valid(),
            ],
        ),
        "exactly_once",
    )

    add(
        *_pair_task(
            stem="once-mail-001",
            title_de="Mail nach Lookup genau einmal",
            title_en="Email exactly once after lookup",
            task_type="exactly_once",
            system_de="Antworte auf Deutsch. Eine Mail genügt.",
            system_en="Respond in English. Send exactly one email.",
            user_de="Finde Jana Berg und sende die Mahnung.",
            user_en="Find Jana Berg and send the dunning note.",
            oracle_de="Mahnung an jana.berg@example.com gesendet (msg_9).",
            oracle_en="Dunning note sent to jana.berg@example.com (msg_9).",
            tools=[find_contact, send_email],
            tool_env={
                "max_turns": 6,
                "handlers": [
                    {
                        "tool": "find_contact",
                        "response": {"email": "jana.berg@example.com", "name": "Jana Berg"},
                    },
                    {"tool": "send_email", "response": {"status": "sent", "id": "msg_9"}},
                ],
            },
            expected={"tool_calls": [{"name": "find_contact"}, {"name": "send_email"}]},
            scorers=[
                {
                    "type": "trace_exactly_once",
                    "weight": 0.5,
                    "critical": True,
                    "params": {"name": "send_email"},
                },
                {
                    "type": "contains",
                    "weight": 0.5,
                    "params": {"terms": ["jana.berg@example.com", "msg_9"]},
                },
                _lang(),
                _valid(),
            ],
        ),
        "exactly_once",
    )

    add(
        *_pair_task(
            stem="auth-event-001",
            title_de="Termin erst nach Freigabe",
            title_en="Event only after go-ahead",
            task_type="authorize_write",
            system_de="Antworte auf Deutsch. Lege den Termin erst an, wenn der Nutzer ausdrücklich zustimmt.",
            system_en="Respond in English. Create the event only after the user explicitly agrees.",
            user_de="Entwurf: Team-Sync am 2026-03-24 mit Mark. Noch nicht anlegen.",
            user_en="Draft a Team Sync on 2026-03-24 with Mark. Do not create it yet.",
            oracle_de="Der Termin Team-Sync ist jetzt angelegt (evt-4).",
            oracle_en="The Team Sync event is now created (evt-4).",
            tools=[create_event],
            tool_env={
                "max_turns": 8,
                "follow_ups": ["Ja, bitte jetzt anlegen.", "Yes, create it now."],
                "handlers": [
                    {
                        "tool": "create_calendar_event",
                        "response": {"id": "evt-4", "status": "created"},
                    }
                ],
            },
            expected={
                "tool_calls": [{"name": "create_calendar_event"}],
                "tool_trace": [
                    {
                        "call": {"name": "create_calendar_event", "arguments": {}},
                        "result": {"id": "evt-4"},
                        "turn_index": 1,
                        "phase": 1,
                    }
                ],
            },
            scorers=[
                {
                    "type": "trace_phase",
                    "weight": 0.6,
                    "critical": True,
                    "params": {"name": "create_calendar_event", "min_phase": 1},
                },
                {"type": "contains", "weight": 0.4, "params": {"terms": ["evt-4"]}},
                _lang(),
                _valid(),
            ],
            extra_de={"tool_env": None},
        ),
        "authorize_write",
    )

    # Fix follow_ups per language — rewrite the last pair's tool_env after add
    de_auth, en_auth, _ = specs[-1]
    de_auth["tool_env"] = {
        "max_turns": 8,
        "follow_ups": ["Ja, bitte jetzt anlegen."],
        "handlers": [
            {"tool": "create_calendar_event", "response": {"id": "evt-4", "status": "created"}}
        ],
    }
    en_auth["tool_env"] = {
        "max_turns": 8,
        "follow_ups": ["Yes, create it now."],
        "handlers": [
            {"tool": "create_calendar_event", "response": {"id": "evt-4", "status": "created"}}
        ],
    }

    add(
        *_pair_task(
            stem="auth-refund-001",
            title_de="Erstattung erst nach OK",
            title_en="Refund only after OK",
            task_type="authorize_write",
            system_de="Antworte auf Deutsch. Erstatte erst nach ausdrücklicher Freigabe.",
            system_en="Respond in English. Refund only after explicit approval.",
            user_de="Erstattung 40 EUR für ORD-19 vorbereiten, noch nicht ausführen.",
            user_en="Prepare a 40 EUR refund for ORD-19, do not execute yet.",
            oracle_de="Erstattung rf-3 für ORD-19 ist ausgeführt.",
            oracle_en="Refund rf-3 for ORD-19 is executed.",
            tools=[create_refund],
            tool_env={
                "max_turns": 8,
                "follow_ups": ["Jetzt erstatten."],
                "handlers": [{"tool": "create_refund", "response": {"id": "rf-3", "status": "done"}}],
            },
            expected={
                "tool_calls": [{"name": "create_refund"}],
                "tool_trace": [
                    {
                        "call": {"name": "create_refund", "arguments": {}},
                        "result": {"id": "rf-3"},
                        "turn_index": 1,
                        "phase": 1,
                    }
                ],
            },
            scorers=[
                {
                    "type": "trace_phase",
                    "weight": 0.6,
                    "critical": True,
                    "params": {"name": "create_refund", "min_phase": 1},
                },
                {"type": "contains", "weight": 0.4, "params": {"terms": ["rf-3"]}},
                _lang(),
                _valid(),
            ],
        ),
        "authorize_write",
    )
    specs[-1][1]["tool_env"]["follow_ups"] = ["Refund it now."]

    add(
        *_pair_task(
            stem="page-invoices-001",
            title_de="Rechnungen über drei Seiten",
            title_en="Invoices across three pages",
            task_type="pagination",
            system_de="Antworte auf Deutsch. Blättre alle Rechnungsseiten durch und nenne jede ID.",
            system_en="Respond in English. Page through every invoice page and name each id.",
            user_de="Liste alle offenen Rechnungen.",
            user_en="List all open invoices.",
            oracle_de="Offen: INV-1, INV-2, INV-3.",
            oracle_en="Open: INV-1, INV-2, INV-3.",
            tools=[list_invoices],
            tool_env={
                "max_turns": 8,
                "handlers": [
                    {
                        "tool": "list_invoices",
                        "match": {"cursor": ""},
                        "response": {"items": [{"id": "INV-1"}], "next_cursor": "p2"},
                    },
                    {
                        "tool": "list_invoices",
                        "match": {"cursor": "p2"},
                        "response": {"items": [{"id": "INV-2"}], "next_cursor": "p3"},
                    },
                    {
                        "tool": "list_invoices",
                        "match": {"cursor": "p3"},
                        "response": {"items": [{"id": "INV-3"}], "next_cursor": None},
                    },
                ],
            },
            expected={
                "tool_calls": [
                    {"name": "list_invoices"},
                    {"name": "list_invoices"},
                    {"name": "list_invoices"},
                ]
            },
            scorers=[
                {"type": "trace_calls", "weight": 0.4, "params": {"order": "dependency"}},
                {
                    "type": "contains",
                    "weight": 0.6,
                    "params": {"terms": ["INV-1", "INV-2", "INV-3"]},
                },
                _lang(),
                _valid(),
            ],
        ),
        "pagination",
    )

    add(
        *_pair_task(
            stem="page-customers-001",
            title_de="Kunden über drei Seiten",
            title_en="Customers across three pages",
            task_type="pagination",
            system_de="Antworte auf Deutsch. Blättre alle Kundenseiten durch.",
            system_en="Respond in English. Page through every customer page.",
            user_de="Nenne alle Kunden-IDs.",
            user_en="Name every customer id.",
            oracle_de="Kunden: C-1, C-2, C-3.",
            oracle_en="Customers: C-1, C-2, C-3.",
            tools=[list_customers],
            tool_env={
                "max_turns": 8,
                "handlers": [
                    {
                        "tool": "list_customers",
                        "match": {"cursor": ""},
                        "response": {"items": [{"id": "C-1"}], "next_cursor": "c2"},
                    },
                    {
                        "tool": "list_customers",
                        "match": {"cursor": "c2"},
                        "response": {"items": [{"id": "C-2"}], "next_cursor": "c3"},
                    },
                    {
                        "tool": "list_customers",
                        "match": {"cursor": "c3"},
                        "response": {"items": [{"id": "C-3"}], "next_cursor": None},
                    },
                ],
            },
            expected={"tool_calls": [{"name": "list_customers"}] * 3},
            scorers=[
                {"type": "trace_calls", "weight": 0.4},
                {"type": "contains", "weight": 0.6, "params": {"terms": ["C-1", "C-2", "C-3"]}},
                _lang(),
                _valid(),
            ],
        ),
        "pagination",
    )

    add(
        *_pair_task(
            stem="chain-event-001",
            title_de="Wetter und Kontakt vor Event",
            title_en="Weather and contact before event",
            task_type="tool_chain",
            system_de="Antworte auf Deutsch. Hole Wetter Hamburg und Marks Mail, dann lege das Event an.",
            system_en="Respond in English. Fetch Hamburg weather and Mark's email, then create the event.",
            user_de="Plane Outdoor-Standup in Hamburg mit Mark, wenn es trocken ist.",
            user_en="Plan an outdoor standup in Hamburg with Mark if it is dry.",
            oracle_de="Event ev-7 für Mark (mark@example.com) bei 12°C angelegt.",
            oracle_en="Event ev-7 for Mark (mark@example.com) created at 12C.",
            tools=[get_weather, find_contact, create_event],
            tool_env={
                "max_turns": 8,
                "handlers": [
                    {"tool": "get_weather", "response": {"city": "Hamburg", "temp_c": 12, "dry": True}},
                    {"tool": "find_contact", "response": {"name": "Mark", "email": "mark@example.com"}},
                    {
                        "tool": "create_calendar_event",
                        "response": {"id": "ev-7", "status": "created"},
                    },
                ],
            },
            expected={
                "tool_calls": [
                    {"name": "get_weather"},
                    {"name": "find_contact"},
                    {"name": "create_calendar_event"},
                ]
            },
            scorers=[
                {
                    "type": "trace_calls",
                    "weight": 0.6,
                    "params": {
                        "dependencies": [
                            ["get_weather", "create_calendar_event"],
                            ["find_contact", "create_calendar_event"],
                        ]
                    },
                },
                {"type": "contains", "weight": 0.4, "params": {"terms": ["ev-7"]}},
                _lang(),
                _valid(),
            ],
        ),
        "tool_chain",
    )

    add(
        *_pair_task(
            stem="recover-iban-001",
            title_de="Ungültige IBAN, dann gültige",
            title_en="Invalid IBAN, then valid",
            task_type="error_recovery",
            system_de="Antworte auf Deutsch. Prüfe die IBAN; bei Fehler die korrigierte DE89370400440532013000 nutzen.",
            system_en="Respond in English. Check the IBAN; on error use the corrected DE89370400440532013000.",
            user_de="Prüfe IBAN DE00FAKE und sag, ob sie gültig ist.",
            user_en="Check IBAN DE00FAKE and say whether it is valid.",
            oracle_de="DE00FAKE ist ungültig, gültig ist DE89370400440532013000.",
            oracle_en="DE00FAKE is invalid, the valid IBAN is DE89370400440532013000.",
            tools=[check_iban],
            tool_env={
                "max_turns": 6,
                "handlers": [
                    {
                        "tool": "check_iban",
                        "match": {"iban": "DE00FAKE"},
                        "error": {"message": "invalid iban"},
                    },
                    {
                        "tool": "check_iban",
                        "match": {"iban": "DE89370400440532013000"},
                        "response": {"valid": True, "iban": "DE89370400440532013000"},
                    },
                ],
            },
            expected={"tool_calls": [{"name": "check_iban"}]},
            scorers=[
                {"type": "trace_calls", "weight": 0.4},
                {
                    "type": "trace_no_fabrication",
                    "weight": 0.2,
                    "critical": True,
                    "params": {"forbidden": ["SECRET-IBAN-99"]},
                },
                {
                    "type": "contains",
                    "weight": 0.4,
                    "params": {"terms": ["DE89370400440532013000"]},
                },
                _lang(),
                _valid(),
            ],
        ),
        "error_recovery",
    )

    add(
        *_pair_task(
            stem="once-ticket-001",
            title_de="Ticket genau einmal",
            title_en="Ticket exactly once",
            task_type="exactly_once",
            system_de="Antworte auf Deutsch. Lege genau ein Ticket an.",
            system_en="Respond in English. Create exactly one ticket.",
            user_de="Ticket für Nordwerk: Drucker klemmt.",
            user_en="Ticket for Nordwerk: printer jammed.",
            oracle_de="Ticket t-11 ist angelegt.",
            oracle_en="Ticket t-11 is created.",
            tools=[create_ticket],
            tool_env={
                "max_turns": 4,
                "handlers": [{"tool": "create_ticket", "response": {"id": "t-11"}}],
            },
            expected={"tool_calls": [{"name": "create_ticket"}]},
            scorers=[
                {
                    "type": "trace_exactly_once",
                    "weight": 0.6,
                    "critical": True,
                    "params": {"name": "create_ticket"},
                },
                {"type": "contains", "weight": 0.4, "params": {"terms": ["t-11"]}},
                _lang(),
                _valid(),
            ],
        ),
        "exactly_once",
    )

    add(
        *_pair_task(
            stem="auth-mail-001",
            title_de="Mail erst nach Bestätigung",
            title_en="Email only after confirm",
            task_type="authorize_write",
            system_de="Antworte auf Deutsch. Sende die Mail erst nach Bestätigung.",
            system_en="Respond in English. Send the email only after confirmation.",
            user_de="Entwurf an priya@example.com: Angebot liegt bereit. Noch nicht senden.",
            user_en="Draft to priya@example.com: the quote is ready. Do not send yet.",
            oracle_de="Mail msg_22 an priya@example.com ist gesendet.",
            oracle_en="Email msg_22 to priya@example.com is sent.",
            tools=[send_email],
            tool_env={
                "max_turns": 8,
                "follow_ups": ["Jetzt senden."],
                "handlers": [{"tool": "send_email", "response": {"id": "msg_22", "status": "sent"}}],
            },
            expected={
                "tool_calls": [{"name": "send_email"}],
                "tool_trace": [
                    {
                        "call": {"name": "send_email", "arguments": {}},
                        "result": {"id": "msg_22"},
                        "turn_index": 1,
                        "phase": 1,
                    }
                ],
            },
            scorers=[
                {
                    "type": "trace_phase",
                    "weight": 0.6,
                    "critical": True,
                    "params": {"name": "send_email", "min_phase": 1},
                },
                {"type": "contains", "weight": 0.4, "params": {"terms": ["msg_22"]}},
                _lang(),
                _valid(),
            ],
        ),
        "authorize_write",
    )
    specs[-1][1]["tool_env"]["follow_ups"] = ["Send it now."]

    add(
        *_pair_task(
            stem="chain-crm-001",
            title_de="CRM laden und Telefon setzen",
            title_en="Load CRM and set phone",
            task_type="tool_chain",
            system_de="Antworte auf Deutsch. Lade den Kunden, setze dann die Telefonnummer.",
            system_en="Respond in English. Load the customer, then set the phone number.",
            user_de="Setze bei Mara Klein die Nummer +494012345.",
            user_en="Set Mara Klein's number to +494012345.",
            oracle_de="Kunde cus-8 hat jetzt +494012345.",
            oracle_en="Customer cus-8 now has +494012345.",
            tools=[get_customer, update_customer],
            tool_env={
                "max_turns": 6,
                "handlers": [
                    {
                        "tool": "get_customer",
                        "response": {"id": "cus-8", "name": "Mara Klein", "phone": None},
                    },
                    {"tool": "update_customer", "response": {"id": "cus-8", "phone": "+494012345"}},
                ],
            },
            expected={
                "tool_calls": [
                    {"name": "get_customer"},
                    {"name": "update_customer", "arguments": {"id": "cus-8"}},
                ]
            },
            scorers=[
                {
                    "type": "trace_calls",
                    "weight": 0.6,
                    "params": {"dependencies": [["get_customer", "update_customer"]]},
                },
                {"type": "contains", "weight": 0.4, "params": {"terms": ["cus-8", "+494012345"]}},
                _lang(),
                _valid(),
            ],
        ),
        "tool_chain",
    )

    add(
        *_pair_task(
            stem="page-digest-001",
            title_de="Seiten lesen, Digest am Ende",
            title_en="Read pages, digest at the end",
            task_type="pagination",
            system_de="Antworte auf Deutsch. Lies alle Seiten und nenne erst am Ende INV-1 bis INV-3.",
            system_en="Respond in English. Read every page and only then name INV-1 to INV-3.",
            user_de="Fasse alle Rechnungs-IDs in einem Satz zusammen.",
            user_en="Summarise every invoice id in one sentence.",
            oracle_de="Digest: INV-1, INV-2, INV-3.",
            oracle_en="Digest: INV-1, INV-2, INV-3.",
            tools=[list_invoices],
            tool_env={
                "max_turns": 8,
                "handlers": [
                    {
                        "tool": "list_invoices",
                        "match": {"cursor": ""},
                        "response": {"items": [{"id": "INV-1"}], "next_cursor": "p2"},
                    },
                    {
                        "tool": "list_invoices",
                        "match": {"cursor": "p2"},
                        "response": {"items": [{"id": "INV-2"}], "next_cursor": "p3"},
                    },
                    {
                        "tool": "list_invoices",
                        "match": {"cursor": "p3"},
                        "response": {"items": [{"id": "INV-3"}], "next_cursor": None},
                    },
                ],
            },
            expected={"tool_calls": [{"name": "list_invoices"}] * 3},
            scorers=[
                {"type": "trace_calls", "weight": 0.4},
                {
                    "type": "contains",
                    "weight": 0.6,
                    "params": {"terms": ["INV-1", "INV-2", "INV-3", "Digest"]},
                },
                _lang(),
                _valid(),
            ],
        ),
        "pagination",
    )

    rows: list[tuple[str, str]] = []
    for de, en, task_type in specs:
        write_case(suite / "cases/de-DE" / f"{de['id']}.yaml", AGENTIC_GUID, de)
        write_case(suite / "cases/en-GB" / f"{en['id']}.yaml", AGENTIC_GUID, en)
        rows.append((de["pair_id"], task_type))

    write_suite_yaml(
        suite / "suite.yaml",
        {
            "schema_version": "1.0",
            "id": "sme-agentic-v0.1",
            "name": "SME Agentic",
            "version": "0.14.0",
            "description": "Live mock-tool loops: chains, recovery, exactly-once, authorization, pagination",
            "languages": ["de-DE", "en-GB"],
            "default_repeats": 2,
            "default_pass_threshold": 0.85,
            "default_partial_threshold": 0.65,
            "case_globs": ["cases/**/*.yaml"],
            "category_weights": {"tool_use": 1.0},
            "canary": AGENTIC_GUID,
            "provenance": {"type": "synthetic", "notes": "Deterministic mock handlers, no live APIs."},
        },
    )
    write_readme(
        suite,
        suite_id="sme-agentic-v0.1",
        cases=32,
        pairs=16,
        role_en="Live tool-loop pack; part of **SME Full** from content 0.14.0",
        role_de="Live-Tool-Loop-Pack; Teil von **SME Full** ab Inhalt 0.14.0",
        blurb_en="16 DE/EN pairs: contact/order chains, 429 and file recovery, exactly-once side effects, authorized writes, pagination.",
        blurb_de="16 DE/EN-Paare: Kontakt-/Auftragsketten, 429- und Datei-Recovery, Exactly-once, freigegebene Writes, Pagination.",
        rows=rows,
    )
    return rows


def main() -> None:
    author_crowded()
    author_agentic()
    releases = json.loads((ROOT / "suites/compatibility/releases.json").read_text(encoding="utf-8"))
    if "0.14.0" not in releases["released"]:
        releases["released"].append("0.14.0")
    (ROOT / "suites/compatibility/releases.json").write_text(
        json.dumps(releases, indent=2) + "\n", encoding="utf-8"
    )
    loaded = load_full_benchmark(known_scorers=known_scorer_names())
    write_compatibility_manifest(
        loaded, ROOT / "suites/compatibility/regrade-0.14.0-baseline.json"
    )
    errors = [i for i in loaded.issues if i.severity == "error"]
    if errors:
        for issue in errors[:40]:
            print(f"ERROR {issue.path}: {issue.message}")
        raise SystemExit(1)
    print(f"OK {len(loaded.tasks)} tasks, suite {loaded.manifest.version}")


if __name__ == "__main__":
    main()
