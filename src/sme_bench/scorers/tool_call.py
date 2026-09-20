"""Tool-call scorers: required call, no-call, and name allow-list."""

from __future__ import annotations

from typing import Any

from sme_bench.models import BenchmarkTask, ScoreResult, ScorerSpec
from sme_bench.scorers.base import register
from sme_bench.scorers.json_fields import _normalize_for_field, _values_match
from sme_bench.utils import get_by_path


def _calls(parsed_output: Any) -> list[dict[str, Any]]:
    if not isinstance(parsed_output, dict):
        return []
    raw = parsed_output.get("tool_calls") or []
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


@register
class ToolCallScorer:
    name = "tool_call"

    def score(
        self,
        *,
        task: BenchmarkTask,
        output_text: str,
        parsed_output: Any | None,
        spec: ScorerSpec,
    ) -> ScoreResult:
        calls = _calls(parsed_output)
        expected_name = str(spec.params.get("name") or "")
        index = int(spec.params.get("index") or 0)
        exactly_one = bool(spec.params.get("exactly_one", False))
        fields: list[str] = list(spec.params.get("arguments_fields") or [])
        expected = task.expected if isinstance(task.expected, dict) else {}
        expected_args = expected.get("arguments") if isinstance(expected.get("arguments"), dict) else expected

        if exactly_one and len(calls) != 1:
            return ScoreResult(
                scorer=self.name,
                score=0.0,
                passed=False,
                critical_failure=bool(spec.critical),
                message=f"expected exactly one tool call, got {len(calls)}",
            )
        if index >= len(calls):
            return ScoreResult(
                scorer=self.name,
                score=0.0,
                passed=False,
                critical_failure=bool(spec.critical),
                message=f"no tool call at index {index}",
            )
        call = calls[index]
        actual_name = str(call.get("name") or "")
        if expected_name and actual_name != expected_name:
            return ScoreResult(
                scorer=self.name,
                score=0.0,
                passed=False,
                critical_failure=bool(spec.critical),
                message=f"tool name {actual_name!r} != {expected_name!r}",
            )
        arguments = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
        if not fields and isinstance(expected_args, dict):
            fields = list(expected_args.keys())
        if not fields:
            return ScoreResult(scorer=self.name, score=1.0, passed=True)

        matched: list[str] = []
        mismatched: list[str] = []
        normalize = spec.params.get("normalize")
        case_insensitive = bool(spec.params.get("case_insensitive", False))
        match_mode = str(spec.params.get("match", "exact"))
        field_aliases = spec.params.get("field_aliases") or spec.params.get("aliases") or {}
        for path in fields:
            try:
                actual_val = get_by_path(arguments, path)
                expected_val = get_by_path(expected_args, path) if isinstance(expected_args, dict) else None
                aliases = field_aliases.get(path)
                if expected_val is None and isinstance(aliases, list) and isinstance(expected_args, dict):
                    for alias in aliases:
                        try:
                            expected_val = get_by_path(expected_args, alias)
                            break
                        except (KeyError, IndexError, TypeError, ValueError):
                            continue
            except (KeyError, IndexError, TypeError, ValueError):
                mismatched.append(path)
                continue
            actual_cmp = _normalize_for_field(actual_val, path=path, mode=normalize)
            expected_cmp = _normalize_for_field(expected_val, path=path, mode=normalize)
            if _values_match(
                actual_cmp, expected_cmp, match_mode=match_mode, case_insensitive=case_insensitive
            ):
                matched.append(path)
            else:
                mismatched.append(path)
        score = (len(matched) / len(fields)) if fields else 0.0
        ok = not mismatched
        return ScoreResult(
            scorer=self.name,
            score=score,
            passed=ok,
            critical_failure=bool(spec.critical and not ok),
            message=None if ok else f"mismatched arguments: {mismatched}",
        )


@register
class NoToolCallScorer:
    name = "no_tool_call"

    def score(
        self,
        *,
        task: BenchmarkTask,
        output_text: str,
        parsed_output: Any | None,
        spec: ScorerSpec,
    ) -> ScoreResult:
        calls = _calls(parsed_output)
        ok = not calls
        return ScoreResult(
            scorer=self.name,
            score=1.0 if ok else 0.0,
            passed=ok,
            critical_failure=bool(spec.critical and not ok),
            message=None if ok else f"unexpected tool calls: {[c.get('name') for c in calls]}",
        )


@register
class ToolNameValidScorer:
    name = "tool_name_valid"

    def score(
        self,
        *,
        task: BenchmarkTask,
        output_text: str,
        parsed_output: Any | None,
        spec: ScorerSpec,
    ) -> ScoreResult:
        allowed = {tool.name for tool in task.tools}
        calls = _calls(parsed_output)
        unknown = [str(c.get("name") or "") for c in calls if c.get("name") not in allowed]
        ok = not unknown
        return ScoreResult(
            scorer=self.name,
            score=1.0 if ok else 0.0,
            passed=ok,
            critical_failure=bool(spec.critical and not ok),
            message=None if ok else f"unknown tools: {unknown}",
        )
