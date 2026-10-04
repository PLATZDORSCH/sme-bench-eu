"""Author SME Full 0.16.0: retire redundant domain pairs, add harder tool cases.

Retires 14 structurally redundant domain pairs (28 cases) and adds six DE/EN
pairs: four live-loop agentic cases and two single-shot tools cases. Net
300 → 284. Existing unchanged cases stay regrade-safe.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sme_bench.qa import format_canary_header, read_canary_guid  # noqa: E402
from sme_bench.regrade import write_compatibility_manifest  # noqa: E402
from sme_bench.reporters.catalog import write_case_catalog  # noqa: E402
from sme_bench.scorers.base import known_scorer_names  # noqa: E402
from sme_bench.task_loader import load_full_benchmark, load_suite  # noqa: E402

CONTENT_VERSION = "0.16.0"
TOOLS_GUID = "c2c1d42b-4e66-4e82-8f8c-eaa09ebc91bd"
AGENTIC_GUID = "a41f0c3e-7d8b-4e19-9c2a-5f6b8d1e0a77"

RETIRE_PAIR_IDS = {
    "ec-injection-001",
    "fi-grounded-002",
    "ho-support-001",
    "lo-order-002",
    "ec-grounded-003",
    "fi-grounded-003",
    "ho-grounded-003",
    "lo-grounded-003",
    "tr-grounded-002",
    "fi-reply-002",
    "ho-reply-001",
    "ec-support-001",
    "lo-support-001",
    "lo-order-001",
}

RETIRE_SUITES = (
    "sme-trades-v0.1",
    "sme-ecommerce-v0.1",
    "sme-financial-v0.1",
    "sme-hospitality-v0.1",
    "sme-logistics-v0.1",
)
NEW_SUITES = ("sme-tools-v0.1", "sme-agentic-v0.1")

README_COUNTS = {
    "sme-trades-v0.1": (12, 6),
    "sme-ecommerce-v0.1": (16, 8),
    "sme-financial-v0.1": (10, 5),
    "sme-hospitality-v0.1": (10, 5),
    "sme-logistics-v0.1": (10, 5),
    "sme-tools-v0.1": (52, 26),
    "sme-agentic-v0.1": (40, 20),
}


def _dump(data: dict) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)


def write_case(path: Path, guid: str, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_canary_header(guid) + "\n" + _dump(payload), encoding="utf-8")


def _lang() -> dict:
    return {"type": "language", "weight": 0, "must_pass": True}


def _valid() -> dict:
    return {"type": "tool_name_valid", "weight": 0, "critical": True}


def bump_suite(suite: str) -> None:
    path = ROOT / "suites" / suite / "suite.yaml"
    manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
    manifest["version"] = CONTENT_VERSION
    path.write_text(_dump(manifest), encoding="utf-8")


def retire_pairs() -> int:
    removed = 0
    for suite in RETIRE_SUITES:
        for case in sorted((ROOT / "suites" / suite).glob("cases/**/*.yaml")):
            parsed = yaml.safe_load(case.read_text(encoding="utf-8")) or {}
            if parsed.get("pair_id") in RETIRE_PAIR_IDS:
                case.unlink()
                removed += 1
    return removed


def _update_readme_count(suite: str, cases: int, pairs: int) -> None:
    for name, label, pair_word in (
        ("README.md", "Cases", "pairs"),
        ("README.de.md", "Fälle", "Paare"),
    ):
        path = ROOT / "suites" / suite / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        text = re.sub(
            rf"(\|\s*\*\*{label}\*\*\s*\|\s*)\d+\s*\(\d+\s+DE/EN[- ]{pair_word}\)",
            rf"\g<1>{cases} ({pairs} DE/EN-{pair_word})"
            if name.endswith(".de.md")
            else rf"\g<1>{cases} ({pairs} DE/EN {pair_word})",
            text,
            count=1,
        )
        # German files already use DE/EN-Paare; keep hyphen.
        if name.endswith(".de.md"):
            text = re.sub(
                rf"(\|\s*\*\*{label}\*\*\s*\|\s*)\d+\s*\(\d+\s+DE/EN[- ]Paare\)",
                rf"\g<1>{cases} ({pairs} DE/EN-Paare)",
                text,
                count=1,
            )
        path.write_text(text, encoding="utf-8")


def _append_task_type_rows(suite: str, rows: list[tuple[str, str]]) -> None:
    for name in ("README.md", "README.de.md"):
        path = ROOT / "suites" / suite / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        extra = "".join(f"| {pair} | {task_type} |\n" for pair, task_type in rows)
        if all(pair in text for pair, _ in rows):
            continue
        # Insert before the first blank line after the last table row.
        marker = "## Usage" if "## Usage" in text else "## Verwendung"
        if marker in text:
            text = text.replace(marker, extra + "\n" + marker, 1)
        path.write_text(text, encoding="utf-8")


def _pair_tools(
    *,
    stem: str,
    title_de: str,
    title_en: str,
    task_type: str,
    system_de: str,
    system_en: str,
    user_de: str,
    user_en: str,
    tools: list[dict[str, Any]],
    expected: dict[str, Any],
    scorers: list[dict[str, Any]],
    rationale: dict[str, str],
    risk: str = "medium",
) -> None:
    base: dict[str, Any] = {
        "schema_version": "1.0",
        "pair_id": stem,
        "category": "tool_use",
        "task_type": task_type,
        "difficulty": "hard",
        "risk": risk,
        "review_status": "approved",
        "data_classification": "synthetic",
        "tags": ["pair-reviewed"],
        "generation": {"max_tokens": 400, "temperature": 0, "response_format": "tool_call"},
        "tools": tools,
        "tool_choice": "required",
        "expected": expected,
        "scorers": [*scorers, _valid(), _lang()],
        "pass_threshold": 0.85,
        "partial_threshold": 0.65,
        "rationale": rationale,
    }
    suite = ROOT / "suites" / "sme-tools-v0.1"
    write_case(
        suite / "cases" / "de-DE" / f"de-{stem}.yaml",
        TOOLS_GUID,
        {
            **base,
            "id": f"de-{stem}",
            "title": title_de,
            "language": "de-DE",
            "messages": [
                {"role": "system", "content": system_de},
                {"role": "user", "content": user_de},
            ],
        },
    )
    write_case(
        suite / "cases" / "en-GB" / f"en-{stem}.yaml",
        TOOLS_GUID,
        {
            **base,
            "id": f"en-{stem}",
            "title": title_en,
            "language": "en-GB",
            "messages": [
                {"role": "system", "content": system_en},
                {"role": "user", "content": user_en},
            ],
        },
    )


def _pair_agentic(
    *,
    stem: str,
    title_de: str,
    title_en: str,
    task_type: str,
    system_de: str,
    system_en: str,
    user_de: str,
    user_en: str,
    tools: list[dict[str, Any]],
    tool_env: dict[str, Any],
    expected: Any,
    scorers: list[dict[str, Any]],
    oracle_de: str,
    oracle_en: str,
    risk: str = "medium",
    extra_de: dict[str, Any] | None = None,
    extra_en: dict[str, Any] | None = None,
) -> None:
    base: dict[str, Any] = {
        "schema_version": "1.0",
        "category": "tool_use",
        "task_type": task_type,
        "difficulty": "hard",
        "risk": risk,
        "review_status": "approved",
        "data_classification": "synthetic",
        "tags": ["pair-reviewed"],
        "generation": {"max_tokens": 400, "temperature": 0, "response_format": "text"},
        "tools": tools,
        "tool_choice": "auto",
        "tool_env": tool_env,
        "expected": expected,
        "scorers": [*scorers, _lang(), _valid()],
        "pass_threshold": 0.85,
        "partial_threshold": 0.65,
        "rationale": {
            "difficulty": (
                "The model must chain mock tools, recover from errors, or wait for authorization."
            ),
            "verification": ("trace_calls / no_tool_call / contains grade the live loop."),
        },
        "pair_id": stem,
    }
    suite = ROOT / "suites" / "sme-agentic-v0.1"
    de_msgs: list[dict[str, Any]] = [{"role": "system", "content": system_de}]
    en_msgs: list[dict[str, Any]] = [{"role": "system", "content": system_en}]
    if extra_de:
        de_msgs.append(extra_de)
    else:
        de_msgs.append({"role": "user", "content": user_de})
    if extra_en:
        en_msgs.append(extra_en)
    else:
        en_msgs.append({"role": "user", "content": user_en})
    write_case(
        suite / "cases" / "de-DE" / f"de-{stem}.yaml",
        AGENTIC_GUID,
        {
            **base,
            "id": f"de-{stem}",
            "title": title_de,
            "language": "de-DE",
            "messages": de_msgs,
            "oracle_output": oracle_de,
        },
    )
    write_case(
        suite / "cases" / "en-GB" / f"en-{stem}.yaml",
        AGENTIC_GUID,
        {
            **base,
            "id": f"en-{stem}",
            "title": title_en,
            "language": "en-GB",
            "messages": en_msgs,
            "oracle_output": oracle_en,
        },
    )


def write_longctx_fixtures() -> None:
    fixtures = ROOT / "suites" / "sme-agentic-v0.1" / "fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    needle_de = (
        "Zahlungsbeleg 19. Juni 2026: Kunde ACC-7741, Betrag 1840.50 EUR, "
        "Referenz RE-4412, Status offen.\n"
    )
    needle_en = (
        "Payment slip 19 June 2026: customer ACC-7741, amount 1840.50 EUR, "
        "reference RE-4412, status open.\n"
    )
    distractors_de = (
        "Entwurf: Kunde ACC-7742, Betrag 1480.50 EUR, nie gebucht.\n"
        "Storno-Notiz: Kunde ACC-7714, Betrag 1845.00 EUR, bereits storniert.\n"
        "Alte Offene-Posten-Liste nennt ACC-7740 mit 1840.00 EUR — nicht diese Zahlung.\n"
    )
    distractors_en = (
        "Draft: customer ACC-7742, amount 1480.50 EUR, never booked.\n"
        "Reversal note: customer ACC-7714, amount 1845.00 EUR, already cancelled.\n"
        "An old open-item list names ACC-7740 at 1840.00 EUR — not this payment.\n"
    )
    pad_de = (
        "Lagerhinweis {n:04d}: Umlagerung ohne Zahlungsbezug, ignorieren. "
        "Artikel ART-{n:04d} Bestand 12, kein Kundenkonto.\n"
    )
    pad_en = (
        "Warehouse note {n:04d}: relocation with no payment link, ignore. "
        "SKU ART-{n:04d} stock 12, no customer account.\n"
    )

    def build(header: str, needle: str, distractors: str, pad: str) -> str:
        body = [header, needle, distractors]
        for n in range(1, 420):
            body.append(pad.format(n=n))
        return "".join(body)

    (fixtures / "de-agentic-longctx-args.txt").write_text(
        build(
            "Buche die offene Zahlung aus dem Auszug.\nOffene Posten Nordwerk, Auszug Juni 2026.\n",
            needle_de,
            distractors_de,
            pad_de,
        ),
        encoding="utf-8",
    )
    (fixtures / "en-agentic-longctx-args.txt").write_text(
        build(
            "Book the open payment from the extract.\nNordwerk open items, June 2026 extract.\n",
            needle_en,
            distractors_en,
            pad_en,
        ),
        encoding="utf-8",
    )


def write_tools_cases() -> None:
    date_rationale = {
        "difficulty": "The model must count ten weekdays and skip the weekend.",
        "verification": "tool_call grades the computed YYYY-MM-DD argument.",
    }
    _pair_tools(
        stem="tools-date-arith-001",
        title_de="Termin in 10 Werktagen",
        title_en="Appointment in 10 weekdays",
        task_type="date_arithmetic",
        system_de=(
            "Du buchst Termine. Antworte auf Deutsch. Nutze create_appointment. "
            "Heute ist 2026-09-21 (Montag). date als YYYY-MM-DD. Der heutige Tag zählt "
            "nicht mit; überspringe Samstag und Sonntag."
        ),
        system_en=(
            "You book appointments. Respond in English. Use create_appointment. "
            "Today is 2026-09-21 (Monday). date as YYYY-MM-DD. Do not count today; "
            "skip Saturday and Sunday."
        ),
        user_de="Termin mit Kundin ACC-774 in genau 10 Werktagen, 10:00, Thema Angebot.",
        user_en="Book ACC-774 in exactly 10 weekdays, 10:00, topic quote.",
        tools=[
            {
                "name": "create_appointment",
                "description": "Book an appointment",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {"type": "string"},
                        "date": {"type": "string"},
                        "time": {"type": "string"},
                        "topic": {"type": "string"},
                    },
                    "required": ["customer_id", "date", "time"],
                },
            }
        ],
        expected={
            "name": "create_appointment",
            "arguments": {
                "customer_id": "ACC-774",
                "date": "2026-10-05",
                "time": "10:00",
            },
        },
        scorers=[
            {
                "type": "tool_call",
                "weight": 1.0,
                "params": {
                    "name": "create_appointment",
                    "arguments_fields": ["customer_id", "date", "time"],
                    "exactly_one": True,
                    "case_insensitive": True,
                },
            }
        ],
        rationale=date_rationale,
    )
    unit_rationale = {
        "difficulty": "The model must convert cents and dozens into EUR and pieces.",
        "verification": "tool_call and set_equality grade unit_price_eur and quantity.",
    }
    _pair_tools(
        stem="tools-unit-convert-001",
        title_de="Angebot aus Cent und Dutzend",
        title_en="Offer from cents and dozens",
        task_type="unit_conversion",
        system_de=(
            "Du erstellst Angebote. Antworte auf Deutsch. Nutze create_offer. "
            "unit_price_eur ist Euro je Stück (Zahl). quantity ist Stückzahl (Zahl). "
            "1 Dutzend = 12 Stück. 100 ct = 1.00 EUR."
        ),
        system_en=(
            "You create quotes. Respond in English. Use create_offer. "
            "unit_price_eur is EUR per piece (number). quantity is pieces (number). "
            "1 dozen = 12 pieces. 100 ct = 1.00 EUR."
        ),
        user_de="Angebot für ACC-774: 3 Dutzend ART-4412 zu 450 ct/Stück.",
        user_en="Quote for ACC-774: 3 dozen ART-4412 at 450 ct each.",
        tools=[
            {
                "name": "create_offer",
                "description": "Create a sales offer with line items",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {"type": "string"},
                        "lines": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "sku": {"type": "string"},
                                    "quantity": {"type": "number"},
                                    "unit_price_eur": {"type": "number"},
                                },
                                "required": ["sku", "quantity", "unit_price_eur"],
                            },
                        },
                    },
                    "required": ["customer_id", "lines"],
                },
            }
        ],
        expected={
            "tool_calls": [
                {
                    "name": "create_offer",
                    "arguments": {
                        "customer_id": "ACC-774",
                        "lines": [
                            {
                                "sku": "ART-4412",
                                "quantity": 36,
                                "unit_price_eur": 4.5,
                            }
                        ],
                    },
                }
            ]
        },
        scorers=[
            {
                "type": "tool_call",
                "weight": 0.3,
                "params": {
                    "name": "create_offer",
                    "arguments_fields": ["customer_id"],
                    "exactly_one": True,
                },
            },
            {
                "type": "set_equality",
                "weight": 0.7,
                "params": {
                    "field": "tool_calls.0.arguments.lines",
                    "keys": ["sku", "quantity", "unit_price_eur"],
                    "ignore_order": True,
                },
            },
        ],
        rationale=unit_rationale,
    )


def write_agentic_cases() -> None:
    write_longctx_fixtures()
    stock_tool = {
        "name": "get_stock",
        "description": "Look up available stock for one SKU",
        "parameters": {
            "type": "object",
            "properties": {"sku": {"type": "string"}},
            "required": ["sku"],
        },
    }
    _pair_agentic(
        stem="agentic-parallel-lookup-001",
        title_de="Drei Bestände in einem Turn",
        title_en="Three stock lookups in one turn",
        task_type="parallel_calls",
        system_de=(
            "Antworte auf Deutsch. Frage den Bestand der drei genannten SKUs "
            "in einem einzigen Schritt parallel ab (drei get_stock-Aufrufe "
            "im selben Turn). Nenne danach die Summe der verfügbaren Stück."
        ),
        system_en=(
            "Respond in English. Look up stock for the three named SKUs in a "
            "single step as parallel get_stock calls in the same turn. Then "
            "name the sum of available pieces."
        ),
        user_de="Bestand ART-101, ART-102 und ART-103. Wie viele Stück sind insgesamt verfügbar?",
        user_en="Stock for ART-101, ART-102 and ART-103. How many pieces are available in total?",
        tools=[stock_tool],
        tool_env={
            "max_turns": 4,
            "handlers": [
                {
                    "tool": "get_stock",
                    "match": {"sku": "ART-101"},
                    "response": {"sku": "ART-101", "qty": 10},
                },
                {
                    "tool": "get_stock",
                    "match": {"sku": "ART-102"},
                    "response": {"sku": "ART-102", "qty": 7},
                },
                {
                    "tool": "get_stock",
                    "match": {"sku": "ART-103"},
                    "response": {"sku": "ART-103", "qty": 4},
                },
            ],
        },
        expected={
            "tool_calls": [
                {"name": "get_stock", "arguments": {"sku": "ART-101"}},
                {"name": "get_stock", "arguments": {"sku": "ART-102"}},
                {"name": "get_stock", "arguments": {"sku": "ART-103"}},
            ],
            "tool_trace": [
                {
                    "call": {"name": "get_stock", "arguments": {"sku": "ART-101"}},
                    "result": {"qty": 10},
                    "turn_index": 0,
                    "phase": 0,
                },
                {
                    "call": {"name": "get_stock", "arguments": {"sku": "ART-102"}},
                    "result": {"qty": 7},
                    "turn_index": 0,
                    "phase": 0,
                },
                {
                    "call": {"name": "get_stock", "arguments": {"sku": "ART-103"}},
                    "result": {"qty": 4},
                    "turn_index": 0,
                    "phase": 0,
                },
            ],
        },
        scorers=[
            {
                "type": "trace_calls",
                "weight": 0.6,
                "params": {"same_turn": True},
            },
            {"type": "contains", "weight": 0.4, "params": {"terms": ["21"]}},
        ],
        oracle_de="Digest: 21 Stück verfügbar.",
        oracle_en="Digest: 21 pieces available.",
    )
    _pair_agentic(
        stem="agentic-branch-stock-001",
        title_de="Unterbestand, Nachbestellung",
        title_en="Short stock, backorder",
        task_type="result_branching",
        system_de=(
            "Antworte auf Deutsch. Prüfe zuerst den Bestand. Liegt er unter der "
            "bestellten Menge, rufe create_backorder auf und nicht confirm_order. "
            "Nenne die vom Tool zurückgegebene ID."
        ),
        system_en=(
            "Respond in English. Check stock first. If available quantity is below "
            "the ordered quantity, call create_backorder and do not call confirm_order. "
            "Name the id the tool returns."
        ),
        user_de="Bestelle 5 Stück ART-4412.",
        user_en="Order 5 units of ART-4412.",
        tools=[
            {
                "name": "check_stock",
                "description": "Check available quantity",
                "parameters": {
                    "type": "object",
                    "properties": {"sku": {"type": "string"}},
                    "required": ["sku"],
                },
            },
            {
                "name": "create_backorder",
                "description": "Place a backorder",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sku": {"type": "string"},
                        "qty": {"type": "number"},
                    },
                    "required": ["sku", "qty"],
                },
            },
            {
                "name": "confirm_order",
                "description": "Confirm an order from stock",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sku": {"type": "string"},
                        "qty": {"type": "number"},
                    },
                    "required": ["sku", "qty"],
                },
            },
        ],
        tool_env={
            "max_turns": 6,
            "handlers": [
                {
                    "tool": "check_stock",
                    "match": {"sku": "ART-4412"},
                    "response": {"sku": "ART-4412", "qty_available": 3},
                },
                {
                    "tool": "create_backorder",
                    "response": {"id": "bo-88", "status": "queued"},
                },
                {
                    "tool": "confirm_order",
                    "response": {"id": "or-1", "status": "confirmed"},
                },
            ],
        },
        expected={
            "tool_calls": [
                {"name": "check_stock", "arguments": {"sku": "ART-4412"}},
                {"name": "create_backorder"},
            ]
        },
        scorers=[
            {
                "type": "trace_calls",
                "weight": 0.6,
                "params": {
                    "order": "dependency",
                    "dependencies": [["check_stock", "create_backorder"]],
                    "forbidden": ["confirm_order"],
                },
            },
            {"type": "contains", "weight": 0.4, "params": {"terms": ["bo-88"]}},
        ],
        oracle_de="Nachbestellung bo-88 ist angelegt.",
        oracle_en="Backorder bo-88 is queued.",
    )
    _pair_agentic(
        stem="agentic-longctx-args-001",
        title_de="Zahlung aus langem Kontoauszug",
        title_en="Payment from a long ledger",
        task_type="longctx_arguments",
        system_de=(
            "Antworte auf Deutsch. Buche nur die offene Zahlung aus dem Auszug "
            "mit record_payment. Nutze Kundennummer und Betrag genau wie im "
            "gültigen Beleg, nicht aus Entwürfen oder Stornos."
        ),
        system_en=(
            "Respond in English. Book only the open payment from the extract "
            "with record_payment. Use the customer id and amount from the valid "
            "slip, not from drafts or reversals."
        ),
        user_de="Buche die offene Zahlung aus dem Auszug.",
        user_en="Book the open payment from the extract.",
        tools=[
            {
                "name": "record_payment",
                "description": "Book a customer payment",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {"type": "string"},
                        "amount": {"type": "string"},
                    },
                    "required": ["customer_id", "amount"],
                },
            }
        ],
        tool_env={
            "max_turns": 4,
            "handlers": [
                {
                    "tool": "record_payment",
                    "match": {"customer_id": "ACC-7741", "amount": "1840.50"},
                    "response": {"id": "pay-19", "status": "booked"},
                }
            ],
        },
        expected={
            "tool_calls": [
                {
                    "name": "record_payment",
                    "arguments": {"customer_id": "ACC-7741", "amount": "1840.50"},
                }
            ]
        },
        scorers=[
            {"type": "trace_calls", "weight": 0.6},
            {"type": "contains", "weight": 0.4, "params": {"terms": ["pay-19"]}},
        ],
        oracle_de="Zahlung pay-19 ist gebucht.",
        oracle_en="Payment pay-19 is booked.",
        extra_de={"role": "user", "fixture": "fixtures/de-agentic-longctx-args.txt"},
        extra_en={"role": "user", "fixture": "fixtures/en-agentic-longctx-args.txt"},
    )
    _pair_agentic(
        stem="agentic-ask-before-call-001",
        title_de="Zwei Müller, erst fragen",
        title_en="Two Millers, ask first",
        task_type="ambiguity_clarification",
        system_de=(
            "Antworte auf Deutsch. Rufe cancel_order nur auf, wenn eindeutig ist, "
            "welche Bestellung gemeint ist. Bei mehreren Treffern frage nach und "
            "rufe kein Werkzeug auf. Nenne beide Kundinnen/Kunden mit Vornamen."
        ),
        system_en=(
            "Respond in English. Call cancel_order only when it is unambiguous "
            "which order is meant. If several people match, ask back and do not "
            "call a tool. Name both customers by first name."
        ),
        user_de=(
            "Im System: Anna Müller, Bestellung SO-100; Klaus Müller, Bestellung "
            "SO-200. Storniere die Bestellung von Müller."
        ),
        user_en=(
            "In the system: Anna Miller, order SO-100; Klaus Miller, order SO-200. "
            "Cancel Miller's order."
        ),
        tools=[
            {
                "name": "cancel_order",
                "description": "Cancel an order",
                "parameters": {
                    "type": "object",
                    "properties": {"order_id": {"type": "string"}},
                    "required": ["order_id"],
                },
            }
        ],
        tool_env={
            "max_turns": 3,
            "handlers": [
                {
                    "tool": "cancel_order",
                    "response": {"id": "cx-1", "status": "cancelled"},
                }
            ],
        },
        expected=None,
        scorers=[
            {"type": "no_tool_call", "weight": 0.6, "critical": True},
            {
                "type": "contains",
                "weight": 0.4,
                "params": {"terms": ["Anna", "Klaus"], "mode": "all"},
            },
        ],
        oracle_de="Welche Bestellung — Anna Müller (SO-100) oder Klaus Müller (SO-200)?",
        oracle_en="Which order — Anna Miller (SO-100) or Klaus Miller (SO-200)?",
    )


def _fix_longctx_user_messages() -> None:
    """Message validator forbids content+fixture; keep fixture only."""
    suite = ROOT / "suites" / "sme-agentic-v0.1"
    for path in (
        suite / "cases" / "de-DE" / "de-agentic-longctx-args-001.yaml",
        suite / "cases" / "en-GB" / "en-agentic-longctx-args-001.yaml",
    ):
        guid = read_canary_guid(path)
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for msg in data["messages"]:
            if msg.get("role") == "user" and msg.get("fixture"):
                msg.pop("content", None)
        write_case(path, guid or AGENTIC_GUID, data)


def update_readme_counts() -> None:
    for suite, (cases, pairs) in README_COUNTS.items():
        _update_readme_count(suite, cases, pairs)


def main() -> None:
    removed = retire_pairs()
    write_tools_cases()
    write_agentic_cases()
    _fix_longctx_user_messages()
    for suite in (*RETIRE_SUITES, *NEW_SUITES):
        bump_suite(suite)
    update_readme_counts()
    _append_task_type_rows(
        "sme-agentic-v0.1",
        [
            ("agentic-parallel-lookup-001", "parallel_calls"),
            ("agentic-branch-stock-001", "result_branching"),
            ("agentic-longctx-args-001", "longctx_arguments"),
            ("agentic-ask-before-call-001", "ambiguity_clarification"),
        ],
    )
    _append_task_type_rows(
        "sme-tools-v0.1",
        [
            ("tools-date-arith-001", "date_arithmetic"),
            ("tools-unit-convert-001", "unit_conversion"),
        ],
    )

    releases_path = ROOT / "suites/compatibility/releases.json"
    releases = json.loads(releases_path.read_text(encoding="utf-8"))
    if CONTENT_VERSION not in releases["released"]:
        releases["released"].append(CONTENT_VERSION)
    releases_path.write_text(json.dumps(releases, indent=2) + "\n", encoding="utf-8")

    known = known_scorer_names()
    for suite in (*RETIRE_SUITES, *NEW_SUITES):
        loaded = load_suite(ROOT / "suites" / suite, known_scorers=known)
        write_case_catalog(
            ROOT / "suites" / suite / "CASES.md",
            loaded.tasks,
            suite_id=loaded.manifest.id,
            suite_version=loaded.manifest.version,
            canary=loaded.manifest.canary,
        )

    loaded = load_full_benchmark(known_scorers=known)
    write_compatibility_manifest(
        loaded, ROOT / "suites/compatibility" / f"regrade-{CONTENT_VERSION}-baseline.json"
    )
    errors = [i for i in loaded.issues if i.severity == "error"]
    if errors:
        for issue in errors[:40]:
            print(f"ERROR {issue.path}: {issue.message}")
        raise SystemExit(1)
    print(f"OK retired {removed} cases, {len(loaded.tasks)} tasks, suite {loaded.manifest.version}")


if __name__ == "__main__":
    main()
