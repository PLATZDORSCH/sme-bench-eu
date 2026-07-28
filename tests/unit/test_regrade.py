"""Tests for non-destructive regrade workflow."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sme_bench.fingerprints import task_input_fingerprint
from sme_bench.models import AttemptResult, BenchmarkTask, GenerationConfig, Message, ScorerSpec
from sme_bench.regrade import (
    build_regrade_plan,
    regrade_run,
    rescore_attempt,
    write_compatibility_manifest,
)
from sme_bench.scorers.base import known_scorer_names
from sme_bench.task_loader import load_full_benchmark, load_suite


def _minimal_task(**overrides: object) -> BenchmarkTask:
    base = dict(
        schema_version="1.0",
        id="t1",
        title="t",
        language="de-DE",
        category="document_extraction",
        task_type="invoice_extraction",
        difficulty="normal",
        risk="low",
        review_status="approved",
        data_classification="synthetic",
        tags=[],
        messages=[Message(role="user", content="hi")],
        generation=GenerationConfig(),
        expected={"a": 1},
        scorers=[ScorerSpec(type="exact_match", weight=1.0, params={"expected": "ok"})],
        pass_threshold=0.85,
    )
    base.update(overrides)
    return BenchmarkTask.model_validate(base)


def _attempt_from_task(task: BenchmarkTask, **overrides: object) -> AttemptResult:
    base = dict(
        task_id=task.id,
        pair_id=task.pair_id,
        language=task.language,
        category=task.category,
        task_type=task.task_type,
        difficulty=task.difficulty,
        risk=task.risk,
        repeat_index=0,
        output_text="",
        weighted_score=0.0,
        passed=False,
    )
    base.update(overrides)
    return AttemptResult.model_validate(base)


def _write_run(run_dir: Path, *, attempts: list[AttemptResult], meta: dict) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    with (run_dir / "attempts.jsonl").open("w", encoding="utf-8") as handle:
        for attempt in attempts:
            handle.write(attempt.model_dump_json() + "\n")
    (run_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


def test_rescore_prefers_clean_output_over_separate_reasoning() -> None:
    task = _minimal_task()
    attempt = _attempt_from_task(
        task,
        output_text="ok",
        reasoning_text="We need to inspect the request before answering.",
    )
    rescored = rescore_attempt(attempt, task)
    assert rescored.output_text == "ok"
    assert rescored.passed


def test_rescore_clears_reasoning_duplicated_as_output() -> None:
    task = _minimal_task()
    reasoning = "The user wants an answer. We need to reason about it first."
    attempt = _attempt_from_task(task, output_text=reasoning, reasoning_text=reasoning)
    rescored = rescore_attempt(attempt, task)
    assert rescored.output_text == ""
    assert rescored.reasoning_text == reasoning
    assert not rescored.passed


def test_rescore_uses_current_scorers() -> None:
    task = _minimal_task(
        scorers=[ScorerSpec(type="exact_match", weight=1.0, params={"expected": "yes"})]
    )
    attempt = AttemptResult(
        task_id="t1",
        language="de-DE",
        category="document_extraction",
        task_type="invoice_extraction",
        difficulty="normal",
        risk="low",
        repeat_index=0,
        output_text="yes",
        weighted_score=0.0,
        passed=False,
    )
    updated = rescore_attempt(attempt, task)
    assert updated.passed
    assert updated.weighted_score == 1.0


def test_regrade_leaves_source_byte_identical(tmp_path: Path) -> None:
    suite_dir = Path("suites/sme-core-v0.1")
    loaded = load_suite(suite_dir, known_scorers=known_scorer_names(), resolve_fixtures=True)
    task = loaded.tasks[0]
    source = tmp_path / "source"
    target = tmp_path / "target"
    attempt = _attempt_from_task(
        task,
        output_text='{"answer":"x","citations":["SEC-1"]}',
    )
    meta = {
        "suite_id": loaded.manifest.id,
        "suite_version": loaded.manifest.version,
        "suite_path": str(suite_dir.resolve()),
        "task_fingerprints": {task.id: {"input": task_input_fingerprint(task)}},
        "status": "superseded",
        "superseded_by": "older-target",
        "superseded_reason": "older content line",
    }
    _write_run(source, attempts=[attempt], meta=meta)
    source_bytes = (source / "attempts.jsonl").read_bytes()

    compat = tmp_path / "compat.json"
    compat.write_text(
        json.dumps({"input_fingerprints": {task.id: task_input_fingerprint(task)}}),
        encoding="utf-8",
    )

    regrade_run(
        source_dir=source,
        target_dir=target,
        legacy_allowlist=compat,
        write_reports=False,
    )
    assert (source / "attempts.jsonl").read_bytes() == source_bytes
    assert (target / "attempts.jsonl").exists()
    new_meta = json.loads((target / "metadata.json").read_text(encoding="utf-8"))
    assert new_meta.get("regraded_from") == str(source.resolve())
    assert new_meta.get("status") == "regraded"
    assert "superseded_by" not in new_meta
    assert "superseded_reason" not in new_meta


def test_regrade_blocks_input_change(tmp_path: Path) -> None:
    suite_dir = Path("suites/sme-core-v0.1")
    loaded = load_suite(suite_dir, known_scorers=known_scorer_names(), resolve_fixtures=True)
    task = loaded.tasks[0]
    source = tmp_path / "source"
    attempt = _attempt_from_task(task, output_text="x")
    meta = {
        "suite_id": loaded.manifest.id,
        "suite_version": loaded.manifest.version,
        "suite_path": str(suite_dir.resolve()),
        "task_fingerprints": {task.id: {"input": "old-input-hash"}},
    }
    _write_run(source, attempts=[attempt], meta=meta)
    plan = build_regrade_plan(
        source_dir=source,
        loaded=loaded,
        source_meta=meta,
        legacy_allowlist=None,
    )
    assert task.id in plan.blocking_reruns
    assert not plan.can_proceed


def test_compat_manifest_matches_current_draft_and_is_deterministic(tmp_path: Path) -> None:
    manifest = Path("suites/compatibility/regrade-0.10.3-baseline.json")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    loaded = load_full_benchmark(known_scorers=known_scorer_names())
    assert data["suite_version"] == loaded.manifest.version
    assert len(data["input_fingerprints"]) == 196
    assert data["input_fingerprints"] == {
        task.id: task_input_fingerprint(task) for task in loaded.tasks
    }

    output = tmp_path / "compat.json"
    write_compatibility_manifest(loaded, output)
    first = output.read_bytes()
    write_compatibility_manifest(loaded, output)
    assert output.read_bytes() == first


def test_merge_partial_runs_requires_full_coverage(tmp_path: Path) -> None:
    from sme_bench.regrade import merge_partial_runs

    loaded = load_full_benchmark(known_scorers=known_scorer_names(), resolve_fixtures=True)
    base = tmp_path / "base"
    base.mkdir()
    (base / "metadata.json").write_text(
        json.dumps(
            {
                "run_id": "base",
                "model": "test-model",
                "seed": 1,
                "repeats": 3,
                "suite_id": "sme-full",
                "suite_version": loaded.manifest.version,
                "task_fingerprints": {
                    task.id: {"input": task_input_fingerprint(task)} for task in loaded.tasks
                },
            }
        ),
        encoding="utf-8",
    )
    with (base / "attempts.jsonl").open("w", encoding="utf-8") as handle:
        for task in loaded.tasks:
            handle.write(_attempt_from_task(task, repeat_index=0).model_dump_json() + "\n")
    with pytest.raises(ValueError, match="incomplete"):
        merge_partial_runs(
            base_dir=base,
            delta_dirs=[],
            target_dir=tmp_path / "out",
            loaded=loaded,
            write_reports=False,
        )


def test_merge_partial_runs_requires_source_fingerprints(tmp_path: Path) -> None:
    from sme_bench.regrade import merge_partial_runs

    loaded = load_full_benchmark(known_scorers=known_scorer_names(), resolve_fixtures=True)
    base = tmp_path / "base"
    _write_run(
        base,
        attempts=[],
        meta={
            "run_id": "base",
            "model": "test-model",
            "seed": 1,
            "repeats": 1,
            "suite_id": "sme-full",
            "suite_version": loaded.manifest.version,
        },
    )
    with pytest.raises(ValueError, match="no task input fingerprints"):
        merge_partial_runs(
            base_dir=base,
            delta_dirs=[],
            target_dir=tmp_path / "out",
            loaded=loaded,
            write_reports=False,
        )


def test_validate_report_rescore_requires_suite_and_fingerprints() -> None:
    from sme_bench.regrade import validate_report_rescore

    task = _minimal_task()
    attempt = _attempt_from_task(task, output_text="ok")
    with pytest.raises(ValueError, match="suite could not be loaded"):
        validate_report_rescore(attempts=[attempt], loaded=None, source_meta={})


def test_validate_report_rescore_rejects_unknown_and_changed_inputs(tmp_path: Path) -> None:
    from sme_bench.models import SuiteManifest
    from sme_bench.regrade import validate_report_rescore
    from sme_bench.task_loader import LoadedSuite

    task = _minimal_task()
    loaded = LoadedSuite(
        directory=tmp_path,
        manifest=SuiteManifest(
            schema_version="1.0",
            id="t",
            name="t",
            version="0.0.1",
            description="",
            languages=["de-DE"],
            default_repeats=1,
            default_pass_threshold=0.85,
            case_globs=[],
            category_weights={},
            provenance={"type": "synthetic"},
        ),
        tasks=[task],
        issues=[],
        suite_hash="x",
    )
    attempt = _attempt_from_task(task, output_text="ok")
    with pytest.raises(ValueError, match="lacks task_fingerprints"):
        validate_report_rescore(
            attempts=[attempt],
            loaded=loaded,
            source_meta={"run_id": "r"},
        )

    unknown = _attempt_from_task(task, task_id="missing-task", output_text="ok")
    with pytest.raises(ValueError, match="unknown task ids"):
        validate_report_rescore(
            attempts=[unknown],
            loaded=loaded,
            source_meta={
                "task_fingerprints": {task.id: {"input": task_input_fingerprint(task)}},
            },
        )

    with pytest.raises(ValueError, match="input fingerprints changed"):
        validate_report_rescore(
            attempts=[attempt],
            loaded=loaded,
            source_meta={"task_fingerprints": {task.id: {"input": "stale-hash"}}},
        )

    validate_report_rescore(
        attempts=[attempt],
        loaded=loaded,
        source_meta={
            "task_fingerprints": {task.id: {"input": task_input_fingerprint(task)}},
        },
    )


def test_merge_partial_runs_rescores_and_prefers_delta(tmp_path: Path) -> None:
    from sme_bench.regrade import merge_partial_runs

    loaded = load_full_benchmark(known_scorers=known_scorer_names(), resolve_fixtures=True)
    tasks = list(loaded.tasks)
    changed = next(t for t in tasks if t.id == "en-ho-missing-001")
    fps = {task.id: {"input": task_input_fingerprint(task)} for task in tasks}

    base = tmp_path / "base"
    base.mkdir()
    (base / "metadata.json").write_text(
        json.dumps(
            {
                "run_id": "base",
                "model": "test-model",
                "served_model_name": "test-model",
                "base_url": "https://example.test/v1",
                "seed": 42,
                "repeats": 1,
                "max_tokens_multiplier": 1.0,
                "max_tokens_floor": 8192,
                "extra_body": {},
                "suite_id": "sme-full",
                "suite_version": loaded.manifest.version,
                "task_fingerprints": fps,
            }
        ),
        encoding="utf-8",
    )
    with (base / "attempts.jsonl").open("w", encoding="utf-8") as handle:
        for task in tasks:
            if task.id == changed.id:
                # Stale wrong score: pretend full pass despite incomplete fields.
                attempt = _attempt_from_task(
                    task,
                    output_text=(
                        '{"missing_fields":["date","time","allergies","phone",'
                        '"seating","weekend_mention"]}'
                    ),
                    weighted_score=1.0,
                    passed=True,
                    partial=False,
                )
            else:
                attempt = _attempt_from_task(
                    task,
                    output_text='{"ok":true}',
                    weighted_score=0.0,
                    passed=False,
                )
            handle.write(attempt.model_dump_json() + "\n")

    delta = tmp_path / "delta"
    delta.mkdir()
    (delta / "metadata.json").write_text(
        json.dumps(
            {
                "run_id": "delta",
                "model": "test-model",
                "served_model_name": "test-model",
                "base_url": "https://example.test/v1",
                "seed": 42,
                "repeats": 1,
                "max_tokens_multiplier": 1.0,
                "max_tokens_floor": 8192,
                "extra_body": {},
                "suite_id": "sme-full",
                "suite_version": loaded.manifest.version,
                "task_fingerprints": {changed.id: fps[changed.id]},
            }
        ),
        encoding="utf-8",
    )
    with (delta / "attempts.jsonl").open("w", encoding="utf-8") as handle:
        handle.write(
            _attempt_from_task(
                changed,
                output_text=('{"missing_fields":["date","time","allergies","phone","seating"]}'),
                weighted_score=0.0,
                passed=False,
            ).model_dump_json()
            + "\n"
        )

    out = tmp_path / "merged"
    merge_partial_runs(
        base_dir=base,
        delta_dirs=[delta],
        target_dir=out,
        loaded=loaded,
        write_reports=False,
    )
    merged = [
        AttemptResult.model_validate(json.loads(line))
        for line in (out / "attempts.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(merged) == len(tasks)
    by_id = {a.task_id: a for a in merged}
    fixed = by_id[changed.id]
    assert fixed.passed is True
    assert fixed.weighted_score == pytest.approx(1.0)
    assert (out / "merge-manifest.json").exists()
    manifest = json.loads((out / "merge-manifest.json").read_text(encoding="utf-8"))
    assert manifest["rescored"] is True
