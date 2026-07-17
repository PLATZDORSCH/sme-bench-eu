"""Runtime configuration models."""

from __future__ import annotations

import json
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
    timeout: float = 120.0
    retries: int = 1
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

    @model_validator(mode="after")
    def concurrency_at_least_one(self) -> RunConfig:
        if self.concurrency < 1:
            raise ValueError("concurrency must be >= 1")
        if self.repeats < 1:
            raise ValueError("repeats must be >= 1")
        return self


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
