"""Deterministic mock-tool executor for live multi-turn cases."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any

from sme_bench.models import BenchmarkTask, ToolCall, ToolEnv, ToolHandlerSpec
from sme_bench.utils import resolve_safe_path


def tool_env_fingerprint_payload(env: ToolEnv | None) -> dict[str, Any] | None:
    """Return a stable dump, or None when the env is default-empty (fingerprint-neutral)."""
    if env is None:
        return None
    dump = env.model_dump(exclude_none=True)
    handlers = dump.get("handlers") or []
    follow_ups = dump.get("follow_ups") or []
    max_turns = dump.get("max_turns", 6)
    noise = dump.get("noise", True)
    if not handlers and not follow_ups and max_turns == 6 and noise is True:
        return None
    return dump


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _arguments(call: ToolCall) -> dict[str, Any]:
    return call.parsed_arguments()


def _values_match(expected: Any, actual: Any) -> bool:
    if expected is None or expected == "":
        return actual in (None, "")
    if actual is None:
        return False
    if expected == actual:
        return True
    exp_s = str(expected)
    act_s = str(actual)
    if exp_s == act_s:
        return True
    return exp_s.casefold() in act_s.casefold()


def handler_matches(handler: ToolHandlerSpec, call: ToolCall) -> bool:
    if handler.tool != call.name:
        return False
    if not handler.match:
        return True
    args = _arguments(call)
    return all(_values_match(expected, args.get(key)) for key, expected in handler.match.items())


def with_noise(payload: dict[str, Any], *, tool_name: str, seed: str) -> dict[str, Any]:
    """Attach deterministic extra metadata so the model must pick the real fields."""
    digest = hashlib.sha256(f"{seed}:{tool_name}:{json.dumps(payload, sort_keys=True)}".encode())
    rng = random.Random(int(digest.hexdigest()[:16], 16))
    noisy = dict(payload)
    noisy.setdefault(
        "_meta",
        {
            "request_id": f"req_{rng.randrange(10**8):08d}",
            "ts": "2026-03-20T09:00:00Z",
            "tool": tool_name,
            "trace_id": f"tr_{rng.randrange(10**6):06d}",
        },
    )
    return noisy


class MockToolExecutor:
    """Resolve tool calls against authored handlers. Unknown tools return an error payload."""

    def __init__(
        self,
        task: BenchmarkTask,
        *,
        suite_dir: Path | None = None,
    ) -> None:
        self.task = task
        self.suite_dir = suite_dir
        self.env = task.tool_env or ToolEnv()
        self._consumed: set[int] = set()
        self._resolved: list[dict[str, Any] | None] = [
            self._load_response(handler) for handler in self.env.handlers
        ]

    def _load_response(self, handler: ToolHandlerSpec) -> dict[str, Any] | None:
        if handler.response is not None:
            return dict(handler.response)
        if handler.fixture and self.suite_dir is not None:
            path = resolve_safe_path(self.suite_dir, handler.fixture)
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {"value": data}
        return None

    def execute(self, call: ToolCall) -> dict[str, Any]:
        for index, handler in enumerate(self.env.handlers):
            if index in self._consumed:
                continue
            if not handler_matches(handler, call):
                continue
            if handler.once:
                self._consumed.add(index)
            if handler.error is not None:
                payload: dict[str, Any] = {"error": handler.error.message}
                if handler.error.status is not None:
                    payload["status"] = handler.error.status
                return payload
            response = self._resolved[index]
            if response is None:
                return {"error": f"handler for {handler.tool!r} has no response"}
            if self.env.noise:
                return with_noise(response, tool_name=call.name, seed=self.task.id)
            return dict(response)
        return {"error": f"unknown tool: {call.name}"}
