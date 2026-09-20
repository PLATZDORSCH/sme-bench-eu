"""Saturation report classification."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sme_bench.models import AttemptResult
from sme_bench.saturation import classify_pair, saturation_report, write_saturation_report


def _attempt(task_id: str, pair_id: str, passed: bool) -> AttemptResult:
    return AttemptResult(
        task_id=task_id,
        pair_id=pair_id,
        language="de-DE",
        category="tool_use",
        task_type="stock_lookup",
        difficulty="easy",
        risk="low",
        repeat_index=0,
        passed=passed,
        started_at=datetime.now(UTC),
    )


def _write_run(path: Path, model: str, attempts: list[AttemptResult]) -> None:
    path.mkdir(parents=True)
    (path / "metadata.json").write_text(json.dumps({"model": model}), encoding="utf-8")
    (path / "attempts.jsonl").write_text(
        "\n".join(a.model_dump_json() for a in attempts) + "\n",
        encoding="utf-8",
    )


def test_classify_pair() -> None:
    assert classify_pair({"a": 1.0, "b": 0.95}) == "saturated"
    assert classify_pair({"a": 1.0, "b": 0.2}) == "discriminating"
    assert classify_pair({"a": 0.0, "b": 0.0}) == "unsolved"


def test_saturation_report_and_write(tmp_path: Path) -> None:
    run_a = tmp_path / "a"
    run_b = tmp_path / "b"
    _write_run(
        run_a,
        "model-a",
        [
            _attempt("de-easy", "easy-001", True),
            _attempt("de-hard", "hard-001", False),
            _attempt("de-gap", "gap-001", True),
        ],
    )
    _write_run(
        run_b,
        "model-b",
        [
            _attempt("de-easy", "easy-001", True),
            _attempt("de-hard", "hard-001", False),
            _attempt("de-gap", "gap-001", False),
        ],
    )
    report = saturation_report([run_a, run_b])
    by_id = {row["pair_id"]: row["status"] for row in report["pairs"]}
    assert by_id["easy-001"] == "saturated"
    assert by_id["hard-001"] == "unsolved"
    assert by_id["gap-001"] == "discriminating"
    out = tmp_path / "saturation.json"
    write_saturation_report(report, out)
    assert json.loads(out.read_text(encoding="utf-8"))["counts"]["saturated"] == 1
    md = tmp_path / "saturation.md"
    write_saturation_report(report, md)
    assert "saturated" in md.read_text(encoding="utf-8")
