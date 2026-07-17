"""Unit tests for task loading and resume."""

from __future__ import annotations

import json
from pathlib import Path

from sme_bench.runner import _load_completed_keys
from sme_bench.scorers.base import known_scorer_names
from sme_bench.task_loader import FULL_SUITE_IDS, load_full_benchmark


def test_resume_key_detection(tmp_path: Path) -> None:
    path = tmp_path / "attempts.jsonl"
    path.write_text(
        json.dumps({"task_id": "a", "repeat_index": 0})
        + "\n"
        + json.dumps({"task_id": "a", "repeat_index": 1})
        + "\n",
        encoding="utf-8",
    )
    keys = _load_completed_keys(path)
    assert keys == {("a", 0), ("a", 1)}


def test_load_full_benchmark() -> None:
    loaded = load_full_benchmark(known_scorers=known_scorer_names())
    assert loaded.manifest.id == "sme-full"
    assert not any(i.severity == "error" for i in loaded.issues)
    assert len(loaded.member_suites) == len(FULL_SUITE_IDS)
    # 72 core + 6*14 domain = 156
    assert len(loaded.tasks) == 156
    assert len({t.id for t in loaded.tasks}) == 156
