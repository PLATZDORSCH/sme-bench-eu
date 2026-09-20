"""Author SME Full 0.14.1: close task-specification gaps found in the first 0.14.0 runs.

Fix-forward on the content line (see docs/VERSIONING.md, "gap in task
specification"): prompts now spell out the closed literals, ids and number
formats the scorers check for. Case files are edited in place; canary GUIDs stay.

- sme-agentic-v0.1: prompts ask for the tool-returned id verbatim; numeric and
  IBAN terms accept the common DE/EN formattings.
- sme-dialog-v0.1 / sme-longctx-v0.1: enum values, boolean fields, formats and
  "name only" rules are listed in the system prompt; keys/enums stay English.
- sme-tools-v0.1: brittle contains terms (Gern, no, Konflikt/conflict) accept
  natural alternatives or are dropped where the critical scorer already covers
  the behaviour.
"""

from __future__ import annotations

import json
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

CONTENT_VERSION = "0.14.1"
SUITES = ("sme-agentic-v0.1", "sme-dialog-v0.1", "sme-longctx-v0.1", "sme-tools-v0.1")


# --------------------------------------------------------------------------- io


def _dump(data: dict) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)


def load_case(path: Path) -> tuple[str, dict[str, Any]]:
    guid = read_canary_guid(path)
    if not guid:
        raise SystemExit(f"{path}: missing canary header")
    return guid, yaml.safe_load(path.read_text(encoding="utf-8"))


def save_case(path: Path, guid: str, payload: dict[str, Any]) -> None:
    path.write_text(format_canary_header(guid) + "\n" + _dump(payload), encoding="utf-8")


def case_path(suite: str, case_id: str) -> Path:
    lang = "de-DE" if case_id.startswith("de-") else "en-GB"
    return ROOT / "suites" / suite / "cases" / lang / f"{case_id}.yaml"


def edit_case(suite: str, case_id: str, fn) -> None:
    path = case_path(suite, case_id)
    guid, data = load_case(path)
    fn(data)
    save_case(path, guid, data)


def set_system(data: dict[str, Any], text: str) -> None:
    for msg in data["messages"]:
        if msg.get("role") == "system":
            msg["content"] = text
            return
    raise SystemExit(f"{data['id']}: no system message")


def append_system(data: dict[str, Any], suffix: str) -> None:
    for msg in data["messages"]:
        if msg.get("role") == "system":
            # Idempotent: drop earlier copies before appending once.
            base = msg["content"].replace(suffix, "").rstrip()
            msg["content"] = base + " " + suffix
            return
    raise SystemExit(f"{data['id']}: no system message")


def scorer(data: dict[str, Any], scorer_type: str) -> dict[str, Any]:
    for spec in data["scorers"]:
        if spec["type"] == scorer_type:
            return spec
    raise SystemExit(f"{data['id']}: no {scorer_type} scorer")


def bump_suite(suite: str) -> None:
    path = ROOT / "suites" / suite / "suite.yaml"
    manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
    manifest["version"] = CONTENT_VERSION
    path.write_text(_dump(manifest), encoding="utf-8")


# ---------------------------------------------------------------- agentic pack

ID_SUFFIX = {
    "de": "Nenne in der Antwort die vom Tool zurückgegebene ID wörtlich (z. B. {example}).",
    "en": "Quote the id returned by the tool verbatim in your answer (e.g. {example}).",
}


def _lang_key(case_id: str) -> str:
    return "de" if case_id.startswith("de-") else "en"


def fix_agentic() -> None:
    suite = "sme-agentic-v0.1"
    id_cases = {
        "chain-order-001": "ORD-19",
        "once-room-001": "bk-2",
        "once-mail-001": "msg_9",
        "auth-event-001": "evt-4",
        "auth-refund-001": "rf-3",
        "chain-event-001": "ev-7",
        "once-ticket-001": "t-11",
        "auth-mail-001": "msg_22",
        "chain-crm-001": "cus-8",
    }
    for stem, example in id_cases.items():
        for prefix in ("de", "en"):
            cid = f"{prefix}-agentic-{stem}"

            def _fix(data: dict[str, Any], *, cid: str = cid, example: str = example) -> None:
                append_system(data, ID_SUFFIX[_lang_key(cid)].format(example=example))
                scorer(data, "contains")["params"]["case_insensitive"] = True

            edit_case(suite, cid, _fix)

    def _file(data: dict[str, Any]) -> None:
        if _lang_key(data["id"]) == "de":
            set_system(
                data,
                "Antworte auf Deutsch. Wenn eine Datei fehlt oder beschädigt ist, lies die "
                "genannte Alternative. Nenne den Umsatz als Zahl aus der Datei (z. B. 184000 EUR).",
            )
        else:
            set_system(
                data,
                "Respond in English. If a file is missing or corrupted, read the named "
                "alternative. Report revenue as the number from the file (e.g. 184000 EUR).",
            )
        scorer(data, "contains")["params"]["terms"] = [["184000", "184.000", "184,000"]]

    edit_case(suite, "de-agentic-recover-file-001", _file)
    edit_case(suite, "en-agentic-recover-file-001", _file)

    def _iban(data: dict[str, Any]) -> None:
        if _lang_key(data["id"]) == "de":
            set_system(
                data,
                "Antworte auf Deutsch. Prüfe die IBAN; bei Fehler die korrigierte "
                "DE89370400440532013000 prüfen. Nenne die gültige IBAN in der Antwort ohne "
                "Leerzeichen.",
            )
        else:
            set_system(
                data,
                "Respond in English. Check the IBAN; on error check the corrected "
                "DE89370400440532013000. Quote the valid IBAN in your answer without spaces.",
            )
        scorer(data, "contains")["params"]["terms"] = [
            ["DE89370400440532013000", "DE89 3704 0044 0532 0130 00"]
        ]

    edit_case(suite, "de-agentic-recover-iban-001", _iban)
    edit_case(suite, "en-agentic-recover-iban-001", _iban)


# ----------------------------------------------------------------- dialog pack

RULES = {
    "de": (
        "Antworte nur mit JSON. JSON-Schlüssel und die aufgezählten Enum-Werte bleiben exakt "
        "wie angegeben (englisch); freie Textwerte auf Deutsch."
    ),
    "en": (
        "Reply with JSON only. Keep JSON keys and the listed enum values exactly as given; "
        "free-text values in English."
    ),
}


def fix_dialog() -> None:
    suite = "sme-dialog-v0.1"
    prompts: dict[str, dict[str, str]] = {
        "dialog-qty-revise-001": {
            "de": "Extrahiere die finale Bestellung als JSON mit den Schlüsseln sku, qty (Zahl), "
            "status. status ist einer von: revised, confirmed, cancelled (revised, wenn der "
            "Kunde eine frühere Angabe geändert hat).",
            "en": "Extract the final order as JSON with keys sku, qty (number), status. status "
            "is one of: revised, confirmed, cancelled (revised when the customer changed an "
            "earlier detail).",
        },
        "dialog-address-001": {
            "de": "Finale Lieferung als JSON mit den Schlüsseln city (nur Stadtname), sku, qty "
            "(Zahl). Die letzte Kundenangabe gilt.",
            "en": "Final delivery as JSON with keys city (city name only), sku, qty (number). "
            "The latest customer statement wins.",
        },
        "dialog-clarify-001": {
            "de": "JSON mit den Schlüsseln needs_clarification (Boolean true/false) und "
            "missing_field. missing_field ist einer von: delivery_date, delivery_address, "
            "quantity, price, none.",
            "en": "JSON with keys needs_clarification (boolean true/false) and missing_field. "
            "missing_field is one of: delivery_date, delivery_address, quantity, price, none.",
        },
        "dialog-escalate-001": {
            "de": "JSON mit den Schlüsseln action und reason. action ist einer von: escalate, "
            "resolve, wait. reason ist einer von: repeat_complaint, sla_breach, safety, none. "
            "Eskaliere bei der zweiten Beschwerde zum selben Defekt.",
            "en": "JSON with keys action and reason. action is one of: escalate, resolve, wait. "
            "reason is one of: repeat_complaint, sla_breach, safety, none. Escalate on the "
            "second complaint about the same defect.",
        },
        "dialog-contradict-001": {
            "de": "JSON mit den Schlüsseln sku (nur die Artikelnummer, z. B. RAL-7016), qty "
            "(Zahl) und contradiction (Boolean true/false: hat der Kunde eine frühere Angabe "
            "widerrufen?). Die letzte Zahl gewinnt.",
            "en": "JSON with keys sku (article number only, e.g. RAL-7016), qty (number) and "
            "contradiction (boolean true/false: did the customer revoke an earlier statement?). "
            "The latest number wins.",
        },
        "dialog-callback-001": {
            "de": "JSON mit den Schlüsseln next_step und promised. next_step ist einer von: "
            "call_now, schedule_callback, email. promised ist die zugesagte Uhrzeit im Format "
            "HH:MM.",
            "en": "JSON with keys next_step and promised. next_step is one of: call_now, "
            "schedule_callback, email. promised is the promised time in HH:MM format.",
        },
        "dialog-multi-issue-001": {
            "de": "JSON mit dem Schlüssel issues (Liste, in der Reihenfolge der Nennung). "
            "Erlaubte Werte: return, duplicate_invoice, delay, damage.",
            "en": "JSON with key issues (list, in order of mention). Allowed values: return, "
            "duplicate_invoice, delay, damage.",
        },
        "dialog-complaint-001": {
            "de": "JSON mit den Schlüsseln tone und sla_breach. tone ist einer von: complaint, "
            "neutral, praise. sla_breach ist ein Boolean true/false.",
            "en": "JSON with keys tone and sla_breach. tone is one of: complaint, neutral, "
            "praise. sla_breach is a boolean true/false.",
        },
    }
    for stem, texts in prompts.items():
        for prefix in ("de", "en"):
            cid = f"{prefix}-{stem}"

            def _fix(
                data: dict[str, Any], *, cid: str = cid, texts: dict[str, str] = texts
            ) -> None:
                lang = _lang_key(cid)
                set_system(data, f"{texts[lang]} {RULES[lang]}")
                if any(s["type"] == "set_equality" for s in data["scorers"]):
                    return  # already migrated (idempotent rerun)
                spec = scorer(data, "json_fields")
                spec["params"]["case_insensitive"] = True
                if "issues" in spec["params"].get("fields", []):
                    # Order of mention is requested but not graded: set semantics.
                    data["scorers"] = [
                        {
                            "type": "set_equality",
                            "weight": spec["weight"],
                            "params": {
                                "field": "issues",
                                "ignore_order": True,
                                "case_insensitive": True,
                            },
                        }
                        if s is spec
                        else s
                        for s in data["scorers"]
                    ]

            edit_case(suite, cid, _fix)


# ---------------------------------------------------------------- longctx pack


def fix_longctx() -> None:
    suite = "sme-longctx-v0.1"
    prompts: dict[str, dict[str, str]] = {
        "longctx-sales-csv-001": {
            "de": "Lies die CSV. JSON mit den Schlüsseln sku und margin. margin ist der Anteil "
            "(revenue − cost) / revenue als Dezimalzahl 0–1 (z. B. 0.12), nicht in Prozent. "
            "Nur SKU-1187.",
            "en": "Read the CSV. JSON with keys sku and margin. margin is the share "
            "(revenue − cost) / revenue as a decimal 0–1 (e.g. 0.12), not a percentage. "
            "Only SKU-1187.",
        },
        "longctx-stock-csv-001": {
            "de": "Lies die CSV. JSON mit den Schlüsseln sku und margin. margin ist der Anteil "
            "(revenue − cost) / revenue als Dezimalzahl 0–1 (z. B. 0.12), nicht in Prozent. "
            "Nur SKU-1310.",
            "en": "Read the CSV. JSON with keys sku and margin. margin is the share "
            "(revenue − cost) / revenue as a decimal 0–1 (e.g. 0.12), not a percentage. "
            "Only SKU-1310.",
        },
        "longctx-invoice-policy-001": {
            "de": "Lies die CSV. JSON mit den Schlüsseln sku und margin. margin ist der Anteil "
            "(revenue − cost) / revenue als Dezimalzahl 0–1 (z. B. 0.12), nicht in Prozent. "
            "Nur SKU-1422.",
            "en": "Read the CSV. JSON with keys sku and margin. margin is the share "
            "(revenue − cost) / revenue as a decimal 0–1 (e.g. 0.12), not a percentage. "
            "Only SKU-1422.",
        },
        "longctx-notice-001": {
            "de": "Lies den Vertrag. JSON mit den Schlüsseln notice_days (Zahl in Tagen) und to. "
            "to ist einer von: quarter_end, month_end, year_end, any_day.",
            "en": "Read the contract. JSON with keys notice_days (number of days) and to. "
            "to is one of: quarter_end, month_end, year_end, any_day.",
        },
        "longctx-liability-001": {
            "de": "Lies den Vertrag. JSON mit den Schlüsseln liability_eur (Zahl ohne Einheit) "
            "und period. period ist einer von: calendar_year, contract_year, per_incident, "
            "total.",
            "en": "Read the contract. JSON with keys liability_eur (number without unit) and "
            "period. period is one of: calendar_year, contract_year, per_incident, total.",
        },
        "longctx-price-thread-001": {
            "de": "Lies den Mail-Thread. JSON mit den Schlüsseln sku, unit_price (Zahl in EUR) "
            "und confirmed_by (nur Vor- und Nachname, ohne Titel oder Funktion).",
            "en": "Read the mail thread. JSON with keys sku, unit_price (number in EUR) and "
            "confirmed_by (first and last name only, no title or role).",
        },
        "longctx-approval-001": {
            "de": "Lies den Mail-Thread. JSON mit den Schlüsseln invoice, skonto_percent (Zahl) "
            "und approver (nur Vor- und Nachname, ohne Titel oder Funktion).",
            "en": "Read the mail thread. JSON with keys invoice, skonto_percent (number) and "
            "approver (first and last name only, no title or role).",
        },
        "longctx-meeting-001": {
            "de": "Lies das Protokoll. JSON mit den Schlüsseln owner (nur Nachname), deliverable "
            "(kurzes snake_case-Token, z. B. forecast_q4) und due (englischer Wochentag: Monday, "
            "Tuesday, Wednesday, Thursday, Friday).",
            "en": "Read the minutes. JSON with keys owner (surname only), deliverable (short "
            "snake_case token, e.g. forecast_q4) and due (weekday: Monday, Tuesday, Wednesday, "
            "Thursday, Friday).",
        },
    }
    for stem, texts in prompts.items():
        for prefix in ("de", "en"):
            cid = f"{prefix}-{stem}"

            def _fix(
                data: dict[str, Any], *, cid: str = cid, texts: dict[str, str] = texts
            ) -> None:
                lang = _lang_key(cid)
                set_system(data, f"{texts[lang]} {RULES[lang]}")
                scorer(data, "json_fields")["params"]["case_insensitive"] = True

            edit_case(suite, cid, _fix)


# ------------------------------------------------------------------ tools pack


def fix_tools() -> None:
    suite = "sme-tools-v0.1"

    def _thanks_de(data: dict[str, Any]) -> None:
        scorer(data, "contains")["params"].update(
            {"terms": [["gern", "freut"], "ART-4412"], "case_insensitive": True}
        )

    def _thanks_en(data: dict[str, Any]) -> None:
        scorer(data, "contains")["params"].update(
            {"terms": [["welcome", "glad", "pleasure"], "ART-4412"], "case_insensitive": True}
        )

    def _halluc_en(data: dict[str, Any]) -> None:
        # ``no`` was a substring gamble; the critical no_tool_call scorer already
        # covers the refusal, contains keeps the tool name plus a negation.
        scorer(data, "contains")["params"].update(
            {
                "terms": ["check_iban", ["no ", "not ", "n't ", "unable", "cannot"]],
                "case_insensitive": True,
            }
        )

    def _halluc_de(data: dict[str, Any]) -> None:
        scorer(data, "contains")["params"].update(
            {"terms": ["check_iban", ["kein", "nicht"]], "case_insensitive": True}
        )

    def _booking_en(data: dict[str, Any]) -> None:
        scorer(data, "contains")["params"].update(
            {
                "terms": ["11:30", ["conflict", "taken", "booked", "unavailable", "not available"]],
                "case_insensitive": True,
            }
        )

    def _booking_de(data: dict[str, Any]) -> None:
        scorer(data, "contains")["params"].update(
            {
                "terms": ["11:30", ["Konflikt", "belegt", "vergeben", "nicht frei", "besetzt"]],
                "case_insensitive": True,
            }
        )

    edit_case(suite, "de-tools-none-thanks-001", _thanks_de)
    edit_case(suite, "en-tools-none-thanks-001", _thanks_en)
    edit_case(suite, "en-tools-halluc-iban-001", _halluc_en)
    edit_case(suite, "de-tools-halluc-iban-001", _halluc_de)
    edit_case(suite, "en-tools-turn-booking-001", _booking_en)
    edit_case(suite, "de-tools-turn-booking-001", _booking_de)


# ------------------------------------------------------------------- release


def main() -> None:
    fix_agentic()
    fix_dialog()
    fix_longctx()
    fix_tools()
    for suite in SUITES:
        bump_suite(suite)

    releases_path = ROOT / "suites/compatibility/releases.json"
    releases = json.loads(releases_path.read_text(encoding="utf-8"))
    if CONTENT_VERSION not in releases["released"]:
        releases["released"].append(CONTENT_VERSION)
    releases_path.write_text(json.dumps(releases, indent=2) + "\n", encoding="utf-8")

    known = known_scorer_names()
    for suite in SUITES:
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
    print(f"OK {len(loaded.tasks)} tasks, suite {loaded.manifest.version}")


if __name__ == "__main__":
    main()
