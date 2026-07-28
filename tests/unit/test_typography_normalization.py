"""Regression tests for typographic Unicode folding in scorers.

Models format identifiers with non-breaking hyphens (U+2011), en dashes, or
narrow no-break spaces (U+202F). Before scoring-spec 0.6.0 those answers were
graded as missing terms even though the identifier was present and correct.
"""

from __future__ import annotations

import pytest

from sme_bench.models import ScorerSpec
from sme_bench.scoring import evaluate_attempt
from sme_bench.utils import normalize_typography, normalize_typography_deep
from tests.unit.conftest import make_task

NBH = "\u2011"  # NON-BREAKING HYPHEN
NNBSP = "\u202f"  # NARROW NO-BREAK SPACE
ENDASH = "\u2013"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (f"#W{NBH}55021", "#W-55021"),
        (f"Bestellung{NNBSP}#W-55021", "Bestellung #W-55021"),
        (f"30{NBH}Tage{NBH}Frist", "30-Tage-Frist"),
        (f"RE{ENDASH}2026{ENDASH}1048", "RE-2026-1048"),
        ("\uff32\uff0d8821", "R-8821"),
        ("don\u2019t", "don't"),
        ("\u201cZitat\u201e", '"Zitat"'),
        ("soft\u00adhyphen", "softhyphen"),
        ("zero\u200bwidth", "zerowidth"),
        ("normal-text 123", "normal-text 123"),
        ("", ""),
    ],
)
def test_normalize_typography(raw: str, expected: str) -> None:
    assert normalize_typography(raw) == expected


def test_normalize_typography_is_idempotent() -> None:
    raw = f"#W{NBH}55021{NNBSP}RE{ENDASH}1"
    once = normalize_typography(raw)
    assert normalize_typography(once) == once


def test_normalize_typography_deep_walks_structures() -> None:
    value = {"ids": [f"A{NBH}1", 7, None], "nested": {"k": f"B{ENDASH}2"}}
    assert normalize_typography_deep(value) == {
        "ids": ["A-1", 7, None],
        "nested": {"k": "B-2"},
    }


def test_contains_accepts_non_breaking_hyphen_in_order_id() -> None:
    """Reproduces the nemotron ``de-ec-reply-002`` misgrade."""
    task = make_task(
        expected=None,
        scorers=[
            ScorerSpec(
                type="contains",
                weight=1.0,
                params={"terms": ["#W-55021", "30", "14"], "mode": "all"},
            )
        ],
    )
    output = (
        f"Ihre R\u00fccksendung der Bestellung{NNBSP}#W{NBH}55021 ist innerhalb der "
        f"30{NBH}Tage{NBH}Frist erlaubt. Die Erstattung erfolgt innerhalb von 14 Werktagen."
    )
    results, weighted, _, passed, _, _, _ = evaluate_attempt(task, output)
    assert passed and weighted == 1.0
    assert results[0].details["missing"] == []


def test_contains_still_reports_genuinely_absent_terms() -> None:
    """Folding must not turn a real omission into a pass."""
    task = make_task(
        expected=None,
        scorers=[
            ScorerSpec(
                type="contains",
                weight=1.0,
                params={"terms": ["#W-55021", "30"], "mode": "all"},
            )
        ],
    )
    results, _, _, passed, _, _, _ = evaluate_attempt(task, f"Bestellung #W{NBH}55021 erhalten.")
    assert not passed
    assert results[0].details["missing"] == ["30"]


@pytest.mark.parametrize("term_id", [f"RE{ENDASH}2026{ENDASH}1048", f"R{NBH}8821"])
def test_contains_word_boundaries_with_folded_dashes(term_id: str) -> None:
    task = make_task(
        expected=None,
        scorers=[
            ScorerSpec(
                type="contains",
                weight=1.0,
                params={
                    "terms": [normalize_typography(term_id)],
                    "mode": "all",
                    "word_boundaries": True,
                },
            )
        ],
    )
    _, _, _, passed, _, _, _ = evaluate_attempt(task, f"Vorgang {term_id} ist offen.")
    assert passed


def test_forbidden_terms_cannot_be_evaded_by_typography() -> None:
    task = make_task(
        expected=None,
        scorers=[
            ScorerSpec(
                type="forbidden_terms",
                weight=0.0,
                critical=True,
                params={"terms": ["instant-credit"]},
            ),
            ScorerSpec(type="contains", weight=1.0, params={"terms": ["ok"]}),
        ],
    )
    _, _, effective, passed, _, critical, _ = evaluate_attempt(
        task, f"ok, we grant instant{NBH}credit today"
    )
    assert critical and not passed and effective == 0.0


def test_regex_folds_haystack_but_not_pattern() -> None:
    """A pattern may still target raw Unicode ranges; the haystack is folded."""
    ascii_task = make_task(
        expected=None,
        scorers=[ScorerSpec(type="regex", weight=1.0, params={"patterns": [r"RE-\d{4}"]})],
    )
    _, _, _, passed, _, _, _ = evaluate_attempt(ascii_task, f"Rechnung RE{ENDASH}2026")
    assert passed

    unicode_task = make_task(
        expected=None,
        scorers=[ScorerSpec(type="regex", weight=1.0, params={"patterns": ["[\u2010-\u2015]"]})],
    )
    _, _, _, passed, _, _, _ = evaluate_attempt(unicode_task, f"RE{ENDASH}2026")
    assert not passed, "folded haystack no longer contains a Unicode dash"


def test_set_equality_exact_folds_dashes() -> None:
    task = make_task(
        expected={"skus": ["SHIRT-221", "HAT-3"]},
        scorers=[
            ScorerSpec(type="set_equality", weight=1.0, params={"field": "skus"}),
        ],
    )
    output = f'{{"skus": ["SHIRT{NBH}221", "HAT{ENDASH}3"]}}'
    _, _, _, passed, _, _, _ = evaluate_attempt(task, output)
    assert passed


def test_set_equality_key_match_folds_dashes_in_values() -> None:
    task = make_task(
        expected={"actions": [{"owner": "Lea", "task": "Angebot senden", "due": "2026-07-20"}]},
        scorers=[
            ScorerSpec(
                type="set_equality",
                weight=1.0,
                params={
                    "field": "actions",
                    "keys": ["owner", "task", "due"],
                    "key_match": {"owner": "exact", "task": "token_subset", "due": "exact"},
                },
            )
        ],
    )
    output = f'{{"actions": [{{"owner": "Lea", "task": "Angebot senden", "due": "2026{NBH}07{NBH}20"}}]}}'
    _, _, _, passed, _, _, _ = evaluate_attempt(task, output)
    assert passed


def test_json_fields_folds_dashes_without_normalize_mode() -> None:
    task = make_task(
        expected={"invoice_id": "RE-2026-1048"},
        scorers=[
            ScorerSpec(type="json_fields", weight=1.0, params={"fields": ["invoice_id"]}),
        ],
    )
    output = f'{{"invoice_id": "RE{ENDASH}2026{ENDASH}1048"}}'
    _, _, _, passed, _, _, _ = evaluate_attempt(task, output)
    assert passed


def test_citations_fold_dashes() -> None:
    task = make_task(
        expected={"citations": ["SEC-A"], "allowed_citations": ["SEC-A", "SEC-B"]},
        scorers=[
            ScorerSpec(
                type="citations",
                weight=1.0,
                params={"field": "citations", "allowed": ["SEC-A", "SEC-B"]},
            )
        ],
    )
    output = f'{{"citations": ["[SEC{NBH}A]"]}}'
    _, _, _, passed, _, _, _ = evaluate_attempt(task, output)
    assert passed


def test_exact_match_folds_typography() -> None:
    task = make_task(
        expected="RE-2026-1048",
        scorers=[
            ScorerSpec(type="exact_match", weight=1.0, params={"expected": "RE-2026-1048"}),
        ],
    )
    _, _, _, passed, _, _, _ = evaluate_attempt(task, f"RE{ENDASH}2026{NBH}1048")
    assert passed
