"""Console summary via Rich."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table

from sme_bench.reporters.i18n import SUMMARY


def print_summary(
    summary: dict[str, Any],
    *,
    model: str,
    suite_label: str,
    version: str = "0.6.0",
    console: Console | None = None,
) -> None:
    out = console or Console()
    overall = summary.get("overall", {})
    out.print(f"SME-Bench {version} · {suite_label} · {model}")
    out.print()
    readiness = summary.get("readiness") or {}
    tier = str(readiness.get("tier") or "")
    tier_labels = {
        "ready": "suitable",
        "supervised": "partly suitable",
        "not_recommended": "not suitable",
        "inconclusive": "inconclusive",
    }
    reasons = readiness.get("reasons") or []
    ci = (summary.get("headline") or {}).get("pass_rate_ci")
    ci_s = f"  (95 % {ci[0] * 100:.1f}–{ci[1] * 100:.1f})" if ci else ""
    out.print(f"[bold]Passed               {overall.get('pass_rate', 0) * 100:.1f} %{ci_s}[/bold]")
    if tier:
        labels = [SUMMARY["en"].get(f"reason_{reason}", reason) for reason in reasons]
        reason_s = f" ({', '.join(labels)})" if labels else ""
        out.print(f"Suitability          {tier_labels.get(tier, tier)}{reason_s}")
    out.print(
        f"Unsolved cases       {overall.get('unsolved_cases', 0)} / {overall.get('unique_tasks', 0)}"
    )
    out.print(f"Critical cases       {overall.get('critical_cases', 0)}")
    out.print(f"Unstable cases       {overall.get('unstable_cases', 0)}")
    out.print(
        f"Coverage             {overall.get('graded_attempts', 0)} / {overall.get('attempts', 0)}"
    )
    out.print(f"Partial attempts     {overall.get('attempt_partial_rate', 0) * 100:.1f} %")
    out.print(f"Infrastructure       {overall.get('infrastructure_error_rate', 0) * 100:.1f} %")
    lang_rate = overall.get("language_compliance_rate")
    lang_rate_s = f"{lang_rate * 100:.1f} %" if isinstance(lang_rate, (int, float)) else "—"
    out.print(f"Language compliance  {lang_rate_s}")
    tps = overall.get("mean_generation_tps")
    tps_s = f"{tps:.1f} tok/s" if isinstance(tps, (int, float)) else "—"
    out.print(f"Output tokens/s (Ø)  {tps_s}")
    out.print()

    by_lang = summary.get("by_language") or {}
    if by_lang:
        table = Table(show_header=True, header_style="bold")
        table.add_column("Language")
        table.add_column("Pass rate", justify="right")
        table.add_column("Unsolved", justify="right")
        table.add_column("Score", justify="right")
        table.add_column("Critical", justify="right")
        table.add_column("p95 latency", justify="right")
        table.add_column("Tok/s", justify="right")
        for lang, metrics in by_lang.items():
            lat = metrics.get("latency_p95")
            lat_s = f"{lat:.2f} s" if isinstance(lat, (int, float)) else "—"
            lang_tps = metrics.get("mean_generation_tps")
            lang_tps_s = f"{lang_tps:.1f}" if isinstance(lang_tps, (int, float)) else "—"
            table.add_row(
                lang,
                f"{metrics.get('pass_rate', 0) * 100:.1f} %",
                f"{metrics.get('unsolved_cases', 0)} / {metrics.get('unique_tasks', 0)}",
                f"{metrics.get('mean_effective_score', 0) * 100:.1f}",
                f"{metrics.get('critical_cases', 0)}",
                lat_s,
                lang_tps_s,
            )
        out.print(table)

    parity = summary.get("language_parity") or {}
    gap = parity.get("language_gap_pass_rate")
    if gap is not None:
        sign = "+" if gap >= 0 else ""
        out.print(f"\nEN-DE pass gap: {sign}{gap * 100:.1f} percentage points")
