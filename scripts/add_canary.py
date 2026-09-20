"""Add sme-bench canary headers to suite case YAML files."""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sme_bench.qa import format_canary_header, parse_canary_header  # noqa: E402


def _ensure_suite_canary(suite_yaml: Path, guid: str | None) -> str:
    raw = suite_yaml.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    existing = data.get("canary") if isinstance(data, dict) else None
    if existing:
        return str(existing)
    chosen = guid or str(uuid.uuid4())
    if raw.endswith("\n"):
        updated = raw + f"canary: {chosen}\n"
    else:
        updated = raw + f"\ncanary: {chosen}\n"
    suite_yaml.write_text(updated, encoding="utf-8")
    return chosen


def _stamp_case(path: Path, guid: str, *, force: bool) -> bool:
    text = path.read_text(encoding="utf-8")
    current = parse_canary_header(text)
    header = format_canary_header(guid) + "\n"
    if current == guid:
        return False
    if current and not force:
        return False
    if current:
        lines = text.splitlines(keepends=True)
        for idx, line in enumerate(lines):
            if line.strip():
                lines[idx] = header
                path.write_text("".join(lines), encoding="utf-8")
                return True
    path.write_text(header + text.lstrip("\n"), encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "suites",
        nargs="*",
        type=Path,
        default=[ROOT / "suites"],
        help="Suite directories or the suites root (default: suites/)",
    )
    parser.add_argument("--guid", help="Canary GUID to write (default: existing or new UUID)")
    parser.add_argument("--force", action="store_true", help="Replace mismatched headers")
    args = parser.parse_args()

    changed = 0
    for root in args.suites:
        root = root.resolve()
        suite_yamls = [root / "suite.yaml"] if (root / "suite.yaml").exists() else list(root.glob("*/suite.yaml"))
        for suite_yaml in suite_yamls:
            guid = _ensure_suite_canary(suite_yaml, args.guid)
            suite_dir = suite_yaml.parent
            for case in sorted(suite_dir.glob("cases/**/*.yaml")):
                if _stamp_case(case, guid, force=args.force):
                    changed += 1
                    print(f"updated {case.relative_to(ROOT)}")
    print(f"{changed} case file(s) updated")


if __name__ == "__main__":
    main()
