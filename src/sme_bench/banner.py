"""Startup banner for CLI runs."""

from __future__ import annotations

from rich.console import Console

SME_BENCH_EU_BANNER = r"""
  ____  __  __ _____     ____  _____ _   _ ____ _   _ _____
 / ___||  \/  | ____|   | __ )| ____| \ | / ___| | | | ____|
 \___ \| |\/| |  _|     |  _ \|  _| |  \| |   | |_| |  _|
  ___) | |  | | |___    | |_) | |___| |\  |___|  _  | |___
 |____/|_|  |_|_____|   |____/|_____|_| \_\____|_| |_|_____|
                      · eu ·
""".strip("\n")


def print_startup_banner(console: Console) -> None:
    """Print the SME-Bench EU banner with spacing before live output."""
    console.print(f"[bold cyan]{SME_BENCH_EU_BANNER}[/bold cyan]")
    console.print()
