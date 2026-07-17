"""JSON field comparison scorer."""

from __future__ import annotations

from typing import Any

from sme_bench.models import BenchmarkTask, ScoreResult, ScorerSpec
from sme_bench.scorers.base import register
from sme_bench.utils import extract_json_payload, get_by_path


@register
class JsonFieldsScorer:
    name = "json_fields"

    def score(
        self,
        *,
        task: BenchmarkTask,
        output_text: str,
        parsed_output: Any | None,
        spec: ScorerSpec,
    ) -> ScoreResult:
        fields: list[str] = list(spec.params.get("fields") or [])
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

        if not isinstance(expected, dict) and not fields:
            return ScoreResult(
                scorer=self.name,
                score=0.0,
                passed=False,
                message="expected must be an object for json_fields",
            )

        if not fields and isinstance(expected, dict):
            fields = list(expected.keys())

        case_insensitive = bool(spec.params.get("case_insensitive", False))
        match_mode = str(spec.params.get("match", "exact"))
        matched: list[str] = []
        mismatched: dict[str, Any] = {}

        for path in fields:
            try:
                actual_val = get_by_path(data, path)
                expected_val = get_by_path(expected, path) if isinstance(expected, dict) else None
            except (KeyError, IndexError, TypeError, ValueError):
                mismatched[path] = {"error": "missing"}
                continue

            if match_mode == "contains" and isinstance(actual_val, str) and isinstance(
                expected_val, str
            ):
                cmp_actual = actual_val.casefold() if case_insensitive else actual_val
                cmp_expected = expected_val.casefold() if case_insensitive else expected_val
                ok = cmp_expected in cmp_actual
            elif case_insensitive and isinstance(actual_val, str) and isinstance(expected_val, str):
                ok = actual_val.casefold() == expected_val.casefold()
            else:
                ok = actual_val == expected_val
            if ok:
                matched.append(path)
            else:
                mismatched[path] = {"expected": expected_val, "actual": actual_val}

        score = (len(matched) / len(fields)) if fields else 0.0
        ok = not mismatched and bool(fields)
        return ScoreResult(
            scorer=self.name,
            score=score,
            passed=ok,
            critical_failure=bool(spec.critical and not ok),
            message=None if ok else f"Mismatched fields: {list(mismatched)}",
            details={"matched": matched, "mismatched": mismatched},
        )
