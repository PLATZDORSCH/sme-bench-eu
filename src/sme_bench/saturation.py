"""Saturation report: which pairs still discriminate across runs."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from sme_bench.models import AttemptResult
from sme_bench.statistics import dedupe_attempts

SATURATED_THRESHOLD = 0.95


def _load_attempts(run_dir: Path) -> list[AttemptResult]:
    path = run_dir / "attempts.jsonl"
    if not path.exists():
        return []
    rows: list[AttemptResult] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(AttemptResult.model_validate(json.loads(line)))
    return dedupe_attempts(rows)


def _model_name(run_dir: Path) -> str:
    meta_path = run_dir / "metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return str(meta.get("model") or run_dir.name)
    return run_dir.name


def pair_pass_rate(attempts: list[AttemptResult]) -> dict[str, float]:
    by_pair: dict[str, list[bool]] = defaultdict(list)
    for attempt in attempts:
        key = attempt.pair_id or attempt.task_id
        by_pair[key].append(attempt.passed)
    return {pair: (sum(flags) / len(flags) if flags else 0.0) for pair, flags in by_pair.items()}


def classify_pair(rates: dict[str, float]) -> str:
    if not rates:
        return "unsolved"
    values = list(rates.values())
    if all(rate >= SATURATED_THRESHOLD for rate in values):
        return "saturated"
    if all(rate <= 0.0 for rate in values):
        return "unsolved"
    return "discriminating"


def saturation_report(run_dirs: list[Path]) -> dict[str, Any]:
    models: list[dict[str, Any]] = []
    pair_rates: dict[str, dict[str, float]] = defaultdict(dict)
    for run_dir in run_dirs:
        attempts = _load_attempts(run_dir)
        model = _model_name(run_dir)
        rates = pair_pass_rate(attempts)
        models.append(
            {
                "model": model,
                "run": str(run_dir),
                "attempts": len(attempts),
                "pass_rate": (sum(a.passed for a in attempts) / len(attempts) if attempts else 0.0),
            }
        )
        for pair, rate in rates.items():
            pair_rates[pair][model] = rate

    pairs: list[dict[str, Any]] = []
    counts = {"saturated": 0, "discriminating": 0, "unsolved": 0}
    for pair_id, rates in sorted(pair_rates.items()):
        status = classify_pair(rates)
        counts[status] += 1
        pairs.append({"pair_id": pair_id, "status": status, "rates": rates})

    return {"models": models, "counts": counts, "pairs": pairs}


def write_saturation_report(report: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() == ".md":
        lines = [
            "# Saturation report",
            "",
            f"- Saturated: {report['counts']['saturated']}",
            f"- Discriminating: {report['counts']['discriminating']}",
            f"- Unsolved: {report['counts']['unsolved']}",
            "",
            "| Pair | Status | " + " | ".join(m["model"] for m in report["models"]) + " |",
            "| --- | --- | " + " | ".join("---:" for _ in report["models"]) + " |",
        ]
        models = [m["model"] for m in report["models"]]
        for pair in report["pairs"]:
            rates = " | ".join(f"{pair['rates'].get(model, 0.0):.2f}" for model in models)
            lines.append(f"| `{pair['pair_id']}` | {pair['status']} | {rates} |")
        output.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
