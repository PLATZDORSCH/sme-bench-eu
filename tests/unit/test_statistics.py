"""Unit tests for statistics and performance metrics."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sme_bench.models import AttemptResult, RequestResult
from sme_bench.statistics import (
    TIER_INCONCLUSIVE,
    TIER_NOT_RECOMMENDED,
    TIER_READY,
    TIER_SUPERVISED,
    aggregate,
    language_parity,
    pass_rate_interval,
    readiness_tier,
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
    assert summary["overall"]["mostly_pass_rate"] == pytest.approx(0.0)
    assert summary["overall"]["unreliable_pass_rate"] == pytest.approx(0.5)
    assert summary["overall"]["failed_task_rate"] == pytest.approx(0.0)
    assert summary["readiness"]["tier"] in {
        TIER_READY,
        TIER_SUPERVISED,
        TIER_NOT_RECOMMENDED,
        TIER_INCONCLUSIVE,
    }
    overall = summary["overall"]
    assert overall["pass_rate"] == pytest.approx(0.75)
    assert overall["unsolved_cases"] == 1
    assert overall["unstable_cases"] == 1
    assert overall["critical_cases"] == 0
    assert summary["headline"]["pass_rate"] == overall["pass_rate"]
    assert summary["headline"]["tier"] == summary["readiness"]["tier"]
    assert "sme_rank_score" not in summary
    assert "sme_core_score" in summary["legacy"]


def test_repeat_pass_buckets_distinguish_three_two_one_and_zero_passes() -> None:
    attempts: list[AttemptResult] = []
    for task_id, pass_count in {
        "reliable": 3,
        "mostly": 2,
        "unreliable": 1,
        "failed": 0,
    }.items():
        for repeat_index in range(3):
            passed = repeat_index < pass_count
            attempts.append(
                AttemptResult(
                    task_id=task_id,
                    language="de-DE",
                    category="c",
                    task_type="t",
                    difficulty="easy",
                    risk="low",
                    repeat_index=repeat_index,
                    passed=passed,
                    effective_score=1.0 if passed else 0.0,
                )
            )

    overall = aggregate(attempts)["overall"]
    assert overall["reliable_pass_rate"] == pytest.approx(0.25)
    assert overall["mostly_pass_rate"] == pytest.approx(0.25)
    assert overall["unreliable_pass_rate"] == pytest.approx(0.25)
    assert overall["failed_task_rate"] == pytest.approx(0.25)
    assert overall["attempt_pass_rate"] == pytest.approx(0.5)


def _attempt(task_id: str, repeat_index: int = 0, **kwargs: object) -> AttemptResult:
    passed = bool(kwargs.pop("passed", True))
    return AttemptResult(
        task_id=task_id,
        language="de-DE",
        category="c",
        task_type="t",
        difficulty="easy",
        risk="low",
        repeat_index=repeat_index,
        passed=passed,
        effective_score=1.0 if passed else 0.0,
        **kwargs,  # type: ignore[arg-type]
    )


def _overall(**kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {
        "completion_rate": 1.0,
        "pass_rate": 1.0,
        "critical_cases": 0,
        "language_compliance_rate": 1.0,
    }
    base.update(kwargs)
    return base


def test_readiness_tier_thresholds() -> None:
    ready = readiness_tier(_overall(pass_rate=0.95))
    assert ready == {"tier": TIER_READY, "reasons": ["pass_ready"]}

    supervised = readiness_tier(_overall(pass_rate=0.85))
    assert supervised == {"tier": TIER_SUPERVISED, "reasons": ["pass_supervised"]}

    not_recommended = readiness_tier(_overall(pass_rate=0.849))
    assert not_recommended == {"tier": TIER_NOT_RECOMMENDED, "reasons": ["pass_not_recommended"]}


def test_readiness_tier_critical_caps_at_supervised() -> None:
    result = readiness_tier(_overall(pass_rate=0.99, critical_cases=1))
    assert result == {"tier": TIER_SUPERVISED, "reasons": ["critical_failures"]}
    # A critical case alone never forces not_recommended.
    result = readiness_tier(_overall(pass_rate=0.86, critical_cases=5))
    assert result["tier"] == TIER_SUPERVISED
    assert result["reasons"] == ["critical_failures", "pass_supervised"]


def test_readiness_tier_language_cap() -> None:
    result = readiness_tier(_overall(pass_rate=0.97, language_compliance_rate=0.99))
    assert result == {"tier": TIER_SUPERVISED, "reasons": ["language_break"]}


def test_readiness_tier_inconclusive_on_low_completion() -> None:
    result = readiness_tier(_overall(completion_rate=0.94))
    assert result == {"tier": TIER_INCONCLUSIVE, "reasons": ["low_completion"]}


def test_infrastructure_errors_are_not_counted_as_failures() -> None:
    attempts = [_attempt(f"t{i}", r) for i in range(30) for r in range(2)]
    attempts.append(_attempt("t30", 0))
    attempts.append(_attempt("t30", 1, passed=False, infrastructure_error=True))
    summary = aggregate(attempts)
    overall = summary["overall"]
    assert overall["attempt_pass_rate"] < 1.0
    assert overall["pass_rate"] == pytest.approx(1.0)
    assert overall["unsolved_cases"] == 0
    assert overall["graded_attempts"] == 61
    assert summary["headline"]["coverage"] == pytest.approx(61 / 62)
    assert summary["readiness"]["tier"] == TIER_READY


def test_case_counts() -> None:
    attempts = [
        _attempt("solved", 0),
        _attempt("solved", 1),
        _attempt("unstable", 0),
        _attempt("unstable", 1, passed=False),
        _attempt("failed", 0, passed=False),
        _attempt("failed", 1, passed=False, critical_failure=True),
    ]
    overall = aggregate(attempts)["overall"]
    assert overall["pass_rate"] == pytest.approx(0.5)
    assert overall["unsolved_cases"] == 2
    assert overall["unstable_cases"] == 1
    assert overall["critical_cases"] == 1


def test_pass_rate_interval_is_deterministic_and_brackets_the_rate() -> None:
    attempts = [
        _attempt(f"t{i}", r, passed=i % 5 != 0, pair_id=f"p{i // 2}")
        for i in range(40)
        for r in range(2)
    ]
    first = pass_rate_interval(attempts)
    assert first == pass_rate_interval(list(reversed(attempts)))
    assert first is not None
    low, high = first
    assert 0.0 <= low < 0.8 < high <= 1.0
    assert pass_rate_interval([]) is None
    assert pass_rate_interval([_attempt("a"), _attempt("b")]) == [1.0, 1.0]


def test_aggregate_with_critical_failure() -> None:
    attempts = [
        _attempt("t1", passed=False, critical_failure=True),
        _attempt("t2"),
    ]
    summary = aggregate(attempts, category_weights={"c": 1.0})
    assert summary["overall"]["critical_failure_rate"] == pytest.approx(0.5)
    assert summary["overall"]["critical_cases"] == 1
    assert summary["legacy"]["sme_core_score"] == pytest.approx(50.0)
    assert summary["readiness"] == {
        "tier": TIER_NOT_RECOMMENDED,
        "reasons": ["pass_not_recommended"],
    }
    # reliable_pass_rate = 0 (only one of two tasks fully reliable)
    assert summary["overall"]["reliable_pass_rate"] == pytest.approx(0.5)


def test_generation_tps_none_on_buffered_stream() -> None:
    """When the server sends the whole answer in one chunk, leave tok/s blank."""
    buffered = RequestResult(
        request_id="r1",
        started_at=datetime.now(UTC),
        start_monotonic=0.0,
        end_monotonic=0.79,
        first_token_monotonic=0.7899,
        completion_tokens=34,
    )
    assert buffered.generation_tps is None
    assert buffered.tps_unreliable is True

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


def test_ttft_cold_and_prompt_buckets() -> None:
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
            ttft=1.0,
            ttfa=1.2,
            prompt_tokens=500,
            format_only_failure=True,
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
            ttft=0.2,
            ttfa=0.3,
            prompt_tokens=5000,
        ),
    ]
    summary = aggregate(attempts)
    assert summary["overall"]["ttft_cold_p50"] == pytest.approx(1.0)
    assert summary["overall"]["ttfa_p50"] == pytest.approx(0.75)
    assert summary["overall"]["format_only_failure_rate"] == pytest.approx(0.5)
    assert "<1k" in summary["by_prompt_bucket"]
    assert "4-16k" in summary["by_prompt_bucket"]


def test_completion_rate_excludes_infra_and_excluded() -> None:
    attempts = [
        AttemptResult(
            task_id="ok",
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
            task_id="infra",
            language="de-DE",
            category="c",
            task_type="t",
            difficulty="easy",
            risk="low",
            repeat_index=0,
            infrastructure_error=True,
            error_type="timeout",
        ),
        AttemptResult(
            task_id="skip",
            language="de-DE",
            category="c",
            task_type="t",
            difficulty="easy",
            risk="low",
            repeat_index=0,
            excluded_reason="tool_choice_required_unsupported",
        ),
    ]
    summary = aggregate(attempts)
    overall = summary["overall"]
    assert overall["attempts"] == 3
    assert overall["graded_attempts"] == 1
    assert overall["completion_rate"] == pytest.approx(1 / 3)
    assert overall["attempt_pass_rate"] == pytest.approx(1 / 3)
    assert overall["attempt_pass_rate_graded"] == pytest.approx(1.0)
    assert summary["completion_rate_warning"] is True


def test_toolset_delta_pairs_crowded_minus_small() -> None:
    attempts = [
        AttemptResult(
            task_id="de-small",
            pair_id="tools-stock-001",
            language="de-DE",
            category="tool_use",
            task_type="stock_lookup",
            difficulty="normal",
            risk="low",
            repeat_index=0,
            passed=True,
            effective_score=1.0,
        ),
        AttemptResult(
            task_id="de-crowded",
            pair_id="tools-stock-001-crowded",
            variant_of="tools-stock-001",
            language="de-DE",
            category="tool_use",
            task_type="toolset_crowded",
            difficulty="normal",
            risk="low",
            repeat_index=0,
            passed=False,
            effective_score=0.4,
        ),
    ]
    summary = aggregate(attempts)
    delta = summary["toolset_delta"]
    assert delta["pairs"]
    assert delta["mean_delta"] == pytest.approx(-0.6)
    assert delta["by_language"]["de-DE"] == pytest.approx(-0.6)
