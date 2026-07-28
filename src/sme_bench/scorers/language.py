"""Language compliance scorer.

A German case answered in English is unusable in practice — the extracted action
items cannot go into a German meeting protocol or ticket system. Before content
0.9.0 that failure surfaced only indirectly, as ``missing`` items in
``set_equality``, and not at all for free-text replies whose scorers check
identifiers and structure only.

The check is deterministic (no LLM judge) and deliberately abstains when the
evidence is thin. It counts *function words* that are unambiguous for one
language and fails only when the wrong language leads by ``margin``. German
business prose is full of English loanwords (``Forecast Q3``, ``BOM``, ``Q3 wine
list``) and structured answers carry English field values by design, so a
single English token must never be enough to fail a case.

JSON *keys* are never scanned: ``missing_fields`` and ``cost_center`` are
English on purpose in both language variants.

Params:
    expected: str — target language code (default: the case ``language``).
    fields: list[str] — restrict scanning to these JSON paths.
    exclude_fields: list[str] — skip these top-level keys. Injection and
        security cases document a refusal in ``reason`` and legitimately quote
        the English payload there; ``forbidden_terms`` excludes the same field
        on the same cases for the same reason.
    margin: int = 2 — how far the other language must lead before failing.
"""

from __future__ import annotations

import re
from typing import Any

from sme_bench.models import BenchmarkTask, ScoreResult, ScorerSpec
from sme_bench.scorers.base import register
from sme_bench.utils import extract_json_payload, get_by_path

# Function words that exist in one language but not (as a common word) in the
# other. Ambiguous tokens are deliberately excluded: ``die`` (EN verb), ``will``
# (DE "wants"), ``also`` (DE "therefore"), ``was`` (DE "what"), ``hat`` (DE
# "has"), ``man`` (DE "one"), plus ``in``, ``an``, ``am``, ``so``, ``rat``.
_DE_MARKERS = frozenset(
    {
        "aber",
        "auf",
        "aus",
        "bei",
        "bereits",
        "bitte",
        "dadurch",
        "daher",
        "damit",
        "das",
        "dass",
        "dem",
        "den",
        "der",
        "des",
        "deshalb",
        "durch",
        "eine",
        "einem",
        "einen",
        "einer",
        "für",
        "freundlichen",
        "geehrte",
        "geehrter",
        "grüßen",
        "haben",
        "innerhalb",
        "ist",
        "jedoch",
        "kann",
        "kein",
        "keine",
        "keinen",
        "können",
        "leider",
        "mit",
        "nach",
        "nicht",
        "noch",
        "oder",
        "sehr",
        "sind",
        "sobald",
        "sowie",
        "über",
        "und",
        "vom",
        "von",
        "werden",
        "wird",
        "wir",
        "zum",
        "zur",
        "zusätzlich",
    }
)
_EN_MARKERS = frozenset(
    {
        "about",
        "additional",
        "and",
        "are",
        "because",
        "been",
        "before",
        "but",
        "can",
        "cannot",
        "could",
        "dear",
        "does",
        "each",
        "from",
        "further",
        "has",
        "have",
        "however",
        "into",
        "its",
        "must",
        "not",
        "of",
        "once",
        "only",
        "onto",
        "our",
        "please",
        "regards",
        "should",
        "since",
        "sincerely",
        "than",
        "that",
        "the",
        "their",
        "there",
        "therefore",
        "these",
        "this",
        "those",
        "thus",
        "to",
        "unfortunately",
        "upon",
        "we",
        "were",
        "which",
        "while",
        "with",
        "within",
        "would",
        "your",
    }
)

_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def _iter_values(value: Any) -> list[str]:
    """Collect string *values* from a structure; keys are never scanned."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for item in value.values():
            out.extend(_iter_values(item))
        return out
    if isinstance(value, list):
        out = []
        for item in value:
            out.extend(_iter_values(item))
        return out
    return []


def _resolve_text(
    *,
    output_text: str,
    parsed_output: Any | None,
    spec: ScorerSpec,
) -> str:
    fields = spec.params.get("fields")
    exclude_fields = spec.params.get("exclude_fields")
    data = parsed_output
    if data is None:
        try:
            data = extract_json_payload(output_text)
        except (ValueError, TypeError):
            data = None

    if not isinstance(data, (dict, list)):
        return output_text

    if isinstance(fields, list):
        parts: list[str] = []
        for path in fields:
            if not isinstance(path, str):
                continue
            try:
                value = get_by_path(data, path)
            except (KeyError, IndexError, TypeError, ValueError):
                continue
            parts.extend(_iter_values(value))
        return "\n".join(parts)

    if isinstance(exclude_fields, list) and isinstance(data, dict):
        excluded = {name for name in exclude_fields if isinstance(name, str)}
        selected = {key: value for key, value in data.items() if key not in excluded}
        return "\n".join(_iter_values(selected))

    return "\n".join(_iter_values(data))


def _count_markers(text: str) -> tuple[int, int]:
    """Return ``(de_markers, en_markers)`` found in *text*."""
    words = [match.group(0).casefold() for match in _WORD_RE.finditer(text)]
    de = sum(1 for word in words if word in _DE_MARKERS)
    en = sum(1 for word in words if word in _EN_MARKERS)
    return de, en


@register
class LanguageScorer:
    name = "language"

    def score(
        self,
        *,
        task: BenchmarkTask,
        output_text: str,
        parsed_output: Any | None,
        spec: ScorerSpec,
    ) -> ScoreResult:
        expected = str(spec.params.get("expected") or task.language)
        margin_raw = spec.params.get("margin", 2)
        margin = margin_raw if isinstance(margin_raw, int) and margin_raw > 0 else 2

        text = _resolve_text(
            output_text=output_text,
            parsed_output=parsed_output,
            spec=spec,
        )
        de_count, en_count = _count_markers(text)
        wants_german = expected.lower().startswith("de")
        target = de_count if wants_german else en_count
        other = en_count if wants_german else de_count

        ok = other < target + margin
        return ScoreResult(
            scorer=self.name,
            score=1.0 if ok else 0.0,
            passed=ok,
            critical_failure=bool(spec.critical and not ok),
            message=(
                None
                if ok
                else (
                    f"Answer language does not match {expected} "
                    f"(de markers {de_count}, en markers {en_count})"
                )
            ),
            details={
                "expected": expected,
                "de_markers": de_count,
                "en_markers": en_count,
                "margin": margin,
            },
        )
