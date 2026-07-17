"""Unit tests for pricing."""

from __future__ import annotations

import pytest

from sme_bench.config import PricingConfig
from sme_bench.pricing import estimate_cost


def test_estimate_cost() -> None:
    cost = estimate_cost(
        prompt_tokens=1_000_000,
        completion_tokens=500_000,
        pricing=PricingConfig(input_price_per_million=1.0, output_price_per_million=2.0),
    )
    assert cost == pytest.approx(2.0)
