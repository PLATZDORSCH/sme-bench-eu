"""Live Rich dashboard for benchmark runs."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.text import Text


class RunDashboard:
    """Terminal dashboard: scrollable attempt log + live counters footer."""

    def __init__(
        self,
        console: Console,
        *,
        model: str,
        suite_label: str,
        total: int,
        max_lines: int = 12,
    ) -> None:
        self._console = console
        self._model = model
        self._suite_label = suite_label
        self._total = total
        self._max_lines = max_lines
        self._lines: deque[tuple[str, str | None]] = deque(maxlen=max_lines)
        self._counters: dict[str, Any] = {
            "passed": 0,
            "partial": 0,
            "failed": 0,
            "critical": 0,
            "infra": 0,
            "done": 0,
        }
        self._mean_tps: float | None = None
        self._live: Live | None = None

    def add_line(self, text: str, style: str | None = None) -> None:
        self._lines.append((text, style))
        if self._live is not None:
            self._live.update(self.render())

    def update_counts(self, counters: dict[str, Any], mean_tps: float | None) -> None:
        self._counters = dict(counters)
        self._mean_tps = mean_tps
        if self._live is not None:
            self._live.update(self.render())

    def render(self) -> RenderableType:
        done = int(self._counters.get("done", 0))
        header = Text.assemble(
            (self._model, "bold"),
            " · ",
            (self._suite_label, "cyan"),
            f"  {done}/{self._total}",
        )
        if self._mean_tps is not None:
            header.append(f"  Output tok/s: {self._mean_tps:.1f}", style="cyan")

        body = Panel(
            self._render_body(),
            title="Attempts",
            border_style="blue",
            height=self._max_lines + 2,
        )

        footer = self._render_footer()
        return Group(header, "", body, "", footer)

    def _text_line(self, text: str, style: str | None) -> Text:
        if style is not None and "[" not in text:
            return Text(text, style=style)
        return Text.from_markup(text)

    def _render_body(self) -> Group:
        """Always render exactly max_lines rows so the panel keeps a fixed height."""
        rows: list[Text] = [self._text_line(text, style) for text, style in self._lines]
        if not rows:
            rows.append(Text("Waiting for first attempt…", style="dim"))
        while len(rows) < self._max_lines:
            rows.append(Text(""))
        if len(rows) > self._max_lines:
            rows = rows[-self._max_lines :]
        return Group(*rows)

    def _render_footer(self) -> Text:
        passed = int(self._counters.get("passed", 0))
        partial = int(self._counters.get("partial", 0))
        failed = int(self._counters.get("failed", 0))
        infra = int(self._counters.get("infra", 0))
        done = int(self._counters.get("done", 0))

        footer = Text()
        footer.append("✓ ", style="bold")
        footer.append(str(passed), style="bold green")
        footer.append("  ~ ", style="bold")
        footer.append(str(partial), style="bold yellow")
        footer.append("  ✗ ", style="bold")
        footer.append(str(failed), style="bold red")
        if infra:
            footer.append("  infra ", style="dim")
            footer.append(str(infra), style="dim")
        if self._mean_tps is not None:
            footer.append("  Output tok/s ", style="dim")
            footer.append(f"{self._mean_tps:.1f}", style="bold cyan")
        footer.append(f"  {done}/{self._total}", style="bold")
        return footer

    @contextmanager
    def live(self) -> Iterator[RunDashboard]:
        with Live(
            self.render(),
            console=self._console,
            refresh_per_second=8,
            transient=False,
        ) as live:
            self._live = live
            try:
                yield self
            finally:
                self._live = None


def use_dashboard(console: Console, dashboard_setting: bool | None) -> bool:
    """Return True when the live dashboard should be used."""
    if dashboard_setting is False:
        return False
    if dashboard_setting is True:
        return True
    return console.is_terminal
