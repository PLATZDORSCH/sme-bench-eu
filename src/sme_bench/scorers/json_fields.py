"""JSON field comparison scorer."""

from __future__ import annotations

import re
from typing import Any

from sme_bench.models import BenchmarkTask, ScoreResult, ScorerSpec
from sme_bench.scorers.base import register
from sme_bench.utils import extract_json_payload, get_by_path

_DASH_RE = re.compile(r"[\u2010-\u2015\u2212\-]+")
_PERCENT_RE = re.compile(r"^(\d+(?:[.,]\d+)?)\s*%$")
_NUMBER_RE = re.compile(r"^(\d+(?:[.,]\d+)?)$")


def _normalize_iban(value: str) -> str:
    return re.sub(r"\s+", "", value).upper()


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_text(value: str) -> str:
    """Controlled text normalize: whitespace + unicode dashes → ASCII hyphen."""
    text = _normalize_whitespace(value)
    text = _DASH_RE.sub("-", text)
    return text


def _normalize_percent(value: Any) -> Any:
    """Treat ``19``, ``19%``, ``19 %`` as equivalent percent tokens."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if float(value).is_integer():
            return f"{int(value)}%"
        return f"{value}%"
    if not isinstance(value, str):
        return value
    text = _normalize_whitespace(value)
    m = _PERCENT_RE.match(text)
    if m:
        num = m.group(1).replace(",", ".")
        if num.endswith(".0"):
            num = num[:-2]
        return f"{num}%"
    m = _NUMBER_RE.match(text)
    if m:
        num = m.group(1).replace(",", ".")
        if num.endswith(".0"):
            num = num[:-2]
        return f"{num}%"
    return text


def _normalize_range(value: Any) -> Any:
    """Normalize numeric ranges like ``3–5`` / ``3 - 5`` / ``3 5`` → ``3-5``."""
    if not isinstance(value, str):
        return value
    text = _normalize_text(value)
    text = re.sub(r"(\d+)\s*-\s*(\d+)", r"\1-\2", text)
    text = re.sub(r"(\d+)\s+(\d+)", r"\1-\2", text)
    return text


def _normalize_terminal_punctuation(value: Any) -> Any:
    """Ignore sentence punctuation accidentally attached to an extracted value."""
    if not isinstance(value, str):
        return value
    return _normalize_text(value).rstrip(".,;:!?")


def _normalize_value(value: Any, *, mode: str | None) -> Any:
    if mode is None:
        return value
    if mode == "iban":
        return _normalize_iban(value) if isinstance(value, str) else value
    if mode == "whitespace":
        return _normalize_whitespace(value) if isinstance(value, str) else value
    if mode == "text":
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return _normalize_text(str(value))
        return _normalize_text(value) if isinstance(value, str) else value
    if mode == "percent":
        return _normalize_percent(value)
    if mode == "range":
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        return _normalize_range(value)
    if mode == "terminal_punctuation":
        return _normalize_terminal_punctuation(value)
    return value


def _values_match(
    actual: Any,
    expected: Any,
    *,
    match_mode: str,
    case_insensitive: bool,
) -> bool:
    if match_mode == "contains":
        if isinstance(actual, (int, float)) and not isinstance(actual, bool):
            actual = str(actual)
        if isinstance(expected, (int, float)) and not isinstance(expected, bool):
            expected = str(expected)
        if isinstance(actual, str) and isinstance(expected, str):
            cmp_actual = actual.casefold() if case_insensitive else actual
            cmp_expected = expected.casefold() if case_insensitive else expected
            return cmp_expected in cmp_actual
        return bool(actual == expected)
    if case_insensitive and isinstance(actual, str) and isinstance(expected, str):
        return actual.casefold() == expected.casefold()
    # Numeric/string equivalence for plain numbers
    if isinstance(actual, str) and isinstance(expected, (int, float)) and not isinstance(
        expected, bool
    ):
        try:
            return float(actual.replace(",", ".").rstrip("%")) == float(expected)
        except ValueError:
            pass
    if isinstance(expected, str) and isinstance(actual, (int, float)) and not isinstance(
        actual, bool
    ):
        try:
            return float(expected.replace(",", ".").rstrip("%")) == float(actual)
        except ValueError:
            pass
    return bool(actual == expected)


def _normalize_for_field(value: Any, *, path: str, mode: str | None) -> Any:
    normalized = _normalize_value(value, mode=mode)
    if mode in {"text", None} and path == "answer":
        normalized = _normalize_range(normalized)
        if isinstance(normalized, str):
            normalized = _normalize_text(normalized)
    elif mode == "percent":
        normalized = _normalize_percent(normalized)
    return normalized


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
        global_normalize = spec.params.get("normalize")
        field_normalize = spec.params.get("field_normalize") or {}
        field_aliases = spec.params.get("field_aliases") or {}
        patterns = spec.params.get("patterns") or {}

        matched: list[str] = []
        mismatched: dict[str, Any] = {}

        for path in fields:
            try:
                actual_val = get_by_path(data, path)
                expected_val = get_by_path(expected, path) if isinstance(expected, dict) else None
            except (KeyError, IndexError, TypeError, ValueError):
                mismatched[path] = {"error": "missing"}
                continue

            normalize_mode = field_normalize.get(path, global_normalize)
            actual_cmp = _normalize_for_field(actual_val, path=path, mode=normalize_mode)
            candidates = [expected_val]
            aliases = field_aliases.get(path)
            if isinstance(aliases, list):
                candidates.extend(aliases)
            expected_candidates = [
                _normalize_for_field(candidate, path=path, mode=normalize_mode)
                for candidate in candidates
            ]

            pattern = patterns.get(path)
            if isinstance(pattern, str) and isinstance(actual_cmp, str):
                flags = re.IGNORECASE if case_insensitive else 0
                ok = re.search(pattern, actual_cmp, flags=flags) is not None
            else:
                ok = any(
                    _values_match(
                        actual_cmp,
                        candidate,
                        match_mode=match_mode,
                        case_insensitive=case_insensitive,
                    )
                    for candidate in expected_candidates
                )
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
