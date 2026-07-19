"""Markdown outcome reports (failures.*.md / success.*.md) with full case context."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Literal

from sme_bench.models import AttemptResult, BenchmarkTask
from sme_bench.reporters.i18n import FAILURES, REPORT_LANGS, SUCCESS, Lang, report_path
from sme_bench.reporters.task_docs import task_brief
from sme_bench.statistics import dedupe_attempts

OutcomeKind = Literal["pass", "partial", "fail", "critical"]


def _truncate(text: str, limit: int = 4000) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _fmt_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, indent=2, default=str)
    except TypeError:
        return str(value)


def _attempt_status(attempt: AttemptResult, *, lang: Lang) -> str:
    t = FAILURES[lang]
    if attempt.infrastructure_error:
        return t["status_infra"]
    if attempt.critical_failure:
        return t["status_critical"]
    if attempt.passed:
        return t["status_pass"]
    if attempt.partial:
        return t["status_partial"]
    return t["status_fail"]


def _failed_scorers(attempt: AttemptResult, *, lang: Lang) -> list[str]:
    t = FAILURES[lang]
    lines: list[str] = []
    for result in attempt.score_results:
        if result.passed:
            continue
        crit = t["ko"] if result.critical_failure else ""
        msg = f" — {result.message}" if result.message else ""
        lines.append(f"- `{result.scorer}`: Score {result.score:.2f}{crit}{msg}")
    if attempt.infrastructure_error:
        lines.append(t["infra_line"].format(error=attempt.error_type or "error"))
    return lines


def _passed_scorers(attempt: AttemptResult) -> list[str]:
    lines: list[str] = []
    for result in attempt.score_results:
        if not result.passed:
            continue
        lines.append(f"- `{result.scorer}`: Score {result.score:.2f}")
    return lines


def _task_aggregate(attempts: list[AttemptResult]) -> dict[str, Any]:
    passed = sum(1 for a in attempts if a.passed)
    partial = sum(1 for a in attempts if a.partial)
    critical = sum(1 for a in attempts if a.critical_failure)
    infra = sum(1 for a in attempts if a.infrastructure_error)
    hard_fail = sum(
        1
        for a in attempts
        if not a.passed and not a.partial and not a.infrastructure_error
    )
    scores = [a.effective_score for a in attempts]
    n = len(attempts)
    return {
        "attempts": n,
        "passed": passed,
        "partial": partial,
        "critical": critical,
        "infra": infra,
        "hard_fail": hard_fail,
        "reliable_pass": passed == n and n > 0,
        "reliable_partial": passed + partial == n and n > 0 and passed != n,
        "mean_score": sum(scores) / n if scores else 0.0,
    }


def _task_outcome(agg: dict[str, Any]) -> OutcomeKind:
    if agg["reliable_pass"]:
        return "pass"
    if agg["critical"] > 0:
        return "critical"
    if agg["reliable_partial"]:
        return "partial"
    return "fail"


def _user_task_text(task: BenchmarkTask) -> str:
    parts: list[str] = []
    for msg in task.messages:
        if msg.role != "user":
            continue
        if msg.content:
            parts.append(msg.content.strip())
        elif msg.fixture:
            parts.append(f"(Fixture: `{msg.fixture}`)")
    return "\n\n".join(parts) if parts else "—"


def _system_task_text(task: BenchmarkTask) -> str:
    for msg in task.messages:
        if msg.role == "system" and msg.content:
            return msg.content.strip()
    return "—"


def _expected_text(task: BenchmarkTask, *, lang: Lang) -> str:
    t = FAILURES[lang]
    if task.expected is not None:
        return _fmt_json(task.expected)
    bits: list[str] = []
    for spec in task.scorers:
        if spec.type == "contains":
            terms = spec.params.get("terms") or []
            if terms:
                bits.append(t["required_contains"].format(terms=terms))
        if spec.type == "forbidden_terms":
            terms = spec.params.get("terms") or []
            if terms:
                bits.append(t["forbidden"].format(terms=terms))
        if spec.type == "exact_match" and "expected" in spec.params:
            bits.append(f"exact_match: {spec.params['expected']!r}")
        if spec.type == "classification" and "expected" in spec.params:
            field = spec.params.get("field", "label")
            bits.append(f"{field} = {spec.params['expected']!r}")
    return "\n".join(bits) if bits else t["no_expected"]


def _case_context(task: BenchmarkTask | None, *, lang: Lang) -> list[str]:
    t = FAILURES[lang]
    if task is None:
        return [
            t["task_missing"],
            "",
            f"{t['expected_heading']} —",
            "",
        ]

    lines = [
        t["task_system"],
        "",
        "```",
        _truncate(_system_task_text(task), 2000),
        "```",
        "",
        t["task_user"],
        "",
        "```",
        _truncate(_user_task_text(task), 4000),
        "```",
        "",
        t["expected_heading"],
        "",
        "```json" if task.expected is not None else "```",
        _truncate(_expected_text(task, lang=lang), 4000),
        "```",
        "",
    ]
    return lines


def _model_output_block(attempt: AttemptResult, *, lang: Lang) -> list[str]:
    t = FAILURES[lang]
    text = attempt.output_text or ""
    if not text and attempt.infrastructure_error:
        text = attempt.error_message or t["empty_infra"]
    if not text:
        text = t["empty_output"]
    return [
        t["model_output"],
        "",
        "```",
        _truncate(text),
        "```",
        "",
    ]


def _group_attempts(
    attempts: list[AttemptResult],
) -> dict[OutcomeKind, list[tuple[str, dict[str, Any], list[AttemptResult]]]]:
    attempts = dedupe_attempts(attempts)
    by_task: dict[str, list[AttemptResult]] = defaultdict(list)
    for attempt in attempts:
        by_task[attempt.task_id].append(attempt)

    grouped: dict[OutcomeKind, list[tuple[str, dict[str, Any], list[AttemptResult]]]] = {
        "critical": [],
        "fail": [],
        "partial": [],
        "pass": [],
    }
    for task_id, task_attempts in by_task.items():
        agg = _task_aggregate(task_attempts)
        grouped[_task_outcome(agg)].append((task_id, agg, task_attempts))
    return grouped


def write_failures_markdown(
    path: Path,
    attempts: list[AttemptResult],
    *,
    model: str,
    suite_id: str = "",
    suite_version: str = "",
    tasks_by_id: dict[str, BenchmarkTask] | None = None,
    lang: Lang = "de",
) -> None:
    """Write a failures report in the given language."""
    t = FAILURES[lang]
    tasks_by_id = tasks_by_id or {}
    grouped = _group_attempts(attempts)
    total_tasks = sum(len(v) for v in grouped.values())
    reliable_pass = len(grouped["pass"])
    reliable_partial = len(grouped["partial"])
    total_critical_attempts = sum(1 for a in attempts if a.critical_failure)

    lines = [
        t["title"].format(model=model),
        "",
        t["suite"].format(suite_id=suite_id, suite_version=suite_version).rstrip(),
        t["full_pass"].format(n=reliable_pass, total=total_tasks),
        t["partial"].format(n=reliable_partial, total=total_tasks),
        t["hard_fail"].format(n=len(grouped["fail"]), total=total_tasks),
        t["critical_attempts"].format(n=total_critical_attempts),
        "",
        t["intro"],
        "",
        t["see_also"].format(lang=lang),
        "",
    ]

    if not grouped["critical"] and not grouped["fail"] and not grouped["partial"]:
        lines.extend([t["all_passed"], ""])
        path.write_text("\n".join(lines), encoding="utf-8")
        return

    if grouped["critical"]:
        lines.extend([t["section_critical"], ""])
        for task_id, agg, task_attempts in sorted(grouped["critical"], key=lambda x: x[0]):
            lines.extend(
                _outcome_block(
                    task_id, agg, task_attempts, tasks_by_id, mode="failure", lang=lang
                )
            )
            lines.append("")

    if grouped["fail"]:
        lines.extend([t["section_fail"], ""])
        for task_id, agg, task_attempts in sorted(grouped["fail"], key=lambda x: x[0]):
            lines.extend(
                _outcome_block(
                    task_id, agg, task_attempts, tasks_by_id, mode="failure", lang=lang
                )
            )
            lines.append("")

    if grouped["partial"]:
        lines.extend([t["section_partial"], "", t["partial_blurb"], ""])
        for task_id, agg, task_attempts in sorted(grouped["partial"], key=lambda x: x[0]):
            lines.extend(
                _outcome_block(
                    task_id, agg, task_attempts, tasks_by_id, mode="failure", lang=lang
                )
            )
            lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_success_markdown(
    path: Path,
    attempts: list[AttemptResult],
    *,
    model: str,
    suite_id: str = "",
    suite_version: str = "",
    tasks_by_id: dict[str, BenchmarkTask] | None = None,
    lang: Lang = "de",
) -> None:
    """Write a success report in the given language."""
    t = SUCCESS[lang]
    tasks_by_id = tasks_by_id or {}
    grouped = _group_attempts(attempts)
    total_tasks = sum(len(v) for v in grouped.values())
    reliable_pass = len(grouped["pass"])

    lines = [
        t["title"].format(model=model),
        "",
        t["suite"].format(suite_id=suite_id, suite_version=suite_version).rstrip(),
        t["full_pass"].format(n=reliable_pass, total=total_tasks),
        "",
        t["intro"].format(lang=lang),
        "",
    ]

    if not grouped["pass"]:
        lines.extend(
            [
                t["none"],
                "",
                t["see_failures"].format(lang=lang),
                "",
            ]
        )
        path.write_text("\n".join(lines), encoding="utf-8")
        return

    lines.extend([t["section"], ""])
    for task_id, agg, task_attempts in sorted(grouped["pass"], key=lambda x: x[0]):
        lines.extend(
            _outcome_block(
                task_id, agg, task_attempts, tasks_by_id, mode="success", lang=lang
            )
        )
        lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_failures_reports(
    run_dir: Path,
    attempts: list[AttemptResult],
    **kwargs: Any,
) -> list[Path]:
    written: list[Path] = []
    for lang in REPORT_LANGS:
        path = run_dir / report_path("failures", lang)
        write_failures_markdown(path, attempts, lang=lang, **kwargs)
        written.append(path)
    return written


def write_success_reports(
    run_dir: Path,
    attempts: list[AttemptResult],
    **kwargs: Any,
) -> list[Path]:
    written: list[Path] = []
    for lang in REPORT_LANGS:
        path = run_dir / report_path("success", lang)
        write_success_markdown(path, attempts, lang=lang, **kwargs)
        written.append(path)
    return written


def _outcome_block(
    task_id: str,
    agg: dict[str, Any],
    task_attempts: list[AttemptResult],
    tasks_by_id: dict[str, BenchmarkTask],
    *,
    mode: Literal["failure", "success"],
    lang: Lang,
) -> list[str]:
    t = FAILURES[lang]
    task = tasks_by_id.get(task_id)
    brief = task_brief(task, lang=lang) if task else None

    title = brief["title"] if brief else task_id
    outcome = _task_outcome(agg)
    outcome_label = {
        "pass": t["outcome_pass"],
        "partial": t["outcome_partial"],
        "fail": t["outcome_fail"],
        "critical": t["outcome_critical"],
    }[outcome]

    lines = [
        f"### `{task_id}` — {title}",
        "",
        t["result_line"].format(
            passed=agg["passed"],
            attempts=agg["attempts"],
            partial=agg["partial"],
            mean=agg["mean_score"],
            outcome=outcome_label,
        ),
    ]

    if brief:
        lines.append(
            t["meta_line"].format(
                task_type=brief["task_type_label"],
                language=brief["language"],
                risk=brief["risk"],
            )
        )
        if brief["critical_checks"] and outcome == "critical":
            lines.append(t["critical_what"])
            for check in brief["critical_checks"]:
                lines.append(f"  - {check}")

    lines.append("")
    lines.extend(_case_context(task, lang=lang))

    for attempt in sorted(task_attempts, key=lambda a: a.repeat_index):
        status = _attempt_status(attempt, lang=lang)
        lines.append(
            t["repeat"].format(
                n=attempt.repeat_index + 1,
                status=status,
                score=attempt.effective_score,
            )
        )
        if mode == "failure":
            scorer_lines = _failed_scorers(attempt, lang=lang)
            if scorer_lines:
                lines.extend(scorer_lines)
            elif not attempt.passed and not attempt.partial:
                lines.append(t["below_partial"].format(score=attempt.weighted_score))
        else:
            scorer_lines = _passed_scorers(attempt)
            if scorer_lines:
                lines.extend(scorer_lines)

        lines.append("")
        lines.extend(_model_output_block(attempt, lang=lang))

    return lines
