"""Benchmark runner: schedule, execute, score, and persist attempts."""

from __future__ import annotations

import asyncio
import contextlib
import json
import platform
import random
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rich.console import Console

from sme_bench import __version__
from sme_bench.client import OpenAICompatibleClient
from sme_bench.config import RunConfig
from sme_bench.dashboard import RunDashboard, use_dashboard
from sme_bench.models import AttemptResult, BenchmarkTask
from sme_bench.pricing import estimate_cost
from sme_bench.progress import ProgressEmitter
from sme_bench.reporters.csv_reporter import write_attempts_csv
from sme_bench.reporters.failures import write_failures_reports, write_success_reports
from sme_bench.reporters.json_reporter import write_summary_json
from sme_bench.reporters.markdown import write_summary_reports
from sme_bench.scoring import evaluate_attempt
from sme_bench.statistics import aggregate
from sme_bench.task_loader import LoadedSuite, filter_tasks
from sme_bench.utils import redact_secrets, sanitize_base_url_for_metadata, suite_path_for_metadata


def _messages_payload(task: BenchmarkTask) -> list[dict[str, str]]:
    return [{"role": m.role, "content": m.content or ""} for m in task.messages]


def _load_completed_keys(attempts_path: Path) -> set[tuple[str, int]]:
    done: set[tuple[str, int]] = set()
    if not attempts_path.exists():
        return done
    with attempts_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "task_id" in row and "repeat_index" in row:
                done.add((row["task_id"], int(row["repeat_index"])))
    return done


def _append_attempt(path: Path, attempt: AttemptResult, *, save_reasoning: bool) -> None:
    data = attempt.model_dump(mode="json")
    if not save_reasoning:
        data.pop("reasoning_text", None)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, ensure_ascii=False) + "\n")


def create_run_dir(output: Path | None, resume: Path | None) -> Path:
    if resume is not None:
        return resume
    if output is not None:
        output.mkdir(parents=True, exist_ok=True)
        return output
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    path = Path("runs") / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_metadata(run_dir: Path, meta: dict[str, Any]) -> None:
    (run_dir / "metadata.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


async def run_benchmark(config: RunConfig, suite: LoadedSuite) -> Path:
    tasks = filter_tasks(
        suite.tasks,
        languages=config.languages,
        categories=config.categories,
        difficulty=config.difficulty,
        tags=config.tags,
    )
    if not tasks:
        raise ValueError("No tasks matched the given filters")

    rng = random.Random(config.seed)
    ordered = list(tasks)
    rng.shuffle(ordered)

    run_dir = create_run_dir(config.output, config.resume)
    attempts_path = run_dir / "attempts.jsonl"
    completed = _load_completed_keys(attempts_path) if config.resume else set()

    run_id = run_dir.name
    progress = ProgressEmitter(config.emit_progress)
    status_stream = sys.stderr if progress.redirects_status_to_stderr else sys.stdout
    status_console = Console(file=status_stream, highlight=False)

    meta: dict[str, Any] = {
        "run_id": run_id,
        "started_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "sme_bench_version": __version__,
        "python_version": sys.version.split()[0],
        "os": platform.platform(),
        "model": config.model,
        "served_model_name": config.served_model_name or config.model,
        "base_url": sanitize_base_url_for_metadata(config.base_url),
        "suite_id": suite.manifest.id,
        "suite_version": suite.manifest.version,
        "suite_path": suite_path_for_metadata(suite.directory),
        "suite_hash": suite.suite_hash,
        "member_suites": suite.member_suites,
        "filters": {
            "languages": config.languages,
            "categories": config.categories,
            "difficulty": config.difficulty,
            "tags": config.tags,
        },
        "repeats": config.repeats,
        "concurrency": config.concurrency,
        "seed": config.seed,
        "timeout": config.timeout,
        "retries": config.retries,
        "pricing": config.pricing.model_dump(),
        "save_reasoning": config.save_reasoning,
        "status": "running",
    }
    write_metadata(run_dir, meta)

    work: list[tuple[BenchmarkTask, int]] = []
    for task in ordered:
        for repeat_index in range(config.repeats):
            if (task.id, repeat_index) in completed:
                continue
            work.append((task, repeat_index))

    total_planned = len(ordered) * config.repeats
    already_done = total_planned - len(work)

    await progress.emit(
        "run_started",
        run_id,
        model=config.model,
        suite_id=suite.manifest.id,
        total_attempts=total_planned,
        remaining=len(work),
    )

    results: list[AttemptResult] = []
    # Load prior attempts for aggregation when resuming
    if attempts_path.exists():
        with attempts_path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    try:
                        results.append(AttemptResult.model_validate(json.loads(line)))
                    except Exception:  # noqa: BLE001
                        continue

    sem = asyncio.Semaphore(config.concurrency)
    lock = asyncio.Lock()
    counters = {
        "passed": 0,
        "partial": 0,
        "failed": 0,
        "critical": 0,
        "infra": 0,
        "done": already_done,
        "tps_sum": 0.0,
        "tps_n": 0,
    }
    interrupted = False
    failed = False
    show_dashboard = use_dashboard(status_console, config.dashboard)
    suite_label = f"{suite.manifest.name} v{suite.manifest.version}"

    async with OpenAICompatibleClient(
        base_url=config.base_url,
        api_key_env=config.api_key_env,
        timeout=config.timeout,
        retries=config.retries,
    ) as client:
        # Health check
        with contextlib.suppress(Exception):
            await client.list_models()

        if config.warmup and work:
            warm_task = work[0][0]
            await client.chat_completion(
                model=config.model,
                messages=_messages_payload(warm_task)[:1] or [{"role": "user", "content": "ping"}],
                max_tokens=8,
                temperature=0,
            )

        async def run_one(task: BenchmarkTask, repeat_index: int) -> AttemptResult:
            async with sem:
                await progress.emit(
                    "task_started",
                    run_id,
                    task_id=task.id,
                    language=task.language,
                    repeat_index=repeat_index,
                )

                async def on_first_response() -> None:
                    await progress.emit(
                        "request_first_response", run_id, task_id=task.id, repeat_index=repeat_index
                    )

                async def on_first_token() -> None:
                    await progress.emit(
                        "request_first_token", run_id, task_id=task.id, repeat_index=repeat_index
                    )

                # Inject suite_dir into json_schema scorers
                for spec in task.scorers:
                    if spec.type == "json_schema":
                        spec.params.setdefault("_suite_dir", str(suite.directory))

                req = await client.chat_completion(
                    model=config.model,
                    messages=_messages_payload(task),
                    max_tokens=task.generation.max_tokens,
                    temperature=task.generation.temperature,
                    seed=task.generation.seed,
                    response_format=task.generation.response_format,
                    extra_body=config.extra_body,
                    on_first_response=on_first_response,
                    on_first_token=on_first_token,
                )

                if req.error_type:
                    attempt = AttemptResult(
                        task_id=task.id,
                        pair_id=task.pair_id,
                        language=task.language,
                        category=task.category,
                        task_type=task.task_type,
                        difficulty=task.difficulty,
                        risk=task.risk,
                        repeat_index=repeat_index,
                        output_text=req.output_text,
                        infrastructure_error=True,
                        error_type=req.error_type,
                        error_message=redact_secrets(req.error_message or ""),
                        retry_count=max(0, req.attempts - 1),
                        ttfr=req.ttfr,
                        ttft=req.ttft,
                        total_latency=req.total_latency,
                        generation_tps=req.generation_tps,
                        prompt_tokens=req.prompt_tokens,
                        completion_tokens=req.completion_tokens,
                        started_at=req.started_at,
                        completed_at=req.completed_at,
                        reasoning_text=req.reasoning_text if config.save_reasoning else None,
                    )
                    await progress.emit(
                        "task_failed",
                        run_id,
                        task_id=task.id,
                        repeat_index=repeat_index,
                        error_type=req.error_type,
                    )
                    return attempt

                score_results, weighted, effective, passed, partial, critical, parsed = evaluate_attempt(
                    task, req.output_text
                )
                cost = estimate_cost(
                    prompt_tokens=req.prompt_tokens,
                    completion_tokens=req.completion_tokens,
                    pricing=config.pricing,
                )
                attempt = AttemptResult(
                    task_id=task.id,
                    pair_id=task.pair_id,
                    language=task.language,
                    category=task.category,
                    task_type=task.task_type,
                    difficulty=task.difficulty,
                    risk=task.risk,
                    repeat_index=repeat_index,
                    output_text=req.output_text,
                    parsed_output=parsed,
                    score_results=score_results,
                    weighted_score=weighted,
                    effective_score=effective,
                    passed=passed,
                    partial=partial,
                    critical_failure=critical,
                    ttfr=req.ttfr,
                    ttft=req.ttft,
                    total_latency=req.total_latency,
                    generation_tps=req.generation_tps,
                    tokens_estimated=req.completion_tokens is None,
                    prompt_tokens=req.prompt_tokens,
                    completion_tokens=req.completion_tokens,
                    cost=cost,
                    retry_count=max(0, req.attempts - 1),
                    started_at=req.started_at,
                    completed_at=req.completed_at,
                    reasoning_text=req.reasoning_text if config.save_reasoning else None,
                )
                await progress.emit(
                    "task_completed",
                    run_id,
                    task_id=task.id,
                    repeat_index=repeat_index,
                    passed=passed,
                    effective_score=effective,
                    critical_failure=critical,
                )
                return attempt

        async def guarded(task: BenchmarkTask, repeat_index: int) -> AttemptResult | None:
            nonlocal failed, interrupted
            try:
                attempt = await run_one(task, repeat_index)
            except asyncio.CancelledError:
                interrupted = True
                raise
            async with lock:
                _append_attempt(attempts_path, attempt, save_reasoning=config.save_reasoning)
                results.append(attempt)
                counters["done"] += 1
                if attempt.infrastructure_error:
                    counters["infra"] += 1
                    if config.fail_fast:
                        failed = True
                    verdict = "[bold red]failed[/bold red] (infrastructure)"
                elif attempt.critical_failure:
                    counters["critical"] += 1
                    counters["failed"] += 1
                    verdict = "[bold red]failed[/bold red] (critical)"
                elif attempt.passed:
                    counters["passed"] += 1
                    verdict = "[bold green]passed[/bold green]"
                elif attempt.partial:
                    counters["partial"] += 1
                    verdict = "[bold yellow]partial[/bold yellow]"
                else:
                    counters["failed"] += 1
                    verdict = "[bold red]failed[/bold red]"

                if not attempt.infrastructure_error and attempt.generation_tps is not None:
                    counters["tps_sum"] += attempt.generation_tps
                    counters["tps_n"] += 1

                mean_tps = (
                    counters["tps_sum"] / counters["tps_n"] if counters["tps_n"] > 0 else None
                )
                attempt_line = (
                    f"[{counters['done']}/{total_planned}] {task.id} "
                    f"({task.language}) repeat={repeat_index + 1}/{config.repeats}  {verdict}"
                )
                if dashboard_obj is not None:
                    dashboard_obj.update_counts(counters, mean_tps)
                    dashboard_obj.add_line(attempt_line)
                else:
                    status_console.print(attempt_line)

                task_attempts = [a for a in results if a.task_id == task.id]
                if len(task_attempts) >= config.repeats:
                    if all(a.passed for a in task_attempts):
                        task_verdict = "[bold green]passed[/bold green]"
                    elif all(a.passed or a.partial for a in task_attempts):
                        task_verdict = "[bold yellow]partial[/bold yellow]"
                    else:
                        task_verdict = "[bold red]failed[/bold red]"
                    passed_n = sum(1 for a in task_attempts if a.passed)
                    partial_n = sum(1 for a in task_attempts if a.partial)
                    rollup_line = (
                        f"[dim]  → {task.id}: {passed_n}/{config.repeats} pass, "
                        f"{partial_n}/{config.repeats} partial[/dim]  {task_verdict}"
                    )
                    if dashboard_obj is not None:
                        dashboard_obj.add_line(rollup_line)
                    else:
                        status_console.print(rollup_line)
            return attempt

        dashboard_obj: RunDashboard | None = None
        if show_dashboard:
            dashboard_obj = RunDashboard(
                status_console,
                model=config.model,
                suite_label=suite_label,
                total=total_planned,
            )

        async def run_pending() -> None:
            nonlocal failed, interrupted
            pending = [asyncio.create_task(guarded(t, r)) for t, r in work]
            try:
                for coro in asyncio.as_completed(pending):
                    if failed:
                        for p in pending:
                            p.cancel()
                        break
                    try:
                        await coro
                    except asyncio.CancelledError:
                        interrupted = True
                        break
            except KeyboardInterrupt:
                interrupted = True
                for p in pending:
                    p.cancel()

        if dashboard_obj is not None:
            status_console.print()
            with dashboard_obj.live():
                await run_pending()
        else:
            await run_pending()

    # Deterministic sort for aggregation
    results.sort(key=lambda a: (a.task_id, a.repeat_index))

    summary = aggregate(results, category_weights=suite.manifest.category_weights)
    summary["run_id"] = run_id
    summary["model"] = config.model
    summary["suite_id"] = suite.manifest.id
    summary["suite_version"] = suite.manifest.version

    write_summary_json(run_dir / "summary.json", summary)
    write_summary_reports(run_dir, summary, model=config.model)
    tasks_by_id = {t.id: t for t in tasks}
    report_kwargs = {
        "model": config.model,
        "suite_id": suite.manifest.id,
        "suite_version": suite.manifest.version,
        "tasks_by_id": tasks_by_id,
    }
    write_failures_reports(run_dir, results, **report_kwargs)
    write_success_reports(run_dir, results, **report_kwargs)
    write_attempts_csv(run_dir / "attempts.csv", results)

    if interrupted:
        meta["status"] = "interrupted"
        await progress.emit("run_interrupted", run_id)
    elif failed:
        meta["status"] = "failed"
        await progress.emit("run_completed", run_id, status="failed")
    else:
        meta["status"] = "completed"
        await progress.emit("run_completed", run_id, status="completed")
    meta["completed_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    write_metadata(run_dir, meta)
    progress.close()
    return run_dir
