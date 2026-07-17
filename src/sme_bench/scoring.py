"""Scorer registry and weighted evaluation."""

from __future__ import annotations

from typing import Any

from sme_bench.models import AttemptResult, BenchmarkTask, ScoreResult, ScorerSpec
from sme_bench.scorers.base import Scorer, get_scorer, known_scorer_names
from sme_bench.utils import extract_json_payload


def evaluate_attempt(
    task: BenchmarkTask,
    output_text: str,
) -> tuple[list[ScoreResult], float, float, bool, bool, bool, Any | None]:
    """Score a single attempt.

    Returns:
        score_results, weighted_score, effective_score, passed, partial,
        critical_failure, parsed_output
    """
    parsed: Any | None = None
    needs_json = any(
        s.type in {"json_schema", "json_fields", "numeric", "set_equality", "citations"}
        or task.generation.response_format == "json"
        for s in task.scorers
    )
    # Also try parse for set_equality on lists
    if needs_json or any(s.type == "set_equality" for s in task.scorers):
        try:
            parsed = extract_json_payload(output_text)
        except (ValueError, TypeError):
            parsed = None

    results: list[ScoreResult] = []
    for spec in task.scorers:
        scorer: Scorer = get_scorer(spec.type)
        result = scorer.score(
            task=task,
            output_text=output_text,
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
    passed = weighted >= task.pass_threshold and not critical_failure
    partial = (
        not critical_failure
        and not passed
        and weighted >= task.partial_threshold
    )
    effective = 0.0 if critical_failure else weighted
    return results, weighted, effective, passed, partial, critical_failure, parsed


def apply_partial_grade(attempt: AttemptResult, task: BenchmarkTask) -> AttemptResult:
    """Recompute partial flag for persisted attempts (e.g. when re-reporting)."""
    if attempt.infrastructure_error or attempt.critical_failure or attempt.passed:
        partial = False
    else:
        partial = attempt.weighted_score >= task.partial_threshold
    return attempt.model_copy(update={"partial": partial})


__all__ = [
    "apply_partial_grade",
    "evaluate_attempt",
    "known_scorer_names",
    "get_scorer",
    "ScoreResult",
    "ScorerSpec",
]
