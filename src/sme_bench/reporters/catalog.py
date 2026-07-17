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
        f"# Fallkatalog — {suite_id} {suite_version}",
        "",
        "Referenz für alle Benchmark-Fälle: Was wird geprüft, welche Fehler sind kritisch?",
        "",
        f"- **Fälle gesamt:** {len(tasks)}",
        f"- **Mit kritischen Scorern:** {critical_count}",
        f"- **Sprachen:** {', '.join(sorted({t.language for t in tasks}))}",
        "",
        "## Schnellübersicht",
        "",
        "| ID | Titel | Sprache | Risiko | Variante | Pair |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for task in sorted_tasks:
        brief = task_brief(task)
        risk_badge = f"**{brief['risk']}**" if brief["risk"] in {"critical", "high"} else brief["risk"]
        lines.append(
            f"| `{brief['id']}` | {brief['title']} | {brief['language']} | "
            f"{risk_badge} | {brief['variant']} | `{brief['pair_id'] or '—'}` |"
        )

    lines.extend(["", "## Nach Task-Typ", ""])

    for task_type in sorted(by_type):
        label = TASK_TYPE_LABELS["de"].get(task_type, task_type)
        lines.extend([f"### {label} (`{task_type}`)", ""])
        for task in by_type[task_type]:
            lines.extend(_task_section(task_brief(task)))
            lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _task_section(brief: dict[str, Any]) -> list[str]:
    lines = [
        f"#### `{brief['id']}` — {brief['title']}",
        "",
        f"- **Sprache:** {brief['language']} · **Pair:** `{brief['pair_id'] or '—'}` · "
        f"**Variante {brief['variant']}:** {brief['variant_label']}",
        f"- **Kategorie:** `{brief['category']}` · **Schwierigkeit:** {brief['difficulty']} · "
        f"**Risiko:** {brief['risk']} — {brief['risk_label']}",
        f"- **Bestehen ab:** {brief['pass_threshold']:.0%} gewichteter Score",
        "",
        "**Aufgabe (System-Prompt):**",
        f"> {brief['system_prompt']}",
        "",
    ]
    if brief["critical_checks"]:
        lines.append("**Kritische Prüfungen (K.-o. bei Verstoß → effektiver Score 0):**")
        for check in brief["critical_checks"]:
            lines.append(f"- {check}")
        lines.append("")
    lines.append("**Scorer:**")
    lines.extend(brief["scorers"] or ["- (keine)"])
    return lines
