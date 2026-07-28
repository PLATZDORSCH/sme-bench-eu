"""Citation ID validation scorer."""

from __future__ import annotations

import re
from typing import Any

from sme_bench.models import BenchmarkTask, ScoreResult, ScorerSpec
from sme_bench.scorers.base import register
from sme_bench.utils import extract_json_payload, get_by_path, normalize_typography

# Leading ``[ID]`` optionally followed by policy text the model copied with the label.
_BRACKETED_ID = re.compile(r"^\[([^\]]+)\](?:\s+.*)?$")


def _normalize_citation(value: Any) -> Any:
    """Normalize a citation ID for comparison.

    Policies label sections as ``[SEC-A]``; models legitimately cite them with or
    without the surrounding brackets. Weak models sometimes paste the whole
    policy line (``[V-1] Standardsteuersatz…``); extract the leading bracketed
    ID in that case. Compare case-insensitively and fold typographic dashes so
    ``SEC‑A`` with a non-breaking hyphen still resolves to ``SEC-A``.
    """
    if not isinstance(value, str):
        return value
    text = normalize_typography(value).strip()
    match = _BRACKETED_ID.match(text)
    text = match.group(1).strip() if match else text.strip("[]").strip()
    return text.casefold()


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

        expected_raw = spec.params.get("expected")
        if expected_raw is None and isinstance(task.expected, dict):
            expected_raw = task.expected.get("citations")
        expected_set = (
            {_normalize_citation(c) for c in expected_raw}
            if isinstance(expected_raw, list)
            else set()
        )

        allowed_norm = {_normalize_citation(c) for c in allowed}
        normalized = [_normalize_citation(c) for c in citations]
        invalid = [c for c in citations if _normalize_citation(c) not in allowed_norm]

        require_unique = bool(spec.params.get("require_unique", False))
        duplicates: list[Any] = []
        if require_unique:
            seen: set[Any] = set()
            for raw, norm in zip(citations, normalized, strict=True):
                if norm in seen:
                    duplicates.append(raw)
                seen.add(norm)

        max_count = spec.params.get("max_count")
        count_ok = not isinstance(max_count, int) or len(citations) <= max_count

        exact_set = bool(spec.params.get("exact_set", False))
        actual_set = set(normalized)
        set_ok = True
        has_expected_list = isinstance(expected_raw, list)
        if exact_set and has_expected_list:
            set_ok = actual_set == expected_set

        require_nonempty = bool(spec.params.get("require_nonempty", True))
        if citations and allowed:
            valid = [c for c in citations if _normalize_citation(c) in allowed_norm]
            score = len(valid) / len(citations)
        elif not citations:
            score = 0.0 if require_nonempty else 1.0
        else:
            score = 0.0

        # Score-effective penalties: extras / duplicates / max_count / exact_set
        # must reduce the weighted contribution, not only flip ``passed``.
        if exact_set and has_expected_list:
            inter = len(actual_set & expected_set)
            union = len(actual_set | expected_set)
            score = (inter / union) if union else 1.0
        if duplicates:
            unique_count = len({_normalize_citation(c) for c in citations})
            score = min(score, unique_count / max(len(citations), 1))
        if not count_ok and isinstance(max_count, int) and max_count >= 0:
            score = min(score, max_count / max(len(citations), 1))
        if invalid:
            score = min(score, 0.0)

        ok = (
            not invalid
            and (bool(citations) if require_nonempty else True)
            and not duplicates
            and count_ok
            and set_ok
        )
        message = None
        if invalid:
            message = f"Invalid citations: {invalid}"
        elif duplicates:
            message = f"Duplicate citations: {duplicates}"
        elif not count_ok:
            message = f"Too many citations: {len(citations)} > {max_count}"
        elif exact_set and not set_ok:
            message = f"Expected citation set {sorted(expected_set)}, got {sorted(actual_set)}"

        return ScoreResult(
            scorer=self.name,
            score=float(score),
            passed=ok,
            critical_failure=bool(spec.critical and not ok),
            message=message,
            details={
                "citations": citations,
                "invalid": invalid,
                "allowed": sorted(allowed),
                "duplicates": duplicates,
                "exact_set_ok": set_ok,
            },
        )
