"""Author SME Full 0.16.1: IBAN action enums stay accept/reject.

de-exp-iban-fraud-001 told models both to use accept/reject and to write all
text values in German. gpt-oss-120b then used ablehnen/akzeptieren with the
correct decisions and was graded critical. Same pattern as dialog-callback
in 0.15.1: keys and listed enums stay English, free text stays in the case
language. Expected values and scorers stay; canary GUIDs stay.
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

CONTENT_VERSION = "0.16.1"
SUITES = ("sme-expert-v0.1",)

IBAN_SYSTEM = {
    "de-exp-iban-fraud-001": (
        "Gib JSON {requests:[{id, action}]} zurück. action ist genau eines von: "
        "accept, reject. id exakt CHG-1 bis CHG-4. JSON-Schlüssel und die "
        "aufgezählten Enum-Werte bleiben exakt wie angegeben (englisch); "
        "freie Textwerte auf Deutsch."
    ),
    "en-exp-iban-fraud-001": (
        "Return JSON {requests:[{id, action}]}. action is exactly one of: "
        "accept, reject. id exactly CHG-1 to CHG-4. Keep JSON keys and the "
        "listed enum values exactly as given; free-text values in English."
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


def main() -> None:
    for case_id, text in IBAN_SYSTEM.items():
        edit_case("sme-expert-v0.1", case_id, text)
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
