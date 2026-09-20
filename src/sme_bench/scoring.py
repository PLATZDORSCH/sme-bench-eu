"""Scorer registry and weighted evaluation."""

from __future__ import annotations

from typing import Any

from sme_bench.models import (
    AttemptResult,
    BenchmarkTask,
    ScoreResult,
    ScorerSpec,
    ToolCall,
    ToolTraceEntry,
)
from sme_bench.scorers.base import Scorer, get_scorer, known_scorer_names
from sme_bench.utils import extract_json_payload, separate_thinking_content

_FORMAT_SCORERS = frozenset({"json_schema", "language"})
_TOOL_SCORERS = frozenset(
    {
        "tool_call",
        "no_tool_call",
        "tool_name_valid",
        "trace_calls",
        "trace_exactly_once",
        "trace_no_fabrication",
        "trace_phase",
    }
)


def _is_format_only_failure(
    *,
    passed: bool,
    critical: bool,
    scorers: list[ScorerSpec],
    results: list[ScoreResult],
) -> bool:
    if passed or critical:
        return False
    format_failed = False
    content_ok = False
    content_seen = False
    for spec, result in zip(scorers, results, strict=True):
        if spec.type in _FORMAT_SCORERS:
            if not result.passed:
                format_failed = True
            continue
        if spec.weight > 0:
            content_seen = True
            if result.passed:
                content_ok = True
            else:
                return False
    return format_failed and (content_ok or not content_seen)


def evaluate_attempt(
    task: BenchmarkTask,
    output_text: str,
    tool_calls: list[ToolCall] | None = None,
    tool_trace: list[ToolTraceEntry] | None = None,
) -> tuple[list[ScoreResult], float, float, bool, bool, bool, Any | None]:
    """Score a single attempt.

    Returns:
        score_results, weighted_score, effective_score, passed, partial,
        critical_failure, parsed_output
    """
    # Strip leaked CoT so rescoring old thinking dumps matches new client behaviour.
    answer_text, _reasoning = separate_thinking_content(output_text)
    calls = list(tool_calls or [])

    parsed: Any | None = None
    needs_json = any(
        s.type in {"json_schema", "json_fields", "numeric", "set_equality", "citations"}
        or task.generation.response_format == "json"
        for s in task.scorers
    )
    # Also try parse for set_equality on lists
    if needs_json or any(s.type == "set_equality" for s in task.scorers):
        try:
            parsed = extract_json_payload(answer_text)
        except (ValueError, TypeError):
            parsed = None

    if task.tools or any(s.type in _TOOL_SCORERS for s in task.scorers) or calls or tool_trace:
        parsed = {
            "tool_calls": [
                {"name": call.name, "arguments": call.parsed_arguments(), "id": call.id}
                for call in calls
            ],
            "content": answer_text,
            "tool_trace": [entry.model_dump(mode="json") for entry in (tool_trace or [])],
        }

    results: list[ScoreResult] = []
    for spec in task.scorers:
        scorer: Scorer = get_scorer(spec.type)
        result = scorer.score(
            task=task,
            output_text=answer_text,
            parsed_output=parsed,
            spec=spec,
        )
        results.append(result)

    positive_weight = sum(s.weight for s in task.scorers if s.weight > 0)
    if positive_weight <= 0:
        weighted = 0.0
    else:
        weighted = (
            sum(
                r.score * s.weight
                for r, s in zip(results, task.scorers, strict=True)
                if s.weight > 0
            )
            / positive_weight
        )

    critical_failure = any(r.critical_failure for r in results)
    # ``must_pass`` scorers may still contribute partial credit, but a failed
    # must_pass scorer blocks a full weighted pass (schema points must not
    # override a wrong required field; adjacent_credit stays partial-only).
    must_pass_failed = any(
        spec.must_pass and not result.passed
        for spec, result in zip(task.scorers, results, strict=True)
    )
    passed = weighted >= task.pass_threshold and not critical_failure and not must_pass_failed
    partial = not critical_failure and not passed and weighted >= task.partial_threshold
    effective = 0.0 if critical_failure else weighted
    return results, weighted, effective, passed, partial, critical_failure, parsed


def is_format_only_failure(
    *,
    passed: bool,
    critical: bool,
    task: BenchmarkTask,
    results: list[ScoreResult],
) -> bool:
    return _is_format_only_failure(
        passed=passed, critical=critical, scorers=task.scorers, results=results
    )


def apply_partial_grade(attempt: AttemptResult, task: BenchmarkTask) -> AttemptResult:
    """Recompute partial flag for persisted attempts (e.g. when re-reporting)."""
    if (
        attempt.infrastructure_error
        or attempt.excluded_reason
        or attempt.critical_failure
        or attempt.passed
    ):
        partial = False
    else:
        partial = attempt.weighted_score >= task.partial_threshold
    return attempt.model_copy(update={"partial": partial})


__all__ = [
    "apply_partial_grade",
    "evaluate_attempt",
    "is_format_only_failure",
    "known_scorer_names",
    "get_scorer",
    "ScoreResult",
    "ScorerSpec",
]
