"""Author SME Full 0.15.0: schema-heavy tool-call cases in ``sme-tools-v0.1``.

Adds eight DE/EN pairs: wide signatures, nested objects, line-item arrays,
enum literals, and optional-field omission. Existing 0.14.2 cases stay
unchanged (regrade-safe). New cases need a ``--task-ids`` delta plus merge.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sme_bench.qa import format_canary_header  # noqa: E402
from sme_bench.regrade import write_compatibility_manifest  # noqa: E402
from sme_bench.reporters.catalog import write_case_catalog  # noqa: E402
from sme_bench.scorers.base import known_scorer_names  # noqa: E402
from sme_bench.task_loader import load_full_benchmark, load_suite  # noqa: E402

CONTENT_VERSION = "0.15.0"
SUITE = "sme-tools-v0.1"
TOOLS_GUID = "c2c1d42b-4e66-4e82-8f8c-eaa09ebc91bd"

EXISTING_ROWS: list[tuple[str, str]] = [
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
    ("tools-stock-001-crowded", "toolset_crowded"),
    ("tools-booking-001-crowded", "toolset_crowded"),
    ("tools-crm-001-crowded", "toolset_crowded"),
    ("tools-refund-001-crowded", "toolset_crowded"),
]

NEW_ROWS: list[tuple[str, str]] = [
    ("tools-wide-customer-001", "wide_signature"),
    ("tools-wide-offer-001", "wide_signature"),
    ("tools-nested-address-001", "nested_argument"),
    ("tools-array-order-001", "array_argument"),
    ("tools-array-timesheet-001", "array_argument"),
    ("tools-enum-ticket-001", "enum_literal"),
    ("tools-enum-date-001", "enum_literal"),
    ("tools-omit-update-001", "optional_omission"),
]


def _dump(data: dict) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)


def write_case(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_canary_header(TOOLS_GUID) + "\n" + _dump(payload), encoding="utf-8")


def _lang() -> dict:
    return {"type": "language", "weight": 0, "must_pass": True}


def _valid() -> dict:
    return {"type": "tool_name_valid", "weight": 0, "critical": True}


def _pair(
    *,
    stem: str,
    title_de: str,
    title_en: str,
    task_type: str,
    user_de: str,
    user_en: str,
    system_de: str,
    system_en: str,
    tools: list[dict[str, Any]],
    expected: dict[str, Any],
    scorers: list[dict[str, Any]],
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
        "rationale": {
            "difficulty": (
                "The model must fill a wide or nested tool schema from the prompt "
                "without inventing optional fields."
            ),
            "verification": (
                "tool_call grades named arguments (dotted paths, absent_fields); "
                "set_equality grades unordered line items when present."
            ),
        },
    }
    de = {
        **base,
        "id": f"de-{stem}",
        "title": title_de,
        "language": "de-DE",
        "messages": [
            {"role": "system", "content": system_de},
            {"role": "user", "content": user_de},
        ],
    }
    en = {
        **base,
        "id": f"en-{stem}",
        "title": title_en,
        "language": "en-GB",
        "messages": [
            {"role": "system", "content": system_en},
            {"role": "user", "content": user_en},
        ],
    }
    suite = ROOT / "suites" / SUITE
    write_case(suite / "cases" / "de-DE" / f"de-{stem}.yaml", de)
    write_case(suite / "cases" / "en-GB" / f"en-{stem}.yaml", en)


def _wide_customer() -> None:
    fields = [
        "company",
        "legal_form",
        "first_name",
        "last_name",
        "email",
        "phone",
        "street",
        "zip",
        "city",
        "country",
        "vat_id",
        "payment_terms_days",
        "delivery_method",
        "customer_group",
    ]
    props = {name: {"type": "string"} for name in fields}
    props["payment_terms_days"] = {"type": "number"}
    args = {
        "company": "Nordwerk GmbH",
        "legal_form": "GmbH",
        "first_name": "Mara",
        "last_name": "Klein",
        "email": "mara.klein@nordwerk.example",
        "phone": "+49401234567",
        "street": "Hafenweg 9",
        "zip": "20095",
        "city": "Hamburg",
        "country": "DE",
        "vat_id": "DE123456789",
        "payment_terms_days": 14,
        "delivery_method": "pickup",
        "customer_group": "trade",
    }
    _pair(
        stem="tools-wide-customer-001",
        title_de="Kunde Nordwerk mit 14 Feldern anlegen",
        title_en="Create Nordwerk customer with 14 fields",
        task_type="wide_signature",
        system_de=(
            "Du legst Kunden im ERP an. Antworte auf Deutsch. Nutze create_customer. "
            "Setze jedes genannte Feld. payment_terms_days ist eine Zahl. "
            "delivery_method: pickup|courier. customer_group: trade|retail."
        ),
        system_en=(
            "You create ERP customers. Respond in English. Use create_customer. "
            "Set every stated field. payment_terms_days is a number. "
            "delivery_method: pickup|courier. customer_group: trade|retail."
        ),
        user_de=(
            "Lege den Kunden Nordwerk GmbH (Rechtsform GmbH) an: Ansprechpartner Mara Klein, "
            "mara.klein@nordwerk.example, +49401234567, Hafenweg 9, 20095 Hamburg, Land DE, "
            "USt-Id DE123456789, Zahlungsziel 14 Tage, Lieferart pickup, Kundengruppe trade."
        ),
        user_en=(
            "Create customer Nordwerk GmbH (legal form GmbH): contact Mara Klein, "
            "mara.klein@nordwerk.example, +49401234567, Hafenweg 9, 20095 Hamburg, country DE, "
            "VAT ID DE123456789, payment terms 14 days, delivery method pickup, customer group trade."
        ),
        tools=[
            {
                "name": "create_customer",
                "description": "Create a CRM/ERP customer record",
                "parameters": {
                    "type": "object",
                    "properties": props,
                    "required": [
                        "company",
                        "first_name",
                        "last_name",
                        "email",
                        "street",
                        "zip",
                        "city",
                        "country",
                    ],
                },
            }
        ],
        expected={"name": "create_customer", "arguments": args},
        scorers=[
            {
                "type": "tool_call",
                "weight": 1.0,
                "params": {
                    "name": "create_customer",
                    "arguments_fields": fields,
                    "exactly_one": True,
                    "case_insensitive": True,
                },
            }
        ],
    )


def _wide_offer() -> None:
    fields = [
        "offer_id",
        "customer_id",
        "sku",
        "qty",
        "unit_price",
        "currency",
        "valid_until",
        "delivery_date",
        "warehouse",
        "payment_terms_days",
        "incoterm",
        "contact_email",
    ]
    props: dict[str, Any] = {name: {"type": "string"} for name in fields}
    props["qty"] = {"type": "number"}
    props["unit_price"] = {"type": "number"}
    props["payment_terms_days"] = {"type": "number"}
    args = {
        "offer_id": "ANG-4412",
        "customer_id": "ACC-774",
        "sku": "ART-4412",
        "qty": 6,
        "unit_price": 89.5,
        "currency": "EUR",
        "valid_until": "2026-10-15",
        "delivery_date": "2026-10-01",
        "warehouse": "HH-01",
        "payment_terms_days": 30,
        "incoterm": "DAP",
        "contact_email": "einkauf@nordwerk.example",
    }
    _pair(
        stem="tools-wide-offer-001",
        title_de="Angebot ANG-4412 mit 12 Feldern",
        title_en="Offer ANG-4412 with 12 fields",
        task_type="wide_signature",
        system_de=(
            "Du erstellst Angebote. Antworte auf Deutsch. Nutze create_offer. "
            "qty, unit_price und payment_terms_days sind Zahlen. Daten als YYYY-MM-DD. "
            "incoterm: DAP|EXW|FOB."
        ),
        system_en=(
            "You create offers. Respond in English. Use create_offer. "
            "qty, unit_price and payment_terms_days are numbers. Dates as YYYY-MM-DD. "
            "incoterm: DAP|EXW|FOB."
        ),
        user_de=(
            "Angebot ANG-4412 für Kunde ACC-774: 6 Stück ART-4412 zu 89.50 EUR, "
            "gültig bis 2026-10-15, Lieferung 2026-10-01 ab Lager HH-01, "
            "Zahlungsziel 30 Tage, Incoterm DAP, Kontakt einkauf@nordwerk.example."
        ),
        user_en=(
            "Offer ANG-4412 for customer ACC-774: 6 units ART-4412 at 89.50 EUR, "
            "valid until 2026-10-15, delivery 2026-10-01 from warehouse HH-01, "
            "payment terms 30 days, incoterm DAP, contact einkauf@nordwerk.example."
        ),
        tools=[
            {
                "name": "create_offer",
                "description": "Create a sales offer",
                "parameters": {
                    "type": "object",
                    "properties": props,
                    "required": [
                        "offer_id",
                        "customer_id",
                        "sku",
                        "qty",
                        "unit_price",
                        "currency",
                    ],
                },
            }
        ],
        expected={"name": "create_offer", "arguments": args},
        scorers=[
            {
                "type": "tool_call",
                "weight": 1.0,
                "params": {
                    "name": "create_offer",
                    "arguments_fields": fields,
                    "exactly_one": True,
                    "case_insensitive": True,
                },
            }
        ],
    )


def _nested_address() -> None:
    args = {
        "customer": {
            "name": "Nordwerk GmbH",
            "address": {
                "street": "Hafenweg 9",
                "zip": "20095",
                "city": "Hamburg",
                "country": "DE",
            },
        },
        "contact": {
            "email": "mara.klein@nordwerk.example",
            "phone": "+49401234567",
        },
    }
    fields = [
        "customer.name",
        "customer.address.street",
        "customer.address.zip",
        "customer.address.city",
        "customer.address.country",
        "contact.email",
        "contact.phone",
    ]
    _pair(
        stem="tools-nested-address-001",
        title_de="Kunde mit Adressobjekt anlegen",
        title_en="Create customer with address object",
        task_type="nested_argument",
        system_de=(
            "Du legst Kunden an. Antworte auf Deutsch. Nutze create_customer. "
            "customer ist ein Objekt mit name und address "
            "(street, zip, city, country). contact ist ein Objekt mit email und phone."
        ),
        system_en=(
            "You create customers. Respond in English. Use create_customer. "
            "customer is an object with name and address "
            "(street, zip, city, country). contact is an object with email and phone."
        ),
        user_de=(
            "Lege Nordwerk GmbH an, Adresse Hafenweg 9, 20095 Hamburg, Land DE. "
            "Kontakt mara.klein@nordwerk.example, +49401234567."
        ),
        user_en=(
            "Create Nordwerk GmbH, address Hafenweg 9, 20095 Hamburg, country DE. "
            "Contact mara.klein@nordwerk.example, +49401234567."
        ),
        tools=[
            {
                "name": "create_customer",
                "description": "Create a customer with nested address",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "address": {
                                    "type": "object",
                                    "properties": {
                                        "street": {"type": "string"},
                                        "zip": {"type": "string"},
                                        "city": {"type": "string"},
                                        "country": {"type": "string"},
                                    },
                                    "required": ["street", "zip", "city", "country"],
                                },
                            },
                            "required": ["name", "address"],
                        },
                        "contact": {
                            "type": "object",
                            "properties": {
                                "email": {"type": "string"},
                                "phone": {"type": "string"},
                            },
                            "required": ["email", "phone"],
                        },
                    },
                    "required": ["customer", "contact"],
                },
            }
        ],
        expected={"name": "create_customer", "arguments": args},
        scorers=[
            {
                "type": "tool_call",
                "weight": 1.0,
                "params": {
                    "name": "create_customer",
                    "arguments_fields": fields,
                    "exactly_one": True,
                    "case_insensitive": True,
                },
            }
        ],
    )


def _array_order() -> None:
    lines = [
        {"sku": "ART-4412", "qty": 6, "unit_price": 12.5},
        {"sku": "ART-1187", "qty": 2, "unit_price": 40.0},
        {"sku": "ART-1310", "qty": 1, "unit_price": 89.5},
        {"sku": "ART-2201", "qty": 4, "unit_price": 7.25},
    ]
    expected = {
        "tool_calls": [
            {
                "name": "create_order",
                "arguments": {"customer_id": "ACC-774", "lines": lines},
            }
        ]
    }
    _pair(
        stem="tools-array-order-001",
        title_de="Auftrag mit vier Positionen",
        title_en="Order with four line items",
        task_type="array_argument",
        system_de=(
            "Du legst Aufträge an. Antworte auf Deutsch. Nutze create_order. "
            "lines ist ein Array von Objekten mit sku, qty (Zahl) und unit_price (Zahl). "
            "Reihenfolge der Positionen ist egal."
        ),
        system_en=(
            "You create orders. Respond in English. Use create_order. "
            "lines is an array of objects with sku, qty (number) and unit_price (number). "
            "Line order does not matter."
        ),
        user_de=(
            "Auftrag für ACC-774: ART-4412 × 6 à 12.50, ART-1187 × 2 à 40.00, "
            "ART-1310 × 1 à 89.50, ART-2201 × 4 à 7.25."
        ),
        user_en=(
            "Order for ACC-774: ART-4412 × 6 at 12.50, ART-1187 × 2 at 40.00, "
            "ART-1310 × 1 at 89.50, ART-2201 × 4 at 7.25."
        ),
        tools=[
            {
                "name": "create_order",
                "description": "Create a sales order with line items",
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
                                    "qty": {"type": "number"},
                                    "unit_price": {"type": "number"},
                                },
                                "required": ["sku", "qty", "unit_price"],
                            },
                        },
                    },
                    "required": ["customer_id", "lines"],
                },
            }
        ],
        expected=expected,
        scorers=[
            {
                "type": "tool_call",
                "weight": 0.3,
                "params": {
                    "name": "create_order",
                    "arguments_fields": ["customer_id"],
                    "exactly_one": True,
                },
            },
            {
                "type": "set_equality",
                "weight": 0.7,
                "params": {
                    "field": "tool_calls.0.arguments.lines",
                    "keys": ["sku", "qty", "unit_price"],
                    "ignore_order": True,
                },
            },
        ],
    )


def _array_timesheet() -> None:
    entries = [
        {"date": "2026-09-15", "hours": 8, "project": "PRJ-A"},
        {"date": "2026-09-16", "hours": 6, "project": "PRJ-B"},
        {"date": "2026-09-17", "hours": 4, "project": "PRJ-A"},
    ]
    expected = {
        "tool_calls": [
            {
                "name": "log_hours",
                "arguments": {"employee": "Lea Berg", "entries": entries},
            }
        ]
    }
    _pair(
        stem="tools-array-timesheet-001",
        title_de="Stunden mit drei Einträgen",
        title_en="Timesheet with three entries",
        task_type="array_argument",
        system_de=(
            "Du buchst Stunden. Antworte auf Deutsch. Nutze log_hours. "
            "entries ist ein Array von Objekten mit date (YYYY-MM-DD), hours (Zahl) und project. "
            "Reihenfolge ist egal."
        ),
        system_en=(
            "You log hours. Respond in English. Use log_hours. "
            "entries is an array of objects with date (YYYY-MM-DD), hours (number) and project. "
            "Order does not matter."
        ),
        user_de=(
            "Stunden für Lea Berg: 2026-09-15 8h auf PRJ-A, 2026-09-16 6h auf PRJ-B, "
            "2026-09-17 4h auf PRJ-A."
        ),
        user_en=(
            "Hours for Lea Berg: 2026-09-15 8h on PRJ-A, 2026-09-16 6h on PRJ-B, "
            "2026-09-17 4h on PRJ-A."
        ),
        tools=[
            {
                "name": "log_hours",
                "description": "Log timesheet entries",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "employee": {"type": "string"},
                        "entries": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "date": {"type": "string"},
                                    "hours": {"type": "number"},
                                    "project": {"type": "string"},
                                },
                                "required": ["date", "hours", "project"],
                            },
                        },
                    },
                    "required": ["employee", "entries"],
                },
            }
        ],
        expected=expected,
        scorers=[
            {
                "type": "tool_call",
                "weight": 0.3,
                "params": {
                    "name": "log_hours",
                    "arguments_fields": ["employee"],
                    "exactly_one": True,
                    "case_insensitive": True,
                },
            },
            {
                "type": "set_equality",
                "weight": 0.7,
                "params": {
                    "field": "tool_calls.0.arguments.entries",
                    "keys": ["date", "hours", "project"],
                    "ignore_order": True,
                },
            },
        ],
    )


def _enum_ticket() -> None:
    args_de = {
        "queue": "hardware",
        "priority": "high",
        "channel": "phone",
        "subject": "Drucker Lager 2 offline",
    }
    args_en = {
        "queue": "hardware",
        "priority": "high",
        "channel": "phone",
        "subject": "Printer warehouse 2 offline",
    }
    tools = [
        {
            "name": "create_ticket",
            "description": "Open a support ticket",
            "parameters": {
                "type": "object",
                "properties": {
                    "queue": {"type": "string", "enum": ["hardware", "software", "billing"]},
                    "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]},
                    "channel": {"type": "string", "enum": ["email", "phone", "portal"]},
                    "subject": {"type": "string"},
                },
                "required": ["queue", "priority", "channel", "subject"],
            },
        }
    ]
    scorers = [
        {
            "type": "tool_call",
            "weight": 1.0,
            "params": {
                "name": "create_ticket",
                "arguments_fields": ["queue", "priority", "channel", "subject"],
                "exactly_one": True,
                "case_insensitive": True,
            },
        }
    ]
    _pair(
        stem="tools-enum-ticket-001",
        title_de="Ticket mit englischen Enums",
        title_en="Ticket with English enums",
        task_type="enum_literal",
        system_de=(
            "Du eröffnest Tickets. Antworte auf Deutsch. Nutze create_ticket. "
            "queue: hardware|software|billing. "
            "priority: low|normal|high|urgent. "
            "channel: email|phone|portal. Keys und Enums auf Englisch."
        ),
        system_en=(
            "You open tickets. Respond in English. Use create_ticket. "
            "queue: hardware|software|billing. "
            "priority: low|normal|high|urgent. "
            "channel: email|phone|portal. Keys and enums in English."
        ),
        user_de="Ticket Queue hardware, Priorität hoch, Kanal per Telefon, Betreff Drucker Lager 2 offline.",
        user_en="Ticket queue hardware, priority high, channel by phone, subject Printer warehouse 2 offline.",
        tools=tools,
        expected={"name": "create_ticket", "arguments": args_de},
        scorers=scorers,
    )
    # EN expected subject differs; rewrite the EN file expected after _pair used DE args.
    en_path = ROOT / "suites" / SUITE / "cases" / "en-GB" / "en-tools-enum-ticket-001.yaml"
    data = yaml.safe_load(en_path.read_text(encoding="utf-8"))
    data["expected"]["arguments"] = args_en
    write_case(en_path, data)


def _enum_date() -> None:
    args = {
        "sku": "ART-4412",
        "qty": 5,
        "unit": "kg",
        "delivery_date": "2026-09-22",
    }
    _pair(
        stem="tools-enum-date-001",
        title_de="Wareneingang Kilo und Übermorgen",
        title_en="Goods receipt kilos and day after tomorrow",
        task_type="enum_literal",
        system_de=(
            "Du buchst Wareneingänge. Antworte auf Deutsch. Nutze receive_goods. "
            "Heute ist 2026-09-20. unit: pcs|kg|m. delivery_date als YYYY-MM-DD. qty ist eine Zahl."
        ),
        system_en=(
            "You book goods receipts. Respond in English. Use receive_goods. "
            "Today is 2026-09-20. unit: pcs|kg|m. delivery_date as YYYY-MM-DD. qty is a number."
        ),
        user_de="5 Kilo ART-4412, Lieferung übermorgen.",
        user_en="5 kilos of ART-4412, delivery the day after tomorrow.",
        tools=[
            {
                "name": "receive_goods",
                "description": "Book a goods receipt",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sku": {"type": "string"},
                        "qty": {"type": "number"},
                        "unit": {"type": "string", "enum": ["pcs", "kg", "m"]},
                        "delivery_date": {"type": "string"},
                    },
                    "required": ["sku", "qty", "unit", "delivery_date"],
                },
            }
        ],
        expected={"name": "receive_goods", "arguments": args},
        scorers=[
            {
                "type": "tool_call",
                "weight": 1.0,
                "params": {
                    "name": "receive_goods",
                    "arguments_fields": ["sku", "qty", "unit", "delivery_date"],
                    "exactly_one": True,
                    "case_insensitive": True,
                },
            }
        ],
    )


def _omit_update() -> None:
    args = {"id": "ACC-774", "phone": "+49407654321"}
    _pair(
        stem="tools-omit-update-001",
        title_de="Nur Telefon setzen, Rest weglassen",
        title_en="Set phone only, omit the rest",
        task_type="optional_omission",
        risk="high",
        system_de=(
            "Du pflegst das CRM. Antworte auf Deutsch. Nutze update_customer. "
            "Setze nur Felder, die der User nennt. Erfinde keine optionalen Werte."
        ),
        system_en=(
            "You maintain the CRM. Respond in English. Use update_customer. "
            "Set only fields the user states. Do not invent optional values."
        ),
        user_de="Bei Konto ACC-774 nur die Telefonnummer auf +49407654321 setzen.",
        user_en="On account ACC-774 set only the phone number to +49407654321.",
        tools=[
            {
                "name": "update_customer",
                "description": "Patch a customer record",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "phone": {"type": "string"},
                        "email": {"type": "string"},
                        "note": {"type": "string"},
                        "payment_terms_days": {"type": "number"},
                        "newsletter": {"type": "boolean"},
                    },
                    "required": ["id"],
                },
            }
        ],
        expected={"name": "update_customer", "arguments": args},
        scorers=[
            {
                "type": "tool_call",
                "weight": 1.0,
                "params": {
                    "name": "update_customer",
                    "arguments_fields": ["id", "phone"],
                    "absent_fields": ["email", "note", "payment_terms_days", "newsletter"],
                    "exactly_one": True,
                },
            }
        ],
    )


def write_readme(suite: Path) -> None:
    rows = EXISTING_ROWS + NEW_ROWS
    table = "\n".join(f"| {pair} | {task_type} |" for pair, task_type in rows)
    (suite / "README.md").write_text(
        f"# {SUITE}\n\n"
        f"| Field | Value |\n| --- | --- |\n"
        f"| **Status** | released (`review_status: approved`) |\n"
        f"| **Suite ID** | `{SUITE}` |\n"
        f"| **Cases** | 48 (24 DE/EN pairs) |\n"
        f"| **Languages** | `de-DE`, `en-GB` |\n"
        f"| **Role** | Tool-use pack; part of **SME Full** from content 0.13.0, "
        f"crowded variants in 0.14.0, schema-heavy calls in 0.15.0 |\n\n"
        f"ERP stock, booking, CRM, tickets, refund policy, negatives, hallucinations, "
        f"four crowded-namespace pairs, plus wide signatures, nested objects, "
        f"line-item arrays, enum literals and optional-field omission.\n\n"
        f"## Task types\n\n| Pair ID | Task type |\n| --- | --- |\n{table}\n\n"
        f"## Usage\n\n```bash\nuv run sme-bench validate suites/{SUITE}\n"
        f"uv run sme-bench run --base-url \"$BASE_URL\" --model \"$MODEL\" \\\n"
        f"  --suite suites/{SUITE} --output runs/{SUITE}\n```\n",
        encoding="utf-8",
    )
    (suite / "README.de.md").write_text(
        f"# {SUITE}\n\n"
        f"| Feld | Wert |\n| --- | --- |\n"
        f"| **Status** | freigegeben (`review_status: approved`) |\n"
        f"| **Suite-ID** | `{SUITE}` |\n"
        f"| **Fälle** | 48 (24 DE/EN-Paare) |\n"
        f"| **Sprachen** | `de-DE`, `en-GB` |\n"
        f"| **Rolle** | Tool-Use-Pack; Teil von **SME Full** ab Inhalt 0.13.0, "
        f"Crowded-Varianten in 0.14.0, Schema-Aufrufe in 0.15.0 |\n\n"
        f"ERP-Bestand, Termin, CRM, Ticket, Erstattung, Negativfälle, Halluzinationen, "
        f"vier Crowded-Namespace-Paare plus breite Signaturen, verschachtelte Objekte, "
        f"Positions-Arrays, Enum-Literale und Weglassen optionaler Felder.\n\n"
        f"## Aufgabentypen\n\n| Pair-ID | Aufgabentyp |\n| --- | --- |\n{table}\n",
        encoding="utf-8",
    )


def main() -> None:
    _wide_customer()
    _wide_offer()
    _nested_address()
    _array_order()
    _array_timesheet()
    _enum_ticket()
    _enum_date()
    _omit_update()

    suite_dir = ROOT / "suites" / SUITE
    manifest_path = suite_dir / "suite.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = CONTENT_VERSION
    manifest["description"] = (
        "Tool-use pack: ERP, booking, CRM, tickets, refunds, negatives, hallucinations, "
        "crowded-namespace variants, plus wide signatures, nested and array arguments"
    )
    manifest_path.write_text(_dump(manifest), encoding="utf-8")
    write_readme(suite_dir)

    releases_path = ROOT / "suites/compatibility/releases.json"
    releases = json.loads(releases_path.read_text(encoding="utf-8"))
    if CONTENT_VERSION not in releases["released"]:
        releases["released"].append(CONTENT_VERSION)
    releases_path.write_text(json.dumps(releases, indent=2) + "\n", encoding="utf-8")

    known = known_scorer_names()
    suite = load_suite(suite_dir, known_scorers=known)
    write_case_catalog(
        suite_dir / "CASES.md",
        suite.tasks,
        suite_id=suite.manifest.id,
        suite_version=suite.manifest.version,
        canary=suite.manifest.canary,
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
    print(f"OK {len(loaded.tasks)} tasks, suite {loaded.manifest.version}")


if __name__ == "__main__":
    main()
