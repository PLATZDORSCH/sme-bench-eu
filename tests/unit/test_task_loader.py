"""Unit tests for task loading and resume."""

from __future__ import annotations

import json
from pathlib import Path

from sme_bench.runner import _load_completed_keys
from sme_bench.scorers.base import known_scorer_names
from sme_bench.task_loader import (
    FULL_SUITE_IDS,
    ValidationIssue,
    _check_pair_consistency,
    _check_variant_review_gate,
    load_full_benchmark,
)
from tests.unit.conftest import make_task


def test_resume_key_detection(tmp_path: Path) -> None:
    path = tmp_path / "attempts.jsonl"
    path.write_text(
        json.dumps({"task_id": "a", "repeat_index": 0})
        + "\n"
        + json.dumps({"task_id": "a", "repeat_index": 1})
        + "\n",
        encoding="utf-8",
    )
    keys = _load_completed_keys(path)
    assert keys == {("a", 0), ("a", 1)}


def test_load_full_benchmark() -> None:
    loaded = load_full_benchmark(known_scorers=known_scorer_names())
    assert loaded.manifest.id == "sme-full"
    assert not any(i.severity == "error" for i in loaded.issues)
    assert len(loaded.member_suites) == len(FULL_SUITE_IDS)
    # 72 core + curated domain noise/edge ≈ 196 (Release 0.4.1)
    assert len(loaded.tasks) == 196
    assert len({t.id for t in loaded.tasks}) == 196


def test_pair_audit_requires_exactly_one_de_and_one_en() -> None:
    issues: list[ValidationIssue] = []
    tasks = [
        make_task(id="de-a", pair_id="pair-a", language="de-DE"),
        make_task(id="de-b", pair_id="pair-a", language="de-DE"),
    ]
    _check_pair_consistency(tasks, issues)
    assert any("exactly one de-DE and one en-GB" in issue.message for issue in issues)


def test_generated_variant_cannot_be_approved_without_review_evidence() -> None:
    issues: list[ValidationIssue] = []
    task = make_task(review_status="approved", tags=["noise-variant"])
    _check_variant_review_gate(task, "case.yaml", issues)
    assert any("reference-calibrated" in issue.message for issue in issues)

    issues.clear()
    task = make_task(
        review_status="approved",
        tags=[
            "noise-variant",
            "pair-reviewed",
            "golden-reviewed",
            "reference-calibrated",
        ],
    )
    _check_variant_review_gate(task, "case.yaml", issues)
    assert not issues
