"""Deterministic structural checks for free-text outputs."""

from __future__ import annotations

import re
from typing import Any

from sme_bench.models import BenchmarkTask, ScoreResult, ScorerSpec
from sme_bench.scorers.base import register
from sme_bench.utils import extract_json_payload, get_by_path


def _count_words(text: str) -> int:
    return len(re.findall(r"\b[\w\u00c0-\u024f'-]+\b", text, flags=re.UNICODE))


def _count_sentences(text: str) -> int:
    chunks = re.split(r"[.!?]+(?:\s+|$)", text.strip())
    return len([c for c in chunks if c.strip()])


def _is_bullet_only(text: str) -> bool:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return False
    return all(re.match(r"^[-*•]\s+\S", ln) for ln in lines)


@register
class TextStructureScorer:
    name = "text_structure"

    def score(
        self,
        *,
        task: BenchmarkTask,
        output_text: str,
        parsed_output: Any | None,
        spec: ScorerSpec,
    ) -> ScoreResult:
        field = spec.params.get("field")
        text = output_text
        if field:
            data = parsed_output
            if data is None:
                try:
                    data = extract_json_payload(output_text)
                except (ValueError, TypeError):
                    data = None
            if isinstance(data, dict):
                try:
                    value = get_by_path(data, field)
                    text = "" if value is None else str(value)
                except (KeyError, IndexError, TypeError, ValueError):
                    text = ""
            else:
                text = ""

        min_words = int(spec.params.get("min_words", 0))
        min_sentences = int(spec.params.get("min_sentences", 0))
        forbid_bullet_only = bool(spec.params.get("forbid_bullet_only", False))

        words = _count_words(text)
        sentences = _count_sentences(text)
        failures: list[str] = []
        if min_words and words < min_words:
            failures.append(f"min_words={min_words} (got {words})")
        if min_sentences and sentences < min_sentences:
            failures.append(f"min_sentences={min_sentences} (got {sentences})")
        if forbid_bullet_only and _is_bullet_only(text):
            failures.append("bullet-only listing")

        ok = not failures
        return ScoreResult(
            scorer=self.name,
            score=1.0 if ok else 0.0,
            passed=ok,
            critical_failure=bool(spec.critical and not ok),
            message=None if ok else "; ".join(failures),
            details={"words": words, "sentences": sentences},
        )
