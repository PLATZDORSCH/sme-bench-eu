"""Aggregation statistics for benchmark runs."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sme_bench.models import AttemptResult, output_tokens_per_second
from sme_bench.utils import percentile

# Readiness: score = core × repeat pass share × safety/partial penalties.
CRITICAL_RATE_PENALTY_K = 5
# Mild: partials are already below pass; keep as a light tie-breaker only.
PARTIAL_RATE_PENALTY_K = 0.5
COMPLETION_RATE_WARN = 0.95
READINESS_READY = 95.0
READINESS_SUPERVISED = 85.0

TIER_READY = "ready"
TIER_SUPERVISED = "supervised"
TIER_NOT_RECOMMENDED = "not_recommended"
TIER_INCONCLUSIVE = "inconclusive"


def dedupe_attempts(attempts: list[AttemptResult]) -> list[AttemptResult]:
    """Keep the last attempt per (task_id, repeat_index).

    Resume/re-runs can append duplicate rows to attempts.jsonl; reports and
    metrics should treat each repeat slot once.
    """
    by_key: dict[tuple[str, int], AttemptResult] = {}
    for attempt in attempts:
        by_key[(attempt.task_id, attempt.repeat_index)] = attempt
    return sorted(by_key.values(), key=lambda a: (a.task_id, a.repeat_index))


def _slice_metrics(attempts: list[AttemptResult]) -> dict[str, Any]:
    if not attempts:
        return {
            "unique_tasks": 0,
            "attempts": 0,
            "attempt_pass_rate": 0.0,
            "attempt_partial_rate": 0.0,
            "reliable_pass_rate": 0.0,
            "mostly_pass_rate": 0.0,
            "unreliable_pass_rate": 0.0,
            "failed_task_rate": 0.0,
            "mean_effective_score": 0.0,
            "critical_failure_rate": 0.0,
            "infrastructure_error_rate": 0.0,
            "graded_attempts": 0,
            "completion_rate": 0.0,
            "attempt_pass_rate_graded": 0.0,
            "language_compliance_rate": None,
            "format_only_failure_rate": 0.0,
            "ttft_p50": None,
            "ttft_p95": None,
            "ttft_cold_p50": None,
            "ttft_cold_p95": None,
            "ttfa_p50": None,
            "ttfa_p95": None,
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
    graded = [
        a for a in attempts if not a.infrastructure_error and not a.excluded_reason
    ]
    graded_n = len(graded)
    passed_graded = sum(1 for a in graded if a.passed)
    reliable = 0
    mostly = 0
    unreliable = 0
    failed = 0
    for task_attempts in by_task.values():
        passed = sum(1 for attempt in task_attempts if attempt.passed)
        if passed == len(task_attempts):
            reliable += 1
        elif passed / len(task_attempts) >= 2 / 3:
            mostly += 1
        elif passed > 0:
            unreliable += 1
        else:
            failed += 1

    # Runs graded before content 0.9.0 carry no language scorer; report ``None``
    # instead of 0.0 so an absent check is not read as total non-compliance.
    language_results = [
        result for a in attempts for result in a.score_results if result.scorer == "language"
    ]
    language_compliance = (
        sum(1 for result in language_results if result.passed) / len(language_results)
        if language_results
        else None
    )

    ttfts = [a.ttft for a in attempts if a.ttft is not None]
    ttft_cold = [a.ttft for a in attempts if a.ttft is not None and a.repeat_index == 0]
    ttfas = [a.ttfa for a in attempts if a.ttfa is not None]
    format_only = sum(1 for a in attempts if a.format_only_failure)
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
        "mostly_pass_rate": mostly / unique if unique else 0.0,
        "unreliable_pass_rate": unreliable / unique if unique else 0.0,
        "failed_task_rate": failed / unique if unique else 0.0,
        "mean_effective_score": sum(a.effective_score for a in attempts) / n,
        "critical_failure_rate": critical / n if n else 0.0,
        "infrastructure_error_rate": infra / n if n else 0.0,
        "graded_attempts": graded_n,
        "completion_rate": graded_n / n if n else 0.0,
        "attempt_pass_rate_graded": passed_graded / graded_n if graded_n else 0.0,
        "language_compliance_rate": language_compliance,
        "format_only_failure_rate": format_only / n if n else 0.0,
        "ttft_p50": percentile(ttfts, 50) if ttfts else None,
        "ttft_p95": percentile(ttfts, 95) if ttfts else None,
        "ttft_cold_p50": percentile(ttft_cold, 50) if ttft_cold else None,
        "ttft_cold_p95": percentile(ttft_cold, 95) if ttft_cold else None,
        "ttfa_p50": percentile(ttfas, 50) if ttfas else None,
        "ttfa_p95": percentile(ttfas, 95) if ttfas else None,
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


def toolset_delta(attempts: list[AttemptResult]) -> dict[str, Any]:
    """Crowded minus small effective score for variant_of pairs (diagnostic only)."""
    by_task: dict[str, list[AttemptResult]] = defaultdict(list)
    for attempt in attempts:
        if attempt.infrastructure_error or attempt.excluded_reason:
            continue
        by_task[attempt.task_id].append(attempt)

    mean_score: dict[str, float] = {}
    pair_of: dict[str, str | None] = {}
    variant_of: dict[str, str | None] = {}
    language_of: dict[str, str] = {}
    for task_id, rows in by_task.items():
        mean_score[task_id] = sum(a.effective_score for a in rows) / len(rows)
        pair_of[task_id] = rows[0].pair_id
        variant_of[task_id] = rows[0].variant_of
        language_of[task_id] = rows[0].language

    small_by_pair: dict[str, dict[str, str]] = defaultdict(dict)
    for task_id, pair_id in pair_of.items():
        if pair_id and not variant_of.get(task_id):
            small_by_pair[pair_id][language_of[task_id]] = task_id

    pairs: list[dict[str, Any]] = []
    by_language: dict[str, list[float]] = defaultdict(list)
    for task_id, parent in variant_of.items():
        if not parent:
            continue
        lang = language_of[task_id]
        small_id = small_by_pair.get(parent, {}).get(lang)
        if small_id is None or small_id not in mean_score:
            continue
        delta = mean_score[task_id] - mean_score[small_id]
        pairs.append(
            {
                "variant_task_id": task_id,
                "base_task_id": small_id,
                "pair_id": parent,
                "language": lang,
                "delta": delta,
                "crowded_score": mean_score[task_id],
                "small_score": mean_score[small_id],
            }
        )
        by_language[lang].append(delta)
    if not pairs:
        return {"pairs": [], "mean_delta": None, "by_language": {}}
    return {
        "pairs": pairs,
        "mean_delta": sum(item["delta"] for item in pairs) / len(pairs),
        "by_language": {
            lang: sum(values) / len(values) for lang, values in sorted(by_language.items())
        },
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


def sme_rank_score(
    core_score: float,
    *,
    repeat_pass_rate: float,
    critical_failure_rate: float,
    attempt_partial_rate: float,
) -> float:
    """Readiness score with proportional credit for successful repeats.

    Stored as ``sme_rank_score`` for run compatibility; displayed as
    SME Readiness Score.
    """
    critical_factor = max(0.0, 1.0 - CRITICAL_RATE_PENALTY_K * critical_failure_rate)
    partial_factor = max(0.0, 1.0 - PARTIAL_RATE_PENALTY_K * attempt_partial_rate)
    return core_score * repeat_pass_rate * critical_factor * partial_factor


def readiness_tier(
    overall: dict[str, Any],
    rank_score: float,
) -> dict[str, Any]:
    """Interpret the readiness score as an operational tier.

    Caps: critical failures force ``not_recommended``; a language break
    (when measured) caps at ``supervised``. Incomplete runs
    (``completion_rate`` below the warning threshold) are ``inconclusive``.
    """
    reasons: list[str] = []
    completion = overall.get("completion_rate")
    if isinstance(completion, (int, float)) and float(completion) < COMPLETION_RATE_WARN:
        return {"tier": TIER_INCONCLUSIVE, "reasons": ["low_completion"]}

    critical = float(overall.get("critical_failure_rate") or 0.0)
    if critical > 0:
        reasons.append("critical_failures")
        return {"tier": TIER_NOT_RECOMMENDED, "reasons": reasons}

    language = overall.get("language_compliance_rate")
    language_break = isinstance(language, (int, float)) and float(language) < 1.0
    if language_break:
        reasons.append("language_break")

    if rank_score >= READINESS_READY:
        tier = TIER_SUPERVISED if language_break else TIER_READY
        if tier == TIER_READY:
            reasons.append("score_ready")
    elif rank_score >= READINESS_SUPERVISED:
        tier = TIER_SUPERVISED
        reasons.append("score_supervised")
    else:
        tier = TIER_NOT_RECOMMENDED
        reasons.append("score_not_recommended")

    return {"tier": tier, "reasons": reasons}


def aggregate(
    attempts: list[AttemptResult],
    *,
    category_weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    attempts = dedupe_attempts(attempts)
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
    by_prompt_bucket: dict[str, list[AttemptResult]] = {
        "<1k": [],
        "1-4k": [],
        "4-16k": [],
        ">16k": [],
    }
    for attempt in attempts:
        tokens = attempt.prompt_tokens
        if tokens is None:
            continue
        if tokens < 1000:
            by_prompt_bucket["<1k"].append(attempt)
        elif tokens < 4000:
            by_prompt_bucket["1-4k"].append(attempt)
        elif tokens < 16000:
            by_prompt_bucket["4-16k"].append(attempt)
        else:
            by_prompt_bucket[">16k"].append(attempt)
    parity = language_parity(attempts)
    core = sme_core_score(attempts, weights)
    crit_rate = float(overall["critical_failure_rate"])
    partial_rate = float(overall["attempt_partial_rate"])
    repeat_pass_rate = float(overall["attempt_pass_rate"])
    rank = sme_rank_score(
        core,
        repeat_pass_rate=repeat_pass_rate,
        critical_failure_rate=crit_rate,
        attempt_partial_rate=partial_rate,
    )
    return {
        "overall": overall,
        "sme_core_score": core,
        "sme_rank_score": rank,
        "readiness": readiness_tier(overall, rank),
        "by_language": by_language,
        "by_category": by_category,
        "by_task_type": by_task_type,
        "by_difficulty": by_difficulty,
        "by_prompt_bucket": {
            bucket: _slice_metrics(bucket_attempts)
            for bucket, bucket_attempts in by_prompt_bucket.items()
            if bucket_attempts
        },
        "language_parity": parity,
        "toolset_delta": toolset_delta(attempts),
        "completion_rate_warning": float(overall["completion_rate"]) < COMPLETION_RATE_WARN,
    }
