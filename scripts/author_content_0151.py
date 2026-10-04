"""Author SME Full 0.15.1: close residual prompt/fixture ambiguity.

The 0.15.0 qwen3.8-27b run failed six ids for specification gaps, not scorer
defects. Prompts and fixtures now state the intended field, citation roles and
discount base. Scorers and expected values stay; canary GUIDs stay.
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

CONTENT_VERSION = "0.15.1"
SUITES = ("sme-dialog-v0.1", "sme-expert-v0.1")

CALLBACK_SYSTEM = {
    "de-dialog-callback-001": (
        "JSON mit den Schlüsseln next_step und promised. next_step ist einer von: "
        "call_now, schedule_callback, email. promised ist die ursprünglich zugesagte "
        "Uhrzeit aus dem Gesprächsverlauf im Format HH:MM (nicht die aktuelle Uhrzeit). "
        "Antworte nur mit JSON. JSON-Schlüssel und die aufgezählten Enum-Werte bleiben "
        "exakt wie angegeben (englisch); freie Textwerte auf Deutsch."
    ),
    "en-dialog-callback-001": (
        "JSON with keys next_step and promised. next_step is one of: call_now, "
        "schedule_callback, email. promised is the time originally promised earlier "
        "in the conversation, HH:MM format (not the current time). Reply with JSON only. "
        "Keep JSON keys and the listed enum values exactly as given; free-text values "
        "in English."
    ),
}

POLICY_SYSTEM = {
    "de-exp-policy-chain-001": (
        'Berechne die Gebühr nur aus der Richtlinie. Gib JSON {"answer":"<Betrag>",'
        '"citations":["ID"]} zurück. citations ohne Klammern. Genau drei IDs: die '
        "Vorrangregel, die die Sondervereinbarung über die AGB stellt; die Vorrangregel, "
        "die die E-Mail-Zusage ausschließt; die konkret angewandte Storno-Klausel. "
        "Formuliere alle Textwerte auf Deutsch; JSON-Schlüssel bleiben unverändert."
    ),
    "en-exp-policy-chain-001": (
        'Compute the fee from the policy only. Return JSON {"answer":"<amount>",'
        '"citations":["ID"]}. citations without brackets. Exactly three IDs: the '
        "precedence rule that the addendum beats the GTC; the precedence rule that "
        "excludes the email promise; the cancellation clause that actually applies. "
        "Write all text values in English; keep JSON keys unchanged."
    ),
}

TCO_FIXTURES = {
    "de-exp-offer-tco.txt": (
        "Heute 2026-06-15. Fläche 120 m². 3-Jahres-TCO: Einmalkosten nach Skonto/Versand\n"
        "plus 3 × jährliche Folgekosten. Nur gültige Angebote. Mindestmenge muss erfüllt sein.\n"
        "\n"
        "Angebot Holm (gültig bis 2026-07-01): 28 EUR/m², Versand 200, 2 % Skonto auf die "
        "Gesamtrechnung inkl. Versand,\n"
        "keine jährlichen Kosten, Mindestfläche 80 m².\n"
        "\n"
        "Angebot BetaCraft (gültig bis 2026-05-01, ABGELAUFEN): Pauschale 3000, Versand 0.\n"
        "\n"
        "Angebot NordStunden: 45 EUR/h × 80 h + Material 900 + Versand 150, plus Service "
        "200 EUR/Jahr,\n"
        "Mindeststunden 60.\n"
    ),
    "en-exp-offer-tco.txt": (
        "Today 2026-06-15. Area 120 m². 3-year TCO: one-off cost after discount/shipping\n"
        "plus 3 × yearly follow-on cost. Valid offers only. Minimum quantity must be met.\n"
        "\n"
        "Offer Holm (valid until 2026-07-01): 28 EUR/m², shipping 200, 2% cash discount on "
        "the total invoice including shipping,\n"
        "no yearly cost, minimum area 80 m².\n"
        "\n"
        "Offer BetaCraft (valid until 2026-05-01, EXPIRED): lump 3000, shipping 0.\n"
        "\n"
        "Offer NordStunden: 45 EUR/h × 80 h + materials 900 + shipping 150, plus service "
        "200 EUR/year,\n"
        "minimum 60 hours.\n"
    ),
}


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


def set_system(data: dict[str, Any], text: str) -> None:
    for msg in data["messages"]:
        if msg.get("role") == "system":
            msg["content"] = text
            return
    raise SystemExit(f"{data['id']}: no system message")


def edit_case(suite: str, case_id: str, text: str) -> None:
    path = case_path(suite, case_id)
    guid, data = load_case(path)
    set_system(data, text)
    save_case(path, guid, data)


def bump_suite(suite: str) -> None:
    path = ROOT / "suites" / suite / "suite.yaml"
    manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
    manifest["version"] = CONTENT_VERSION
    path.write_text(_dump(manifest), encoding="utf-8")


def fix_callback() -> None:
    for case_id, text in CALLBACK_SYSTEM.items():
        edit_case("sme-dialog-v0.1", case_id, text)


def fix_policy() -> None:
    for case_id, text in POLICY_SYSTEM.items():
        edit_case("sme-expert-v0.1", case_id, text)


def fix_tco_fixtures() -> None:
    fixtures = ROOT / "suites" / "sme-expert-v0.1" / "fixtures"
    for name, text in TCO_FIXTURES.items():
        (fixtures / name).write_text(text, encoding="utf-8")


def main() -> None:
    fix_callback()
    fix_policy()
    fix_tco_fixtures()
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
