"""Trace scorers for live mock-tool loops."""

from __future__ import annotations

import json
from typing import Any

from sme_bench.models import BenchmarkTask, ScoreResult, ScorerSpec, ToolTraceEntry
from sme_bench.scorers.base import register


def _as_entries(parsed_output: Any) -> list[dict[str, Any]]:
    if not isinstance(parsed_output, dict):
        return []
    raw = parsed_output.get("tool_trace") or []
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _entry_name(entry: dict[str, Any]) -> str:
    call = entry.get("call") or {}
    if isinstance(call, dict):
        return str(call.get("name") or "")
    return ""


def _entry_args(entry: dict[str, Any]) -> dict[str, Any]:
    """Return call arguments as a dict.

    OpenAI-compatible servers stream ``arguments`` as a JSON string; the trace
    keeps that raw form, so parse it here before matching (scoring-spec 0.8.1).
    """
    call = entry.get("call") or {}
    if not isinstance(call, dict):
        return {}
    args = call.get("arguments")
    if isinstance(args, dict):
        return args
    if isinstance(args, str) and args.strip():
        try:
            data = json.loads(args)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}
    return {}


def _entry_error(entry: dict[str, Any]) -> bool:
    if entry.get("error"):
        return True
    result = entry.get("result")
    return isinstance(result, dict) and "error" in result


def _expected_calls(task: BenchmarkTask, spec: ScorerSpec) -> list[dict[str, Any]]:
    raw = spec.params.get("calls")
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    expected = task.expected if isinstance(task.expected, dict) else {}
    for key in ("tool_calls", "calls"):
        value = expected.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _call_ok(expected: dict[str, Any], entry: dict[str, Any]) -> bool:
    name = str(expected.get("name") or expected.get("tool") or "")
    if name and _entry_name(entry) != name:
        return False
    exp_args = expected.get("arguments")
    if isinstance(exp_args, dict):
        actual = _entry_args(entry)
        for key, value in exp_args.items():
            if actual.get(key) != value and str(actual.get(key)) != str(value):
                return False
    return True


@register
class TraceCallsScorer:
    name = "trace_calls"

    def score(
        self,
        *,
        task: BenchmarkTask,
        output_text: str,
        parsed_output: Any | None,
        spec: ScorerSpec,
    ) -> ScoreResult:
        entries = _as_entries(parsed_output)
        expected = _expected_calls(task, spec)
        if not expected:
            ok = bool(entries)
            return ScoreResult(
                scorer=self.name,
                score=1.0 if ok else 0.0,
                passed=ok,
                critical_failure=bool(spec.critical and not ok),
                message=None if ok else "no expected calls and empty trace",
            )
        order = str(spec.params.get("order") or "dependency")
        remaining = list(enumerate(entries))
        used_indexes: list[int] = []
        missing: list[str] = []
        for exp in expected:
            found_at: int | None = None
            for pos, (idx, entry) in enumerate(remaining):
                if _call_ok(exp, entry):
                    found_at = pos
                    used_indexes.append(idx)
                    break
            if found_at is None:
                missing.append(str(exp.get("name") or exp.get("tool") or "?"))
            else:
                remaining.pop(found_at)
        if missing:
            return ScoreResult(
                scorer=self.name,
                score=max(0.0, 1.0 - len(missing) / len(expected)),
                passed=False,
                critical_failure=bool(spec.critical),
                message=f"missing calls: {missing}",
            )
        if order == "strict":
            if used_indexes != sorted(used_indexes):
                return ScoreResult(
                    scorer=self.name,
                    score=0.5,
                    passed=False,
                    critical_failure=bool(spec.critical),
                    message="calls occurred out of the required order",
                )
        else:
            dependencies = spec.params.get("dependencies") or []
            name_first: dict[str, int] = {}
            for idx, entry in enumerate(entries):
                name = _entry_name(entry)
                name_first.setdefault(name, idx)
            for pair in dependencies:
                if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                    continue
                producer, consumer = str(pair[0]), str(pair[1])
                if producer not in name_first or consumer not in name_first:
                    return ScoreResult(
                        scorer=self.name,
                        score=0.5,
                        passed=False,
                        critical_failure=bool(spec.critical),
                        message=f"dependency {producer} → {consumer} not observed",
                    )
                if name_first[consumer] < name_first[producer]:
                    return ScoreResult(
                        scorer=self.name,
                        score=0.5,
                        passed=False,
                        critical_failure=bool(spec.critical),
                        message=f"consumer {consumer} ran before {producer}",
                    )
        return ScoreResult(scorer=self.name, score=1.0, passed=True)


@register
class TraceExactlyOnceScorer:
    name = "trace_exactly_once"

    def score(
        self,
        *,
        task: BenchmarkTask,
        output_text: str,
        parsed_output: Any | None,
        spec: ScorerSpec,
    ) -> ScoreResult:
        name = str(spec.params.get("name") or "")
        entries = _as_entries(parsed_output)
        success_only = bool(spec.params.get("success_only", True))
        hits = [
            entry
            for entry in entries
            if _entry_name(entry) == name and (not success_only or not _entry_error(entry))
        ]
        ok = len(hits) == 1
        return ScoreResult(
            scorer=self.name,
            score=1.0 if ok else 0.0,
            passed=ok,
            critical_failure=bool(spec.critical and not ok),
            message=None if ok else f"{name} succeeded {len(hits)} time(s), expected 1",
        )


def _stringify_values(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"error", "status", "message", "_meta"}:
                continue
            found.extend(_stringify_values(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_stringify_values(item))
    elif isinstance(value, bool) or value is None:
        return found
    else:
        text = str(value).strip()
        if text and text not in {"0", "0.0"}:
            found.append(text)
    return found


@register
class TraceNoFabricationScorer:
    name = "trace_no_fabrication"

    def score(
        self,
        *,
        task: BenchmarkTask,
        output_text: str,
        parsed_output: Any | None,
        spec: ScorerSpec,
    ) -> ScoreResult:
        forbidden = [str(item) for item in (spec.params.get("forbidden") or []) if item]
        haystack = output_text or ""
        if not forbidden:
            for entry in _as_entries(parsed_output):
                if not _entry_error(entry):
                    continue
                result = entry.get("result") if isinstance(entry.get("result"), dict) else {}
                forbidden.extend(_stringify_values(result))
        leaked = [term for term in forbidden if term and term in haystack]
        ok = not leaked
        return ScoreResult(
            scorer=self.name,
            score=1.0 if ok else 0.0,
            passed=ok,
            critical_failure=bool(spec.critical and not ok),
            message=None if ok else f"answer reused failed-tool values: {leaked}",
        )


@register
class TracePhaseScorer:
    name = "trace_phase"

    def score(
        self,
        *,
        task: BenchmarkTask,
        output_text: str,
        parsed_output: Any | None,
        spec: ScorerSpec,
    ) -> ScoreResult:
        name = str(spec.params.get("name") or "")
        min_phase = int(spec.params.get("min_phase") or 0)
        hits = [entry for entry in _as_entries(parsed_output) if _entry_name(entry) == name]
        if not hits:
            return ScoreResult(
                scorer=self.name,
                score=0.0,
                passed=False,
                critical_failure=bool(spec.critical),
                message=f"{name} was never called",
            )
        early = [entry for entry in hits if int(entry.get("phase") or 0) < min_phase]
        ok = not early
        return ScoreResult(
            scorer=self.name,
            score=1.0 if ok else 0.0,
            passed=ok,
            critical_failure=bool(spec.critical and not ok),
            message=None if ok else f"{name} called before authorizing user turn {min_phase}",
        )


def entries_from_models(trace: list[ToolTraceEntry]) -> list[dict[str, Any]]:
    return [entry.model_dump(mode="json") for entry in trace]
