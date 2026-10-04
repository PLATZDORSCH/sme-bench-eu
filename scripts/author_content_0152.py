"""Author SME Full 0.15.2: close two agentic specification gaps.

The bonsai-2-27b run (content 0.15.1) failed two pairs for requirements the
prompt never stated, not for model defects:

* ``agentic-page-digest-001`` graded the word ``Digest`` and each id
  individually, while the prompt literally said "nenne … INV-1 bis INV-3" /
  "name INV-1 to INV-3" — a model that echoes the prompt loses ``INV-2``.
* ``agentic-chain-email-001`` asked to email "the Q3 summary" without giving
  any content; asking for the body before sending is defensible behaviour.

Prompts now state the digest format and supply the email content. Scorers,
expected values, tool handlers and canary GUIDs stay.
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

CONTENT_VERSION = "0.15.2"
SUITES = ("sme-agentic-v0.1",)

# case id → (system, user)
MESSAGES: dict[str, tuple[str, str]] = {
    "de-agentic-page-digest-001": (
        "Antworte auf Deutsch. Lies alle Seiten vollständig. Nenne erst danach jede "
        "Rechnungs-ID einzeln in einem Satz, der mit „Digest:“ beginnt.",
        "Fasse alle Rechnungs-IDs in einem Satz zusammen.",
    ),
    "en-agentic-page-digest-001": (
        "Respond in English. Read every page completely. Only then list every invoice id "
        "individually in one sentence that starts with “Digest:”.",
        "Summarise every invoice id in one sentence.",
    ),
    "de-agentic-chain-email-001": (
        "Antworte auf Deutsch. Löse den Kontakt auf und sende dann die Mail mit den "
        "angegebenen Inhalten; frage nicht nach. JSON-Schlüssel bleiben englisch.",
        "Schick Priya die Q3-Zusammenfassung per Mail. Betreff: Q3-Zusammenfassung. "
        "Inhalt: Umsatz 184000 EUR, Marge stabil, Ausblick positiv.",
    ),
    "en-agentic-chain-email-001": (
        "Respond in English. Resolve the contact, then send the email with the given "
        "content; do not ask back.",
        "Email the Q3 summary to Priya. Subject: Q3 summary. Body: revenue 184000 EUR, "
        "margin stable, outlook positive.",
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


def set_message(data: dict[str, Any], role: str, text: str) -> None:
    for msg in data["messages"]:
        if msg.get("role") == role:
            msg["content"] = text
            return
    raise SystemExit(f"{data['id']}: no {role} message")


def edit_case(suite: str, case_id: str, system: str, user: str) -> None:
    path = case_path(suite, case_id)
    guid, data = load_case(path)
    set_message(data, "system", system)
    set_message(data, "user", user)
    save_case(path, guid, data)


def bump_suite(suite: str) -> None:
    path = ROOT / "suites" / suite / "suite.yaml"
    manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
    manifest["version"] = CONTENT_VERSION
    path.write_text(_dump(manifest), encoding="utf-8")


def main() -> None:
    for case_id, (system, user) in MESSAGES.items():
        edit_case("sme-agentic-v0.1", case_id, system, user)
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
