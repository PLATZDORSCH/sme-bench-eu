"""Startup banner for CLI runs."""

from __future__ import annotations

from rich.console import Console

# FIGlet "standard" — SME-BENCH-EU (kein Extra-Buchstabe hinter H)
SME_BENCH_EU_BANNER = r"""
  ____  __  __ _____      ____  _____ _   _  ____ _   _       _____ _   _ 
 / ___||  \/  | ____|    | __ )| ____| \ | |/ ___| | | |     | ____| | | |
 \___ \| |\/| |  _| _____|  _ \|  _| |  \| | |   | |_| |_____|  _| | | | |
  ___) | |  | | |__|_____| |_) | |___| |\  | |___|  _  |_____| |___| |_| |
 |____/|_|  |_|_____|    |____/|_____|_| \_|\____|_| |_|     |_____|\___/ 
""".strip("\n")


def print_startup_banner(console: Console) -> None:
    """Print the sme-bench-eu banner with spacing before live output."""
    console.print(f"[bold cyan]{SME_BENCH_EU_BANNER}[/bold cyan]")
    console.print()
