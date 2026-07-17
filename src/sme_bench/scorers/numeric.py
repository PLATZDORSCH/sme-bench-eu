"""Numeric field comparison with tolerances."""

from __future__ import annotations

from typing import Any

from sme_bench.models import BenchmarkTask, ScoreResult, ScorerSpec
from sme_bench.scorers.base import register
from sme_bench.utils import extract_json_payload, get_by_path


def _as_float(value: Any) -> float:
    if isinstance(value, bool):
        raise TypeError("bool is not numeric")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(" ", "")
        # Reject ambiguous mixed separators; after parse we compare floats only
        if "," in cleaned and "." in cleaned:
            # Assume EU format: 1.234,56
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        return float(cleaned)
    raise TypeError(f"Cannot coerce to float: {value!r}")


@register
class NumericScorer:
    name = "numeric"

    def score(
        self,
        *,
        task: BenchmarkTask,
        output_text: str,
        parsed_output: Any | None,
        spec: ScorerSpec,
    ) -> ScoreResult:
        fields: list[str] = list(spec.params.get("fields") or [])
        abs_tol = float(spec.params.get("absolute_tolerance", 0.0))
        rel_tol = float(spec.params.get("relative_tolerance", 0.0))
        expected = task.expected
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

        if not fields and isinstance(expected, dict):
            fields = [
                k
                for k, v in expected.items()
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            ]

        matched: list[str] = []
        mismatched: dict[str, Any] = {}
        for path in fields:
            try:
                actual_raw = get_by_path(data, path)
                expected_raw = get_by_path(expected, path)
                actual = _as_float(actual_raw)
                exp = _as_float(expected_raw)
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                mismatched[path] = {"error": str(exc)}
                continue

            diff = abs(actual - exp)
            allowed = abs_tol
            if rel_tol > 0:
                allowed = max(allowed, abs(exp) * rel_tol)
            if diff <= allowed:
                matched.append(path)
            else:
                mismatched[path] = {
                    "expected": exp,
                    "actual": actual,
                    "diff": diff,
                    "tolerance": allowed,
                }

        score = (len(matched) / len(fields)) if fields else 0.0
        ok = not mismatched and bool(fields)
        return ScoreResult(
            scorer=self.name,
            score=score,
            passed=ok,
            critical_failure=bool(spec.critical and not ok),
            message=None if ok else f"Numeric mismatches: {list(mismatched)}",
            details={"matched": matched, "mismatched": mismatched},
        )
