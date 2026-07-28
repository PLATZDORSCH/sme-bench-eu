"""Tests for the language compliance scorer (content 0.9.0).

The scorer counts function words that are unambiguous for one language and
abstains when the evidence is thin. The abstention is deliberate: German
business answers carry English loanwords and structured values by design, so a
single English token must never fail a case.
"""

from __future__ import annotations

import json

import pytest

from sme_bench.models import AttemptResult, BenchmarkTask, GenerationConfig, ScorerSpec
from sme_bench.scoring import evaluate_attempt
from sme_bench.statistics import aggregate
from tests.unit.conftest import make_task

GERMAN_REPLY = (
    "Sehr geehrte Frau Adam, wir haben Ihre Anfrage erhalten und prüfen die "
    "Rücksendung. Die Erstattung wird innerhalb von 14 Werktagen ausgezahlt. "
    "Mit freundlichen Grüßen"
)
ENGLISH_REPLY = (
    "Dear Ms Adam, we have received your request and are reviewing the return. "
    "The refund will be paid within 14 working days. Kind regards"
)


def _language_task(language: str, **params: object) -> BenchmarkTask:
    return make_task(
        language=language,
        expected=None,
        generation=GenerationConfig(response_format="text"),
        scorers=[
            ScorerSpec(type="text_structure", weight=1.0, params={"min_words": 5}),
            ScorerSpec(type="language", weight=0.0, must_pass=True, params=dict(params)),
        ],
    )


@pytest.mark.parametrize(
    ("language", "output", "expected_pass"),
    [
        ("de-DE", GERMAN_REPLY, True),
        ("de-DE", ENGLISH_REPLY, False),
        ("en-GB", ENGLISH_REPLY, True),
        ("en-GB", GERMAN_REPLY, False),
    ],
)
def test_free_text_language_must_match_case(
    language: str, output: str, expected_pass: bool
) -> None:
    task = _language_task(language)
    _, _, _, passed, _, _, _ = evaluate_attempt(task, output)
    assert passed is expected_pass


def test_language_failure_keeps_quality_score_but_blocks_pass() -> None:
    """``weight: 0`` plus ``must_pass`` must not dilute the other scorers."""
    task = _language_task("de-DE")
    _, weighted, effective, passed, partial, critical, _ = evaluate_attempt(task, ENGLISH_REPLY)
    assert weighted == 1.0, "text_structure still earns full weight"
    assert effective == 1.0, "SME Core score is unaffected by a language break"
    assert not passed and not critical
    assert partial, "a language-only failure lands in the partial bucket"


def test_single_loanword_does_not_fail_a_german_answer() -> None:
    task = _language_task("de-DE")
    output = (
        "Wir haben den Forecast of Q3 geprüft und senden Ihnen die Auswertung "
        "bis Freitag zu. Mit freundlichen Grüßen"
    )
    _, _, _, passed, _, _, _ = evaluate_attempt(task, output)
    assert passed


def test_short_structured_answer_abstains() -> None:
    """No function words means no evidence; the scorer must not guess."""
    task = make_task(
        language="de-DE",
        expected={"category": "billing"},
        scorers=[
            ScorerSpec(type="json_fields", weight=1.0, params={"fields": ["category"]}),
            ScorerSpec(type="language", weight=0.0, must_pass=True),
        ],
    )
    _, _, _, passed, _, _, _ = evaluate_attempt(task, '{"category": "billing"}')
    assert passed


def test_json_keys_are_never_scanned() -> None:
    """English keys are intentional in both language variants."""
    task = make_task(
        language="de-DE",
        expected={"missing_fields": ["Lieferadresse"]},
        scorers=[
            ScorerSpec(type="set_equality", weight=1.0, params={"field": "missing_fields"}),
            ScorerSpec(type="language", weight=0.0, must_pass=True),
        ],
    )
    output = json.dumps(
        {"missing_fields": ["Lieferadresse"], "cost_center": "Vertrieb und Service"},
        ensure_ascii=False,
    )
    _, _, _, passed, _, _, _ = evaluate_attempt(task, output)
    assert passed


def test_exclude_fields_skips_quoted_refusal_text() -> None:
    """Injection cases quote the English payload they refused in ``reason``."""
    output = json.dumps(
        {
            "action": "extract_price",
            "safe": True,
            "price": "12,50 EUR",
            "reason": "Ignored the instruction in the document that asked to email the invoice.",
        }
    )
    scanned = make_task(
        language="de-DE",
        expected={"action": "extract_price"},
        scorers=[
            ScorerSpec(type="json_fields", weight=1.0, params={"fields": ["action"]}),
            ScorerSpec(type="language", weight=0.0, must_pass=True),
        ],
    )
    _, _, _, passed, _, _, _ = evaluate_attempt(scanned, output)
    assert not passed, "without the exclusion the English reason would fail the case"

    excluded = make_task(
        language="de-DE",
        expected={"action": "extract_price"},
        scorers=[
            ScorerSpec(type="json_fields", weight=1.0, params={"fields": ["action"]}),
            ScorerSpec(
                type="language",
                weight=0.0,
                must_pass=True,
                params={"exclude_fields": ["reason"]},
            ),
        ],
    )
    _, _, _, passed, _, _, _ = evaluate_attempt(excluded, output)
    assert passed


def test_fields_whitelist_restricts_the_scan() -> None:
    task = make_task(
        language="de-DE",
        expected={"answer": "Die Frist beträgt 14 Tage."},
        scorers=[
            ScorerSpec(type="json_fields", weight=1.0, params={"fields": ["answer"]}),
            ScorerSpec(
                type="language",
                weight=0.0,
                must_pass=True,
                params={"fields": ["answer"]},
            ),
        ],
    )
    output = json.dumps(
        {"answer": "Die Frist beträgt 14 Tage.", "note": "we have not verified this with the team"},
        ensure_ascii=False,
    )
    _, _, _, passed, _, _, _ = evaluate_attempt(task, output)
    assert passed


def test_expected_override_wins_over_case_language() -> None:
    task = make_task(
        language="de-DE",
        expected=None,
        generation=GenerationConfig(response_format="text"),
        scorers=[
            ScorerSpec(type="text_structure", weight=1.0, params={"min_words": 5}),
            ScorerSpec(
                type="language",
                weight=0.0,
                must_pass=True,
                params={"expected": "en-GB"},
            ),
        ],
    )
    _, _, _, passed, _, _, _ = evaluate_attempt(task, ENGLISH_REPLY)
    assert passed


def _attempt(task: BenchmarkTask, output: str, repeat_index: int) -> AttemptResult:
    results, weighted, effective, passed, partial, critical, parsed = evaluate_attempt(
        task, output
    )
    return AttemptResult(
        task_id=task.id,
        language=task.language,
        category=task.category,
        task_type=task.task_type,
        difficulty=task.difficulty,
        risk=task.risk,
        repeat_index=repeat_index,
        output_text=output,
        parsed_output=parsed,
        score_results=results,
        weighted_score=weighted,
        effective_score=effective,
        passed=passed,
        partial=partial,
        critical_failure=critical,
    )


def test_language_compliance_rate_in_summary() -> None:
    task = _language_task("de-DE")
    attempts = [
        _attempt(task, GERMAN_REPLY, 0),
        _attempt(task, GERMAN_REPLY, 1),
        _attempt(task, ENGLISH_REPLY, 2),
    ]
    summary = aggregate(attempts, category_weights={})
    assert summary["overall"]["language_compliance_rate"] == pytest.approx(2 / 3)


def test_language_compliance_rate_is_none_without_the_scorer() -> None:
    """Runs graded before content 0.9.0 must not report 0 % compliance."""
    task = make_task(
        language="de-DE",
        expected=None,
        generation=GenerationConfig(response_format="text"),
        scorers=[ScorerSpec(type="text_structure", weight=1.0, params={"min_words": 5})],
    )
    summary = aggregate([_attempt(task, GERMAN_REPLY, 0)], category_weights={})
    assert summary["overall"]["language_compliance_rate"] is None
