"""Console summary via Rich."""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table


def print_summary(
    summary: dict[str, Any],
    *,
    model: str,
    suite_label: str,
    version: str = "0.1.0",
    console: Console | None = None,
) -> None:
    out = console or Console()
    overall = summary.get("overall", {})
    score = summary.get("sme_core_score", 0.0)
    out.print(f"SME-Bench {version} · {suite_label} · {model}")
    out.print()
    out.print(f"SME Core Score       {score:.1f} / 100")
    out.print(f"Attempt Pass Rate    {overall.get('attempt_pass_rate', 0) * 100:.1f} %")
    out.print(f"Attempt Partial Rate {overall.get('attempt_partial_rate', 0) * 100:.1f} %")
    out.print(f"Reliable Pass Rate   {overall.get('reliable_pass_rate', 0) * 100:.1f} %")
    out.print(f"Critical Failures    {overall.get('critical_failure_rate', 0) * 100:.1f} %")
    out.print(f"Infrastructure       {overall.get('infrastructure_error_rate', 0) * 100:.1f} %")
    tps = overall.get("mean_generation_tps")
    tps_s = f"{tps:.1f} tok/s" if isinstance(tps, (int, float)) else "—"
    out.print(f"Output tokens/s (Ø)  {tps_s}")
    out.print()

    by_lang = summary.get("by_language") or {}
    if by_lang:
        table = Table(show_header=True, header_style="bold")
        table.add_column("Language")
        table.add_column("Pass rate", justify="right")
        table.add_column("Reliable", justify="right")
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
                f"{metrics.get('attempt_pass_rate', 0) * 100:.1f} %",
                f"{metrics.get('reliable_pass_rate', 0) * 100:.1f} %",
                f"{metrics.get('mean_effective_score', 0) * 100:.1f}",
                f"{metrics.get('critical_failure_rate', 0) * 100:.1f} %",
                lat_s,
                lang_tps_s,
            )
        out.print(table)

    parity = summary.get("language_parity") or {}
    gap = parity.get("language_gap_pass_rate")
    if gap is not None:
        sign = "+" if gap >= 0 else ""
        out.print(f"\nEN-DE pass gap: {sign}{gap * 100:.1f} percentage points")
