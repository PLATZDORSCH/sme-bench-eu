"""CSV attempts reporter."""

from __future__ import annotations

import csv
from pathlib import Path

from sme_bench.models import AttemptResult


def write_attempts_csv(path: Path, attempts: list[AttemptResult]) -> None:
    fieldnames = [
        "task_id",
        "pair_id",
        "language",
        "category",
        "task_type",
        "difficulty",
        "risk",
        "repeat_index",
        "passed",
        "partial",
        "critical_failure",
        "weighted_score",
        "effective_score",
        "ttfr",
        "ttft",
        "total_latency",
        "generation_tps",
        "prompt_tokens",
        "completion_tokens",
        "cost",
        "infrastructure_error",
        "error_type",
        "retry_count",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for attempt in attempts:
            row = {k: getattr(attempt, k) for k in fieldnames}
            writer.writerow(row)
