"""Aggregation statistics for benchmark runs."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sme_bench.models import AttemptResult, output_tokens_per_second
from sme_bench.utils import percentile


def _slice_metrics(attempts: list[AttemptResult]) -> dict[str, Any]:
    if not attempts:
        return {
            "unique_tasks": 0,
            "attempts": 0,
            "attempt_pass_rate": 0.0,
            "attempt_partial_rate": 0.0,
            "reliable_pass_rate": 0.0,
            "mean_effective_score": 0.0,
            "critical_failure_rate": 0.0,
            "infrastructure_error_rate": 0.0,
            "ttft_p50": None,
            "ttft_p95": None,
            "latency_p50": None,
            "latency_p95": None,
            "mean_generation_tps": None,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_cost": None,
            "cost_per_passed_attempt": None,
        }

    by_task: dict[str, list[AttemptResult]] = defaultdict(list)
    for a in attempts:
        by_task[a.task_id].append(a)

    unique = len(by_task)
    n = len(attempts)
    passed_attempts = sum(1 for a in attempts if a.passed)
    partial_attempts = sum(1 for a in attempts if a.partial)
    critical = sum(1 for a in attempts if a.critical_failure)
    infra = sum(1 for a in attempts if a.infrastructure_error)
    reliable = sum(
        1
        for task_attempts in by_task.values()
        if task_attempts and all(a.passed for a in task_attempts)
    )

    ttfts = [a.ttft for a in attempts if a.ttft is not None]
    latencies = [a.total_latency for a in attempts if a.total_latency is not None]
    tps = [
        rate
        for a in attempts
        if not a.infrastructure_error
        for rate in [
            output_tokens_per_second(
                completion_tokens=a.completion_tokens,
                total_latency=a.total_latency,
                ttft=a.ttft,
            )
        ]
        if rate is not None
    ]
    costs = [a.cost for a in attempts if a.cost is not None]
    passed_costs = [a.cost for a in attempts if a.passed and a.cost is not None]

    prompt_tokens = sum(a.prompt_tokens or 0 for a in attempts)
    completion_tokens = sum(a.completion_tokens or 0 for a in attempts)
    total_cost = sum(costs) if costs else None
    cost_per_passed = (sum(passed_costs) / len(passed_costs)) if passed_costs else None

    return {
        "unique_tasks": unique,
        "attempts": n,
        "attempt_pass_rate": passed_attempts / n if n else 0.0,
        "attempt_partial_rate": partial_attempts / n if n else 0.0,
        "reliable_pass_rate": reliable / unique if unique else 0.0,
        "mean_effective_score": sum(a.effective_score for a in attempts) / n,
        "critical_failure_rate": critical / n if n else 0.0,
        "infrastructure_error_rate": infra / n if n else 0.0,
        "ttft_p50": percentile(ttfts, 50) if ttfts else None,
        "ttft_p95": percentile(ttfts, 95) if ttfts else None,
        "latency_p50": percentile(latencies, 50) if latencies else None,
        "latency_p95": percentile(latencies, 95) if latencies else None,
        "mean_generation_tps": (sum(tps) / len(tps)) if tps else None,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_cost": total_cost,
        "cost_per_passed_attempt": cost_per_passed,
    }


def language_parity(attempts: list[AttemptResult]) -> dict[str, Any]:
    by_lang: dict[str, list[AttemptResult]] = defaultdict(list)
    for a in attempts:
        by_lang[a.language].append(a)

    de = _slice_metrics(by_lang.get("de-DE", []))
    en = _slice_metrics(by_lang.get("en-GB", []))

    by_pair: dict[str, dict[str, bool]] = defaultdict(dict)
    for a in attempts:
        if not a.pair_id:
            continue
        # majority pass per language for the pair
        by_pair[a.pair_id].setdefault("_attempts", {})  # type: ignore[arg-type]

    pair_lang_pass: dict[str, dict[str, list[bool]]] = defaultdict(lambda: defaultdict(list))
    for a in attempts:
        if a.pair_id:
            pair_lang_pass[a.pair_id][a.language].append(a.passed)

    consistent = 0
    total_pairs = 0
    for _pair_id, langs in pair_lang_pass.items():
        if "de-DE" in langs and "en-GB" in langs:
            total_pairs += 1
            de_pass = all(langs["de-DE"])
            en_pass = all(langs["en-GB"])
            if de_pass == en_pass:
                consistent += 1

    return {
        "de-DE": de,
        "en-GB": en,
        "language_gap_pass_rate": en["attempt_pass_rate"] - de["attempt_pass_rate"],
        "language_gap_score": en["mean_effective_score"] - de["mean_effective_score"],
        "pair_consistency": (consistent / total_pairs) if total_pairs else None,
        "paired_count": total_pairs,
    }


def sme_core_score(
    attempts: list[AttemptResult],
    category_weights: dict[str, float],
) -> float:
    by_cat: dict[str, list[AttemptResult]] = defaultdict(list)
    for a in attempts:
        by_cat[a.category].append(a)

    if not by_cat:
        return 0.0

    weighted_sum = 0.0
    weight_total = 0.0
    for category, cat_attempts in by_cat.items():
        weight = category_weights.get(category, 1.0)
        cat_score = sum(a.effective_score for a in cat_attempts) / len(cat_attempts)
        weighted_sum += cat_score * weight
        weight_total += weight
    if weight_total <= 0:
        return 0.0
    return (weighted_sum / weight_total) * 100.0


def aggregate(
    attempts: list[AttemptResult],
    *,
    category_weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    weights = category_weights or {}
    overall = _slice_metrics(attempts)
    by_language = {
        lang: _slice_metrics([a for a in attempts if a.language == lang])
        for lang in sorted({a.language for a in attempts})
    }
    by_category = {
        cat: _slice_metrics([a for a in attempts if a.category == cat])
        for cat in sorted({a.category for a in attempts})
    }
    by_task_type = {
        tt: _slice_metrics([a for a in attempts if a.task_type == tt])
        for tt in sorted({a.task_type for a in attempts})
    }
    by_difficulty = {
        d: _slice_metrics([a for a in attempts if a.difficulty == d])
        for d in sorted({a.difficulty for a in attempts})
    }
    parity = language_parity(attempts)
    return {
        "overall": overall,
        "sme_core_score": sme_core_score(attempts, weights),
        "by_language": by_language,
        "by_category": by_category,
        "by_task_type": by_task_type,
        "by_difficulty": by_difficulty,
        "language_parity": parity,
    }
