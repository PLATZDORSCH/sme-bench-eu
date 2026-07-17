"""Set equality scorer."""

from __future__ import annotations

from typing import Any

from sme_bench.models import BenchmarkTask, ScoreResult, ScorerSpec
from sme_bench.scorers.base import register
from sme_bench.utils import extract_json_payload, get_by_path


def _to_hashable(item: Any) -> Any:
    if isinstance(item, dict):
        return tuple(sorted((k, _to_hashable(v)) for k, v in item.items()))
    if isinstance(item, list):
        return tuple(_to_hashable(v) for v in item)
    return item


def _project(item: Any, keys: list[str] | None) -> Any:
    """Reduce dict items to the given keys before comparison.

    Used when only a subset of fields is deterministically gradable (e.g. compare
    order items by ``sku``/``qty`` while ignoring free-text ``variant`` phrasing).
    """
    if keys and isinstance(item, dict):
        return {k: item.get(k) for k in keys}
    return item


def _coerce_to_list(value: Any, *, coerce_scalar: bool) -> Any:
    if coerce_scalar and not isinstance(value, list):
        return [value]
    return value


def _alias_lookup(aliases: dict[str, list[str]] | None) -> dict[str, str]:
    """Map alternate labels (casefolded) → canonical expected token."""
    lookup: dict[str, str] = {}
    if not aliases:
        return lookup
    for canonical, alts in aliases.items():
        lookup[str(canonical).casefold()] = str(canonical)
        for alt in alts or []:
            lookup[str(alt).casefold()] = str(canonical)
    return lookup


def _normalize_token(item: Any, lookup: dict[str, str]) -> Any:
    if isinstance(item, str) and lookup:
        return lookup.get(item.casefold(), item)
    return item


def _elements_match(
    actual: Any,
    expected: Any,
    *,
    match_mode: str,
    alias_lookup: dict[str, str] | None = None,
) -> bool:
    lookup = alias_lookup or {}
    actual_n = _normalize_token(actual, lookup)
    expected_n = _normalize_token(expected, lookup)
    if match_mode == "substring" and isinstance(actual_n, str) and isinstance(expected_n, str):
        return expected_n.casefold() in actual_n.casefold()
    return bool(actual_n == expected_n)


def _match_lists(
    actual_items: list[Any],
    expected_items: list[Any],
    *,
    match_mode: str,
    alias_lookup: dict[str, str] | None = None,
) -> tuple[list[Any], list[Any], int]:
    matched_actual: set[int] = set()
    matched_expected: set[int] = set()
    for ei, exp in enumerate(expected_items):
        for ai, act in enumerate(actual_items):
            if ai in matched_actual:
                continue
            if _elements_match(
                act, exp, match_mode=match_mode, alias_lookup=alias_lookup
            ):
                matched_expected.add(ei)
                matched_actual.add(ai)
                break
    missing = [expected_items[i] for i in range(len(expected_items)) if i not in matched_expected]
    unexpected = [actual_items[i] for i in range(len(actual_items)) if i not in matched_actual]
    matched_count = len(matched_expected)
    return missing, unexpected, matched_count


@register
class SetEqualityScorer:
    name = "set_equality"

    def score(
        self,
        *,
        task: BenchmarkTask,
        output_text: str,
        parsed_output: Any | None,
        spec: ScorerSpec,
    ) -> ScoreResult:
        field = spec.params.get("field")
        ignore_order = bool(spec.params.get("ignore_order", True))
        coerce_scalar = bool(spec.params.get("coerce_scalar", False))
        match_mode = str(spec.params.get("match", "exact"))
        keys = spec.params.get("keys")
        aliases = spec.params.get("aliases")
        alias_lookup = _alias_lookup(aliases if isinstance(aliases, dict) else None)
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

        actual_list: Any = data
        expected_list: Any = expected
        if field:
            try:
                actual_list = get_by_path(data, field) if not isinstance(data, list) else data
                if isinstance(expected, dict):
                    expected_list = get_by_path(expected, field)
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                return ScoreResult(
                    scorer=self.name,
                    score=0.0,
                    passed=False,
                    critical_failure=bool(spec.critical),
                    message=str(exc),
                )

        # Allow expected to be the list directly, or under field key
        if isinstance(expected, dict) and field and field in expected:
            expected_list = expected[field]
        if isinstance(data, dict) and field and field in data:
            actual_list = data[field]

        actual_list = _coerce_to_list(actual_list, coerce_scalar=coerce_scalar)
        expected_list = _coerce_to_list(expected_list, coerce_scalar=coerce_scalar)

        if not isinstance(actual_list, list) or not isinstance(expected_list, list):
            return ScoreResult(
                scorer=self.name,
                score=0.0,
                passed=False,
                critical_failure=bool(spec.critical),
                message="Both actual and expected must be lists",
                details={"actual_type": type(actual_list).__name__},
            )

        actual_proj = [
            _normalize_token(_project(x, keys), alias_lookup) for x in actual_list
        ]
        expected_proj = [
            _normalize_token(_project(x, keys), alias_lookup) for x in expected_list
        ]

        if ignore_order:
            if match_mode == "substring" or alias_lookup:
                missing, unexpected, matched_count = _match_lists(
                    actual_proj,
                    expected_proj,
                    match_mode=match_mode,
                    alias_lookup=alias_lookup,
                )
                ok = not missing and not unexpected
                union_size = len(actual_proj) + len(expected_proj) - matched_count
                score = (matched_count / union_size) if union_size else 1.0
            else:
                actual_set = {_to_hashable(x) for x in actual_proj}
                expected_set = {_to_hashable(x) for x in expected_proj}
                missing = list(expected_set - actual_set)
                unexpected = list(actual_set - expected_set)
                ok = not missing and not unexpected
                # Partial credit by Jaccard
                union = actual_set | expected_set
                inter = actual_set & expected_set
                score = (len(inter) / len(union)) if union else 1.0
        else:
            ok = actual_proj == expected_proj
            score = 1.0 if ok else 0.0
            missing = (
                expected_list[len(actual_list) :] if len(expected_list) > len(actual_list) else []
            )
            unexpected = (
                actual_list[len(expected_list) :] if len(actual_list) > len(expected_list) else []
            )

        return ScoreResult(
            scorer=self.name,
            score=score,
            passed=ok,
            critical_failure=bool(spec.critical and not ok),
            message=None if ok else "Set mismatch",
            details={"missing": missing, "unexpected": unexpected},
        )
