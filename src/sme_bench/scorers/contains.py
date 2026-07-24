"""Contains scorer."""

from __future__ import annotations

import re
from typing import Any

from sme_bench.models import BenchmarkTask, ScoreResult, ScorerSpec
from sme_bench.scorers.base import register
from sme_bench.utils import extract_json_payload, get_by_path


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _normalize_term_groups(raw_terms: Any) -> list[list[str]]:
    """Normalize ``terms`` into groups of alternatives.

    Each entry may be a string (exact requirement) or a list/tuple of
    strings (any alternative satisfies the group).
    """
    if not isinstance(raw_terms, list):
        return []
    groups: list[list[str]] = []
    for item in raw_terms:
        if isinstance(item, (list, tuple)):
            alts = [_as_str(t) for t in item if _as_str(t)]
            if alts:
                groups.append(alts)
        else:
            text = _as_str(item)
            if text:
                groups.append([text])
    return groups


def _resolve_haystack(
    *,
    output_text: str,
    parsed_output: Any | None,
    spec: ScorerSpec,
) -> str:
    field = spec.params.get("field")
    fields = spec.params.get("fields")
    if not field and not fields:
        return output_text

    data = parsed_output
    if data is None:
        try:
            data = extract_json_payload(output_text)
        except (ValueError, TypeError):
            return ""

    if isinstance(fields, list):
        parts: list[str] = []
        for path in fields:
            if not isinstance(path, str):
                continue
            try:
                value = get_by_path(data, path) if isinstance(data, dict) else None
            except (KeyError, IndexError, TypeError, ValueError):
                value = None
            if value is not None:
                parts.append(_as_str(value))
        return "\n".join(parts)

    if isinstance(field, str) and isinstance(data, dict):
        try:
            return _as_str(get_by_path(data, field))
        except (KeyError, IndexError, TypeError, ValueError):
            return ""
    return output_text


def _term_present(
    needle: str,
    haystack: str,
    *,
    case_insensitive: bool,
    word_boundaries: bool,
) -> bool:
    if word_boundaries:
        flags = re.IGNORECASE if case_insensitive else 0
        pattern = rf"\b{re.escape(needle)}\b"
        return re.search(pattern, haystack, flags=flags) is not None
    if case_insensitive:
        return needle.casefold() in haystack.casefold()
    return needle in haystack


def _count_occurrences(
    needle: str,
    haystack: str,
    *,
    case_insensitive: bool,
    word_boundaries: bool,
) -> int:
    if word_boundaries:
        flags = re.IGNORECASE if case_insensitive else 0
        pattern = rf"\b{re.escape(needle)}\b"
        return len(re.findall(pattern, haystack, flags=flags))
    if case_insensitive:
        return haystack.casefold().count(needle.casefold())
    return haystack.count(needle)


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
        groups = _normalize_term_groups(raw_terms)
        mode = spec.params.get("mode", "all")
        case_insensitive = bool(spec.params.get("case_insensitive", False))
        word_boundaries = bool(spec.params.get("word_boundaries", False))
        min_count = spec.params.get("min_count")
        max_count = spec.params.get("max_count")
        haystack = _resolve_haystack(
            output_text=output_text,
            parsed_output=parsed_output,
            spec=spec,
        )
        if case_insensitive:
            haystack = haystack.casefold()

        found: list[str] = []
        missing: list[str] = []
        count_violations: list[str] = []
        for group in groups:
            needles = [t.casefold() if case_insensitive else t for t in group]
            hit = next(
                (
                    t
                    for t, n in zip(group, needles, strict=True)
                    if _term_present(
                        n,
                        haystack,
                        case_insensitive=False,
                        word_boundaries=word_boundaries,
                    )
                ),
                None,
            )
            if hit is not None:
                found.append(hit)
                matched_needle = needles[group.index(hit)]
                if min_count is not None or max_count is not None:
                    count = _count_occurrences(
                        matched_needle,
                        haystack,
                        case_insensitive=False,
                        word_boundaries=word_boundaries,
                    )
                    if isinstance(min_count, int) and count < min_count:
                        count_violations.append(f"{hit}: count {count} < {min_count}")
                    if isinstance(max_count, int) and count > max_count:
                        count_violations.append(f"{hit}: count {count} > {max_count}")
            else:
                missing.append(" | ".join(group) if len(group) > 1 else group[0])

        if mode == "any":
            ok = bool(found) and not count_violations
            score = 1.0 if ok else 0.0
        else:
            score = (len(found) / len(groups)) if groups else 0.0
            ok = not missing and not count_violations
        message = None
        if missing:
            message = f"Missing terms: {missing}"
        elif count_violations:
            message = "; ".join(count_violations)
        return ScoreResult(
            scorer=self.name,
            score=score,
            passed=ok,
            critical_failure=bool(spec.critical and not ok),
            message=message,
            details={
                "found": found,
                "missing": missing,
                "mode": mode,
                "count_violations": count_violations,
            },
        )
