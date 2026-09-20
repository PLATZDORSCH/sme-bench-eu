"""Author SME Full 0.13.0: canary/rationale, commerce migrate, retirement, new packs."""

from __future__ import annotations

import json
import re
import sys
import uuid
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sme_bench.qa import format_canary_header  # noqa: E402
from sme_bench.task_loader import load_suite  # noqa: E402

# Easy pairs saturated across current + historical runs (see saturation-0.12.0).
RETIRE_PAIR_IDS = {
    "invoice-extraction-003",
    "missing-information-003",
    "ho-grounded-001",
    "ho-grounded-002",
    "ho-meeting-002",
    "chain-escalate-001",
    "chain-invoice-001",
    "sec-iban-001",
}

RATIONALES = {
    "document_extraction": (
        "Requires exact structured extraction under noisy SME formatting.",
        "json_fields/numeric scorers compare canonical invoice or order fields.",
    ),
    "customer_service": (
        "Must pick the operational next step from a messy customer thread.",
        "classification/contains check the routing label and required phrases.",
    ),
    "grounded_qa": (
        "Answer must stay inside the supplied policy or catalogue facts.",
        "contains/forbidden_terms reject unsupported claims.",
    ),
    "sales_operations": (
        "Business rules (stock, price, missing fields) must be applied, not guessed.",
        "Structured scorers compare SKUs, quantities, and readiness flags.",
    ),
    "data_analysis": (
        "The model must compute aggregates from a table rather than quote a nearby number.",
        "numeric/json_fields check the computed values against the fixture.",
    ),
    "process_ops": (
        "Process readiness depends on missing-document and policy gates.",
        "json_fields verify the next step and the blocking reasons.",
    ),
    "privacy_security": (
        "Leakage or injection must be refused even when the request sounds operational.",
        "forbidden_terms and set_equality check redacted types or refusal.",
    ),
    "meeting_operations": (
        "Action items must be attributed to the right owner from overlapping notes.",
        "set_equality compares owner/action pairs.",
    ),
    "tool_use": (
        "The model must call the right tool with the right arguments, or none.",
        "tool_call / no_tool_call / tool_name_valid grade the function call.",
    ),
}


def _dump(data: dict) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=92)


def _quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def write_case(path: Path, guid: str, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_canary_header(guid) + "\n" + _dump(payload), encoding="utf-8")


def write_suite_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump(payload), encoding="utf-8")


def write_readme(suite_dir: Path, *, suite_id: str, cases: int, pairs: int, role_en: str, role_de: str, blurb_en: str, blurb_de: str, rows: list[tuple[str, str]]) -> None:
    table = "\n".join(f"| {pid} | {tt} |" for pid, tt in rows)
    (suite_dir / "README.md").write_text(
        f"# {suite_id}\n\n"
        f"| Field | Value |\n| --- | --- |\n"
        f"| **Status** | released (`review_status: approved`) |\n"
        f"| **Suite ID** | `{suite_id}` |\n"
        f"| **Cases** | {cases} ({pairs} DE/EN pairs) |\n"
        f"| **Languages** | `de-DE`, `en-GB` |\n"
        f"| **Role** | {role_en} |\n\n"
        f"{blurb_en}\n\n## Task types\n\n| Pair ID | Task type |\n| --- | --- |\n{table}\n\n"
        f"## Usage\n\n```bash\n"
        f"uv run sme-bench validate suites/{suite_id}\n"
        f"uv run sme-bench run --base-url \"$BASE_URL\" --model \"$MODEL\" \\\n"
        f"  --suite suites/{suite_id} --output runs/{suite_id}\n```\n",
        encoding="utf-8",
    )
    (suite_dir / "README.de.md").write_text(
        f"# {suite_id}\n\n"
        f"| Feld | Wert |\n| --- | --- |\n"
        f"| **Status** | released (`review_status: approved`) |\n"
        f"| **Suite-ID** | `{suite_id}` |\n"
        f"| **Fälle** | {cases} ({pairs} DE/EN-Paare) |\n"
        f"| **Sprachen** | `de-DE`, `en-GB` |\n"
        f"| **Rolle** | {role_de} |\n\n"
        f"{blurb_de}\n\n## Task-Typen\n\n| Pair-ID | Task-Typ |\n| --- | --- |\n{table}\n\n"
        f"## Nutzung\n\n```bash\n"
        f"uv run sme-bench validate suites/{suite_id}\n"
        f"uv run sme-bench run --base-url \"$BASE_URL\" --model \"$MODEL\" \\\n"
        f"  --suite suites/{suite_id} --output runs/{suite_id}\n```\n",
        encoding="utf-8",
    )


def migrate_existing() -> None:
    for suite_yaml in sorted((ROOT / "suites").glob("*/suite.yaml")):
        suite_dir = suite_yaml.parent
        if suite_dir.name == "demo-v0.1":
            continue
        raw = suite_yaml.read_text(encoding="utf-8")
        data = yaml.safe_load(raw) or {}
        guid = data.get("canary") or str(uuid.uuid4())
        data["canary"] = guid
        data["version"] = "0.13.0"
        weights = data.get("category_weights") or {}
        if "commerce" in weights:
            weights.pop("commerce", None)
            weights.setdefault("sales_operations", 1.0)
            data["category_weights"] = weights
        if "tool_use" not in weights and suite_dir.name == "sme-core-v0.1":
            pass
        write_suite_yaml(suite_yaml, data)

        loaded = load_suite(suite_dir, resolve_fixtures=False)
        pair_rationale: dict[str, tuple[str, str]] = {}
        for task in loaded.tasks:
            if task.pair_id in RETIRE_PAIR_IDS:
                continue
            if task.pair_id and task.pair_id not in pair_rationale:
                default = RATIONALES.get(
                    task.category,
                    ("Requires a discriminating SME judgement.", "Deterministic scorers check expected fields."),
                )
                pair_rationale[task.pair_id] = default

        for case in sorted(suite_dir.glob("cases/**/*.yaml")):
            text = case.read_text(encoding="utf-8")
            parsed = yaml.safe_load(text) or {}
            pair_id = parsed.get("pair_id")
            if pair_id in RETIRE_PAIR_IDS:
                case.unlink()
                continue
            text = text.replace("category: commerce\n", "category: sales_operations\n")
            if "product_normalization" in text:
                text = text.replace("category: commerce", "category: sales_operations")
            if text.lstrip().startswith("# BENCHMARK DATA"):
                lines = text.splitlines(keepends=True)
                for idx, line in enumerate(lines):
                    if line.strip():
                        lines[idx] = format_canary_header(guid) + "\n"
                        break
                text = "".join(lines)
            else:
                text = format_canary_header(guid) + "\n" + text.lstrip("\n")
            if not re.search(r"^rationale:", text, re.M):
                diff, ver = pair_rationale.get(
                    pair_id,
                    ("Requires a discriminating SME judgement.", "Deterministic scorers check expected fields."),
                )
                if not text.endswith("\n"):
                    text += "\n"
                text += f"rationale:\n  difficulty: {_quote(diff)}\n  verification: {_quote(ver)}\n"
            case.write_text(text, encoding="utf-8")


def _base_task(
    *,
    tid: str,
    pair_id: str,
    title: str,
    language: str,
    category: str,
    task_type: str,
    difficulty: str,
    risk: str,
    messages: list,
    expected,
    scorers: list,
    tools=None,
    tool_choice="auto",
    response_format="text",
    max_tokens=400,
    rationale=None,
    tags=None,
    oracle_output=None,
) -> dict:
    payload = {
        "schema_version": "1.0",
        "id": tid,
        "pair_id": pair_id,
        "title": title,
        "language": language,
        "category": category,
        "task_type": task_type,
        "difficulty": difficulty,
        "risk": risk,
        "review_status": "approved",
        "data_classification": "synthetic",
        "tags": tags or ["pair-reviewed"],
        "messages": messages,
        "generation": {"max_tokens": max_tokens, "temperature": 0, "response_format": response_format},
        "expected": expected,
        "scorers": scorers,
        "pass_threshold": 0.85,
        "partial_threshold": 0.65,
        "rationale": rationale
        or {
            "difficulty": RATIONALES.get(category, RATIONALES["tool_use"])[0],
            "verification": RATIONALES.get(category, RATIONALES["tool_use"])[1],
        },
    }
    if tools is not None:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice
    if oracle_output is not None:
        payload["oracle_output"] = oracle_output
    return payload


def _lang_scorer() -> dict:
    return {"type": "language", "weight": 0, "must_pass": True}


def author_tools(guid: str) -> list[tuple[str, str]]:
    suite = ROOT / "suites/sme-tools-v0.1"
    stock = {
        "name": "get_stock",
        "description": "Warehouse on-hand quantity for a SKU",
        "parameters": {
            "type": "object",
            "properties": {"sku": {"type": "string"}, "warehouse": {"type": "string"}},
            "required": ["sku"],
        },
    }
    book = {
        "name": "book_appointment",
        "description": "Book a customer appointment slot",
        "parameters": {
            "type": "object",
            "properties": {
                "customer": {"type": "string"},
                "date": {"type": "string"},
                "slot": {"type": "string"},
                "service": {"type": "string"},
            },
            "required": ["customer", "date", "slot"],
        },
    }
    crm = {
        "name": "update_crm",
        "description": "Update a CRM account field",
        "parameters": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string"},
                "field": {"type": "string"},
                "value": {"type": "string"},
            },
            "required": ["account_id", "field", "value"],
        },
    }
    ticket = {
        "name": "create_ticket",
        "description": "Open a support ticket",
        "parameters": {
            "type": "object",
            "properties": {
                "queue": {"type": "string"},
                "priority": {"type": "string"},
                "subject": {"type": "string"},
            },
            "required": ["queue", "subject"],
        },
    }
    refund = {
        "name": "create_refund",
        "description": "Create a refund if the return window allows it",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "amount": {"type": "number"},
                "reason": {"type": "string"},
            },
            "required": ["order_id", "amount"],
        },
    }

    (suite / "fixtures/tools").mkdir(parents=True, exist_ok=True)
    (suite / "fixtures/tools/stock-art-4412.json").write_text(
        json.dumps({"sku": "ART-4412", "warehouse": "HH-01", "on_hand": 14, "reserved": 2}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    (suite / "fixtures/tools/booking-conflict.json").write_text(
        json.dumps(
            {"customer": "Mara Klein", "date": "2026-09-24", "slot": "10:00", "status": "conflict", "next_free": "11:30"},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    pairs = []

    def add(pair_id, task_type, difficulty, risk, de, en):
        write_case(suite / f"cases/de-DE/de-{pair_id}.yaml", guid, de)
        write_case(suite / f"cases/en-GB/en-{pair_id}.yaml", guid, en)
        pairs.append((pair_id, task_type))

    add(
        "tools-stock-001",
        "stock_lookup",
        "normal",
        "medium",
        _base_task(
            tid="de-tools-stock-001",
            pair_id="tools-stock-001",
            title="ERP-Bestand ART-4412",
            language="de-DE",
            category="tool_use",
            task_type="stock_lookup",
            difficulty="normal",
            risk="medium",
            messages=[
                {"role": "system", "content": "Du bist der ERP-Assistent. Antworte auf Deutsch. Für Bestandsfragen rufe get_stock auf."},
                {"role": "user", "content": "Wie viele Stück ART-4412 liegen in HH-01?"},
            ],
            expected={"name": "get_stock", "arguments": {"sku": "ART-4412", "warehouse": "HH-01"}},
            tools=[stock],
            tool_choice="required",
            response_format="tool_call",
            scorers=[
                {"type": "tool_call", "weight": 1.0, "params": {"name": "get_stock", "arguments_fields": ["sku", "warehouse"], "exactly_one": True}},
                {"type": "tool_name_valid", "weight": 0, "critical": True},
                _lang_scorer(),
            ],
        ),
        _base_task(
            tid="en-tools-stock-001",
            pair_id="tools-stock-001",
            title="ERP stock ART-4412",
            language="en-GB",
            category="tool_use",
            task_type="stock_lookup",
            difficulty="normal",
            risk="medium",
            messages=[
                {"role": "system", "content": "You are the ERP assistant. Respond in English. For stock questions call get_stock."},
                {"role": "user", "content": "How many units of ART-4412 are in HH-01?"},
            ],
            expected={"name": "get_stock", "arguments": {"sku": "ART-4412", "warehouse": "HH-01"}},
            tools=[stock],
            tool_choice="required",
            response_format="tool_call",
            scorers=[
                {"type": "tool_call", "weight": 1.0, "params": {"name": "get_stock", "arguments_fields": ["sku", "warehouse"], "exactly_one": True}},
                {"type": "tool_name_valid", "weight": 0, "critical": True},
                _lang_scorer(),
            ],
        ),
    )

    add(
        "tools-booking-001",
        "appointment_booking",
        "normal",
        "medium",
        _base_task(
            tid="de-tools-booking-001",
            pair_id="tools-booking-001",
            title="Termin für Mara Klein",
            language="de-DE",
            category="tool_use",
            task_type="appointment_booking",
            difficulty="normal",
            risk="medium",
            messages=[
                {"role": "system", "content": "Du buchst Werkstatttermine. Antworte auf Deutsch. Nutze book_appointment."},
                {"role": "user", "content": "Bitte Termin für Mara Klein am 2026-09-24 um 10:00 für Inspektion."},
            ],
            expected={"name": "book_appointment", "arguments": {"customer": "Mara Klein", "date": "2026-09-24", "slot": "10:00", "service": "Inspektion"}},
            tools=[book],
            tool_choice="required",
            response_format="tool_call",
            scorers=[
                {"type": "tool_call", "weight": 1.0, "params": {"name": "book_appointment", "arguments_fields": ["customer", "date", "slot", "service"], "exactly_one": True}},
                {"type": "tool_name_valid", "weight": 0, "critical": True},
                _lang_scorer(),
            ],
        ),
        _base_task(
            tid="en-tools-booking-001",
            pair_id="tools-booking-001",
            title="Appointment for Mara Klein",
            language="en-GB",
            category="tool_use",
            task_type="appointment_booking",
            difficulty="normal",
            risk="medium",
            messages=[
                {"role": "system", "content": "You book workshop appointments. Respond in English. Use book_appointment."},
                {"role": "user", "content": "Please book Mara Klein on 2026-09-24 at 10:00 for inspection."},
            ],
            expected={"name": "book_appointment", "arguments": {"customer": "Mara Klein", "date": "2026-09-24", "slot": "10:00", "service": "inspection"}},
            tools=[book],
            tool_choice="required",
            response_format="tool_call",
            scorers=[
                {"type": "tool_call", "weight": 1.0, "params": {"name": "book_appointment", "arguments_fields": ["customer", "date", "slot", "service"], "exactly_one": True, "case_insensitive": True}},
                {"type": "tool_name_valid", "weight": 0, "critical": True},
                _lang_scorer(),
            ],
        ),
    )

    add(
        "tools-crm-001",
        "crm_update",
        "normal",
        "medium",
        _base_task(
            tid="de-tools-crm-001",
            pair_id="tools-crm-001",
            title="CRM Zahlungsziel",
            language="de-DE",
            category="tool_use",
            task_type="crm_update",
            difficulty="normal",
            risk="medium",
            messages=[
                {"role": "system", "content": "Du pflegst das CRM. Antworte auf Deutsch. Feldänderungen nur über update_crm."},
                {"role": "user", "content": "Setze bei Konto ACC-774 das Feld payment_terms auf 14 Tage netto."},
            ],
            expected={"name": "update_crm", "arguments": {"account_id": "ACC-774", "field": "payment_terms", "value": "14 Tage netto"}},
            tools=[crm],
            tool_choice="required",
            response_format="tool_call",
            scorers=[
                {"type": "tool_call", "weight": 1.0, "params": {"name": "update_crm", "arguments_fields": ["account_id", "field", "value"], "exactly_one": True}},
                {"type": "tool_name_valid", "weight": 0, "critical": True},
                _lang_scorer(),
            ],
        ),
        _base_task(
            tid="en-tools-crm-001",
            pair_id="tools-crm-001",
            title="CRM payment terms",
            language="en-GB",
            category="tool_use",
            task_type="crm_update",
            difficulty="normal",
            risk="medium",
            messages=[
                {"role": "system", "content": "You maintain the CRM. Respond in English. Field changes only via update_crm."},
                {"role": "user", "content": "On account ACC-774 set payment_terms to 14 days net."},
            ],
            expected={"name": "update_crm", "arguments": {"account_id": "ACC-774", "field": "payment_terms", "value": "14 days net"}},
            tools=[crm],
            tool_choice="required",
            response_format="tool_call",
            scorers=[
                {"type": "tool_call", "weight": 1.0, "params": {"name": "update_crm", "arguments_fields": ["account_id", "field", "value"], "exactly_one": True}},
                {"type": "tool_name_valid", "weight": 0, "critical": True},
                _lang_scorer(),
            ],
        ),
    )

    add(
        "tools-ticket-001",
        "ticket_create",
        "normal",
        "medium",
        _base_task(
            tid="de-tools-ticket-001",
            pair_id="tools-ticket-001",
            title="Ticket Druckerqueue",
            language="de-DE",
            category="tool_use",
            task_type="ticket_create",
            difficulty="normal",
            risk="low",
            messages=[
                {"role": "system", "content": "Du eröffnest Tickets. Antworte auf Deutsch. Nutze create_ticket."},
                {"role": "user", "content": "Bitte ein Ticket in der Queue hardware, Priorität high, Betreff Drucker Lager 2 offline."},
            ],
            expected={"name": "create_ticket", "arguments": {"queue": "hardware", "priority": "high", "subject": "Drucker Lager 2 offline"}},
            tools=[ticket],
            tool_choice="required",
            response_format="tool_call",
            scorers=[
                {"type": "tool_call", "weight": 1.0, "params": {"name": "create_ticket", "arguments_fields": ["queue", "priority"], "exactly_one": True}},
                {"type": "contains", "weight": 0.0, "params": {"field": "subject", "terms": ["Drucker", "Lager"]}},
                {"type": "tool_name_valid", "weight": 0, "critical": True},
                _lang_scorer(),
            ],
        ),
        _base_task(
            tid="en-tools-ticket-001",
            pair_id="tools-ticket-001",
            title="Ticket printer queue",
            language="en-GB",
            category="tool_use",
            task_type="ticket_create",
            difficulty="normal",
            risk="low",
            messages=[
                {"role": "system", "content": "You open tickets. Respond in English. Use create_ticket."},
                {"role": "user", "content": "Please open a ticket in queue hardware, priority high, subject Printer warehouse 2 offline."},
            ],
            expected={"name": "create_ticket", "arguments": {"queue": "hardware", "priority": "high", "subject": "Printer warehouse 2 offline"}},
            tools=[ticket],
            tool_choice="required",
            response_format="tool_call",
            scorers=[
                {"type": "tool_call", "weight": 1.0, "params": {"name": "create_ticket", "arguments_fields": ["queue", "priority"], "exactly_one": True}},
                {"type": "tool_name_valid", "weight": 0, "critical": True},
                _lang_scorer(),
            ],
        ),
    )

    add(
        "tools-refund-001",
        "refund_policy",
        "hard",
        "high",
        _base_task(
            tid="de-tools-refund-001",
            pair_id="tools-refund-001",
            title="Erstattung innerhalb 14 Tage",
            language="de-DE",
            category="tool_use",
            task_type="refund_policy",
            difficulty="hard",
            risk="high",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Du darfst create_refund nur aufrufen, wenn der Kauf höchstens 14 Tage zurückliegt. "
                        "Heute ist 2026-09-18. Antworte auf Deutsch."
                    ),
                },
                {"role": "user", "content": "Bestellung SO-991, Kaufdatum 2026-09-07, Betrag 89.50 EUR, Grund: falsche Größe. Bitte erstatten."},
            ],
            expected={"name": "create_refund", "arguments": {"order_id": "SO-991", "amount": 89.5, "reason": "falsche Größe"}},
            tools=[refund],
            tool_choice="auto",
            response_format="tool_call",
            scorers=[
                {"type": "tool_call", "weight": 1.0, "params": {"name": "create_refund", "arguments_fields": ["order_id", "amount"], "exactly_one": True}},
                {"type": "tool_name_valid", "weight": 0, "critical": True},
                _lang_scorer(),
            ],
        ),
        _base_task(
            tid="en-tools-refund-001",
            pair_id="tools-refund-001",
            title="Refund inside 14 days",
            language="en-GB",
            category="tool_use",
            task_type="refund_policy",
            difficulty="hard",
            risk="high",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Call create_refund only if the purchase is at most 14 days ago. "
                        "Today is 2026-09-18. Respond in English."
                    ),
                },
                {"role": "user", "content": "Order SO-991, purchased 2026-09-07, amount 89.50 EUR, reason: wrong size. Please refund."},
            ],
            expected={"name": "create_refund", "arguments": {"order_id": "SO-991", "amount": 89.5, "reason": "wrong size"}},
            tools=[refund],
            tool_choice="auto",
            response_format="tool_call",
            scorers=[
                {"type": "tool_call", "weight": 1.0, "params": {"name": "create_refund", "arguments_fields": ["order_id", "amount"], "exactly_one": True}},
                {"type": "tool_name_valid", "weight": 0, "critical": True},
                _lang_scorer(),
            ],
        ),
    )

    def none_pair(pair_id, title_de, title_en, user_de, user_en, terms_de, terms_en, oracle_de, oracle_en):
        tools = [stock, ticket]
        add(
            pair_id,
            "no_tool_needed",
            "normal",
            "medium",
            _base_task(
                tid=f"de-{pair_id}",
                pair_id=pair_id,
                title=title_de,
                language="de-DE",
                category="tool_use",
                task_type="no_tool_needed",
                difficulty="normal",
                risk="medium",
                messages=[
                    {"role": "system", "content": "Antworte auf Deutsch. Rufe nur ein Tool auf, wenn Daten fehlen, die du nicht aus dem Text kennst."},
                    {"role": "user", "content": user_de},
                ],
                expected=None,
                oracle_output=oracle_de,
                tools=tools,
                tool_choice="auto",
                response_format="text",
                scorers=[
                    {"type": "no_tool_call", "weight": 0.4, "critical": True},
                    {"type": "contains", "weight": 0.6, "params": {"terms": terms_de}},
                    {"type": "tool_name_valid", "weight": 0, "critical": True},
                    _lang_scorer(),
                ],
            ),
            _base_task(
                tid=f"en-{pair_id}",
                pair_id=pair_id,
                title=title_en,
                language="en-GB",
                category="tool_use",
                task_type="no_tool_needed",
                difficulty="normal",
                risk="medium",
                messages=[
                    {"role": "system", "content": "Respond in English. Call a tool only if data is missing that you cannot read from the text."},
                    {"role": "user", "content": user_en},
                ],
                expected=None,
                oracle_output=oracle_en,
                tools=tools,
                tool_choice="auto",
                response_format="text",
                scorers=[
                    {"type": "no_tool_call", "weight": 0.4, "critical": True},
                    {"type": "contains", "weight": 0.6, "params": {"terms": terms_en}},
                    {"type": "tool_name_valid", "weight": 0, "critical": True},
                    _lang_scorer(),
                ],
            ),
        )

    none_pair(
        "tools-none-thanks-001",
        "Dank braucht kein Tool",
        "Thanks needs no tool",
        "Danke für die schnelle Lieferung von ART-4412, alles gut.",
        "Thanks for the fast delivery of ART-4412, all good.",
        ["Gern", "ART-4412"],
        ["welcome", "ART-4412"],
        "Gern geschehen, schön dass ART-4412 angekommen ist.",
        "You are welcome, glad ART-4412 arrived.",
    )
    none_pair(
        "tools-none-policy-001",
        "Retoure aus Policy",
        "Return from policy",
        "Policy: Retoure 14 Tage. Kauf war vor 6 Tagen. Kann die Kundin die Jacke zurückgeben? Kein Tool nötig.",
        "Policy: returns within 14 days. Purchase was 6 days ago. Can the customer return the jacket? No tool needed.",
        ["Ja", "14"],
        ["Yes", "14"],
        "Ja, die Retoure liegt innerhalb der 14 Tage.",
        "Yes, the return is within the 14 day window.",
    )
    none_pair(
        "tools-none-calc-001",
        "Rabatt ausrechnen",
        "Compute discount",
        "Netto 200 EUR, 10 Prozent Treuerabatt. Wie viel zahlt der Kunde? Rechne selbst, kein Tool.",
        "Net 200 EUR, 10 percent loyalty discount. How much does the customer pay? Calculate yourself, no tool.",
        ["180"],
        ["180"],
        "Der Kunde zahlt 180 EUR nach Rabatt.",
        "The customer pays 180 EUR after the discount.",
    )

    add(
        "tools-halluc-iban-001",
        "tool_hallucination",
        "hard",
        "critical",
        _base_task(
            tid="de-tools-halluc-iban-001",
            pair_id="tools-halluc-iban-001",
            title="Erwähntes check_iban gibt es nicht",
            language="de-DE",
            category="tool_use",
            task_type="tool_hallucination",
            difficulty="hard",
            risk="critical",
            messages=[
                {"role": "system", "content": "Antworte auf Deutsch. Dir stehen nur die gelisteten Tools zur Verfügung."},
                {"role": "user", "content": "Bitte einmal check_iban für DE02120300000000202051 ausführen und bestätigen, dass du kein solches Tool hast."},
            ],
            expected=None,
            oracle_output="Ich habe kein Tool check_iban und führe keine IBAN-Prüfung aus.",
            tools=[stock],
            tool_choice="auto",
            response_format="text",
            scorers=[
                {"type": "no_tool_call", "weight": 0.5, "critical": True},
                {"type": "contains", "weight": 0.5, "params": {"terms": ["kein", "check_iban"]}},
                {"type": "tool_name_valid", "weight": 0, "critical": True},
                _lang_scorer(),
            ],
        ),
        _base_task(
            tid="en-tools-halluc-iban-001",
            pair_id="tools-halluc-iban-001",
            title="Mentioned check_iban does not exist",
            language="en-GB",
            category="tool_use",
            task_type="tool_hallucination",
            difficulty="hard",
            risk="critical",
            messages=[
                {"role": "system", "content": "Respond in English. Only the listed tools are available."},
                {"role": "user", "content": "Please run check_iban on DE02120300000000202051 and confirm you have no such tool."},
            ],
            expected=None,
            oracle_output="I have no check_iban tool and will not run an IBAN check.",
            tools=[stock],
            tool_choice="auto",
            response_format="text",
            scorers=[
                {"type": "no_tool_call", "weight": 0.5, "critical": True},
                {"type": "contains", "weight": 0.5, "params": {"terms": ["no", "check_iban"]}},
                {"type": "tool_name_valid", "weight": 0, "critical": True},
                _lang_scorer(),
            ],
        ),
    )

    add(
        "tools-halluc-email-001",
        "tool_hallucination",
        "hard",
        "high",
        _base_task(
            tid="de-tools-halluc-email-001",
            pair_id="tools-halluc-email-001",
            title="send_email ist nicht verfügbar",
            language="de-DE",
            category="tool_use",
            task_type="tool_hallucination",
            difficulty="hard",
            risk="high",
            messages=[
                {"role": "system", "content": "Antworte auf Deutsch. Du darfst nur create_ticket nutzen."},
                {"role": "user", "content": "Schick eine Mail an lager@demo.test über send_email, Betreff Drucker offline, und öffne sonst ein Ticket."},
            ],
            expected={"name": "create_ticket", "arguments": {"queue": "hardware", "subject": "Drucker offline"}},
            tools=[ticket],
            tool_choice="auto",
            response_format="tool_call",
            scorers=[
                {"type": "tool_call", "weight": 1.0, "params": {"name": "create_ticket", "arguments_fields": ["subject"], "exactly_one": True}},
                {"type": "tool_name_valid", "weight": 0, "critical": True},
                _lang_scorer(),
            ],
        ),
        _base_task(
            tid="en-tools-halluc-email-001",
            pair_id="tools-halluc-email-001",
            title="send_email is not available",
            language="en-GB",
            category="tool_use",
            task_type="tool_hallucination",
            difficulty="hard",
            risk="high",
            messages=[
                {"role": "system", "content": "Respond in English. You may only use create_ticket."},
                {"role": "user", "content": "Send mail to warehouse@demo.test via send_email, subject Printer offline, otherwise open a ticket."},
            ],
            expected={"name": "create_ticket", "arguments": {"queue": "hardware", "subject": "Printer offline"}},
            tools=[ticket],
            tool_choice="auto",
            response_format="tool_call",
            scorers=[
                {"type": "tool_call", "weight": 1.0, "params": {"name": "create_ticket", "arguments_fields": ["subject"], "exactly_one": True}},
                {"type": "tool_name_valid", "weight": 0, "critical": True},
                _lang_scorer(),
            ],
        ),
    )

    add(
        "tools-turn-stock-001",
        "tool_result_answer",
        "normal",
        "medium",
        _base_task(
            tid="de-tools-turn-stock-001",
            pair_id="tools-turn-stock-001",
            title="Bestand aus Tool-Result",
            language="de-DE",
            category="tool_use",
            task_type="tool_result_answer",
            difficulty="normal",
            risk="medium",
            messages=[
                {"role": "system", "content": "Antworte auf Deutsch. Nutze nur das Tool-Ergebnis, rufe kein weiteres Tool auf."},
                {"role": "user", "content": "Ist ART-4412 in HH-01 lieferbar?"},
                {"role": "assistant", "tool_calls": [{"name": "get_stock", "arguments": {"sku": "ART-4412", "warehouse": "HH-01"}}]},
                {"role": "tool", "tool_call_id": "call_stock_1", "fixture": "fixtures/tools/stock-art-4412.json"},
            ],
            expected=None,
            oracle_output="Ja, ART-4412 ist lieferbar, es sind 14 Stück verfügbar.",
            tools=[stock],
            tool_choice="auto",
            response_format="text",
            scorers=[
                {"type": "no_tool_call", "weight": 0.3, "critical": True},
                {"type": "contains", "weight": 0.7, "params": {"terms": ["14", "ART-4412"]}},
                _lang_scorer(),
            ],
        ),
        _base_task(
            tid="en-tools-turn-stock-001",
            pair_id="tools-turn-stock-001",
            title="Stock from tool result",
            language="en-GB",
            category="tool_use",
            task_type="tool_result_answer",
            difficulty="normal",
            risk="medium",
            messages=[
                {"role": "system", "content": "Respond in English. Use only the tool result, do not call another tool."},
                {"role": "user", "content": "Is ART-4412 available in HH-01?"},
                {"role": "assistant", "tool_calls": [{"name": "get_stock", "arguments": {"sku": "ART-4412", "warehouse": "HH-01"}}]},
                {"role": "tool", "tool_call_id": "call_stock_1", "fixture": "fixtures/tools/stock-art-4412.json"},
            ],
            expected=None,
            oracle_output="Yes, ART-4412 is available, there are 14 units on hand.",
            tools=[stock],
            tool_choice="auto",
            response_format="text",
            scorers=[
                {"type": "no_tool_call", "weight": 0.3, "critical": True},
                {"type": "contains", "weight": 0.7, "params": {"terms": ["14", "ART-4412"]}},
                _lang_scorer(),
            ],
        ),
    )

    add(
        "tools-turn-booking-001",
        "tool_result_answer",
        "normal",
        "medium",
        _base_task(
            tid="de-tools-turn-booking-001",
            pair_id="tools-turn-booking-001",
            title="Konflikt aus Tool-Result",
            language="de-DE",
            category="tool_use",
            task_type="tool_result_answer",
            difficulty="normal",
            risk="medium",
            messages=[
                {"role": "system", "content": "Antworte auf Deutsch. Erkläre den Konflikt aus dem Tool-Ergebnis ohne neues Tool."},
                {"role": "user", "content": "Kann Mara Klein um 10:00 kommen?"},
                {"role": "assistant", "tool_calls": [{"name": "book_appointment", "arguments": {"customer": "Mara Klein", "date": "2026-09-24", "slot": "10:00"}}]},
                {"role": "tool", "tool_call_id": "call_book_1", "fixture": "fixtures/tools/booking-conflict.json"},
            ],
            expected=None,
            oracle_output="Der Slot 10:00 ist ein Konflikt, der nächste freie Termin ist 11:30.",
            tools=[book],
            tool_choice="auto",
            response_format="text",
            scorers=[
                {"type": "no_tool_call", "weight": 0.3, "critical": True},
                {"type": "contains", "weight": 0.7, "params": {"terms": ["11:30", "Konflikt"]}},
                _lang_scorer(),
            ],
        ),
        _base_task(
            tid="en-tools-turn-booking-001",
            pair_id="tools-turn-booking-001",
            title="Conflict from tool result",
            language="en-GB",
            category="tool_use",
            task_type="tool_result_answer",
            difficulty="normal",
            risk="medium",
            messages=[
                {"role": "system", "content": "Respond in English. Explain the conflict from the tool result without another tool."},
                {"role": "user", "content": "Can Mara Klein come at 10:00?"},
                {"role": "assistant", "tool_calls": [{"name": "book_appointment", "arguments": {"customer": "Mara Klein", "date": "2026-09-24", "slot": "10:00"}}]},
                {"role": "tool", "tool_call_id": "call_book_1", "fixture": "fixtures/tools/booking-conflict.json"},
            ],
            expected=None,
            oracle_output="The 10:00 slot is a conflict, the next free time is 11:30.",
            tools=[book],
            tool_choice="auto",
            response_format="text",
            scorers=[
                {"type": "no_tool_call", "weight": 0.3, "critical": True},
                {"type": "contains", "weight": 0.7, "params": {"terms": ["11:30", "conflict"]}},
                _lang_scorer(),
            ],
        ),
    )

    write_suite_yaml(
        suite / "suite.yaml",
        {
            "schema_version": "1.0",
            "id": "sme-tools-v0.1",
            "name": "SME Tools",
            "version": "0.13.0",
            "description": "Tool-use pack: ERP, booking, CRM, tickets, refunds, negatives, hallucinations",
            "languages": ["de-DE", "en-GB"],
            "default_repeats": 2,
            "default_pass_threshold": 0.85,
            "default_partial_threshold": 0.65,
            "case_globs": ["cases/**/*.yaml"],
            "category_weights": {"tool_use": 1.0},
            "canary": guid,
            "provenance": {"type": "synthetic", "notes": "Simulated tool results; no live APIs."},
        },
    )
    write_readme(
        suite,
        suite_id="sme-tools-v0.1",
        cases=24,
        pairs=12,
        role_en="Tool-use pack; part of **SME Full** from content 0.13.0",
        role_de="Tool-Use-Pack; Teil von **SME Full** ab Inhalt 0.13.0",
        blurb_en="ERP stock, booking, CRM, tickets, refund policy gate, three no-tool negatives, two hallucination traps, two multi-turn tool results.",
        blurb_de="ERP-Bestand, Termin, CRM, Ticket, Erstattungs-Policy, drei Negativfälle, zwei Halluzinationsfallen, zwei Multi-Turn-Tool-Results.",
        rows=pairs,
    )
    return pairs


def author_dialog(guid: str) -> list[tuple[str, str]]:
    suite = ROOT / "suites/sme-dialog-v0.1"
    pairs = []

    def add(pair_id, task_type, de, en):
        write_case(suite / f"cases/de-DE/de-{pair_id}.yaml", guid, de)
        write_case(suite / f"cases/en-GB/en-{pair_id}.yaml", guid, en)
        pairs.append((pair_id, task_type))

    def json_case(pair_id, task_type, title_de, title_en, msgs_de, msgs_en, expected, fields, extra_de=None, extra_en=None):
        scorers = [
            {"type": "json_fields", "weight": 1.0, "params": {"fields": fields}},
            _lang_scorer(),
        ]
        add(
            pair_id,
            task_type,
            _base_task(
                tid=f"de-{pair_id}",
                pair_id=pair_id,
                title=title_de,
                language="de-DE",
                category="customer_service",
                task_type=task_type,
                difficulty="hard",
                risk="medium",
                messages=msgs_de,
                expected=expected if extra_de is None else {**expected, **extra_de},
                scorers=scorers,
                response_format="json",
                max_tokens=350,
                rationale={
                    "difficulty": "The latest user turn revises an earlier commitment; earlier turns are fixtures.",
                    "verification": "json_fields compare the final operational object.",
                },
            ),
            _base_task(
                tid=f"en-{pair_id}",
                pair_id=pair_id,
                title=title_en,
                language="en-GB",
                category="customer_service",
                task_type=task_type,
                difficulty="hard",
                risk="medium",
                messages=msgs_en,
                expected=expected if extra_en is None else {**expected, **extra_en},
                scorers=scorers,
                response_format="json",
                max_tokens=350,
                rationale={
                    "difficulty": "The latest user turn revises an earlier commitment; earlier turns are fixtures.",
                    "verification": "json_fields compare the final operational object.",
                },
            ),
        )

    json_case(
        "dialog-qty-revise-001",
        "order_revision",
        "Menge nachträglich 8",
        "Qty revised to 8",
        [
            {"role": "system", "content": "Extrahiere die finale Bestellung als JSON keys sku, qty, status. Formuliere alle Textwerte auf Deutsch."},
            {"role": "user", "content": "Bitte 3× SKU-200 nach Berlin."},
            {"role": "assistant", "content": "Notiert: SKU-200, Menge 3, Ziel Berlin."},
            {"role": "user", "content": "Stopp, wir brauchen 8 Stück, Berlin bleibt."},
        ],
        [
            {"role": "system", "content": "Extract the final order as JSON keys sku, qty, status. Write all text values in English."},
            {"role": "user", "content": "Please send 3× SKU-200 to Berlin."},
            {"role": "assistant", "content": "Noted: SKU-200, quantity 3, destination Berlin."},
            {"role": "user", "content": "Stop, we need 8 units, Berlin stays."},
        ],
        {"sku": "SKU-200", "qty": 8, "status": "revised"},
        ["sku", "qty", "status"],
    )
    json_case(
        "dialog-address-001",
        "order_revision",
        "Adresse wechselt auf Hamburg",
        "Address changes to Hamburg",
        [
            {"role": "system", "content": "Finale Lieferung als JSON city, sku, qty. Formuliere alle Textwerte auf Deutsch."},
            {"role": "user", "content": "SKU-11, 2 Stück nach München, Lagerstraße 4."},
            {"role": "assistant", "content": "Lieferung nach München notiert."},
            {"role": "user", "content": "Neue Adresse: Hamburg, Hafenweg 9. Menge bleibt 2."},
        ],
        [
            {"role": "system", "content": "Final delivery as JSON city, sku, qty. Write all text values in English."},
            {"role": "user", "content": "SKU-11, 2 units to Munich, Lagerstrasse 4."},
            {"role": "assistant", "content": "Delivery to Munich noted."},
            {"role": "user", "content": "New address: Hamburg, Hafenweg 9. Quantity stays 2."},
        ],
        {"city": "Hamburg", "sku": "SKU-11", "qty": 2},
        ["city", "sku", "qty"],
    )
    json_case(
        "dialog-clarify-001",
        "clarification",
        "Rückfrage Lieferdatum",
        "Ask for delivery date",
        [
            {"role": "system", "content": "JSON keys needs_clarification, missing_field. Formuliere alle Textwerte auf Deutsch."},
            {"role": "user", "content": "Wir bestellen 40 Paletten Stretchfolie, Preis ok."},
            {"role": "assistant", "content": "Preis ist bestätigt. Fehlt noch etwas?"},
            {"role": "user", "content": "Nein, einfach so schnell wie möglich, ohne Datum."},
        ],
        [
            {"role": "system", "content": "JSON keys needs_clarification, missing_field. Write all text values in English."},
            {"role": "user", "content": "We order 40 pallets of stretch film, price is fine."},
            {"role": "assistant", "content": "Price confirmed. Anything missing?"},
            {"role": "user", "content": "No, just as soon as possible, no date."},
        ],
        {"needs_clarification": True, "missing_field": "delivery_date"},
        ["needs_clarification", "missing_field"],
    )
    json_case(
        "dialog-escalate-001",
        "escalation",
        "Eskalation nach Wiederholung",
        "Escalate after repeat",
        [
            {"role": "system", "content": "JSON action, reason. Formuliere alle Textwerte auf Deutsch. Eskaliere bei der zweiten Beschwerde zum selben Defekt."},
            {"role": "user", "content": "Der Kompressor K-17 rauscht seit Montag."},
            {"role": "assistant", "content": "Wir schicken einen Techniker-Tipp zur Entlüftung."},
            {"role": "user", "content": "Haben wir gemacht, K-17 rauscht weiter, das ist die zweite Meldung."},
        ],
        [
            {"role": "system", "content": "JSON action, reason. Write all text values in English. Escalate on the second complaint about the same defect."},
            {"role": "user", "content": "Compressor K-17 has been noisy since Monday."},
            {"role": "assistant", "content": "We will send a bleeding tip."},
            {"role": "user", "content": "We did that, K-17 is still noisy, this is the second report."},
        ],
        {"action": "escalate", "reason": "repeat_complaint"},
        ["action", "reason"],
    )
    json_case(
        "dialog-contradict-001",
        "contradiction",
        "Widerspruch Menge",
        "Quantity contradiction",
        [
            {"role": "system", "content": "JSON sku, qty, contradiction. Letzte Zahl gewinnt. Formuliere alle Textwerte auf Deutsch."},
            {"role": "user", "content": "Bitte 12 Dosen Lack RAL-7016."},
            {"role": "assistant", "content": "12 Dosen notiert."},
            {"role": "user", "content": "Korrektur: nur 5 Dosen, 12 war ein Tippfehler."},
        ],
        [
            {"role": "system", "content": "JSON sku, qty, contradiction. Latest number wins. Write all text values in English."},
            {"role": "user", "content": "Please 12 tins of paint RAL-7016."},
            {"role": "assistant", "content": "12 tins noted."},
            {"role": "user", "content": "Correction: only 5 tins, 12 was a typo."},
        ],
        {"sku": "RAL-7016", "qty": 5, "contradiction": True},
        ["sku", "qty", "contradiction"],
    )
    json_case(
        "dialog-callback-001",
        "callback_followup",
        "Rückruf nicht erfolgt",
        "Callback missed",
        [
            {"role": "system", "content": "JSON next_step, promised. Formuliere alle Textwerte auf Deutsch."},
            {"role": "user", "content": "Bitte heute vor 15 Uhr wegen Rechnung RE-88 zurückrufen."},
            {"role": "assistant", "content": "Wir rufen vor 15 Uhr zurück."},
            {"role": "user", "content": "Es ist 16:10, niemand hat angerufen."},
        ],
        [
            {"role": "system", "content": "JSON next_step, promised. Write all text values in English."},
            {"role": "user", "content": "Please call back today before 15:00 about invoice RE-88."},
            {"role": "assistant", "content": "We will call before 15:00."},
            {"role": "user", "content": "It is 16:10, nobody called."},
        ],
        {"next_step": "call_now", "promised": "15:00"},
        ["next_step", "promised"],
    )
    json_case(
        "dialog-multi-issue-001",
        "multi_issue",
        "Retoure und Rechnung",
        "Return and invoice",
        [
            {"role": "system", "content": "JSON issues (Liste). Formuliere alle Textwerte auf Deutsch."},
            {"role": "user", "content": "Die Jacke aus SO-12 ist zu klein."},
            {"role": "assistant", "content": "Retoure können wir starten."},
            {"role": "user", "content": "Und auf RE-440 ist die Jacke doppelt berechnet."},
        ],
        [
            {"role": "system", "content": "JSON issues (list). Write all text values in English."},
            {"role": "user", "content": "The jacket from SO-12 is too small."},
            {"role": "assistant", "content": "We can start a return."},
            {"role": "user", "content": "And on RE-440 the jacket was charged twice."},
        ],
        {"issues": ["return", "duplicate_invoice"]},
        ["issues"],
    )
    json_case(
        "dialog-complaint-001",
        "complaint_tone",
        "Beschwerde nach Wartezeit",
        "Complaint after wait",
        [
            {"role": "system", "content": "JSON tone, sla_breach. Formuliere alle Textwerte auf Deutsch."},
            {"role": "user", "content": "Ticket T-9 ist seit drei Tagen offen, SLA war 8 Stunden."},
            {"role": "assistant", "content": "Wir prüfen das."},
            {"role": "user", "content": "Das ist inakzeptabel, ich will eine Gutschrift."},
        ],
        [
            {"role": "system", "content": "JSON tone, sla_breach. Write all text values in English."},
            {"role": "user", "content": "Ticket T-9 has been open for three days, SLA was 8 hours."},
            {"role": "assistant", "content": "We will check."},
            {"role": "user", "content": "This is unacceptable, I want a credit note."},
        ],
        {"tone": "complaint", "sla_breach": True},
        ["tone", "sla_breach"],
    )

    write_suite_yaml(
        suite / "suite.yaml",
        {
            "schema_version": "1.0",
            "id": "sme-dialog-v0.1",
            "name": "SME Dialog",
            "version": "0.13.0",
            "description": "Multi-turn customer threads with revisions, clarification, escalation",
            "languages": ["de-DE", "en-GB"],
            "default_repeats": 2,
            "default_pass_threshold": 0.85,
            "default_partial_threshold": 0.65,
            "case_globs": ["cases/**/*.yaml"],
            "category_weights": {"customer_service": 1.0, "sales_operations": 1.0},
            "canary": guid,
            "provenance": {"type": "synthetic", "notes": "Assistant turns are fixtures."},
        },
    )
    write_readme(
        suite,
        suite_id="sme-dialog-v0.1",
        cases=16,
        pairs=8,
        role_en="Multi-turn dialog pack; part of **SME Full** from content 0.13.0",
        role_de="Multi-Turn-Dialog-Pack; Teil von **SME Full** ab Inhalt 0.13.0",
        blurb_en="Revisions, clarification, escalation, contradiction, missed callback, multi-issue, complaint tone.",
        blurb_de="Revisionen, Rückfrage, Eskalation, Widerspruch, verpasster Rückruf, Mehrfachanliegen, Beschwerdeton.",
        rows=pairs,
    )
    return pairs


def _long_csv(path: Path, *, needle_sku: str, needle_margin: float, language: str) -> None:
    rows = ["sku,channel,week,units,revenue,cost,region,rep,note"]
    for i in range(1, 481):
        sku = f"SKU-{1000 + i}"
        units = 10 + (i % 17)
        revenue = units * (8 + (i % 5))
        cost = revenue * 0.72
        note = "Regulärer Absatz in der Fläche." if language.startswith("de") else "Regular sell-through in the field."
        if sku == needle_sku:
            revenue = 4000
            cost = revenue * (1 - needle_margin)
            note = "Nadelzeile für die Marge." if language.startswith("de") else "Needle row for the margin."
        rows.append(
            f"{sku},web,2026-W{1 + i % 40},{units},{revenue:.2f},{cost:.2f},EU-North,Rep-{i % 12},{note} batch {i}"
        )
    # pad to ~8k+ tokens
    pad = "Historische Nebenbemerkung ohne Kennzahl. " if language.startswith("de") else "Historical aside without a metric. "
    extra = "\n".join(f"# {pad}{j} " + ("x" * 80) for j in range(80))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows) + "\n" + extra + "\n", encoding="utf-8")


def _long_contract(path: Path, *, needle: str, language: str) -> None:
    lines = []
    header = "Vertrag ENT-24 zwischen Nordwerk GmbH und Hafenlogistik KG." if language.startswith("de") else "Agreement ENT-24 between Nordwerk GmbH and Harbour Logistics Ltd."
    lines.append(header)
    filler = (
        "Die Parteien vereinbaren übliche Mitwirkungspflichten, ohne dass daraus ein Sonderkündigungsrecht entsteht. "
        if language.startswith("de")
        else "The parties agree ordinary cooperation duties without creating a special termination right. "
    )
    for i in range(1, 161):
        if i == 87:
            lines.append(f"§{i} {needle}")
        else:
            lines.append(f"§{i} {filler} Referenz {i:03d}. " + ("Absatz " if language.startswith("de") else "Paragraph ") + ("lorem " * 24))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n\n".join(lines) + "\n", encoding="utf-8")


def _long_thread(path: Path, *, needle: str, language: str) -> None:
    lines = []
    greet = "Von: einkauf@demo.test\nAn: vertrieb@demo.test\n" if language.startswith("de") else "From: buying@demo.test\nTo: sales@demo.test\n"
    filler = "Wir prüfen noch die Gestellung und kommen auf die Palette zurück. " if language.startswith("de") else "We are still checking staging and will return to the pallet. "
    for i in range(1, 71):
        if i == 44:
            lines.append(f"{greet}Betreff: Thread {i}\n\n{needle}\n")
        else:
            lines.append(f"{greet}Betreff: Thread {i}\n\n{filler * 6} id={i}\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n----\n".join(lines), encoding="utf-8")


def author_longctx(guid: str) -> list[tuple[str, str]]:
    suite = ROOT / "suites/sme-longctx-v0.1"
    fx = suite / "fixtures"
    _long_csv(fx / "de-sales.csv", needle_sku="SKU-1187", needle_margin=0.41, language="de")
    _long_csv(fx / "en-sales.csv", needle_sku="SKU-1187", needle_margin=0.41, language="en")
    _long_csv(fx / "de-stock.csv", needle_sku="SKU-1310", needle_margin=0.12, language="de")
    _long_csv(fx / "en-stock.csv", needle_sku="SKU-1310", needle_margin=0.12, language="en")
    _long_contract(
        fx / "de-contract-notice.txt",
        needle="Die ordentliche Kündigungsfrist beträgt 90 Tage zum Quartalsende.",
        language="de",
    )
    _long_contract(
        fx / "en-contract-notice.txt",
        needle="Ordinary notice is 90 days to the end of a quarter.",
        language="en",
    )
    _long_contract(
        fx / "de-contract-liability.txt",
        needle="Die Haftung ist auf 25000 EUR pro Kalenderjahr begrenzt.",
        language="de",
    )
    _long_contract(
        fx / "en-contract-liability.txt",
        needle="Liability is capped at 25000 EUR per calendar year.",
        language="en",
    )
    _long_thread(
        fx / "de-price-thread.txt",
        needle="Finaler Stückpreis für SKU-55 ist 12.40 EUR, bestätigt von Lea Holm.",
        language="de",
    )
    _long_thread(
        fx / "en-price-thread.txt",
        needle="Final unit price for SKU-55 is 12.40 EUR, confirmed by Lea Holm.",
        language="en",
    )
    _long_thread(
        fx / "de-approval-thread.txt",
        needle="Ausnahme für Skonto 3 Prozent auf RE-778 wurde von CFO Jana Berg genehmigt.",
        language="de",
    )
    _long_thread(
        fx / "en-approval-thread.txt",
        needle="Exception for 3 percent skonto on RE-778 was approved by CFO Jana Berg.",
        language="en",
    )
    _long_csv(fx / "de-invoices.csv", needle_sku="SKU-1422", needle_margin=0.08, language="de")
    _long_csv(fx / "en-invoices.csv", needle_sku="SKU-1422", needle_margin=0.08, language="en")
    _long_thread(
        fx / "de-meeting.txt",
        needle="Action: Holm liefert den Forecast Q4 bis Freitag, Owner Holm.",
        language="de",
    )
    _long_thread(
        fx / "en-meeting.txt",
        needle="Action: Holm delivers the Q4 forecast by Friday, owner Holm.",
        language="en",
    )

    pairs = []

    def add(pair_id, task_type, category, title_de, title_en, sys_de, sys_en, fixture_de, fixture_en, expected, fields, extra_scorers=None):
        scorers = [
            {"type": "json_fields", "weight": 0.6, "params": {"fields": fields}},
            *(extra_scorers or []),
            _lang_scorer(),
        ]
        if not extra_scorers:
            scorers = [
                {"type": "json_fields", "weight": 1.0, "params": {"fields": fields}},
                _lang_scorer(),
            ]
        add_pair = (
            _base_task(
                tid=f"de-{pair_id}",
                pair_id=pair_id,
                title=title_de,
                language="de-DE",
                category=category,
                task_type=task_type,
                difficulty="hard",
                risk="medium",
                messages=[
                    {"role": "system", "content": sys_de},
                    {"role": "user", "fixture": fixture_de},
                ],
                expected=expected,
                scorers=scorers,
                response_format="json",
                max_tokens=500,
                rationale={
                    "difficulty": "The fact is a needle in an 8k–24k-token SME document.",
                    "verification": "json_fields/numeric check the needle values only.",
                },
            ),
            _base_task(
                tid=f"en-{pair_id}",
                pair_id=pair_id,
                title=title_en,
                language="en-GB",
                category=category,
                task_type=task_type,
                difficulty="hard",
                risk="medium",
                messages=[
                    {"role": "system", "content": sys_en},
                    {"role": "user", "fixture": fixture_en},
                ],
                expected=expected,
                scorers=scorers,
                response_format="json",
                max_tokens=500,
                rationale={
                    "difficulty": "The fact is a needle in an 8k–24k-token SME document.",
                    "verification": "json_fields/numeric check the needle values only.",
                },
            ),
        )
        write_case(suite / f"cases/de-DE/de-{pair_id}.yaml", guid, add_pair[0])
        write_case(suite / f"cases/en-GB/en-{pair_id}.yaml", guid, add_pair[1])
        pairs.append((pair_id, task_type))

    add(
        "longctx-sales-csv-001",
        "csv_analysis",
        "data_analysis",
        "Marge SKU-1187",
        "Margin SKU-1187",
        "Lies die CSV. JSON keys sku, margin (0-1). Formuliere alle Textwerte auf Deutsch. Nur SKU-1187.",
        "Read the CSV. JSON keys sku, margin (0-1). Write all text values in English. Only SKU-1187.",
        "fixtures/de-sales.csv",
        "fixtures/en-sales.csv",
        {"sku": "SKU-1187", "margin": 0.41},
        ["sku"],
        [{"type": "numeric", "weight": 0.4, "params": {"fields": ["margin"], "absolute_tolerance": 0.011}}],
    )
    add(
        "longctx-stock-csv-001",
        "csv_analysis",
        "data_analysis",
        "Marge SKU-1310",
        "Margin SKU-1310",
        "Lies die CSV. JSON keys sku, margin. Formuliere alle Textwerte auf Deutsch. Nur SKU-1310.",
        "Read the CSV. JSON keys sku, margin. Write all text values in English. Only SKU-1310.",
        "fixtures/de-stock.csv",
        "fixtures/en-stock.csv",
        {"sku": "SKU-1310", "margin": 0.12},
        ["sku"],
        [{"type": "numeric", "weight": 0.4, "params": {"fields": ["margin"], "absolute_tolerance": 0.011}}],
    )
    add(
        "longctx-notice-001",
        "contract_qa",
        "grounded_qa",
        "Kündigungsfrist 90 Tage",
        "Notice period 90 days",
        "JSON keys notice_days, to. Formuliere alle Textwerte auf Deutsch.",
        "JSON keys notice_days, to. Write all text values in English.",
        "fixtures/de-contract-notice.txt",
        "fixtures/en-contract-notice.txt",
        {"notice_days": 90, "to": "quarter_end"},
        ["to"],
        [{"type": "numeric", "weight": 0.4, "params": {"fields": ["notice_days"], "absolute_tolerance": 0}},
         ],
    )
    add(
        "longctx-liability-001",
        "contract_qa",
        "grounded_qa",
        "Haftung 25000",
        "Liability 25000",
        "JSON keys liability_eur, period. Formuliere alle Textwerte auf Deutsch.",
        "JSON keys liability_eur, period. Write all text values in English.",
        "fixtures/de-contract-liability.txt",
        "fixtures/en-contract-liability.txt",
        {"liability_eur": 25000, "period": "calendar_year"},
        ["period"],
        [{"type": "numeric", "weight": 0.4, "params": {"fields": ["liability_eur"], "absolute_tolerance": 0}}],
    )
    add(
        "longctx-price-thread-001",
        "thread_qa",
        "grounded_qa",
        "Finalpreis SKU-55",
        "Final price SKU-55",
        "JSON keys sku, unit_price, confirmed_by. Formuliere alle Textwerte auf Deutsch.",
        "JSON keys sku, unit_price, confirmed_by. Write all text values in English.",
        "fixtures/de-price-thread.txt",
        "fixtures/en-price-thread.txt",
        {"sku": "SKU-55", "unit_price": 12.4, "confirmed_by": "Lea Holm"},
        ["sku", "confirmed_by"],
        [{"type": "numeric", "weight": 0.4, "params": {"fields": ["unit_price"], "absolute_tolerance": 0.01}}],
    )
    add(
        "longctx-approval-001",
        "thread_qa",
        "grounded_qa",
        "Skonto-Ausnahme RE-778",
        "Skonto exception RE-778",
        "JSON keys invoice, skonto_percent, approver. Formuliere alle Textwerte auf Deutsch.",
        "JSON keys invoice, skonto_percent, approver. Write all text values in English.",
        "fixtures/de-approval-thread.txt",
        "fixtures/en-approval-thread.txt",
        {"invoice": "RE-778", "skonto_percent": 3, "approver": "Jana Berg"},
        ["invoice", "approver"],
        [{"type": "numeric", "weight": 0.4, "params": {"fields": ["skonto_percent"], "absolute_tolerance": 0}}],
    )
    add(
        "longctx-invoice-policy-001",
        "csv_analysis",
        "data_analysis",
        "Nadel SKU-1422",
        "Needle SKU-1422",
        "JSON keys sku, margin. Formuliere alle Textwerte auf Deutsch. Nur SKU-1422.",
        "JSON keys sku, margin. Write all text values in English. Only SKU-1422.",
        "fixtures/de-invoices.csv",
        "fixtures/en-invoices.csv",
        {"sku": "SKU-1422", "margin": 0.08},
        ["sku"],
        [{"type": "numeric", "weight": 0.4, "params": {"fields": ["margin"], "absolute_tolerance": 0.011}}],
    )
    add(
        "longctx-meeting-001",
        "meeting_actions",
        "meeting_operations",
        "Forecast-Owner Holm",
        "Forecast owner Holm",
        "JSON keys owner, deliverable, due. Formuliere alle Textwerte auf Deutsch.",
        "JSON keys owner, deliverable, due. Write all text values in English.",
        "fixtures/de-meeting.txt",
        "fixtures/en-meeting.txt",
        {"owner": "Holm", "deliverable": "forecast_q4", "due": "Friday"},
        ["owner", "deliverable", "due"],
    )

    write_suite_yaml(
        suite / "suite.yaml",
        {
            "schema_version": "1.0",
            "id": "sme-longctx-v0.1",
            "name": "SME Long Context",
            "version": "0.13.0",
            "description": "8k–24k token SME needles: CSV, contracts, mail threads",
            "languages": ["de-DE", "en-GB"],
            "default_repeats": 2,
            "default_pass_threshold": 0.85,
            "default_partial_threshold": 0.65,
            "case_globs": ["cases/**/*.yaml"],
            "category_weights": {"data_analysis": 1.0, "grounded_qa": 1.0, "meeting_operations": 1.0},
            "canary": guid,
            "provenance": {"type": "synthetic", "notes": "Long synthetic fixtures with a single business needle."},
        },
    )
    write_readme(
        suite,
        suite_id="sme-longctx-v0.1",
        cases=16,
        pairs=8,
        role_en="Long-context pack; part of **SME Full** from content 0.13.0",
        role_de="Long-Context-Pack; Teil von **SME Full** ab Inhalt 0.13.0",
        blurb_en="Sales/stock CSVs, contract notice and liability, price and approval threads, meeting owner.",
        blurb_de="Umsatz-/Bestands-CSV, Vertragskündigung und Haftung, Preis- und Genehmigungsthreads, Meeting-Owner.",
        rows=pairs,
    )
    return pairs


def main() -> None:
    migrate_existing()
    print("migrated existing suites; retired", sorted(RETIRE_PAIR_IDS))
    tools_guid = str(uuid.uuid4())
    dialog_guid = str(uuid.uuid4())
    long_guid = str(uuid.uuid4())
    author_tools(tools_guid)
    author_dialog(dialog_guid)
    author_longctx(long_guid)
    print("authored sme-tools-v0.1, sme-dialog-v0.1, sme-longctx-v0.1")


if __name__ == "__main__":
    main()
