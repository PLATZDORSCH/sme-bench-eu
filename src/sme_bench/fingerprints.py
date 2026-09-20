"""Task input/scoring fingerprints for safe regrade."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sme_bench.config import SCORING_SPEC_VERSION
from sme_bench.models import BenchmarkTask
from sme_bench.tool_env import tool_env_fingerprint_payload


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def task_input_fingerprint(task: BenchmarkTask) -> str:
    """Hash everything that affects the model prompt and generation settings."""
    payload = {
        "messages": [
            {"role": m.role, "content": m.content or "", "fixture": m.fixture}
            for m in task.messages
        ],
        "generation": task.generation.model_dump(),
    }
    if task.tools:
        payload["tools"] = [spec.model_dump(by_alias=True) for spec in task.tools]
    if task.tool_choice != "auto":
        payload["tool_choice"] = task.tool_choice
    env_payload = tool_env_fingerprint_payload(task.tool_env)
    if env_payload is not None:
        payload["tool_env"] = env_payload
    return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


def task_scoring_fingerprint(task: BenchmarkTask) -> str:
    """Hash expected answers, scorers, and grade thresholds."""
    scorers = [
        {
            "type": s.type,
            "weight": s.weight,
            "critical": s.critical,
            "must_pass": s.must_pass,
            "params": s.params,
        }
        for s in task.scorers
    ]
    payload = {
        "scoring_spec_version": SCORING_SPEC_VERSION,
        "expected": task.expected,
        "pass_threshold": task.pass_threshold,
        "partial_threshold": task.partial_threshold,
        "scorers": scorers,
    }
    return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


def build_task_fingerprints(tasks: list[BenchmarkTask]) -> dict[str, dict[str, str]]:
    """Map task_id → {input, scoring} fingerprints."""
    out: dict[str, dict[str, str]] = {}
    for task in tasks:
        out[task.id] = {
            "input": task_input_fingerprint(task),
            "scoring": task_scoring_fingerprint(task),
        }
    return out
