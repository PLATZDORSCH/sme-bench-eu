"""Tests for task filtering including --task-ids."""

from __future__ import annotations

import pytest

from sme_bench.models import BenchmarkTask, GenerationConfig, Message, ScorerSpec
from sme_bench.task_loader import filter_tasks


def _task(task_id: str, *, language: str = "de-DE", tags: list[str] | None = None) -> BenchmarkTask:
    return BenchmarkTask.model_validate(
        {
            "schema_version": "1.0",
            "id": task_id,
            "title": task_id,
            "language": language,
            "category": "document_extraction",
            "task_type": "invoice_extraction",
            "difficulty": "normal",
            "risk": "low",
            "review_status": "approved",
            "data_classification": "synthetic",
            "tags": tags or [],
            "messages": [Message(role="user", content="x")],
            "generation": GenerationConfig(),
            "expected": {},
            "scorers": [ScorerSpec(type="exact_match", weight=1.0)],
        }
    )


def test_filter_tasks_by_ids() -> None:
    tasks = [_task("a"), _task("b"), _task("c")]
    assert [t.id for t in filter_tasks(tasks, task_ids=["c", "a"])] == ["a", "c"]


def test_filter_tasks_rejects_unknown_ids() -> None:
    with pytest.raises(ValueError, match="Unknown task id"):
        filter_tasks([_task("a")], task_ids=["a", "missing"])


def test_filter_tasks_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="Duplicate task id"):
        filter_tasks([_task("a"), _task("b")], task_ids=["a", "a"])
