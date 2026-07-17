"""Exact match scorer."""

from __future__ import annotations

import re
from typing import Any

from sme_bench.models import BenchmarkTask, ScoreResult, ScorerSpec
from sme_bench.scorers.base import register


def _normalize(text: str, *, case_insensitive: bool, strip_whitespace: bool) -> str:
    value = text.strip() if strip_whitespace else text
    if strip_whitespace:
        value = re.sub(r"\s+", " ", value)
    if case_insensitive:
        value = value.casefold()
    return value


@register
class ExactMatchScorer:
    name = "exact_match"

    def score(
        self,
        *,
        task: BenchmarkTask,
        output_text: str,
        parsed_output: Any | None,
        spec: ScorerSpec,
    ) -> ScoreResult:
        expected = spec.params.get("expected", task.expected)
        if expected is None:
            return ScoreResult(
                scorer=self.name,
                score=0.0,
                passed=False,
                message="No expected value configured",
            )
        case_insensitive = bool(spec.params.get("case_insensitive", False))
        strip_ws = bool(spec.params.get("normalize_whitespace", True))
        actual = _normalize(
            output_text, case_insensitive=case_insensitive, strip_whitespace=strip_ws
        )
        exp = _normalize(
            str(expected), case_insensitive=case_insensitive, strip_whitespace=strip_ws
        )
        ok = actual == exp
        return ScoreResult(
            scorer=self.name,
            score=1.0 if ok else 0.0,
            passed=ok,
            critical_failure=bool(spec.critical and not ok),
            message=None if ok else "Output does not exactly match expected",
            details={"expected": exp, "actual": actual},
        )
