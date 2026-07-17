"""Pricing helpers."""

from __future__ import annotations

from sme_bench.config import PricingConfig


def estimate_cost(
    *,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    pricing: PricingConfig,
) -> float | None:
    if pricing.input_price_per_million is None and pricing.output_price_per_million is None:
        return None
    if prompt_tokens is None and completion_tokens is None:
        return None
    cost = 0.0
    if pricing.input_price_per_million is not None and prompt_tokens is not None:
        cost += (prompt_tokens / 1_000_000) * pricing.input_price_per_million
    if pricing.output_price_per_million is not None and completion_tokens is not None:
        cost += (completion_tokens / 1_000_000) * pricing.output_price_per_million
    return cost
