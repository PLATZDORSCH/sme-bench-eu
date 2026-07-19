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
        haystack = output_text.casefold() if case_insensitive else output_text

        found: list[str] = []
        missing: list[str] = []
        for group in groups:
            needles = [t.casefold() if case_insensitive else t for t in group]
            hit = next((t for t, n in zip(group, needles, strict=True) if n in haystack), None)
            if hit is not None:
                found.append(hit)
            else:
                missing.append(" | ".join(group) if len(group) > 1 else group[0])

        if mode == "any":
            ok = bool(found)
            score = 1.0 if ok else 0.0
        else:
            score = (len(found) / len(groups)) if groups else 0.0
            ok = not missing
        return ScoreResult(
            scorer=self.name,
            score=score,
            passed=ok,
            critical_failure=bool(spec.critical and not ok),
            message=None if ok else f"Missing terms: {missing}",
            details={"found": found, "missing": missing, "mode": mode},
        )
