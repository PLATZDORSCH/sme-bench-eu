#!/usr/bin/env python3
"""Export deterministic input fingerprints from an explicit historical Git ref."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tarfile
import tempfile
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sme_bench.fingerprints import build_task_fingerprints  # noqa: E402
from sme_bench.scorers.base import known_scorer_names  # noqa: E402
from sme_bench.task_loader import load_suite  # noqa: E402

BASELINE_REF = "9ec61a5"
DEFAULT_OUTPUT = ROOT / "suites/compatibility/regrade-0.2.0-baseline.json"


def export_manifest(*, git_ref: str, output: Path) -> dict[str, object]:
    """Build a stable manifest from *git_ref* without consulting the working tree."""
    commit = subprocess.run(
        ["git", "rev-parse", "--verify", f"{git_ref}^{{commit}}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    merged: dict[str, str] = {}
    suite_meta: list[dict[str, str]] = []

    for suite_path in sorted((ROOT / "suites").glob("sme-*-v0.1")):
        rel = suite_path.relative_to(ROOT)
        proc = subprocess.run(
            ["git", "archive", commit, str(rel)],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            with tarfile.open(fileobj=BytesIO(proc.stdout), mode="r:") as archive:
                archive.extractall(tmp_root, filter="data")
            archived = tmp_root / rel
            loaded = load_suite(archived, known_scorers=known_scorer_names(), resolve_fixtures=True)
            errors = [i for i in loaded.issues if i.severity == "error"]
            if errors:
                raise RuntimeError(f"{rel}: {errors[0].message}")
            fps = build_task_fingerprints(loaded.tasks)
            for task_id, fp in fps.items():
                merged[task_id] = fp["input"]
            suite_meta.append({"suite_id": loaded.manifest.id, "task_count": str(len(fps))})

    payload: dict[str, object] = {
        "schema_version": "1.0",
        "description": "Immutable input fingerprints for SME Full content 0.2.0",
        "source_ref": git_ref,
        "source_commit": commit,
        "member_suites": suite_meta,
        "input_fingerprints": merged,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    output.write_text(rendered, encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ref",
        default=BASELINE_REF,
        help=f"Historical Git ref to archive (default: {BASELINE_REF})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Manifest path (default: {DEFAULT_OUTPUT.relative_to(ROOT)})",
    )
    args = parser.parse_args(argv)
    payload = export_manifest(git_ref=args.ref, output=args.output.resolve())
    fingerprints = payload["input_fingerprints"]
    if not isinstance(fingerprints, dict):
        raise RuntimeError("Exporter produced invalid input_fingerprints")
    count = len(fingerprints)
    print(f"Wrote {count} task fingerprints to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
