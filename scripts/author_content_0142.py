"""Author SME Full 0.14.2: remove the residual ambiguity in ``dialog-clarify-001``.

The 0.14.1 rerun showed the model answering ``missing_field: delivery_address``:
the dialog never mentions an address, so it is as legitimately "missing" as the
date. The first user turn now states the delivery address, leaving only the
date open. Only ``sme-dialog-v0.1`` changes; canary GUIDs stay.
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

CONTENT_VERSION = "0.14.2"
SUITE = "sme-dialog-v0.1"

FIRST_TURN = {
    "de-dialog-clarify-001": (
        "Wir bestellen 40 Paletten Stretchfolie, Lieferung nach Hamburg, Hafenweg 9. Preis ok."
    ),
    "en-dialog-clarify-001": (
        "We order 40 pallets of stretch film, delivery to Hamburg, Hafenweg 9. Price is fine."
    ),
}


def _dump(data: dict) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)


def edit_case(path: Path, fn) -> None:
    guid = read_canary_guid(path)
    if not guid:
        raise SystemExit(f"{path}: missing canary header")
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    fn(data)
    path.write_text(format_canary_header(guid) + "\n" + _dump(data), encoding="utf-8")


def fix_clarify() -> None:
    for case_id, text in FIRST_TURN.items():
        lang = "de-DE" if case_id.startswith("de-") else "en-GB"
        path = ROOT / "suites" / SUITE / "cases" / lang / f"{case_id}.yaml"

        def _fix(data: dict[str, Any], *, text: str = text) -> None:
            users = [m for m in data["messages"] if m.get("role") == "user"]
            users[0]["content"] = text

        edit_case(path, _fix)


def main() -> None:
    fix_clarify()

    manifest_path = ROOT / "suites" / SUITE / "suite.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = CONTENT_VERSION
    manifest_path.write_text(_dump(manifest), encoding="utf-8")

    releases_path = ROOT / "suites/compatibility/releases.json"
    releases = json.loads(releases_path.read_text(encoding="utf-8"))
    if CONTENT_VERSION not in releases["released"]:
        releases["released"].append(CONTENT_VERSION)
    releases_path.write_text(json.dumps(releases, indent=2) + "\n", encoding="utf-8")

    known = known_scorer_names()
    suite = load_suite(ROOT / "suites" / SUITE, known_scorers=known)
    write_case_catalog(
        ROOT / "suites" / SUITE / "CASES.md",
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
