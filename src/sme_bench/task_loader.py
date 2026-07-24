"""Load and validate benchmark suites and tasks."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from sme_bench.fingerprints import task_input_fingerprint
from sme_bench.models import BenchmarkTask, Message, SuiteManifest
from sme_bench.scorer_specs import validate_scorer_spec
from sme_bench.utils import (
    compute_suite_hash,
    resolve_safe_path,
    sha256_text,
    suite_path_for_metadata,
)


@dataclass
class ValidationIssue:
    path: str
    message: str
    severity: str = "error"


@dataclass
class LoadedSuite:
    directory: Path
    manifest: SuiteManifest
    tasks: list[BenchmarkTask]
    suite_hash: str
    issues: list[ValidationIssue] = field(default_factory=list)
    member_suites: list[dict[str, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)


# Default Full benchmark: Core + all domain packs (all v0.1).
FULL_SUITE_IDS: tuple[str, ...] = (
    "sme-core-v0.1",
    "sme-trades-v0.1",
    "sme-ecommerce-v0.1",
    "sme-financial-v0.1",
    "sme-hospitality-v0.1",
    "sme-logistics-v0.1",
    "sme-chains-v0.1",
)

# Older full-run metadata may reference Core v0.2 while only v0.1 is on disk.
_SUITE_DIR_ALIASES: dict[str, str] = {
    "sme-core-v0.2": "sme-core-v0.1",
}


def _resolve_suite_dir(root: Path, suite_id: str) -> Path:
    suite_dir = root / suite_id
    if suite_dir.is_dir():
        return suite_dir
    alias = _SUITE_DIR_ALIASES.get(suite_id)
    if alias:
        fallback = root / alias
        if fallback.is_dir():
            return fallback
    return suite_dir


def default_suites_root() -> Path:
    return Path("suites")


def load_full_benchmark(
    suites_root: Path | None = None,
    *,
    known_scorers: set[str] | None = None,
    resolve_fixtures: bool = True,
    suite_ids: tuple[str, ...] | None = None,
) -> LoadedSuite:
    """Load and merge Core + all domain packs into one virtual suite."""
    root = (suites_root or default_suites_root()).resolve()
    ids = suite_ids or FULL_SUITE_IDS
    issues: list[ValidationIssue] = []
    tasks: list[BenchmarkTask] = []
    seen_ids: set[str] = set()
    category_weights: dict[str, float] = {}
    members: list[dict[str, str]] = []
    hash_parts: list[str] = []

    for suite_id in ids:
        suite_dir = _resolve_suite_dir(root, suite_id)
        if not suite_dir.is_dir():
            issues.append(ValidationIssue(str(suite_dir), f"Suite directory not found: {suite_id}"))
            continue
        loaded = load_suite(
            suite_dir,
            known_scorers=known_scorers,
            resolve_fixtures=resolve_fixtures,
        )
        for issue in loaded.issues:
            issues.append(
                ValidationIssue(
                    f"{suite_id}/{issue.path}",
                    issue.message,
                    severity=issue.severity,
                )
            )
        for task in loaded.tasks:
            if task.id in seen_ids:
                issues.append(
                    ValidationIssue(
                        suite_id,
                        f"Duplicate task id across suites: {task.id}",
                    )
                )
                continue
            seen_ids.add(task.id)
            tasks.append(task)
        for cat, weight in loaded.manifest.category_weights.items():
            category_weights[cat] = max(category_weights.get(cat, 0.0), weight)
        members.append(
            {
                "id": loaded.manifest.id,
                "version": loaded.manifest.version,
                "path": str(suite_dir),
                "hash": loaded.suite_hash,
                "tasks": str(len(loaded.tasks)),
            }
        )
        hash_parts.append(f"{loaded.manifest.id}:{loaded.suite_hash}")

    for member in members:
        member["path"] = suite_path_for_metadata(Path(member["path"]))

    suite_hash = sha256_text("\n".join(hash_parts)) if hash_parts else ""
    manifest = SuiteManifest(
        schema_version="1.0",
        id="sme-full",
        name="SME Full Benchmark",
        version="0.8.0",
        description=(
            "Standard ranking pack: Core + Trades, E-Commerce, Financial, "
            "Hospitality, Logistics, Chains (196 DE/EN cases; curated noise/edge expansion)"
        ),
        languages=["de-DE", "en-GB"],
        default_repeats=3,
        default_pass_threshold=0.85,
        case_globs=[],
        category_weights=category_weights,
        provenance={
            "type": "synthetic",
            "notes": "Virtual suite assembled from released packs (default run target)",
            "member_suites": [m["id"] for m in members],
        },
    )
    # Cross-suite audits (fingerprints / variants) after merge
    _check_fingerprint_uniqueness(tasks, issues)
    _check_variant_message_divergence(tasks, issues)
    return LoadedSuite(
        directory=root,
        manifest=manifest,
        tasks=tasks,
        suite_hash=suite_hash,
        issues=issues,
        member_suites=members,
    )


def _safe_load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _discover_case_files(suite_dir: Path, globs: list[str]) -> list[Path]:
    files: set[Path] = set()
    for pattern in globs:
        files.update(suite_dir.glob(pattern))
    return sorted(p for p in files if p.is_file() and p.suffix in {".yaml", ".yml"})


def _resolve_messages(suite_dir: Path, task: BenchmarkTask, source: Path) -> BenchmarkTask:
    resolved: list[Message] = []
    for msg in task.messages:
        if msg.fixture is not None:
            fixture_path = resolve_safe_path(suite_dir, msg.fixture)
            if not fixture_path.exists():
                raise ValueError(f"{source}: fixture not found: {msg.fixture}")
            content = fixture_path.read_text(encoding="utf-8")
            resolved.append(Message(role=msg.role, content=content))
        else:
            resolved.append(msg)
    return task.model_copy(update={"messages": resolved})


def _scorer_identity(scorer: Any) -> str:
    """Canonical full scorer identity used only for exact duplicate detection."""
    payload = {
        "type": scorer.type,
        "weight": scorer.weight,
        "critical": scorer.critical,
        "must_pass": scorer.must_pass,
        "params": scorer.params or {},
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def _check_scorer_integrity(task: BenchmarkTask, rel: str, issues: list[ValidationIssue]) -> None:
    seen: set[str] = set()
    for scorer in task.scorers:
        key = _scorer_identity(scorer)
        if key in seen:
            issues.append(
                ValidationIssue(
                    rel,
                    f"Duplicate scorer specification: type={scorer.type!r}",
                )
            )
        seen.add(key)
        for svi in validate_scorer_spec(scorer, path=rel, strict=True):
            issues.append(ValidationIssue(svi.path, svi.message, severity=svi.severity))

    positive = [s.weight for s in task.scorers if s.weight > 0]
    if positive:
        total = sum(positive)
        if abs(total - 1.0) > 1e-6:
            issues.append(
                ValidationIssue(
                    rel,
                    f"Positive scorer weights must sum to 1.0, got {total:.6f}",
                )
            )


def _check_variant_review_gate(
    task: BenchmarkTask,
    rel: str,
    issues: list[ValidationIssue],
) -> None:
    variant_tags = {"noise-variant", "edge-variant"}
    if not variant_tags.intersection(task.tags) or task.review_status != "approved":
        return
    required = {"pair-reviewed", "golden-reviewed", "reference-calibrated"}
    missing = sorted(required - set(task.tags))
    if missing:
        issues.append(
            ValidationIssue(
                rel,
                "Approved generated variant is missing review evidence tags: "
                f"{missing}; keep it draft until review/calibration is complete",
            )
        )


def _variant_family(task_id: str) -> tuple[str, str] | None:
    """Return (stem, variant) for ids ending in -001/-002/-003."""
    match = re.search(r"^(.*)-(\d{3})$", task_id)
    if not match:
        return None
    return match.group(1), match.group(2)


def _check_fingerprint_uniqueness(
    tasks: list[BenchmarkTask],
    issues: list[ValidationIssue],
) -> None:
    by_fp: dict[str, list[str]] = {}
    for task in tasks:
        # Explicit repeat declaration opts out of uniqueness (future-proof).
        if "intentional-repeat" in (task.tags or []):
            continue
        fp = task_input_fingerprint(task)
        by_fp.setdefault(fp, []).append(task.id)
    for fp, ids in by_fp.items():
        if len(ids) > 1:
            issues.append(
                ValidationIssue(
                    ids[0],
                    "Identical input fingerprint across task ids "
                    f"{sorted(ids)} (fp={fp[:12]}…); declare tag "
                    "'intentional-repeat' only for true repeats",
                )
            )


def _check_variant_message_divergence(
    tasks: list[BenchmarkTask],
    issues: list[ValidationIssue],
) -> None:
    families: dict[str, dict[str, BenchmarkTask]] = {}
    for task in tasks:
        family = _variant_family(task.id)
        if not family:
            continue
        stem, variant = family
        # Scope by language so DE/EN pairs don't collide
        key = f"{task.language}::{stem}"
        families.setdefault(key, {})[variant] = task
    for key, variants in families.items():
        if len(variants) < 2:
            continue
        messages: dict[str, str] = {}
        for variant, task in variants.items():
            blob = "\n".join(f"{m.role}:{m.content or ''}" for m in task.messages)
            messages[variant] = blob
        # Any two variants with identical resolved messages → error
        seen: dict[str, str] = {}
        for variant, blob in messages.items():
            if blob in seen:
                issues.append(
                    ValidationIssue(
                        key,
                        f"Variants {seen[blob]} and {variant} have identical resolved messages",
                    )
                )
            else:
                seen[blob] = variant


def _check_shared_fixtures(
    tasks: list[BenchmarkTask],
    issues: list[ValidationIssue],
) -> None:
    """Flag when distinct variant ids unintentionally share the same fixture path."""
    by_fixture: dict[str, list[str]] = {}
    for task in tasks:
        for msg in task.messages:
            # After resolve, fixture is None and content is inlined; use raw if present
            fixture = getattr(msg, "fixture", None)
            if not fixture:
                continue
            by_fixture.setdefault(str(fixture), []).append(task.id)
    for fixture, ids in by_fixture.items():
        families = {_variant_family(i) for i in ids}
        stems = {f[0] for f in families if f}
        variants = {f[1] for f in families if f}
        if len(stems) == 1 and len(variants) > 1:
            issues.append(
                ValidationIssue(
                    fixture,
                    f"Fixture shared across variants {sorted(ids)}; each variant needs its own path",
                )
            )


def _check_pair_expected_and_risk(
    tasks: list[BenchmarkTask],
    issues: list[ValidationIssue],
) -> None:
    by_pair: dict[str, list[BenchmarkTask]] = {}
    for task in tasks:
        if task.pair_id:
            by_pair.setdefault(task.pair_id, []).append(task)
    for pair_id, pair_tasks in by_pair.items():
        languages = [t.language for t in pair_tasks]
        if len(pair_tasks) != 2 or set(languages) != {"de-DE", "en-GB"}:
            issues.append(
                ValidationIssue(
                    pair_id,
                    f"pair_id '{pair_id}' must contain exactly one de-DE and one en-GB task; "
                    f"got {languages}",
                )
            )
        risks = {t.risk for t in pair_tasks}
        if len(risks) > 1:
            issues.append(
                ValidationIssue(
                    pair_id,
                    f"pair_id '{pair_id}' has inconsistent risk levels: {sorted(risks)}",
                )
            )
        # Expected top-level keys should match when both are objects
        object_expected = [t for t in pair_tasks if isinstance(t.expected, dict)]
        if len(object_expected) >= 2:
            key_sets = [frozenset(t.expected.keys()) for t in object_expected]
            if len({frozenset(k) for k in key_sets}) > 1:
                issues.append(
                    ValidationIssue(
                        pair_id,
                        f"pair_id '{pair_id}' has inconsistent expected field coverage: "
                        f"{[sorted(k) for k in key_sets]}",
                    )
                )


def _check_pair_consistency(tasks: list[BenchmarkTask], issues: list[ValidationIssue]) -> None:
    by_pair: dict[str, list[BenchmarkTask]] = {}
    for task in tasks:
        if task.pair_id:
            by_pair.setdefault(task.pair_id, []).append(task)

    for pair_id, pair_tasks in by_pair.items():
        if len(pair_tasks) < 2:
            issues.append(
                ValidationIssue(
                    path=pair_tasks[0].id,
                    message=f"pair_id '{pair_id}' has fewer than 2 language variants",
                    severity="warning",
                )
            )
            continue
        types = {t.task_type for t in pair_tasks}
        diffs = {t.difficulty for t in pair_tasks}
        if len(types) > 1:
            issues.append(
                ValidationIssue(
                    path=pair_id,
                    message=f"pair_id '{pair_id}' has inconsistent task_type: {sorted(types)}",
                )
            )
        if len(diffs) > 1:
            issues.append(
                ValidationIssue(
                    path=pair_id,
                    message=f"pair_id '{pair_id}' has inconsistent difficulty: {sorted(diffs)}",
                )
            )
        # Comparable scorer weights: sum of positive weights within 0.05
        weight_sums = []
        for t in pair_tasks:
            weight_sums.append(sum(s.weight for s in t.scorers if s.weight > 0))
        if max(weight_sums) - min(weight_sums) > 0.05:
            issues.append(
                ValidationIssue(
                    path=pair_id,
                    message=(
                        f"pair_id '{pair_id}' has incomparable scorer weight sums: {weight_sums}"
                    ),
                )
            )
    _check_pair_expected_and_risk(tasks, issues)


def load_suite(
    suite_dir: Path,
    *,
    known_scorers: set[str] | None = None,
    resolve_fixtures: bool = True,
) -> LoadedSuite:
    suite_dir = suite_dir.resolve()
    issues: list[ValidationIssue] = []
    manifest_path = suite_dir / "suite.yaml"
    if not manifest_path.exists():
        issues.append(ValidationIssue(str(manifest_path), "suite.yaml not found"))
        empty = SuiteManifest(
            schema_version="1.0",
            id="invalid",
            name="invalid",
            version="0.0.0",
            languages=[],
        )
        return LoadedSuite(suite_dir, empty, [], "", issues)

    try:
        raw_manifest = _safe_load_yaml(manifest_path)
        manifest = SuiteManifest.model_validate(raw_manifest)
    except (yaml.YAMLError, ValidationError, TypeError, ValueError) as exc:
        issues.append(ValidationIssue(str(manifest_path), f"Invalid suite.yaml: {exc}"))
        empty = SuiteManifest(
            schema_version="1.0",
            id="invalid",
            name="invalid",
            version="0.0.0",
            languages=[],
        )
        return LoadedSuite(suite_dir, empty, [], "", issues)

    tasks: list[BenchmarkTask] = []
    unresolved_tasks: list[BenchmarkTask] = []
    seen_ids: set[str] = set()
    case_files = _discover_case_files(suite_dir, manifest.case_globs)

    for case_path in case_files:
        rel = str(case_path.relative_to(suite_dir))
        try:
            raw = _safe_load_yaml(case_path)
            task = BenchmarkTask.model_validate(raw)
            threshold_updates: dict[str, float] = {}
            if "pass_threshold" not in raw:
                threshold_updates["pass_threshold"] = manifest.default_pass_threshold
            if "partial_threshold" not in raw:
                threshold_updates["partial_threshold"] = manifest.default_partial_threshold
            if threshold_updates:
                task = task.model_copy(update=threshold_updates)
        except (yaml.YAMLError, ValidationError, TypeError, ValueError) as exc:
            issues.append(ValidationIssue(rel, str(exc)))
            continue

        if task.id in seen_ids:
            issues.append(ValidationIssue(rel, f"Duplicate task id: {task.id}"))
            continue
        seen_ids.add(task.id)

        if task.language not in manifest.languages:
            issues.append(
                ValidationIssue(
                    rel,
                    f"Language '{task.language}' not listed in suite languages",
                )
            )

        if known_scorers is not None:
            for scorer in task.scorers:
                if scorer.type not in known_scorers:
                    issues.append(ValidationIssue(rel, f"Unknown scorer type: {scorer.type}"))
        _check_scorer_integrity(task, rel, issues)
        _check_variant_review_gate(task, rel, issues)

        # Validate fixture paths exist and stay inside suite
        try:
            for msg in task.messages:
                if msg.fixture:
                    resolve_safe_path(suite_dir, msg.fixture)
            # Validate and absolutize schema refs for scorers
            for scorer in task.scorers:
                schema_ref = scorer.params.get("schema")
                if isinstance(schema_ref, str):
                    schema_path = resolve_safe_path(suite_dir, schema_ref)
                    if not schema_path.exists():
                        issues.append(ValidationIssue(rel, f"Schema not found: {schema_ref}"))
                    else:
                        scorer.params["schema"] = str(schema_path)
                        scorer.params["_suite_dir"] = str(suite_dir)

            unresolved = task
            if resolve_fixtures:
                task = _resolve_messages(suite_dir, task, case_path)
            tasks.append(task)
            unresolved_tasks.append(unresolved)
        except ValueError as exc:
            issues.append(ValidationIssue(rel, str(exc)))

    _check_pair_consistency(tasks, issues)
    _check_fingerprint_uniqueness(tasks, issues)
    _check_variant_message_divergence(tasks, issues)
    _check_shared_fixtures(unresolved_tasks, issues)
    suite_hash = compute_suite_hash(suite_dir, [t.id for t in tasks]) if tasks else ""
    return LoadedSuite(suite_dir, manifest, tasks, suite_hash, issues)


def filter_tasks(
    tasks: list[BenchmarkTask],
    *,
    languages: list[str] | None = None,
    categories: list[str] | None = None,
    difficulty: list[str] | None = None,
    tags: list[str] | None = None,
    task_ids: list[str] | None = None,
) -> list[BenchmarkTask]:
    result = tasks
    if task_ids:
        id_set = set(task_ids)
        unknown = sorted(id_set - {t.id for t in tasks})
        if unknown:
            preview = ", ".join(unknown[:10])
            suffix = f" (+{len(unknown) - 10} more)" if len(unknown) > 10 else ""
            raise ValueError(f"Unknown task id(s): {preview}{suffix}")
        duplicates = sorted({tid for tid in task_ids if task_ids.count(tid) > 1})
        if duplicates:
            raise ValueError(f"Duplicate task id(s): {', '.join(duplicates)}")
        result = [t for t in result if t.id in id_set]
    if languages:
        lang_set = set(languages)
        result = [t for t in result if t.language in lang_set]
    if categories:
        cat_set = set(categories)
        result = [t for t in result if t.category in cat_set]
    if difficulty:
        diff_set = set(difficulty)
        result = [t for t in result if t.difficulty in diff_set]
    if tags:
        tag_set = set(tags)
        result = [t for t in result if tag_set.intersection(t.tags)]
    return result


def load_suite_from_metadata(
    meta: dict[str, Any],
    *,
    known_scorers: set[str] | None = None,
    resolve_fixtures: bool = True,
) -> LoadedSuite | None:
    """Load a single suite or reassemble a ``--full`` multi-suite run."""
    from sme_bench.utils import resolve_suite_path

    members = meta.get("member_suites") or []
    if meta.get("suite_id") == "sme-full" or members:
        ids: list[str] = []
        for member in members:
            if isinstance(member, dict) and member.get("id"):
                ids.append(str(member["id"]))
        suite_ids = tuple(ids) if ids else FULL_SUITE_IDS
        return load_full_benchmark(
            known_scorers=known_scorers,
            resolve_fixtures=resolve_fixtures,
            suite_ids=suite_ids,
        )
    path = resolve_suite_path(meta)
    if path is None:
        return None
    return load_suite(
        path,
        known_scorers=known_scorers,
        resolve_fixtures=resolve_fixtures,
    )
