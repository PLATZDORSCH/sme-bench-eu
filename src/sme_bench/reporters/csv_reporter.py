"""CSV attempts reporter."""

from __future__ import annotations

import csv
import json
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
        "format_only_failure",
        "weighted_score",
        "effective_score",
        "ttfr",
        "ttft",
        "ttfa",
        "total_latency",
        "generation_tps",
        "tps_unreliable",
        "prompt_tokens",
        "completion_tokens",
        "cost",
        "infrastructure_error",
        "excluded_reason",
        "turns_used",
        "median_turn_latency",
        "variant_of",
        "error_type",
        "finish_reason",
        "retry_count",
        "tool_calls",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for attempt in attempts:
            row = {k: getattr(attempt, k) for k in fieldnames if k != "tool_calls"}
            row["tool_calls"] = json.dumps(
                [call.model_dump(exclude_none=True) for call in attempt.tool_calls],
                ensure_ascii=False,
            )
            writer.writerow(row)
