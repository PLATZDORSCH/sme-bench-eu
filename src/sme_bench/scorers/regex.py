"""Regex scorer."""

from __future__ import annotations

import re
from typing import Any

from sme_bench.models import BenchmarkTask, ScoreResult, ScorerSpec
from sme_bench.scorers.base import register
from sme_bench.utils import normalize_typography


@register
class RegexScorer:
    name = "regex"

    def score(
        self,
        *,
        task: BenchmarkTask,
        output_text: str,
        parsed_output: Any | None,
        spec: ScorerSpec,
    ) -> ScoreResult:
        patterns = spec.params.get("patterns") or []
        if "pattern" in spec.params:
            patterns = [spec.params["pattern"], *patterns]
        flags = re.IGNORECASE if spec.params.get("case_insensitive") else 0
        # Only the haystack is folded; normalizing a pattern would rewrite
        # character classes such as ``[\u2010-\u2015]``.
        haystack = normalize_typography(output_text)
        matched: list[str] = []
        missing: list[str] = []
        for pattern in patterns:
            if re.search(pattern, haystack, flags):
                matched.append(pattern)
            else:
                missing.append(pattern)
        ok = not missing and bool(patterns)
        score = (len(matched) / len(patterns)) if patterns else 0.0
        return ScoreResult(
            scorer=self.name,
            score=score,
            passed=ok,
            critical_failure=bool(spec.critical and not ok),
            message=None if ok else f"Missing patterns: {missing}",
            details={"matched": matched, "missing": missing},
        )
