"""Classification scorer."""

from __future__ import annotations

import re
from typing import Any

from sme_bench.models import BenchmarkTask, ScoreResult, ScorerSpec
from sme_bench.scorers.base import register


def _normalize_label(text: str) -> str:
    value = text.strip()
    value = value.strip("\"'`")
    value = re.sub(r"\s+", " ", value)
    return value


@register
class ClassificationScorer:
    name = "classification"

    def score(
        self,
        *,
        task: BenchmarkTask,
        output_text: str,
        parsed_output: Any | None,
        spec: ScorerSpec,
    ) -> ScoreResult:
        expected = spec.params.get("expected", task.expected)
        allowed = spec.params.get("allowed")
        field = spec.params.get("field")
        actual_raw: Any = output_text
        if field and isinstance(parsed_output, dict):
            actual_raw = parsed_output.get(field, "")
        elif isinstance(parsed_output, dict) and "label" in parsed_output:
            actual_raw = parsed_output["label"]
        elif isinstance(parsed_output, dict) and "category" in parsed_output:
            actual_raw = parsed_output["category"]
        elif isinstance(parsed_output, str):
            actual_raw = parsed_output

        actual = _normalize_label(str(actual_raw))
        exp = _normalize_label(str(expected)) if expected is not None else None
        case_insensitive = bool(spec.params.get("case_insensitive", True))
        cmp_actual = actual.casefold() if case_insensitive else actual
        cmp_exp = exp.casefold() if exp is not None and case_insensitive else exp

        if allowed:
            allowed_norm = [
                a.casefold() if case_insensitive else _normalize_label(str(a)) for a in allowed
            ]
            if cmp_actual not in allowed_norm:
                return ScoreResult(
                    scorer=self.name,
                    score=0.0,
                    passed=False,
                    critical_failure=bool(spec.critical),
                    message=f"Label not in allowed set: {actual}",
                    details={"actual": actual, "allowed": allowed},
                )

        scale = spec.params.get("scale")
        adjacent_credit = float(spec.params.get("adjacent_credit", 0.0))
        if scale and cmp_exp is not None and cmp_actual != cmp_exp:
            scale_norm = [
                s.casefold() if case_insensitive else _normalize_label(str(s)) for s in scale
            ]
            if cmp_actual in scale_norm and cmp_exp in scale_norm:
                actual_idx = scale_norm.index(cmp_actual)
                expected_idx = scale_norm.index(cmp_exp)
                distance = abs(actual_idx - expected_idx)
                if distance == 1:
                    return ScoreResult(
                        scorer=self.name,
                        score=adjacent_credit,
                        passed=False,
                        critical_failure=bool(spec.critical),
                        message=f"Expected '{exp}', got '{actual}' (adjacent on scale)",
                        details={"expected": exp, "actual": actual, "distance": distance},
                    )
                return ScoreResult(
                    scorer=self.name,
                    score=0.0,
                    passed=False,
                    critical_failure=bool(spec.critical),
                    message=f"Expected '{exp}', got '{actual}'",
                    details={"expected": exp, "actual": actual, "distance": distance},
                )

        ok = cmp_exp is not None and cmp_actual == cmp_exp
        return ScoreResult(
            scorer=self.name,
            score=1.0 if ok else 0.0,
            passed=ok,
            critical_failure=bool(spec.critical and not ok),
            message=None if ok else f"Expected '{exp}', got '{actual}'",
            details={"expected": exp, "actual": actual},
        )
