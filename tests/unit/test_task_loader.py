"""Unit tests for task loading and resume."""

from __future__ import annotations

import json
from pathlib import Path

from sme_bench.models import ScorerSpec
from sme_bench.qa import check_nop, check_oracle, format_canary_header
from sme_bench.runner import _load_completed_keys
from sme_bench.scorers.base import known_scorer_names
from sme_bench.task_loader import (
    FULL_SUITE_IDS,
    ValidationIssue,
    _check_oracle_and_nop,
    _check_pair_consistency,
    _check_variant_review_gate,
    load_full_benchmark,
    load_suite,
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
    # 244 previous + 32 agentic + 8 crowded tool variants = 284
    assert len(loaded.tasks) == 284
    assert len({t.id for t in loaded.tasks}) == 284


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


def test_oracle_passes_on_expected_json() -> None:
    task = make_task(
        expected={"a": 1},
        scorers=[
            ScorerSpec(type="json_fields", weight=1.0, params={"fields": ["a"]}),
        ],
    )
    ok, message = check_oracle(task)
    assert ok, message


def test_nop_empty_object_must_not_pass() -> None:
    task = make_task(
        expected={"a": 1},
        scorers=[
            ScorerSpec(type="json_fields", weight=1.0, params={"fields": ["a"]}),
        ],
    )
    findings = check_nop(task)
    assert all(not passed for _label, _out, passed, _partial in findings)


def test_oracle_and_nop_issues_on_approved_task() -> None:
    issues: list[ValidationIssue] = []
    broken = make_task(
        review_status="approved",
        expected={"a": 99},
        scorers=[
            ScorerSpec(type="json_fields", weight=1.0, params={"fields": ["missing"]}),
        ],
    )
    _check_oracle_and_nop(broken, "case.yaml", issues)
    assert any(i.severity == "error" and "oracle" in i.message for i in issues)


def test_load_suite_reports_missing_canary(tmp_path: Path) -> None:
    (tmp_path / "cases" / "de-DE").mkdir(parents=True)
    (tmp_path / "suite.yaml").write_text(
        "\n".join(
            [
                "schema_version: '1.0'",
                "id: tmp-suite",
                "name: Tmp",
                "version: 0.0.1",
                "languages: [de-DE]",
                "case_globs: ['cases/**/*.yaml']",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    case = tmp_path / "cases" / "de-DE" / "de-tmp-001.yaml"
    case.write_text(
        "\n".join(
            [
                format_canary_header("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
                "schema_version: '1.0'",
                "id: de-tmp-001",
                "title: tmp",
                "language: de-DE",
                "category: customer_service",
                "task_type: support_routing",
                "difficulty: easy",
                "risk: low",
                "review_status: draft",
                "data_classification: synthetic",
                "messages:",
                "  - role: user",
                "    content: hi",
                "expected: {a: 1}",
                "scorers:",
                "  - type: json_fields",
                "    weight: 1.0",
                "    params: {fields: [a]}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    loaded = load_suite(tmp_path, known_scorers=known_scorer_names())
    assert loaded.ok
    assert not any("oracle" in i.message and i.severity == "error" for i in loaded.issues)
