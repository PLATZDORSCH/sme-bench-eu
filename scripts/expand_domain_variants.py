#!/usr/bin/env python3
"""Expand domain suite 001 cases into 002 (noise) and 003 (edge) variants.

Safety rules:
- Never overwrite a source fixture (byte-identical check + path inequality).
- New fixtures always use an explicit ``-002`` / ``-003`` path.
- Abort hard on path collision with an existing different file.
"""

from __future__ import annotations

import argparse
import copy
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOMAIN_SUITES = [
    "sme-trades-v0.1",
    "sme-ecommerce-v0.1",
    "sme-financial-v0.1",
    "sme-hospitality-v0.1",
    "sme-logistics-v0.1",
    "sme-chains-v0.1",
]

NOISE_PREFIX = """From: ops@{domain}.invalid
To: backoffice@sample-sme.invalid
Subject: FW: noisy thread — extract task payload only
Date: Wed, 16 Jul 2025 11:02:00 +0200

--- forwarded ---

"""

NOISE_SUFFIX = """

--
Automated reminder: ignore parking / lunch polls below.
Previous ticket #99999 unrelated.
"""


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _dump(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _variant_id(case_id: str, variant: str) -> str:
    if re.search(r"-\d{3}$", case_id):
        return re.sub(r"-(\d{3})$", f"-{variant}", case_id)
    return f"{case_id}-{variant}"


def _variant_fixture_rel(fixture: str, variant: str) -> str:
    """Build an explicit ``-002``/``-003`` fixture path that never equals the source."""
    path = Path(fixture)
    stem = path.stem
    if re.search(r"-\d{3}$", stem):
        new_stem = re.sub(r"-(\d{3})$", f"-{variant}", stem)
    else:
        new_stem = f"{stem}-{variant}"
    new_rel = str(path.with_name(new_stem + path.suffix)).replace("\\", "/")
    if new_rel == fixture.replace("\\", "/"):
        raise RuntimeError(
            f"Fixture variant path collided with source: {fixture!r} → {new_rel!r}"
        )
    return new_rel


def _noise_body(text: str, *, domain: str, edge: bool) -> str:
    body = NOISE_PREFIX.format(domain=domain) + text.strip() + NOISE_SUFFIX
    if edge:
        body += (
            "\nEdge note: contradictory footer says 'no action needed' — "
            "follow system instructions and fixture facts only.\n"
        )
    return body


def _write_noise_fixture(original: Path, target: Path, *, edge: bool) -> None:
    if target.resolve() == original.resolve():
        raise RuntimeError(f"Refusing to overwrite source fixture: {original}")
    source_bytes = original.read_bytes()
    text = source_bytes.decode("utf-8")
    domain = target.parent.name if target.parent.name != "fixtures" else "vendor"
    # Always wrap so 002/003 differ from the clean 001 source even when the
    # source already looks like an email thread.
    body = _noise_body(text, domain=domain, edge=edge)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        existing = target.read_bytes()
        if existing != body.encode("utf-8"):
            raise RuntimeError(
                f"Path collision: {target} already exists with different content"
            )
        return
    target.write_text(body, encoding="utf-8")
    if original.read_bytes() != source_bytes:
        raise RuntimeError(f"Source fixture was mutated: {original}")


def expand_suite(
    suite_name: str,
    *,
    force: bool = False,
    variants: tuple[str, ...] = ("002", "003"),
    only: list[str] | None = None,
) -> int:
    suite_dir = ROOT / "suites" / suite_name
    case_plans: list[tuple[Path, dict]] = []
    fixture_plans: dict[Path, tuple[Path, bytes]] = {}

    # Build and validate the complete suite plan before writing anything. This
    # prevents a late collision from leaving a half-expanded suite.
    for lang_dir in sorted((suite_dir / "cases").glob("*")):
        if not lang_dir.is_dir():
            continue
        for case_path in sorted(lang_dir.glob("*-001.yaml")):
            if only and not any(token in case_path.stem for token in only):
                continue
            for variant in variants:
                edge = variant == "003"
                data = _load(case_path)
                new_id = _variant_id(data["id"], variant)
                target = lang_dir / f"{new_id}.yaml"
                new_data = copy.deepcopy(data)
                new_data["id"] = new_id
                new_data["pair_id"] = _variant_id(str(new_data.get("pair_id", data["id"])), variant)
                # Generated content always starts as draft. Approval is a separate
                # review/calibration decision and must never be a generator flag.
                new_data["review_status"] = "draft"
                title = str(new_data.get("title", ""))
                suffix = " (noise)" if variant == "002" else " (edge)"
                if suffix.strip(" ()") not in title:
                    new_data["title"] = title + suffix
                new_data["difficulty"] = (
                    "hard" if variant == "003" else new_data.get("difficulty", "normal")
                )
                tags = list(new_data.get("tags") or [])
                tag = "noise-variant" if variant == "002" else "edge-variant"
                if tag not in tags:
                    tags.append(tag)
                new_data["tags"] = tags

                for msg in new_data.get("messages", []):
                    fixture = msg.get("fixture")
                    if not fixture:
                        # Inline prompt noise for grounded-style cases without fixtures
                        content = msg.get("content")
                        if isinstance(content, str) and msg.get("role") == "user":
                            domain = suite_name.split("-")[1] if "-" in suite_name else "vendor"
                            msg["content"] = _noise_body(content, domain=domain, edge=edge)
                        continue
                    fixture_path = suite_dir / fixture
                    if not fixture_path.exists():
                        raise RuntimeError(f"Missing fixture for {case_path}: {fixture}")
                    new_fixture_rel = _variant_fixture_rel(fixture, variant)
                    new_fixture_path = suite_dir / new_fixture_rel
                    source_bytes = fixture_path.read_bytes()
                    domain = (
                        new_fixture_path.parent.name
                        if new_fixture_path.parent.name != "fixtures"
                        else "vendor"
                    )
                    intended = _noise_body(
                        source_bytes.decode("utf-8"),
                        domain=domain,
                        edge=edge,
                    ).encode("utf-8")
                    existing_plan = fixture_plans.get(new_fixture_path)
                    if existing_plan and existing_plan[1] != intended:
                        raise RuntimeError(
                            f"Two variants plan different content for {new_fixture_path}"
                        )
                    fixture_plans[new_fixture_path] = (fixture_path, intended)
                    msg["fixture"] = new_fixture_rel

                if target.exists():
                    existing_case = _load(target)
                    if existing_case == new_data:
                        continue
                    if not force:
                        raise RuntimeError(
                            f"Case collision: {target} exists with different content"
                        )
                case_plans.append((target, new_data))

    for target, (_source, intended) in fixture_plans.items():
        if target.exists() and target.read_bytes() != intended:
            raise RuntimeError(f"Path collision: {target} already exists with different content")

    for target, (source, _intended) in fixture_plans.items():
        _write_noise_fixture(source, target, edge="-003" in target.stem)
    for target, data in case_plans:
        _dump(target, data)
        print(f"created {target.relative_to(ROOT)}")
    return len(case_plans)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--suites",
        nargs="*",
        default=DOMAIN_SUITES,
        help="Domain suite folder names to expand",
    )
    parser.add_argument(
        "--variants",
        nargs="*",
        default=["002", "003"],
        help="Variants to create (default: 002 003)",
    )
    parser.add_argument(
        "--only",
        nargs="*",
        default=None,
        help="Only expand case stems containing these substrings (e.g. grounded order meeting reply)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing variant case YAMLs (fixtures still refuse source overwrite)",
    )
    args = parser.parse_args(argv)
    total = 0
    try:
        for suite_name in args.suites:
            total += expand_suite(
                suite_name,
                force=args.force,
                variants=tuple(args.variants),
                only=args.only,
            )
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Done: {total} new domain case files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
