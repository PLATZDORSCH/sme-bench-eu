"""SME-Bench CLI."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, TypeVar

import typer
from rich.console import Console
from rich.table import Table

from sme_bench import __version__
from sme_bench.banner import print_startup_banner
from sme_bench.client import run_doctor
from sme_bench.config import (
    DEFAULT_MAX_TOKENS_FLOOR,
    DEFAULT_TIMEOUT_SECONDS,
    PricingConfig,
    RunConfig,
    apply_enable_thinking,
    load_extra_body,
)
from sme_bench.env import load_env_files
from sme_bench.models import AttemptResult, BenchmarkTask
from sme_bench.reporters.catalog import write_case_catalog
from sme_bench.reporters.console import print_summary
from sme_bench.reporters.csv_reporter import write_attempts_csv
from sme_bench.reporters.failures import write_failures_reports, write_success_reports
from sme_bench.reporters.json_reporter import write_summary_json
from sme_bench.reporters.markdown import write_summary_reports
from sme_bench.runner import run_benchmark
from sme_bench.scorers.base import known_scorer_names
from sme_bench.scoring import apply_partial_grade, evaluate_attempt
from sme_bench.statistics import aggregate, dedupe_attempts
from sme_bench.task_loader import load_suite, load_suite_from_metadata
from sme_bench.utils import is_thinking_dump, separate_thinking_content

load_env_files()

app = typer.Typer(
    name="sme-bench",
    help="Benchmark language models on realistic SME business tasks (DE/EN).",
    no_args_is_help=True,
)
console = Console()

T = TypeVar("T")


def _run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine, even if an event loop is already running (e.g. tests)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()


def _parse_csv(value: str | None) -> list[str] | None:
    if value is None or value.strip() == "":
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


@app.callback()
def main_callback() -> None:
    """SME-Bench command group."""


@app.command("doctor")
def doctor_cmd(
    base_url: str = typer.Option(..., "--base-url", help="OpenAI-compatible base URL"),
    model: str = typer.Option(..., "--model", help="Model id"),
    api_key_env: str = typer.Option("OPENAI_API_KEY", "--api-key-env"),
    timeout: float = typer.Option(60.0, "--timeout"),
) -> None:
    """Check endpoint reachability, streaming, and usage."""
    report = _run_async(
        run_doctor(base_url=base_url, model=model, api_key_env=api_key_env, timeout=timeout)
    )
    console.print_json(data=report)
    if not report.get("chat_ok"):
        raise typer.Exit(code=1)


@app.command("list")
def list_cmd(
    suite: Path = typer.Option(..., "--suite", help="Path to suite directory"),
) -> None:
    """List suite categories, languages, and pair coverage."""
    loaded = load_suite(suite, known_scorers=known_scorer_names())
    table = Table(title=f"{loaded.manifest.name} ({loaded.manifest.id})")
    table.add_column("ID")
    table.add_column("Lang")
    table.add_column("Category")
    table.add_column("Type")
    table.add_column("Difficulty")
    table.add_column("Pair")
    for task in loaded.tasks:
        table.add_row(
            task.id,
            task.language,
            task.category,
            task.task_type,
            task.difficulty,
            task.pair_id or "",
        )
    console.print(table)
    pairs = {t.pair_id for t in loaded.tasks if t.pair_id}
    console.print(
        f"\nTasks: {len(loaded.tasks)} · Languages: {', '.join(loaded.manifest.languages)} · "
        f"Pairs: {len(pairs)}"
    )


@app.command("validate")
def validate_cmd(
    suite: Path = typer.Argument(..., help="Path to suite directory"),
) -> None:
    """Validate suite manifest, tasks, fixtures, and scorers."""
    loaded = load_suite(suite, known_scorers=known_scorer_names(), resolve_fixtures=True)
    errors = [i for i in loaded.issues if i.severity == "error"]
    warnings = [i for i in loaded.issues if i.severity == "warning"]
    for issue in loaded.issues:
        style = "red" if issue.severity == "error" else "yellow"
        console.print(f"[{style}]{issue.severity.upper()}[/{style}] {issue.path}: {issue.message}")
    if errors:
        console.print(f"\n[red]Validation failed with {len(errors)} error(s).[/red]")
        raise typer.Exit(code=1)
    console.print(
        f"[green]OK[/green] {len(loaded.tasks)} tasks, "
        f"{len(warnings)} warning(s), hash={loaded.suite_hash[:12]}…"
    )


@app.command("run")
def run_cmd(
    base_url: str = typer.Option(..., "--base-url"),
    model: str = typer.Option(..., "--model"),
    suite: Path | None = typer.Option(
        None,
        "--suite",
        help="Optional: run a single suite instead of the default Full pack",
    ),
    full: bool = typer.Option(
        False,
        "--full",
        help="Explicit Full pack (default when --suite is omitted)",
    ),
    served_model_name: str | None = typer.Option(None, "--served-model-name"),
    api_key_env: str = typer.Option("OPENAI_API_KEY", "--api-key-env"),
    languages: str | None = typer.Option(None, "--languages"),
    categories: str | None = typer.Option(None, "--categories"),
    difficulty: str | None = typer.Option(None, "--difficulty"),
    tags: str | None = typer.Option(None, "--tags"),
    repeats: int = typer.Option(3, "--repeats"),
    concurrency: int = typer.Option(1, "--concurrency"),
    seed: int = typer.Option(42, "--seed"),
    timeout: float = typer.Option(
        DEFAULT_TIMEOUT_SECONDS,
        "--timeout",
        help=f"Per-request timeout in seconds (default {int(DEFAULT_TIMEOUT_SECONDS)}).",
    ),
    retries: int = typer.Option(1, "--retries"),
    max_tokens_mult: float = typer.Option(
        1.0,
        "--max-tokens-mult",
        help="Scale every task's max_tokens by this factor "
        "(give reasoning models room to think + answer).",
    ),
    max_tokens_min: int = typer.Option(
        DEFAULT_MAX_TOKENS_FLOOR,
        "--max-tokens-min",
        help=(
            "Raise any task's max_tokens up to at least this floor "
            f"(default {DEFAULT_MAX_TOKENS_FLOOR}; use 0 to disable). "
            "Prevents mid-CoT truncation on short suite budgets."
        ),
    ),
    extra_body_file: Path | None = typer.Option(None, "--extra-body-file"),
    enable_thinking: bool = typer.Option(
        False,
        "--enable-thinking",
        help="Set chat_template_kwargs.enable_thinking=true (Qwen/vLLM/LiteLLM).",
    ),
    input_price_per_million: float | None = typer.Option(None, "--input-price-per-million"),
    output_price_per_million: float | None = typer.Option(None, "--output-price-per-million"),
    save_reasoning: bool = typer.Option(False, "--save-reasoning"),
    fail_fast: bool = typer.Option(False, "--fail-fast"),
    resume: Path | None = typer.Option(None, "--resume"),
    output: Path | None = typer.Option(None, "--output"),
    emit_progress: str | None = typer.Option(None, "--emit-progress"),
    no_warmup: bool = typer.Option(False, "--no-warmup"),
    dashboard: bool | None = typer.Option(
        None,
        "--dashboard/--no-dashboard",
        help="Live run dashboard (default: on in TTY, off when piped)",
    ),
) -> None:
    """Run the benchmark against an OpenAI-compatible endpoint.

    Default target is **SME Full** (Core + all domain packs, ~156 cases).
    Pass ``--suite PATH`` to run only one pack (e.g. Core alone).
    """
    print_startup_banner(console)

    from sme_bench.task_loader import FULL_SUITE_IDS, load_full_benchmark

    use_full = suite is None or full
    if full and suite is not None:
        console.print("[yellow]Hinweis:[/yellow] --full und --suite gesetzt — Full hat Vorrang.")
        use_full = True

    if use_full:
        loaded = load_full_benchmark(known_scorers=known_scorer_names())
        suite_path = Path("suites")
        console.print(
            f"SME Full: {len(loaded.tasks)} Fälle aus "
            f"{len(loaded.member_suites)} Suites ({', '.join(FULL_SUITE_IDS)})"
        )
    else:
        assert suite is not None
        loaded = load_suite(suite, known_scorers=known_scorer_names())
        suite_path = suite

    errors = [i for i in loaded.issues if i.severity == "error"]
    if errors:
        for issue in errors:
            console.print(f"[red]ERROR[/red] {issue.path}: {issue.message}")
        raise typer.Exit(code=1)

    if max_tokens_min < 0:
        console.print("[red]--max-tokens-min must be >= 0 (0 disables the floor).[/red]")
        raise typer.Exit(code=1)
    tokens_floor = None if max_tokens_min == 0 else max_tokens_min

    config = RunConfig(
        base_url=base_url,
        model=model,
        served_model_name=served_model_name,
        api_key_env=api_key_env,
        suite=suite_path,
        languages=_parse_csv(languages),
        categories=_parse_csv(categories),
        difficulty=_parse_csv(difficulty),
        tags=_parse_csv(tags),
        repeats=repeats,
        concurrency=concurrency,
        seed=seed,
        timeout=timeout,
        retries=retries,
        max_tokens_multiplier=max_tokens_mult,
        max_tokens_floor=tokens_floor,
        extra_body=apply_enable_thinking(
            load_extra_body(extra_body_file),
            enabled=enable_thinking,
        ),
        pricing=PricingConfig(
            input_price_per_million=input_price_per_million,
            output_price_per_million=output_price_per_million,
        ),
        save_reasoning=save_reasoning,
        fail_fast=fail_fast,
        resume=resume,
        output=output,
        emit_progress=emit_progress,
        warmup=not no_warmup,
        dashboard=dashboard,
    )
    run_dir = _run_async(run_benchmark(config, loaded))
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    print_summary(
        summary,
        model=model,
        suite_label=f"{loaded.manifest.name} v{loaded.manifest.version}",
        version=__version__,
    )
    console.print(f"\nResults written to {run_dir}")


@app.command("catalog")
def catalog_cmd(
    suite: Path = typer.Argument(..., help="Path to suite directory"),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path (default: <suite>/CASES.md)",
    ),
) -> None:
    """Generate CASES.md — human-readable documentation for every task."""
    loaded = load_suite(suite, known_scorers=known_scorer_names())
    out = output or (suite / "CASES.md")
    write_case_catalog(
        out,
        loaded.tasks,
        suite_id=loaded.manifest.id,
        suite_version=loaded.manifest.version,
    )
    console.print(f"Wrote {len(loaded.tasks)} case docs to {out}")


def _rescore_source_text(attempt: AttemptResult) -> str:
    """Pick the best stored text to re-separate thinking from.

    When a prior buggy recovery left a short anti-example in ``output_text`` but
    the full CoT dump is still in ``reasoning_text``, re-derive the answer from
    that dump. Otherwise use ``output_text``.
    """
    reasoning = attempt.reasoning_text or ""
    output = attempt.output_text or ""
    if is_thinking_dump(reasoning):
        return reasoning
    if is_thinking_dump(output):
        return output
    return output


def _rescore_attempt(attempt: AttemptResult, task: BenchmarkTask) -> AttemptResult:
    """Re-run scorers on a stored model output using the current suite definition.

    Infrastructure errors have no usable output and are left untouched.
    Persists a cleaned ``output_text`` when leaked thinking was stripped.
    """
    if attempt.infrastructure_error:
        return attempt
    source = _rescore_source_text(attempt)
    answer_text, reasoning = separate_thinking_content(source)
    # evaluate_attempt also strips thinking; pass the post-split answer directly.
    score_results, weighted, effective, passed, partial, critical, parsed = evaluate_attempt(
        task, answer_text
    )
    updates: dict[str, Any] = {
        "parsed_output": parsed,
        "score_results": score_results,
        "weighted_score": weighted,
        "effective_score": effective,
        "passed": passed,
        "partial": partial,
        "critical_failure": critical,
        "output_text": answer_text,
    }
    if reasoning:
        updates["reasoning_text"] = reasoning
    elif is_thinking_dump(source) and not answer_text:
        # Whole blob was thinking with no post-delimiter answer.
        updates["reasoning_text"] = source
    return attempt.model_copy(update=updates)


@app.command("report")
def report_cmd(
    run_dir: Path = typer.Argument(..., help="Existing run directory"),
    format: str = typer.Option(
        "markdown",
        "--format",
        help="json|csv|markdown|failures|success|all",
    ),
    rescore: bool = typer.Option(
        False,
        "--rescore",
        help="Re-run scorers on the stored model outputs using the current suite definition.",
    ),
) -> None:
    """Rebuild reports from existing attempts.jsonl without model calls."""
    attempts_path = run_dir / "attempts.jsonl"
    meta_path = run_dir / "metadata.json"
    if not attempts_path.exists():
        console.print(f"[red]Missing {attempts_path}[/red]")
        raise typer.Exit(code=1)
    attempts: list[AttemptResult] = []
    with attempts_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                attempts.append(AttemptResult.model_validate(json.loads(line)))
    attempts = dedupe_attempts(attempts)
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    weights: dict[str, float] = {}
    tasks_by_id: dict[str, BenchmarkTask] = {}
    loaded = load_suite_from_metadata(
        meta,
        known_scorers=known_scorer_names(),
        resolve_fixtures=True,
    )
    if loaded is not None:
        weights = loaded.manifest.category_weights
        tasks_by_id = {t.id: t for t in loaded.tasks}
        if rescore:
            for spec_task in loaded.tasks:
                for spec in spec_task.scorers:
                    if spec.type == "json_schema":
                        # Prefer per-suite dir from absolutized schema parent when present
                        schema_ref = spec.params.get("schema")
                        if isinstance(schema_ref, str) and Path(schema_ref).is_absolute():
                            spec.params.setdefault(
                                "_suite_dir", str(Path(schema_ref).parents[1])
                            )
                        else:
                            spec.params.setdefault("_suite_dir", str(loaded.directory))
            attempts = [
                _rescore_attempt(a, tasks_by_id[a.task_id])
                if a.task_id in tasks_by_id
                else a
                for a in attempts
            ]
            # Persist rescored attempts so attempts.jsonl matches reports
            with attempts_path.open("w", encoding="utf-8") as handle:
                for attempt in attempts:
                    handle.write(attempt.model_dump_json() + "\n")
        else:
            attempts = [
                apply_partial_grade(a, tasks_by_id[a.task_id])
                if a.task_id in tasks_by_id
                else a
                for a in attempts
            ]

    summary = aggregate(attempts, category_weights=weights)
    summary["run_id"] = meta.get("run_id", run_dir.name)
    summary["model"] = meta.get("model", "")
    summary["suite_id"] = meta.get("suite_id", "")
    summary["suite_version"] = meta.get("suite_version", "")

    fmt = format.lower()
    if fmt in {"json", "all"}:
        write_summary_json(run_dir / "summary.json", summary)
    if fmt in {"markdown", "all"}:
        write_summary_reports(run_dir, summary, model=str(summary.get("model")))
    if fmt in {"csv", "all"}:
        write_attempts_csv(run_dir / "attempts.csv", attempts)
    report_kwargs = {
        "model": str(summary.get("model") or run_dir.name),
        "suite_id": str(summary.get("suite_id") or ""),
        "suite_version": str(summary.get("suite_version") or ""),
        "tasks_by_id": tasks_by_id,
    }
    if fmt in {"failures", "success", "all"}:
        write_failures_reports(run_dir, attempts, **report_kwargs)
        write_success_reports(run_dir, attempts, **report_kwargs)
    if fmt == "markdown":
        console.print((run_dir / "summary.de.md").read_text(encoding="utf-8"))
    elif fmt == "failures":
        console.print((run_dir / "failures.de.md").read_text(encoding="utf-8"))
    elif fmt == "success":
        console.print((run_dir / "success.de.md").read_text(encoding="utf-8"))
    else:
        console.print(f"Reports updated in {run_dir}")


@app.command("compare")
def compare_cmd(
    run_dirs: list[Path] = typer.Argument(..., help="Two or more run directories"),
    allow_suite_mismatch: bool = typer.Option(False, "--allow-suite-mismatch"),
) -> None:
    """Compare compatible runs side by side."""
    if len(run_dirs) < 2:
        console.print("[red]Need at least two run directories[/red]")
        raise typer.Exit(code=1)

    metas = []
    summaries = []
    for path in run_dirs:
        meta = json.loads((path / "metadata.json").read_text(encoding="utf-8"))
        summary = json.loads((path / "summary.json").read_text(encoding="utf-8"))
        metas.append(meta)
        summaries.append(summary)

    hashes = {m.get("suite_hash") for m in metas}
    if len(hashes) > 1 and not allow_suite_mismatch:
        console.print(
            "[red]Suite hashes differ. Re-run with --allow-suite-mismatch to compare anyway.[/red]"
        )
        for m in metas:
            console.print(f"  {m.get('run_id')}: {m.get('suite_hash')}")
        raise typer.Exit(code=1)

    # Primary leaderboard line: Rank Score is the ranking metric.
    rank_bits = [
        f"[bold]{m.get('model', m.get('run_id'))}: {s.get('sme_rank_score', 0):.1f}[/bold]"
        for m, s in zip(metas, summaries, strict=True)
    ]
    console.print("SME-Bench Leaderboard · [bold]SME Rank Score[/bold]")
    console.print("  " + "  ·  ".join(rank_bits))
    console.print()

    table = Table(title="SME-Bench Compare")
    table.add_column("Metric")
    for m in metas:
        table.add_column(str(m.get("model", m.get("run_id"))))
    rows = [
        ("SME Rank Score", "sme_rank_score", False, True),
        ("SME Core Score", "sme_core_score", False, False),
        ("Attempt Pass Rate", "attempt_pass_rate", True, False),
        ("Attempt Partial Rate", "attempt_partial_rate", True, False),
        ("Reliable Pass Rate", "reliable_pass_rate", True, False),
        ("Critical Failures", "critical_failure_rate", True, False),
    ]
    for label, key, is_rate, bold in rows:
        values = []
        for s in summaries:
            if key in {"sme_core_score", "sme_rank_score"}:
                val = f"{s.get(key, 0):.1f}"
            else:
                raw = s.get("overall", {}).get(key, 0)
                val = f"{raw * 100:.1f}%" if is_rate else f"{raw:.3f}"
            values.append(f"[bold]{val}[/bold]" if bold else val)
        row_label = f"[bold]{label}[/bold]" if bold else label
        table.add_row(row_label, *values)
    console.print(table)


if __name__ == "__main__":
    app()
