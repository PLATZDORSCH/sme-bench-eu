"""Unit tests for statistics and performance metrics."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sme_bench.models import AttemptResult, RequestResult
from sme_bench.statistics import (
    CRITICAL_RATE_PENALTY_K,
    PARTIAL_RATE_PENALTY_K,
    aggregate,
    language_parity,
    sme_rank_score,
)


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
    assert "sme_rank_score" in summary
    overall = summary["overall"]
    assert summary["sme_rank_score"] == pytest.approx(
        summary["sme_core_score"]
        * overall["reliable_pass_rate"]
        * (1 - CRITICAL_RATE_PENALTY_K * overall["critical_failure_rate"])
        * (1 - PARTIAL_RATE_PENALTY_K * overall["attempt_partial_rate"])
    )


def test_sme_rank_score_penalty() -> None:
    assert sme_rank_score(
        96.5,
        reliable_pass_rate=1.0,
        critical_failure_rate=0.0,
        attempt_partial_rate=0.0,
    ) == pytest.approx(96.5)
    assert sme_rank_score(
        96.5,
        reliable_pass_rate=0.853,
        critical_failure_rate=0.0085,
        attempt_partial_rate=0.068,
    ) == pytest.approx(
        96.5
        * 0.853
        * (1 - CRITICAL_RATE_PENALTY_K * 0.0085)
        * (1 - PARTIAL_RATE_PENALTY_K * 0.068)
    )
    assert sme_rank_score(
        90.0,
        reliable_pass_rate=1.0,
        critical_failure_rate=0.2,
        attempt_partial_rate=0.0,
    ) == pytest.approx(0.0)
    assert sme_rank_score(
        90.0,
        reliable_pass_rate=0.5,
        critical_failure_rate=0.0,
        attempt_partial_rate=0.0,
    ) == pytest.approx(45.0)


def test_aggregate_rank_score_with_critical_failures() -> None:
    attempts = [
        AttemptResult(
            task_id="t1",
            language="de-DE",
            category="c",
            task_type="t",
            difficulty="easy",
            risk="critical",
            repeat_index=0,
            passed=False,
            critical_failure=True,
            effective_score=0.0,
        ),
        AttemptResult(
            task_id="t2",
            language="de-DE",
            category="c",
            task_type="t",
            difficulty="easy",
            risk="low",
            repeat_index=0,
            passed=True,
            effective_score=1.0,
        ),
    ]
    summary = aggregate(attempts, category_weights={"c": 1.0})
    assert summary["overall"]["critical_failure_rate"] == pytest.approx(0.5)
    assert summary["sme_core_score"] == pytest.approx(50.0)
    assert summary["sme_rank_score"] == pytest.approx(0.0)
    # reliable_pass_rate = 0 (only one of two tasks fully reliable)
    assert summary["overall"]["reliable_pass_rate"] == pytest.approx(0.5)


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
