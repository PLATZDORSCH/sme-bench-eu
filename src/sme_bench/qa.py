"""Oracle, nop/trivial, and canary quality checks for loaded tasks."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from sme_bench.models import (
    CANARY_BANNER,
    CANARY_GUID_PREFIX,
    BenchmarkTask,
)
from sme_bench.scoring import evaluate_attempt, is_format_only_failure

CANARY_LINE_RE = re.compile(
    rf"^#\s*{re.escape(CANARY_BANNER)}\s+{re.escape(CANARY_GUID_PREFIX)}\s+"
    r"(?P<guid>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\s*$"
)

def render_oracle_output(task: BenchmarkTask) -> str | None:
    """Return a candidate oracle string, or None if one cannot be derived."""
    if task.oracle_output is not None:
        return task.oracle_output
    expected = task.expected
    if isinstance(expected, (dict, list)):
        return json.dumps(expected, ensure_ascii=False, default=str)
    if isinstance(expected, str):
        return expected
    if expected is None:
        return _synthesize_text_oracle(task)
    return str(expected)


def _contains_terms(task: BenchmarkTask) -> list[str]:
    terms: list[str] = []
    for spec in task.scorers:
        if spec.type != "contains":
            continue
        raw = spec.params.get("terms") or spec.params.get("required") or []
        if isinstance(raw, str):
            terms.append(raw)
            continue
        if not isinstance(raw, list):
            continue
        for item in raw:
            if isinstance(item, list) and item:
                terms.append(str(item[0]))
            elif item is not None:
                terms.append(str(item))
    return terms


def _synthesize_text_oracle(task: BenchmarkTask) -> str | None:
    terms = _contains_terms(task)
    if not terms:
        return None
    body = ", ".join(terms)
    if task.language.startswith("de"):
        return (
            f"Guten Tag, hiermit bestätigen wir die Angaben {body}. "
            "Mit freundlichen Grüßen"
        )
    return f"Hello, we hereby confirm the details {body}. Kind regards"


def _blanked_expected(expected: Any) -> Any:
    if isinstance(expected, dict):
        blanked: dict[str, Any] = {}
        for key, value in expected.items():
            if isinstance(value, list):
                blanked[key] = []
            elif isinstance(value, dict):
                blanked[key] = _blanked_expected(value)
            elif isinstance(value, bool):
                blanked[key] = False
            elif isinstance(value, (int, float)):
                blanked[key] = 0
            else:
                blanked[key] = None
        return blanked
    if isinstance(expected, list):
        return []
    return None


def check_oracle(task: BenchmarkTask) -> tuple[bool, str]:
    """Return (ok, message). ok means the rendered oracle fully passes."""
    output = render_oracle_output(task)
    if output is None:
        return False, "no oracle_output and expected is not renderable"
    tool_calls = None
    tool_trace = None
    tool_scorers = {
        "tool_call",
        "no_tool_call",
        "tool_name_valid",
        "trace_calls",
        "trace_exactly_once",
        "trace_no_fabrication",
        "trace_phase",
    }
    if task.tools or any(s.type in tool_scorers for s in task.scorers):
        from sme_bench.models import ToolCall, ToolTraceEntry

        expected = task.expected if isinstance(task.expected, dict) else {}
        if "tool_calls" in expected and isinstance(expected["tool_calls"], list):
            tool_calls = [
                ToolCall.model_validate(item) if isinstance(item, dict) else item
                for item in expected["tool_calls"]
            ]
        elif expected.get("name") or expected.get("tool"):
            tool_calls = [
                ToolCall(
                    name=str(expected.get("name") or expected.get("tool")),
                    arguments=expected.get("arguments") or {},
                )
            ]
        raw_trace = expected.get("tool_trace")
        if isinstance(raw_trace, list):
            tool_trace = [
                ToolTraceEntry.model_validate(item) if isinstance(item, dict) else item
                for item in raw_trace
            ]
        elif tool_calls:
            tool_trace = [
                ToolTraceEntry(call=call, result={}, turn_index=idx, phase=0)
                for idx, call in enumerate(tool_calls)
            ]
    _results, _w, _e, passed, _partial, critical, _parsed = evaluate_attempt(
        task, output, tool_calls=tool_calls, tool_trace=tool_trace
    )
    if passed and not critical:
        return True, "oracle passed"
    return False, f"oracle did not pass (passed={passed}, critical={critical})"


def check_nop(task: BenchmarkTask) -> list[tuple[str, str, bool, bool]]:
    """Score trivial outputs. Each item is (label, output, passed, partial)."""
    outputs: list[tuple[str, str]] = [("", ""), ("empty_object", "{}"), ("empty_array", "[]")]
    blanked = _blanked_expected(task.expected)
    if isinstance(blanked, (dict, list)):
        outputs.append(("blanked_expected", json.dumps(blanked, ensure_ascii=False)))
    findings: list[tuple[str, str, bool, bool]] = []
    for label, output in outputs:
        _r, _w, _e, passed, partial, _c, _p = evaluate_attempt(task, output)
        findings.append((label, output, passed, partial))
    return findings


def parse_canary_header(raw_text: str) -> str | None:
    """Return the canary GUID from the first non-empty line, if present."""
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        match = CANARY_LINE_RE.match(stripped)
        if match:
            return match.group("guid")
        return None
    return None


def format_canary_header(guid: str) -> str:
    return f"# {CANARY_BANNER} {CANARY_GUID_PREFIX} {guid}"


def read_canary_guid(path: Path) -> str | None:
    return parse_canary_header(path.read_text(encoding="utf-8"))


__all__ = [
    "CANARY_LINE_RE",
    "check_nop",
    "check_oracle",
    "format_canary_header",
    "is_format_only_failure",
    "parse_canary_header",
    "read_canary_guid",
    "render_oracle_output",
]
