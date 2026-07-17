"""Shared fixtures for unit tests."""

from __future__ import annotations

from sme_bench.models import BenchmarkTask, GenerationConfig, Message, ScorerSpec


def make_task(**overrides: object) -> BenchmarkTask:
    base = dict(
        schema_version="1.0",
        id="t1",
        title="t",
        language="de-DE",
        category="document_extraction",
        task_type="invoice_extraction",
        difficulty="normal",
        risk="low",
        review_status="draft",
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
