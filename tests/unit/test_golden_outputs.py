"""Golden adversarial scoring checks for hardened scorers."""

from __future__ import annotations

import json

import pytest

from sme_bench.models import GenerationConfig, ScorerSpec
from sme_bench.scoring import evaluate_attempt
from tests.unit.conftest import make_task

GOLDEN = [
    pytest.param(
        "grounded_correct",
        make_task(
            expected={"answer": "30 days", "citations": ["SEC-1"]},
            scorers=[
                ScorerSpec(
                    type="json_fields",
                    weight=0.5,
                    params={
                        "fields": ["answer"],
                        "match": "contains",
                        "case_insensitive": True,
                        "normalize": "text",
                    },
                ),
                ScorerSpec(
                    type="citations",
                    weight=0.5,
                    params={
                        "field": "citations",
                        "allowed": ["SEC-1", "SEC-2"],
                        "exact_set": True,
                        "require_unique": True,
                        "expected": ["SEC-1"],
                    },
                ),
            ],
            generation=GenerationConfig(response_format="json"),
        ),
        '{"answer":"You have 30 days to return an item.","citations":["SEC-1"]}',
        True,
        id="grounded-correct",
    ),
    pytest.param(
        "grounded_extra_citation",
        make_task(
            expected={"answer": "30 days", "citations": ["SEC-1"]},
            scorers=[
                ScorerSpec(
                    type="citations",
                    weight=1.0,
                    params={
                        "field": "citations",
                        "allowed": ["SEC-1", "SEC-2"],
                        "exact_set": True,
                        "require_unique": True,
                        "expected": ["SEC-1"],
                        "max_count": 1,
                    },
                )
            ],
            generation=GenerationConfig(response_format="json"),
        ),
        '{"answer":"30 days","citations":["SEC-1","SEC-2"]}',
        False,
        id="grounded-extra-citation",
    ),
    pytest.param(
        "grounded_percent_19",
        make_task(
            expected={"answer": "19%", "citations": ["V-1"]},
            scorers=[
                ScorerSpec(
                    type="json_fields",
                    weight=1.0,
                    params={
                        "fields": ["answer"],
                        "match": "contains",
                        "case_insensitive": True,
                        "normalize": "text",
                        "field_normalize": {"answer": "percent"},
                    },
                )
            ],
            generation=GenerationConfig(response_format="json"),
        ),
        '{"answer":"19%","citations":["V-1"]}',
        True,
        id="grounded-19-percent",
    ),
    pytest.param(
        "grounded_unicode_range",
        make_task(
            expected={"answer": "2-4", "citations": ["L-1"]},
            scorers=[
                ScorerSpec(
                    type="json_fields",
                    weight=1.0,
                    params={
                        "fields": ["answer"],
                        "match": "contains",
                        "case_insensitive": True,
                        "normalize": "text",
                    },
                )
            ],
            generation=GenerationConfig(response_format="json"),
        ),
        '{"answer":"2–4 Werktage","citations":["L-1"]}',
        True,
        id="grounded-unicode-range",
    ),
    pytest.param(
        "grounded_localized_days",
        make_task(
            expected={"answer": "14 Tage", "citations": ["H-1"]},
            language="de-DE",
            scorers=[
                ScorerSpec(
                    type="json_fields",
                    weight=1.0,
                    params={
                        "fields": ["answer"],
                        "match": "contains",
                        "case_insensitive": True,
                        "normalize": "text",
                    },
                )
            ],
            generation=GenerationConfig(response_format="json"),
        ),
        '{"answer":"Nachbesserung innerhalb von 14 Tagen.","citations":["H-1"]}',
        True,
        id="grounded-localized-14-tage",
    ),
    pytest.param(
        "grounded_wrong_answer_right_cite",
        make_task(
            expected={"answer": "30 days", "citations": ["SEC-1"]},
            pass_threshold=0.85,
            scorers=[
                ScorerSpec(
                    type="json_fields",
                    weight=0.55,
                    params={
                        "fields": ["answer"],
                        "match": "contains",
                        "case_insensitive": True,
                    },
                ),
                ScorerSpec(
                    type="citations",
                    weight=0.45,
                    params={
                        "field": "citations",
                        "allowed": ["SEC-1", "SEC-2"],
                        "exact_set": True,
                        "expected": ["SEC-1"],
                    },
                ),
            ],
            generation=GenerationConfig(response_format="json"),
        ),
        '{"answer":"90 days lifetime warranty","citations":["SEC-1"]}',
        False,
        id="grounded-wrong-answer-right-cite",
    ),
    pytest.param(
        "meeting_keyword_stuffing",
        make_task(
            expected={
                "actions": [
                    {"owner": "Lea", "task": "send quote", "due": "2026-07-20"},
                    {"owner": "Omar", "task": "update stock", "due": "2026-07-18"},
                ]
            },
            scorers=[
                ScorerSpec(
                    type="set_equality",
                    weight=1.0,
                    params={
                        "field": "actions",
                        "keys": ["owner", "task", "due"],
                        "key_match": {"task": "substring", "owner": "exact", "due": "exact"},
                    },
                )
            ],
            generation=GenerationConfig(response_format="json"),
        ),
        json.dumps(
            {
                "actions": [
                    {"owner": "Lea", "task": "misc", "due": "2026-07-20"},
                    {"owner": "Omar", "task": "misc", "due": "2026-07-18"},
                ]
            }
        ),
        False,
        id="meeting-wrong-task-pairing",
    ),
    pytest.param(
        "negated_g12_claim",
        make_task(
            scorers=[
                ScorerSpec(
                    type="forbidden_terms",
                    weight=0,
                    critical=True,
                    params={
                        "ignore_negated": True,
                        "mode": "claims",
                        "terms": [
                            "Ausgleich mit G-12",
                            "G-12 verrechnen",
                            "G-12",
                        ],
                    },
                ),
                ScorerSpec(
                    type="contains",
                    weight=1.0,
                    params={"terms": ["RE-2026"], "mode": "all"},
                ),
            ],
        ),
        "Zu RE-2026: kein Ausgleich mit G-12 und keine Verrechnung zugesagt.",
        True,
        id="negated-g12-allowed",
    ),
    pytest.param(
        "adjacent_classification_weighted_pass",
        make_task(
            expected={"priority": "urgent"},
            pass_threshold=0.85,
            scorers=[
                ScorerSpec(
                    type="classification",
                    weight=0.3,
                    params={
                        "field": "priority",
                        "expected": "urgent",
                        "allowed": ["low", "medium", "high", "urgent"],
                        "scale": ["low", "medium", "high", "urgent"],
                        "adjacent_credit": 0.5,
                    },
                ),
                ScorerSpec(
                    type="contains",
                    weight=0.7,
                    params={"terms": ["billing"], "mode": "all"},
                ),
            ],
            generation=GenerationConfig(response_format="json"),
        ),
        # classification adjacent 0.5 * 0.3 + contains 1.0 * 0.7 = 0.85 → pass
        # (must NOT be blocked by all_positive_passed)
        '{"priority":"high","notes":"billing queue"}',
        True,
        id="adjacent-credit-weighted-pass",
    ),
    pytest.param(
        "iban_reason_only",
        make_task(
            expected={
                "action": "use_invoice_iban",
                "safe": True,
                "iban_used": "DE11 2222 3333 4444 5555 66",
            },
            scorers=[
                ScorerSpec(
                    type="json_fields",
                    weight=1.0,
                    params={
                        "fields": ["action", "safe", "iban_used"],
                        "field_normalize": {"iban_used": "iban"},
                    },
                )
            ],
            generation=GenerationConfig(response_format="json"),
        ),
        '{"action":"use_invoice_iban","safe":true,"reason":"DE11222233334444555566"}',
        False,
        id="iban-reason-only-leak",
    ),
]


@pytest.mark.parametrize(("name", "task", "output", "expected_pass"), GOLDEN)
def test_golden_outputs(name: str, task, output: str, expected_pass: bool) -> None:
    del name
    _, _, _, passed, _, _, _ = evaluate_attempt(task, output)
    assert passed is expected_pass
