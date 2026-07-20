"""Load and validate benchmark suites and tasks."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from sme_bench.models import BenchmarkTask, Message, SuiteManifest
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
            issues.append(
                ValidationIssue(str(suite_dir), f"Suite directory not found: {suite_id}")
            )
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
        version="0.4.0",
        description=(
            "Standard ranking pack: Core + Trades, E-Commerce, Financial, "
            "Hospitality, Logistics, Chains (~156 cases)"
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

            if resolve_fixtures:
                task = _resolve_messages(suite_dir, task, case_path)
            tasks.append(task)
        except ValueError as exc:
            issues.append(ValidationIssue(rel, str(exc)))

    _check_pair_consistency(tasks, issues)
    suite_hash = compute_suite_hash(suite_dir, [t.id for t in tasks]) if tasks else ""
    return LoadedSuite(suite_dir, manifest, tasks, suite_hash, issues)


def filter_tasks(
    tasks: list[BenchmarkTask],
    *,
    languages: list[str] | None = None,
    categories: list[str] | None = None,
    difficulty: list[str] | None = None,
    tags: list[str] | None = None,
) -> list[BenchmarkTask]:
    result = tasks
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
