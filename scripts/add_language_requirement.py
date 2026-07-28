"""Add the explicit language requirement and `language` scorer to every case.

Content 0.9.0 makes language compliance a *stated* requirement instead of an
unwritten one. Grading a German case against German expected values while the
prompt never asked for German is a specification gap, so the instruction goes
into the prompt and the check becomes an explicit scorer.

The scorer carries ``weight: 0`` with ``must_pass: true``. Any positive weight
would renormalise every other scorer (see ``evaluate_attempt``) and silently
dilute real errors, which would flip unrelated near-miss attempts to passing.

Idempotent: re-running leaves already migrated cases untouched.

Usage:
    python scripts/add_language_requirement.py [--check]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]

# JSON keys such as ``missing_fields`` and ``cost_center`` are English by design
# in both language variants, so the instruction scopes itself to text values.
INSTRUCTIONS = {
    ("de-DE", "json"): "Formuliere alle Textwerte auf Deutsch; JSON-Schlüssel bleiben unverändert.",
    ("de-DE", "text"): "Antworte auf Deutsch.",
    ("en-GB", "json"): "Write all text values in English; keep JSON keys unchanged.",
    ("en-GB", "text"): "Respond in English.",
    ("en-US", "json"): "Write all text values in English; keep JSON keys unchanged.",
    ("en-US", "text"): "Respond in English.",
}

# Fields whose content is not a language contract. ``reasons`` on offer
# comparison holds language-neutral tokens such as ``lower_than_beta_870`` and
# is not scored by any other scorer. Injection and security cases need no entry
# here: they are picked up by the ``forbidden_terms`` alignment below, which
# already excludes ``reason`` because a refusal legitimately quotes the English
# payload it refused.
EXCLUDE_BY_TASK_TYPE = {
    "offer_comparison": ["reasons"],
}


def _system_index(messages: list[dict[str, Any]]) -> int | None:
    for index, message in enumerate(messages):
        if message.get("role") == "system" and isinstance(message.get("content"), str):
            return index
    return None


def _exclude_fields(case: dict[str, Any]) -> list[str]:
    task_type = str(case.get("task_type") or "")
    if task_type in EXCLUDE_BY_TASK_TYPE:
        return EXCLUDE_BY_TASK_TYPE[task_type]
    # Fall back to the field set ``forbidden_terms`` already excludes, so both
    # gates stay aligned when a new case reuses that pattern.
    for spec in case.get("scorers") or []:
        if spec.get("type") == "forbidden_terms":
            excluded = (spec.get("params") or {}).get("exclude_fields")
            if isinstance(excluded, list) and excluded:
                return [str(name) for name in excluded]
    return []


def migrate(path: Path) -> tuple[bool, str]:
    """Return ``(changed, note)`` for one case file."""
    raw = path.read_text(encoding="utf-8")
    case = yaml.safe_load(raw)
    if not isinstance(case, dict):
        return False, "not a mapping"

    messages = case.get("messages")
    if not isinstance(messages, list):
        return False, "no messages"
    index = _system_index(messages)
    if index is None:
        return False, "no system message"

    language = str(case.get("language") or "")
    fmt = str((case.get("generation") or {}).get("response_format") or "text")
    instruction = INSTRUCTIONS.get((language, fmt))
    if instruction is None:
        return False, f"no instruction for {language}/{fmt}"

    changed = False
    content = str(messages[index]["content"]).rstrip()
    if instruction not in content:
        messages[index]["content"] = f"{content} {instruction}"
        changed = True

    scorers = case.get("scorers")
    if not isinstance(scorers, list):
        return False, "no scorers"
    if not any(spec.get("type") == "language" for spec in scorers):
        spec: dict[str, Any] = {"type": "language", "weight": 0, "must_pass": True}
        excluded = _exclude_fields(case)
        if excluded:
            spec["params"] = {"exclude_fields": excluded}
        scorers.append(spec)
        changed = True

    if changed:
        path.write_text(
            yaml.safe_dump(case, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    return changed, "ok"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report cases that would change without writing",
    )
    args = parser.parse_args()

    paths = sorted((ROOT / "suites").glob("sme-*/cases/*/*.yaml"))
    changed: list[Path] = []
    skipped: list[tuple[Path, str]] = []
    for path in paths:
        if args.check:
            before = path.read_text(encoding="utf-8")
            would, note = migrate(path)
            if would:
                path.write_text(before, encoding="utf-8")
                changed.append(path)
            elif note != "ok":
                skipped.append((path, note))
            continue
        did, note = migrate(path)
        if did:
            changed.append(path)
        elif note != "ok":
            skipped.append((path, note))

    verb = "would change" if args.check else "changed"
    print(f"{len(changed)} of {len(paths)} cases {verb}")
    for path, note in skipped:
        print(f"  skipped {path.relative_to(ROOT)}: {note}")
    return 1 if (args.check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
