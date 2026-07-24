"""Non-destructive regrade: copy attempts and re-score with current suite definition."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from sme_bench import __version__
from sme_bench.config import SCORING_SPEC_VERSION
from sme_bench.fingerprints import build_task_fingerprints
from sme_bench.models import AttemptResult, BenchmarkTask
from sme_bench.reporters.csv_reporter import write_attempts_csv
from sme_bench.reporters.failures import write_failures_reports, write_success_reports
from sme_bench.reporters.json_reporter import write_summary_json
from sme_bench.reporters.markdown import write_summary_reports
from sme_bench.scorers.base import known_scorer_names
from sme_bench.scoring import apply_partial_grade, evaluate_attempt
from sme_bench.statistics import aggregate, dedupe_attempts
from sme_bench.task_loader import LoadedSuite, load_suite_from_metadata
from sme_bench.utils import is_thinking_dump, separate_thinking_content

CompatStatus = Literal["regrade_ok", "rerun_required", "new_case", "missing_in_source"]


@dataclass
class TaskCompat:
    task_id: str
    status: CompatStatus
    reason: str = ""


@dataclass
class RegradePlan:
    source_dir: Path
    target_dir: Path
    tasks: list[TaskCompat] = field(default_factory=list)

    @property
    def regrade_ok(self) -> list[str]:
        return [t.task_id for t in self.tasks if t.status == "regrade_ok"]

    @property
    def rerun_required(self) -> list[str]:
        return [t.task_id for t in self.tasks if t.status == "rerun_required"]

    @property
    def new_cases(self) -> list[str]:
        return [t.task_id for t in self.tasks if t.status == "new_case"]

    @property
    def blocking_reruns(self) -> list[str]:
        source_ids = {a.task_id for a in _load_attempts(self.source_dir)}
        return [
            t.task_id
            for t in self.tasks
            if t.status == "rerun_required" and t.task_id in source_ids
        ]

    @property
    def can_proceed(self) -> bool:
        return bool(self.regrade_ok) and not self.blocking_reruns


def _load_legacy_input_allowlist(path: Path | None) -> dict[str, str] | None:
    """Optional manifest: task_id → expected input fingerprint for legacy runs."""
    if path is None or not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    allowed = data.get("input_fingerprints") or data.get("tasks") or data
    if not isinstance(allowed, dict):
        raise ValueError("Compatibility manifest must be a JSON object of task_id → input hash")
    return {str(k): str(v) for k, v in allowed.items()}


def _source_input_fingerprints(meta: dict[str, Any]) -> dict[str, str]:
    stored = meta.get("task_fingerprints") or {}
    if isinstance(stored, dict):
        out: dict[str, str] = {}
        for task_id, fp in stored.items():
            if isinstance(fp, dict) and "input" in fp:
                out[str(task_id)] = str(fp["input"])
            elif isinstance(fp, str):
                out[str(task_id)] = fp
        if out:
            return out
    return {}


def validate_report_rescore(
    *,
    attempts: list[AttemptResult],
    loaded: LoadedSuite | None,
    source_meta: dict[str, Any],
) -> None:
    """Raise ``ValueError`` when ``report --rescore`` would be unsafe.

    Requires a loaded suite, every attempt task id present in that suite, and
    matching input fingerprints for all rescored tasks.
    """
    if loaded is None:
        raise ValueError("Cannot --rescore: suite could not be loaded from run metadata")

    tasks_by_id = {task.id: task for task in loaded.tasks}
    missing = sorted({a.task_id for a in attempts} - set(tasks_by_id))
    if missing:
        preview = ", ".join(missing[:12])
        more = "" if len(missing) <= 12 else f" (+{len(missing) - 12} more)"
        raise ValueError(f"Cannot --rescore: unknown task ids in attempts: {preview}{more}")

    source_fps = _source_input_fingerprints(source_meta)
    if not source_fps:
        raise ValueError(
            "Cannot --rescore: metadata lacks task_fingerprints input hashes; "
            "use `sme-bench regrade` for scored copies instead"
        )

    current_fps = build_task_fingerprints(loaded.tasks)
    mismatched = sorted(
        task_id
        for task_id in {a.task_id for a in attempts}
        if source_fps.get(task_id) != current_fps[task_id]["input"]
    )
    if mismatched:
        preview = ", ".join(mismatched[:12])
        more = "" if len(mismatched) <= 12 else f" (+{len(mismatched) - 12} more)"
        raise ValueError(
            "Cannot --rescore: input fingerprints changed for "
            f"{preview}{more}; rerun those tasks or use `sme-bench regrade`"
        )


def build_regrade_plan(
    *,
    source_dir: Path,
    loaded: LoadedSuite,
    source_meta: dict[str, Any],
    legacy_allowlist: Path | None = None,
) -> RegradePlan:
    target_dir = source_dir  # placeholder; caller sets real target
    plan = RegradePlan(source_dir=source_dir, target_dir=target_dir)
    current_fps = build_task_fingerprints(loaded.tasks)
    source_fps = _source_input_fingerprints(source_meta)
    allowlist = _load_legacy_input_allowlist(legacy_allowlist)

    source_task_ids = {a.task_id for a in _load_attempts(source_dir)}

    for task in loaded.tasks:
        cur_in = current_fps[task.id]["input"]
        if task.id in source_fps:
            if source_fps[task.id] == cur_in:
                plan.tasks.append(TaskCompat(task.id, "regrade_ok"))
            else:
                plan.tasks.append(
                    TaskCompat(
                        task.id,
                        "rerun_required",
                        "input fingerprint changed since source run",
                    )
                )
        elif allowlist and task.id in allowlist:
            if allowlist[task.id] == cur_in:
                plan.tasks.append(TaskCompat(task.id, "regrade_ok", "legacy allowlist"))
            else:
                plan.tasks.append(
                    TaskCompat(
                        task.id,
                        "rerun_required",
                        "input differs from compatibility manifest",
                    )
                )
        elif task.id in source_task_ids:
            plan.tasks.append(
                TaskCompat(
                    task.id,
                    "rerun_required",
                    "no stored input fingerprint; legacy run",
                )
            )
        else:
            plan.tasks.append(TaskCompat(task.id, "new_case", "not present in source run"))

    for tid in sorted(source_task_ids):
        if tid not in current_fps:
            plan.tasks.append(TaskCompat(tid, "missing_in_source", "removed from suite"))

    return plan


def _rescore_source_text(attempt: AttemptResult) -> str:
    reasoning = attempt.reasoning_text or ""
    output = attempt.output_text or ""
    if output and output != reasoning and not is_thinking_dump(output):
        return output
    if is_thinking_dump(output):
        return output
    if reasoning and (not output or output == reasoning) and is_thinking_dump(reasoning):
        return reasoning
    return output


def rescore_attempt(attempt: AttemptResult, task: BenchmarkTask) -> AttemptResult:
    if attempt.infrastructure_error:
        return attempt
    source = _rescore_source_text(attempt)
    answer_text, reasoning = separate_thinking_content(source)
    score_results, weighted, effective, passed, partial, critical, parsed = evaluate_attempt(
        task, answer_text
    )
    updates: dict[str, Any] = {
        "parsed_output": parsed,
        "score_results": score_results,
        "weighted_score": weighted,
        "effective_score": effective,
        "passed": passed,
        "partial": partial,
        "critical_failure": critical,
        "output_text": answer_text,
    }
    if reasoning:
        updates["reasoning_text"] = reasoning
    elif is_thinking_dump(source) and not answer_text:
        updates["reasoning_text"] = source
    return attempt.model_copy(update=updates)


def _load_attempts(run_dir: Path) -> list[AttemptResult]:
    path = run_dir / "attempts.jsonl"
    if not path.exists():
        return []
    attempts: list[AttemptResult] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                attempts.append(AttemptResult.model_validate(json.loads(line)))
    return dedupe_attempts(attempts)


def format_compat_report(plan: RegradePlan) -> str:
    lines = [
        f"Source: {plan.source_dir}",
        f"Regrade OK: {len(plan.regrade_ok)}",
        f"Rerun required: {len(plan.rerun_required)}",
        f"New cases: {len(plan.new_cases)}",
        "",
    ]
    for item in sorted(plan.tasks, key=lambda t: (t.status, t.task_id)):
        suffix = f" — {item.reason}" if item.reason else ""
        lines.append(f"  [{item.status}] {item.task_id}{suffix}")
    return "\n".join(lines)


def regrade_run(
    *,
    source_dir: Path,
    target_dir: Path,
    legacy_allowlist: Path | None = None,
    write_reports: bool = True,
) -> tuple[Path, RegradePlan]:
    """Copy a run, re-score compatible attempts; source directory is never modified."""
    source_dir = source_dir.resolve()
    target_dir = target_dir.resolve()
    if target_dir.exists() and any(target_dir.iterdir()):
        raise FileExistsError(f"Target directory not empty: {target_dir}")

    meta_path = source_dir / "metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Missing {meta_path}")
    source_meta = json.loads(meta_path.read_text(encoding="utf-8"))

    loaded = load_suite_from_metadata(
        source_meta,
        known_scorers=known_scorer_names(),
        resolve_fixtures=True,
    )
    if loaded is None:
        raise ValueError("Could not load suite from source metadata")

    plan = build_regrade_plan(
        source_dir=source_dir,
        loaded=loaded,
        source_meta=source_meta,
        legacy_allowlist=legacy_allowlist,
    )
    plan.target_dir = target_dir

    if not plan.can_proceed:
        return target_dir, plan

    target_dir.mkdir(parents=True, exist_ok=True)
    ok_ids = set(plan.regrade_ok)
    tasks_by_id = {t.id: t for t in loaded.tasks}

    for spec_task in loaded.tasks:
        for spec in spec_task.scorers:
            if spec.type == "json_schema":
                schema_ref = spec.params.get("schema")
                if isinstance(schema_ref, str) and Path(schema_ref).is_absolute():
                    spec.params.setdefault("_suite_dir", str(Path(schema_ref).parents[1]))
                else:
                    spec.params.setdefault("_suite_dir", str(loaded.directory))

    rescored: list[AttemptResult] = []
    for attempt in _load_attempts(source_dir):
        if attempt.task_id not in ok_ids:
            continue
        task = tasks_by_id.get(attempt.task_id)
        if task is None:
            continue
        updated = rescore_attempt(attempt, task)
        updated = apply_partial_grade(updated, task)
        rescored.append(updated)

    attempts_path = target_dir / "attempts.jsonl"
    with attempts_path.open("w", encoding="utf-8") as handle:
        for attempt in rescored:
            handle.write(attempt.model_dump_json() + "\n")

    new_meta = dict(source_meta)
    # A regrade can itself be used as the source for a newer content line.
    # Supersession belongs to the source run and must not leak into the target.
    new_meta.pop("superseded_by", None)
    new_meta.pop("superseded_reason", None)
    new_meta.update(
        {
            "run_id": target_dir.name,
            "regraded_from": str(source_dir),
            "regraded_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "regrade_sme_bench_version": __version__,
            "source_suite_hash": source_meta.get("suite_hash"),
            "suite_hash": loaded.suite_hash,
            "suite_version": loaded.manifest.version,
            "task_fingerprints": build_task_fingerprints(loaded.tasks),
            "scoring_spec_version": SCORING_SPEC_VERSION,
            "inference_preserved_from": str(source_dir),
            "status": "regraded",
        }
    )
    if loaded.member_suites:
        new_meta["member_suites"] = loaded.member_suites
    (target_dir / "metadata.json").write_text(
        json.dumps(new_meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    if write_reports and rescored:
        weights = loaded.manifest.category_weights
        summary = aggregate(rescored, category_weights=weights)
        summary["run_id"] = target_dir.name
        summary["model"] = new_meta.get("model", "")
        summary["suite_id"] = new_meta.get("suite_id", "")
        summary["suite_version"] = loaded.manifest.version
        summary["regraded_from"] = str(source_dir)
        write_summary_json(target_dir / "summary.json", summary)
        write_summary_reports(
            target_dir,
            summary,
            model=str(summary.get("model") or target_dir.name),
        )
        write_attempts_csv(target_dir / "attempts.csv", rescored)
        report_kwargs = {
            "model": str(summary.get("model") or target_dir.name),
            "suite_id": str(summary.get("suite_id") or ""),
            "suite_version": loaded.manifest.version,
            "tasks_by_id": tasks_by_id,
        }
        write_failures_reports(target_dir, rescored, **report_kwargs)
        write_success_reports(target_dir, rescored, **report_kwargs)

    return target_dir, plan


def write_compatibility_manifest(loaded: LoadedSuite, output: Path) -> Path:
    """Write baseline input fingerprints for legacy regrade."""
    fps = build_task_fingerprints(loaded.tasks)
    payload = {
        "schema_version": "1.0",
        "description": "Baseline input fingerprints for regrade / partial merge",
        "suite_id": loaded.manifest.id,
        "suite_version": loaded.manifest.version,
        "suite_hash": loaded.suite_hash,
        "input_fingerprints": {task_id: fp["input"] for task_id, fp in fps.items()},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output


def _inference_signature(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": meta.get("model"),
        "served_model_name": meta.get("served_model_name"),
        "base_url": meta.get("base_url"),
        "seed": meta.get("seed"),
        "repeats": meta.get("repeats"),
        "max_tokens_multiplier": meta.get("max_tokens_multiplier"),
        "max_tokens_floor": meta.get("max_tokens_floor"),
        "extra_body": meta.get("extra_body"),
    }


def merge_partial_runs(
    *,
    base_dir: Path,
    delta_dirs: list[Path],
    target_dir: Path,
    loaded: LoadedSuite,
    write_reports: bool = True,
) -> tuple[Path, dict[str, Any]]:
    """Merge compatible attempt sets into a run covering the current task ID set.

    Requires matching model/seed/repeats/generation settings. Target attempts must
    cover every current task id with matching input fingerprints when present.
    """
    base_dir = base_dir.resolve()
    target_dir = target_dir.resolve()
    if target_dir.exists() and any(target_dir.iterdir()):
        raise FileExistsError(f"Target directory not empty: {target_dir}")

    base_meta = json.loads((base_dir / "metadata.json").read_text(encoding="utf-8"))
    base_sig = _inference_signature(base_meta)
    current_fps = build_task_fingerprints(loaded.tasks)
    required_ids = {t.id for t in loaded.tasks}
    repeats = base_meta.get("repeats")
    if not isinstance(repeats, int) or isinstance(repeats, bool) or repeats <= 0:
        raise ValueError("Base run metadata.repeats must be a positive integer")
    required_keys = {(task_id, repeat) for task_id in required_ids for repeat in range(repeats)}

    sources = [base_dir, *[d.resolve() for d in delta_dirs]]
    by_key: dict[tuple[str, int], AttemptResult] = {}
    source_map: dict[str, str] = {}

    for src in sources:
        meta = json.loads((src / "metadata.json").read_text(encoding="utf-8"))
        sig = _inference_signature(meta)
        mismatches = {
            k: (base_sig.get(k), sig.get(k)) for k in base_sig if base_sig.get(k) != sig.get(k)
        }
        if mismatches:
            raise ValueError(f"Inference settings mismatch for {src}: {mismatches}")
        src_fps = _source_input_fingerprints(meta)
        if not src_fps:
            raise ValueError(f"Source run has no task input fingerprints: {src}")
        for attempt in _load_attempts(src):
            if attempt.task_id not in required_ids:
                continue
            expected_fp = current_fps.get(attempt.task_id, {}).get("input")
            stored_fp = src_fps.get(attempt.task_id)
            if stored_fp is None:
                raise ValueError(f"Missing input fingerprint for {attempt.task_id} in {src.name}")
            # Changed historical attempts are intentionally skipped; a compatible
            # delta run must provide their exact task×repeat keys.
            if expected_fp and stored_fp != expected_fp:
                continue
            if attempt.repeat_index < 0 or attempt.repeat_index >= repeats:
                raise ValueError(
                    f"Unexpected repeat index for {attempt.task_id} in {src.name}: "
                    f"{attempt.repeat_index} (repeats={repeats})"
                )
            key = (attempt.task_id, attempt.repeat_index)
            # Later sources win (base first, then deltas) so changed-input
            # attempts from a delta replace stale base attempts.
            by_key[key] = attempt
            source_map[f"{attempt.task_id}::{attempt.repeat_index}"] = str(src)

    missing = sorted(required_keys - set(by_key))
    if missing:
        rendered = [f"{task_id}#{repeat}" for task_id, repeat in missing[:20]]
        raise ValueError(
            "Merged run incomplete; missing task/repeat keys: "
            + ", ".join(rendered)
            + (f" (+{len(missing) - 20} more)" if len(missing) > 20 else "")
        )

    target_dir.mkdir(parents=True, exist_ok=True)
    merged_raw = [by_key[k] for k in sorted(by_key)]

    tasks_by_id = {t.id: t for t in loaded.tasks}
    for spec_task in loaded.tasks:
        for spec in spec_task.scorers:
            if spec.type == "json_schema":
                schema_ref = spec.params.get("schema")
                if isinstance(schema_ref, str) and Path(schema_ref).is_absolute():
                    spec.params.setdefault("_suite_dir", str(Path(schema_ref).parents[1]))
                else:
                    # Member suites already stamp ``_suite_dir`` during load.
                    spec.params.setdefault("_suite_dir", str(loaded.directory))

    merged: list[AttemptResult] = []
    for attempt in merged_raw:
        task = tasks_by_id.get(attempt.task_id)
        if task is None:
            raise ValueError(f"Merged attempt references unknown task: {attempt.task_id}")
        updated = rescore_attempt(attempt, task)
        updated = apply_partial_grade(updated, task)
        merged.append(updated)

    with (target_dir / "attempts.jsonl").open("w", encoding="utf-8") as handle:
        for attempt in merged:
            handle.write(attempt.model_dump_json() + "\n")

    new_meta = dict(base_meta)
    new_meta.pop("superseded_by", None)
    new_meta.pop("superseded_reason", None)
    new_meta.update(
        {
            "run_id": target_dir.name,
            "merged_from": [str(s) for s in sources],
            "merged_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "merge_sme_bench_version": __version__,
            "suite_hash": loaded.suite_hash,
            "suite_version": loaded.manifest.version,
            "task_fingerprints": current_fps,
            "scoring_spec_version": SCORING_SPEC_VERSION,
            "task_source_map": source_map,
            "status": "merged",
        }
    )
    if loaded.member_suites:
        new_meta["member_suites"] = loaded.member_suites
    (target_dir / "metadata.json").write_text(
        json.dumps(new_meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (target_dir / "merge-manifest.json").write_text(
        json.dumps(
            {
                "required_task_ids": sorted(required_ids),
                "required_attempt_keys": [
                    f"{task_id}::{repeat}" for task_id, repeat in sorted(required_keys)
                ],
                "sources": [str(s) for s in sources],
                "task_source_map": source_map,
                "suite_version": loaded.manifest.version,
                "rescored": True,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    if write_reports and merged:
        summary = aggregate(merged, category_weights=loaded.manifest.category_weights)
        summary["run_id"] = target_dir.name
        summary["model"] = new_meta.get("model", "")
        summary["suite_id"] = new_meta.get("suite_id", "")
        summary["suite_version"] = loaded.manifest.version
        summary["merged_from"] = new_meta["merged_from"]
        write_summary_json(target_dir / "summary.json", summary)
        write_summary_reports(
            target_dir,
            summary,
            model=str(summary.get("model") or target_dir.name),
        )
        write_attempts_csv(target_dir / "attempts.csv", merged)
        report_kwargs = {
            "model": str(summary.get("model") or target_dir.name),
            "suite_id": str(summary.get("suite_id") or ""),
            "suite_version": loaded.manifest.version,
            "tasks_by_id": tasks_by_id,
        }
        write_failures_reports(target_dir, merged, **report_kwargs)
        write_success_reports(target_dir, merged, **report_kwargs)

    return target_dir, new_meta
