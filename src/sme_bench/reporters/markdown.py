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


def _points(value: float | None) -> str:
    """A difference of two rates, in percentage points."""
    return "—" if value is None else f"{value * 100:+.1f} pp"


def _signed(value: float | None, digits: int) -> str:
    return "—" if value is None else f"{value:+.{digits}f}"


def _seconds(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f} s"


def write_summary_markdown(
    path: Path,
    summary: dict[str, Any],
    *,
    model: str,
    lang: Lang = "de",
) -> None:
    t = SUMMARY[lang]
    overall = summary.get("overall", {})
    ci = (summary.get("headline") or {}).get("pass_rate_ci")
    readiness = summary.get("readiness") or {}
    tier_key = str(readiness.get("tier") or "")
    reasons = [t.get(f"reason_{reason}", reason) for reason in readiness.get("reasons") or []]

    rows: list[tuple[str, str]] = [
        (t["pass_rate"], f"**{_pct(overall.get('pass_rate'))}**"),
        (
            t["interval"],
            t["interval_value"].format(low=_pct(ci[0]), high=_pct(ci[1])) if ci else "—",
        ),
        (t["readiness_tier"], t.get(f"tier_{tier_key}", tier_key or "—")),
    ]
    if reasons:
        rows.append((t["readiness_reason"], ", ".join(reasons)))
    rows.extend(
        [
            (
                t["unsolved"],
                t["of_total"].format(
                    count=overall.get("unsolved_cases", 0), total=overall.get("unique_tasks", 0)
                ),
            ),
            (t["critical_cases"], str(overall.get("critical_cases", 0))),
            (t["unstable"], str(overall.get("unstable_cases", 0))),
            (
                t["coverage"],
                t["of_total"].format(
                    count=overall.get("graded_attempts", 0), total=overall.get("attempts", 0)
                ),
            ),
            (t["mean_score"], _num(overall.get("mean_effective_score"), 3)),
            (t["attempt_partial"], _pct(overall.get("attempt_partial_rate"))),
            (t["infra_rate"], _pct(overall.get("infrastructure_error_rate"))),
            (t["language_rate"], _pct(overall.get("language_compliance_rate"))),
            (t["format_only"], _pct(overall.get("format_only_failure_rate"))),
            (t["tps"], _num(overall.get("mean_generation_tps"), 1)),
            (t["ttft_cold"], _seconds(overall.get("ttft_cold_p50"))),
            (t["ttfa"], _seconds(overall.get("ttfa_p50"))),
        ]
    )
    if summary.get("baseline_latency_s") is not None:
        rows.append((t["baseline"], _seconds(summary.get("baseline_latency_s"))))
    runtime = summary.get("runtime") or {}
    if any(runtime.get(key) for key in ("engine", "hardware", "quantization")):
        rows.append(
            (
                t["runtime"],
                t["runtime_value"].format(
                    engine=runtime.get("engine") or "—",
                    hardware=runtime.get("hardware") or "—",
                    quantization=runtime.get("quantization") or "—",
                ),
            )
        )

    lines = [
        t["title"].format(model=model),
        "",
        t["suite"].format(
            suite_id=summary.get("suite_id", ""),
            suite_version=summary.get("suite_version", ""),
        ),
    ]
    if summary.get("regraded_from"):
        lines.extend(["", f"Regraded from: `{summary['regraded_from']}` (inference preserved)"])
    lines.extend(["", t["metrics_header"], "| --- | ---: |"])
    lines.extend(f"| {label} | {value} |" for label, value in rows)
    lines.extend(
        [
            "",
            t["by_language"],
            "",
            t["lang_header"],
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for lang_key, m in (summary.get("by_language") or {}).items():
        lines.append(
            f"| {lang_key} | {_pct(m.get('pass_rate'))} | {m.get('unsolved_cases', 0)} / {m.get('unique_tasks', 0)} | "
            f"{_num(m.get('mean_effective_score'))} | {m.get('critical_cases', 0)} | "
            f"{_num(m.get('latency_p95'), 2)} s | {_num(m.get('mean_generation_tps'), 1)} |"
        )

    buckets = summary.get("by_prompt_bucket") or {}
    if buckets:
        lines.extend(
            ["", t["by_prompt"], "", t["prompt_header"], "| --- | ---: | ---: | ---: | ---: |"]
        )
        for bucket, m in buckets.items():
            lines.append(
                f"| {bucket} | {_pct(m.get('pass_rate'))} | {m.get('unsolved_cases', 0)} / {m.get('unique_tasks', 0)} | "
                f"{_num(m.get('mean_effective_score'))} | {_num(m.get('mean_generation_tps'), 1)} |"
            )

    lines.extend(["", t["by_category"], ""])
    lines.append(t["cat_header"])
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for cat, m in (summary.get("by_category") or {}).items():
        lines.append(
            f"| {cat} | {_pct(m.get('pass_rate'))} | {m.get('unsolved_cases', 0)} / {m.get('unique_tasks', 0)} | "
            f"{_num(m.get('mean_effective_score'))} | {m.get('critical_cases', 0)} |"
        )

    parity = summary.get("language_parity") or {}
    lines.extend(
        [
            "",
            t["parity"],
            "",
            t["parity_pass"].format(value=_points(parity.get("language_gap_pass_rate"))),
            t["parity_score"].format(value=_signed(parity.get("language_gap_score"), 3)),
            t["parity_pair"].format(value=_pct(parity.get("pair_consistency"))),
            "",
        ]
    )
    if summary.get("completion_rate_warning"):
        lines.extend([t["completion_warn"], ""])
    delta = summary.get("toolset_delta") or {}
    pairs = delta.get("pairs") or []
    if pairs:
        lines.extend(
            [
                t["toolset_delta"],
                "",
                t["toolset_mean"].format(value=_num(delta.get("mean_delta"), 3)),
                "",
                t["toolset_header"],
                "| --- | --- | ---: | ---: | ---: |",
            ]
        )
        for item in pairs:
            lines.append(
                f"| {item.get('pair_id')} | {item.get('language')} | "
                f"{_num(item.get('small_score'))} | {_num(item.get('crowded_score'))} | "
                f"{_num(item.get('delta'))} |"
            )
        lines.append("")
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
