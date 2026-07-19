"""Markdown summary reporter (bilingual)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sme_bench.reporters.i18n import REPORT_LANGS, SUMMARY, Lang, report_path


def _pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.1f}%"


def _num(value: float | None, digits: int = 3) -> str:
    if value is None:
        return "—"
    return f"{value:.{digits}f}"


def write_summary_markdown(
    path: Path,
    summary: dict[str, Any],
    *,
    model: str,
    lang: Lang = "de",
) -> None:
    t = SUMMARY[lang]
    overall = summary.get("overall", {})
    lines = [
        t["title"].format(model=model),
        "",
        t["suite"].format(
            suite_id=summary.get("suite_id", ""),
            suite_version=summary.get("suite_version", ""),
        ),
        t["rank_score"].format(score=float(summary.get("sme_rank_score", 0))),
        t["core_score"].format(score=float(summary.get("sme_core_score", 0))),
        t["attempt_pass"].format(value=_pct(overall.get("attempt_pass_rate"))),
        t["attempt_partial"].format(value=_pct(overall.get("attempt_partial_rate"))),
        t["reliable_pass"].format(value=_pct(overall.get("reliable_pass_rate"))),
        t["critical_rate"].format(value=_pct(overall.get("critical_failure_rate"))),
        t["infra_rate"].format(value=_pct(overall.get("infrastructure_error_rate"))),
        t["tps"].format(value=_num(overall.get("mean_generation_tps"), 1)),
        "",
        t["by_language"],
        "",
        t["lang_header"],
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for lang_key, m in (summary.get("by_language") or {}).items():
        lines.append(
            f"| {lang_key} | {_pct(m.get('attempt_pass_rate'))} | {_pct(m.get('reliable_pass_rate'))} | "
            f"{_num(m.get('mean_effective_score'))} | {_pct(m.get('critical_failure_rate'))} | "
            f"{_num(m.get('latency_p95'), 2)} s | {_num(m.get('mean_generation_tps'), 1)} |"
        )

    lines.extend(["", t["by_category"], ""])
    lines.append(t["cat_header"])
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for cat, m in (summary.get("by_category") or {}).items():
        lines.append(
            f"| {cat} | {_pct(m.get('attempt_pass_rate'))} | {_pct(m.get('reliable_pass_rate'))} | "
            f"{_num(m.get('mean_effective_score'))} | {_pct(m.get('critical_failure_rate'))} |"
        )

    parity = summary.get("language_parity") or {}
    lines.extend(
        [
            "",
            t["parity"],
            "",
            t["parity_pass"].format(value=_num(parity.get("language_gap_pass_rate"), 4)),
            t["parity_score"].format(value=_num(parity.get("language_gap_score"), 4)),
            t["parity_pair"].format(value=_pct(parity.get("pair_consistency"))),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_summary_reports(
    run_dir: Path,
    summary: dict[str, Any],
    *,
    model: str,
) -> list[Path]:
    """Write ``summary.de.md`` and ``summary.en.md`` into ``run_dir``."""
    written: list[Path] = []
    for lang in REPORT_LANGS:
        path = run_dir / report_path("summary", lang)
        write_summary_markdown(path, summary, model=model, lang=lang)
        written.append(path)
    return written
