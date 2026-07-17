"""Contains scorer."""

from __future__ import annotations

from typing import Any

from sme_bench.models import BenchmarkTask, ScoreResult, ScorerSpec
from sme_bench.scorers.base import register


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


@register
class ContainsScorer:
    name = "contains"

    def score(
        self,
        *,
        task: BenchmarkTask,
        output_text: str,
        parsed_output: Any | None,
        spec: ScorerSpec,
    ) -> ScoreResult:
        raw_terms = spec.params.get("terms") or spec.params.get("required") or []
        terms = [_as_str(t) for t in raw_terms if _as_str(t)]
        mode = spec.params.get("mode", "all")
        case_insensitive = bool(spec.params.get("case_insensitive", False))
        haystack = output_text.casefold() if case_insensitive else output_text
        needles = [t.casefold() if case_insensitive else t for t in terms]
        found = [t for t, n in zip(terms, needles, strict=True) if n in haystack]
        missing = [t for t in terms if t not in found]
        if mode == "any":
            ok = bool(found)
            score = 1.0 if ok else 0.0
        else:
            score = (len(found) / len(terms)) if terms else 0.0
            ok = not missing
        return ScoreResult(
            scorer=self.name,
            score=score,
            passed=ok,
            critical_failure=bool(spec.critical and not ok),
            message=None if ok else f"Missing terms: {missing}",
            details={"found": found, "missing": missing, "mode": mode},
        )
