"""Unit tests for run config helpers."""

from __future__ import annotations

from sme_bench.config import (
    DEFAULT_MAX_TOKENS_FLOOR,
    DEFAULT_TIMEOUT_SECONDS,
    THINKING_MAX_TOKENS_MIN,
    THINKING_TIMEOUT_SECONDS,
    RunConfig,
    apply_enable_thinking,
)


def test_safe_defaults() -> None:
    assert DEFAULT_MAX_TOKENS_FLOOR == 8192
    assert DEFAULT_TIMEOUT_SECONDS == 300.0
    assert THINKING_MAX_TOKENS_MIN == DEFAULT_MAX_TOKENS_FLOOR
    assert THINKING_TIMEOUT_SECONDS == DEFAULT_TIMEOUT_SECONDS
    assert RunConfig.model_fields["timeout"].default == DEFAULT_TIMEOUT_SECONDS


def test_effective_max_tokens_floor() -> None:
    cfg = RunConfig(
        base_url="http://localhost:11434/v1",
        model="qwen",
        suite="suites",
        max_tokens_multiplier=8.0,
        max_tokens_floor=DEFAULT_MAX_TOKENS_FLOOR,
    )
    # Short JSON tasks: floor wins over 8×150=1200
    assert cfg.effective_max_tokens(150) == DEFAULT_MAX_TOKENS_FLOOR
    # Longer extraction tasks: floor still wins over 8×350=2800
    assert cfg.effective_max_tokens(350) == DEFAULT_MAX_TOKENS_FLOOR


def test_effective_max_tokens_without_floor() -> None:
    cfg = RunConfig(
        base_url="http://localhost:11434/v1",
        model="qwen",
        suite="suites",
        max_tokens_multiplier=1.0,
        max_tokens_floor=None,
    )
    assert cfg.effective_max_tokens(200) == 200


def test_apply_enable_thinking_merges_kwargs() -> None:
    body = apply_enable_thinking({"temperature": 0.0}, enabled=True)
    assert body["chat_template_kwargs"]["enable_thinking"] is True
    assert body["temperature"] == 0.0
    assert apply_enable_thinking({}, enabled=False) == {}
