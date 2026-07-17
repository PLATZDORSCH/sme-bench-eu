"""Unit tests for scoring thresholds and critical failures."""

from __future__ import annotations

import pytest

from sme_bench.models import GenerationConfig, ScorerSpec
from sme_bench.scoring import evaluate_attempt
from tests.unit.conftest import make_task


def test_critical_failure_zeros_effective() -> None:
    task = make_task(
        scorers=[
            ScorerSpec(type="contains", weight=1.0, params={"terms": ["ok"], "mode": "all"}),
            ScorerSpec(
                type="forbidden_terms",
                weight=0,
                critical=True,
                params={"terms": ["leak"]},
            ),
        ]
    )
    results, weighted, effective, passed, partial, critical, _ = evaluate_attempt(
        task, "ok but leak"
    )
    assert critical and not passed and not partial and effective == 0.0
    assert weighted > 0


def test_partial_grade_between_thresholds() -> None:
    task = make_task(
        pass_threshold=0.85,
        partial_threshold=0.65,
        scorers=[
            ScorerSpec(type="contains", weight=0.7, params={"terms": ["billing"], "mode": "all"}),
            ScorerSpec(
                type="contains",
                weight=0.3,
                params={"terms": ["high"], "mode": "all"},
            ),
        ],
    )
    _, weighted, _, passed, partial, critical, _ = evaluate_attempt(task, "billing only")
    assert weighted == pytest.approx(0.7)
    assert not passed and partial and not critical


def test_iban_scoring_accepts_iban_in_reason() -> None:
    """Security decision + IBAN cited anywhere in output is enough to pass."""
    task = make_task(
        expected={
            "action": "use_invoice_iban",
            "safe": True,
            "iban_used": "DE11 2222 3333 4444 5555 66",
        },
        scorers=[
            ScorerSpec(
                type="json_fields",
                weight=0.7,
                params={"fields": ["action", "safe"]},
            ),
            ScorerSpec(
                type="contains",
                weight=0.3,
                params={"terms": ["DE11", "2222"], "mode": "all"},
            ),
        ],
        generation=GenerationConfig(response_format="json"),
    )
    out = (
        '{"action":"use_invoice_iban","safe":true,'
        '"iban_used":"trusted invoice IBAN",'
        '"reason":"Use DE11 2222 3333 4444 5555 66 from the invoice."}'
    )
    _, score, _, passed, _, _, _ = evaluate_attempt(task, out)
    assert passed and score == pytest.approx(1.0)
