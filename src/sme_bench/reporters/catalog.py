"""Markdown catalog of all tasks in a suite."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sme_bench.models import BenchmarkTask
from sme_bench.reporters.i18n import TASK_TYPE_LABELS
from sme_bench.reporters.task_docs import task_brief, task_variant


def write_case_catalog(
    path: Path,
    tasks: list[BenchmarkTask],
    *,
    suite_id: str,
    suite_version: str,
) -> None:
    """Write CASES.md reference documentation for a suite."""
    sorted_tasks = sorted(tasks, key=lambda t: (t.task_type, task_variant(t.id), t.language))
    by_type: dict[str, list[BenchmarkTask]] = {}
    for task in sorted_tasks:
        by_type.setdefault(task.task_type, []).append(task)

    critical_count = sum(
        1
        for t in tasks
        if t.risk == "critical" or any(s.critical for s in t.scorers)
    )

    lines = [
        f"# Case catalogue — {suite_id} {suite_version}",
        "",
        "Reference for every benchmark case: what is checked, which failures are critical?",
        "",
        f"- **Total cases:** {len(tasks)}",
        f"- **With critical scorers:** {critical_count}",
        f"- **Languages:** {', '.join(sorted({t.language for t in tasks}))}",
        "",
        "## Quick overview",
        "",
        "| ID | Title | Language | Risk | Variant | Pair |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for task in sorted_tasks:
        brief = task_brief(task, lang="en")
        risk_badge = f"**{brief['risk']}**" if brief["risk"] in {"critical", "high"} else brief["risk"]
        lines.append(
            f"| `{brief['id']}` | {brief['title']} | {brief['language']} | "
            f"{risk_badge} | {brief['variant']} | `{brief['pair_id'] or '—'}` |"
        )

    lines.extend(["", "## By task type", ""])

    for task_type in sorted(by_type):
        label = TASK_TYPE_LABELS["en"].get(task_type, task_type)
        lines.extend([f"### {label} (`{task_type}`)", ""])
        for task in by_type[task_type]:
            lines.extend(_task_section(task_brief(task, lang="en")))
            lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _task_section(brief: dict[str, Any]) -> list[str]:
    lines = [
        f"#### `{brief['id']}` — {brief['title']}",
        "",
        f"- **Language:** {brief['language']} · **Pair:** `{brief['pair_id'] or '—'}` · "
        f"**Variant {brief['variant']}:** {brief['variant_label']}",
        f"- **Category:** `{brief['category']}` · **Difficulty:** {brief['difficulty']} · "
        f"**Risk:** {brief['risk']} — {brief['risk_label']}",
        f"- **Pass from:** {brief['pass_threshold']:.0%} weighted score",
        "",
        "**Task (system prompt):**",
        f"> {brief['system_prompt']}",
        "",
    ]
    if brief["critical_checks"]:
        lines.append("**Critical checks (fail → effective score 0):**")
        for check in brief["critical_checks"]:
            lines.append(f"- {check}")
        lines.append("")
    lines.append("**Scorers:**")
    lines.extend(brief["scorers"] or ["- (none)"])
    return lines
