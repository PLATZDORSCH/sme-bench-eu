"""Unit tests for statistics and performance metrics."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sme_bench.models import AttemptResult, RequestResult
from sme_bench.statistics import aggregate, language_parity


def test_language_parity_and_aggregate_reliable_pass() -> None:
    attempts = [
        AttemptResult(
            task_id="de-1",
            pair_id="p1",
            language="de-DE",
            category="c",
            task_type="t",
            difficulty="easy",
            risk="low",
            repeat_index=0,
            passed=True,
            effective_score=1.0,
        ),
        AttemptResult(
            task_id="de-1",
            pair_id="p1",
            language="de-DE",
            category="c",
            task_type="t",
            difficulty="easy",
            risk="low",
            repeat_index=1,
            passed=False,
            effective_score=0.0,
        ),
        AttemptResult(
            task_id="en-1",
            pair_id="p1",
            language="en-GB",
            category="c",
            task_type="t",
            difficulty="easy",
            risk="low",
            repeat_index=0,
            passed=True,
            effective_score=1.0,
        ),
        AttemptResult(
            task_id="en-1",
            pair_id="p1",
            language="en-GB",
            category="c",
            task_type="t",
            difficulty="easy",
            risk="low",
            repeat_index=1,
            passed=True,
            effective_score=1.0,
        ),
    ]
    parity = language_parity(attempts)
    assert parity["language_gap_pass_rate"] == pytest.approx(0.5)
    summary = aggregate(attempts, category_weights={"c": 1.0})
    assert summary["overall"]["reliable_pass_rate"] == pytest.approx(0.5)
    assert "sme_core_score" in summary


def test_generation_tps_fallback_on_buffered_stream() -> None:
    """When the server sends the whole answer in one chunk, use total latency."""
    buffered = RequestResult(
        request_id="r1",
        started_at=datetime.now(UTC),
        start_monotonic=0.0,
        end_monotonic=0.79,
        first_token_monotonic=0.7899,
        completion_tokens=34,
    )
    assert buffered.generation_tps == pytest.approx(34 / 0.79, rel=0.01)

    streamed = RequestResult(
        request_id="r2",
        started_at=datetime.now(UTC),
        start_monotonic=0.0,
        end_monotonic=2.0,
        first_token_monotonic=0.5,
        completion_tokens=500,
    )
    assert streamed.generation_tps == pytest.approx(500 / 1.5, rel=0.01)


def test_aggregate_mean_generation_tps() -> None:
    attempts = [
        AttemptResult(
            task_id="t1",
            language="de-DE",
            category="c",
            task_type="t",
            difficulty="easy",
            risk="low",
            repeat_index=0,
            passed=True,
            effective_score=1.0,
            completion_tokens=100,
            total_latency=1.0,
            ttft=0.2,
        ),
        AttemptResult(
            task_id="t1",
            language="de-DE",
            category="c",
            task_type="t",
            difficulty="easy",
            risk="low",
            repeat_index=1,
            passed=True,
            effective_score=1.0,
            completion_tokens=200,
            total_latency=1.0,
            ttft=0.2,
        ),
    ]
    summary = aggregate(attempts)
    # decode window 0.8s each → 100/0.8=125, 200/0.8=250 → mean 187.5
    assert summary["overall"]["mean_generation_tps"] == pytest.approx(187.5)
