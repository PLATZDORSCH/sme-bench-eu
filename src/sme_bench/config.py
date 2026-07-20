"""Runtime configuration models."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from sme_bench.utils import normalize_base_url


class PricingConfig(BaseModel):
    input_price_per_million: float | None = None
    output_price_per_million: float | None = None


class RunConfig(BaseModel):
    base_url: str
    model: str
    served_model_name: str | None = None
    api_key_env: str = "OPENAI_API_KEY"
    suite: Path
    languages: list[str] | None = None
    categories: list[str] | None = None
    difficulty: list[str] | None = None
    tags: list[str] | None = None
    repeats: int = 3
    concurrency: int = 1
    seed: int = 42
    timeout: float = 300.0
    retries: int = 1
    max_tokens_multiplier: float = 1.0
    max_tokens_floor: int | None = None
    extra_body: dict[str, Any] = Field(default_factory=dict)
    pricing: PricingConfig = Field(default_factory=PricingConfig)
    save_reasoning: bool = False
    fail_fast: bool = False
    resume: Path | None = None
    output: Path | None = None
    emit_progress: str | None = None
    warmup: bool = True
    dashboard: bool | None = None

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        return normalize_base_url(value)

    @field_validator("repeats", "concurrency", "retries")
    @classmethod
    def positive_ints(cls, value: int) -> int:
        if value < 0:
            raise ValueError("must be >= 0")
        return value

    @field_validator("max_tokens_multiplier")
    @classmethod
    def multiplier_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("max_tokens_multiplier must be > 0")
        return value

    @field_validator("max_tokens_floor")
    @classmethod
    def floor_positive(cls, value: int | None) -> int | None:
        if value is not None and value < 1:
            raise ValueError("max_tokens_floor must be >= 1")
        return value

    @model_validator(mode="after")
    def concurrency_at_least_one(self) -> RunConfig:
        if self.concurrency < 1:
            raise ValueError("concurrency must be >= 1")
        if self.repeats < 1:
            raise ValueError("repeats must be >= 1")
        return self

    def effective_max_tokens(self, task_max_tokens: int) -> int:
        """Apply the per-run multiplier and floor to a task's ``max_tokens``.

        Lets reasoning models (which stream chain-of-thought into ``content``)
        finish thinking *and* emit the final answer instead of being truncated
        mid-reasoning. Neutral by default (multiplier 1.0, no floor).
        """
        value = math.ceil(task_max_tokens * self.max_tokens_multiplier)
        if self.max_tokens_floor is not None:
            value = max(value, self.max_tokens_floor)
        return max(1, value)


def load_extra_body(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("extra_body file must contain a JSON object")
    forbidden = {"model", "messages", "stream", "authorization", "api_key"}
    overlap = forbidden.intersection({k.lower() for k in data})
    # Check exact keys that would silently override request
    blocked = {"model", "messages", "stream"}
    if any(k in data for k in blocked):
        raise ValueError(
            "extra_body must not override model, messages, or stream; "
            f"found: {sorted(k for k in data if k in blocked)}"
        )
    # Soft-check auth-like keys
    auth_keys = [k for k in data if k.lower() in {"authorization", "api_key", "api-key"}]
    if auth_keys:
        raise ValueError(f"extra_body must not contain auth fields: {auth_keys}")
    _ = overlap
    return data


# Safe default completion budget: suite task max_tokens are often 150–400, which
# truncates reasoning models mid-CoT (gpt-oss, Qwen thinking, Nemotron, …).
# Billing is usually on tokens actually generated; the floor is only a ceiling.
DEFAULT_MAX_TOKENS_FLOOR = 8192
# Headroom for an 8k completion budget at modest tok/s (was 120s CLI default).
DEFAULT_TIMEOUT_SECONDS = 300.0
# Back-compat aliases (thinking / enable-thinking docs).
THINKING_MAX_TOKENS_MIN = DEFAULT_MAX_TOKENS_FLOOR
THINKING_TIMEOUT_SECONDS = DEFAULT_TIMEOUT_SECONDS


def apply_enable_thinking(extra_body: dict[str, Any], *, enabled: bool) -> dict[str, Any]:
    """Merge ``chat_template_kwargs.enable_thinking`` into ``extra_body``.

    Used by LiteLLM / vLLM-style endpoints (e.g. Platzdorsch Token Studio, Qwen).
    CLI ``--enable-thinking`` wins over the same key from ``--extra-body-file``.
    Returns a shallow-copied dict; nested ``chat_template_kwargs`` is also copied.
    """
    if not enabled:
        return dict(extra_body)
    merged = dict(extra_body)
    raw_kwargs = merged.get("chat_template_kwargs") or {}
    if not isinstance(raw_kwargs, dict):
        raise ValueError("extra_body.chat_template_kwargs must be a JSON object")
    kwargs = dict(raw_kwargs)
    kwargs["enable_thinking"] = True
    merged["chat_template_kwargs"] = kwargs
    return merged
