"""Strict scorer-parameter validation tests."""

from __future__ import annotations

import pytest

from sme_bench.models import ScorerSpec
from sme_bench.scorer_specs import validate_scorer_spec


@pytest.mark.parametrize(
    "spec",
    [
        ScorerSpec(type="citations", weight=1, params={"allowed": "SEC-1"}),
        ScorerSpec(type="set_equality", weight=1, params={"keys": "sku"}),
        ScorerSpec(type="json_fields", weight=1, params={"fields": "answer"}),
        ScorerSpec(type="set_equality", weight=1, params={"key_match": ["sku"]}),
        ScorerSpec(type="json_fields", weight=1, params={"patterns": ["x"]}),
        ScorerSpec(type="json_fields", weight=1, params={"patterns": {"answer": "["}}),
        ScorerSpec(type="json_fields", weight=1, params={"field_aliases": {"answer": "x"}}),
        ScorerSpec(type="regex", weight=1, params={"patterns": ["["]}),
    ],
)
def test_strict_validation_rejects_bad_parameter_shapes(spec: ScorerSpec) -> None:
    issues = validate_scorer_spec(spec, path="case.yaml", strict=True)
    assert any(issue.severity == "error" for issue in issues)


def test_strict_validation_accepts_valid_structured_params() -> None:
    spec = ScorerSpec(
        type="set_equality",
        weight=1,
        params={
            "field": "items",
            "keys": ["sku", "qty"],
            "key_match": {"sku": "exact", "qty": "exact"},
            "key_aliases": {"sku": {"A-1": ["A1"]}},
        },
    )
    assert not validate_scorer_spec(spec, path="case.yaml", strict=True)
