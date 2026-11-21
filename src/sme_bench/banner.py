"""Startup banner for CLI runs."""

from __future__ import annotations

from rich.console import Console

# FIGlet "standard" — SME-BENCH
SME_BENCH_BANNER = r"""
  ____  __  __ _____      ____  _____ _   _  ____ _   _
 / ___||  \/  | ____|    | __ )| ____| \ | |/ ___| | | |
 \___ \| |\/| |  _| _____|  _ \|  _| |  \| | |   | |_| |
  ___) | |  | | |__|_____| |_) | |___| |\  | |___|  _  |
 |____/|_|  |_|_____|    |____/|_____|_| \_|\____|_| |_|
""".strip("\n")


def print_startup_banner(console: Console) -> None:
    """Print the sme-bench banner with spacing before live output."""
    console.print(f"[bold cyan]{SME_BENCH_BANNER}[/bold cyan]")
    console.print()
