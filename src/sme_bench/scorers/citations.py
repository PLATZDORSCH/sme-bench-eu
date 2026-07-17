"""Citation ID validation scorer."""

from __future__ import annotations

from typing import Any

from sme_bench.models import BenchmarkTask, ScoreResult, ScorerSpec
from sme_bench.scorers.base import register
from sme_bench.utils import extract_json_payload, get_by_path


def _normalize_citation(value: Any) -> Any:
    """Normalize a citation ID for comparison.

    Policies label sections as ``[SEC-A]``; models legitimately cite them with or
    without the surrounding brackets. Strip brackets and whitespace so both forms
    match, and compare case-insensitively.
    """
    if not isinstance(value, str):
        return value
    return value.strip().strip("[]").strip().casefold()


@register
class CitationsScorer:
    name = "citations"

    def score(
        self,
        *,
        task: BenchmarkTask,
        output_text: str,
        parsed_output: Any | None,
        spec: ScorerSpec,
    ) -> ScoreResult:
        field = spec.params.get("field", "citations")
        allowed = set(spec.params.get("allowed") or [])
        if not allowed and isinstance(task.expected, dict):
            allowed = set(task.expected.get("allowed_citations") or [])
        data = parsed_output
        if data is None:
            try:
                data = extract_json_payload(output_text)
            except (ValueError, TypeError) as exc:
                return ScoreResult(
                    scorer=self.name,
                    score=0.0,
                    passed=False,
                    critical_failure=bool(spec.critical),
                    message=f"Invalid JSON: {exc}",
                )

        try:
            citations = get_by_path(data, field) if isinstance(data, dict) else data
        except (KeyError, IndexError, TypeError, ValueError):
            citations = []

        if not isinstance(citations, list):
            return ScoreResult(
                scorer=self.name,
                score=0.0,
                passed=False,
                critical_failure=bool(spec.critical),
                message="Citations must be a list",
            )

        allowed_norm = {_normalize_citation(c) for c in allowed}
        invalid = [c for c in citations if _normalize_citation(c) not in allowed_norm]
        require_nonempty = bool(spec.params.get("require_nonempty", True))
        if citations and allowed:
            valid = [c for c in citations if _normalize_citation(c) in allowed_norm]
            score = len(valid) / len(citations)
        elif not citations:
            score = 0.0 if require_nonempty else 1.0
        else:
            score = 0.0

        ok = not invalid and (bool(citations) if require_nonempty else True)
        return ScoreResult(
            scorer=self.name,
            score=score,
            passed=ok,
            critical_failure=bool(spec.critical and not ok),
            message=None if ok else f"Invalid citations: {invalid}",
            details={"citations": citations, "invalid": invalid, "allowed": sorted(allowed)},
        )
