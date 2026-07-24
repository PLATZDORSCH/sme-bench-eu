"""Tests for official-run exclusion policy."""

from __future__ import annotations

import json
from pathlib import Path

from sme_bench.run_validity import invalid_reason, load_invalid_runs


def test_registry_marks_invalid_run(tmp_path: Path) -> None:
    registry_path = tmp_path / "invalid-runs.json"
    registry_path.write_text(
        json.dumps({"runs": {"bad-run": {"reason": "duplicate inputs"}}}),
        encoding="utf-8",
    )
    registry = load_invalid_runs(registry_path)
    assert invalid_reason(tmp_path / "bad-run", {"run_id": "bad-run"}, registry=registry) == (
        "duplicate inputs"
    )
    assert invalid_reason(tmp_path / "good-run", {"run_id": "good-run"}, registry=registry) is None


def test_invalid_marker_and_metadata_status(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "INVALID.txt").write_text("broken calibration\n", encoding="utf-8")
    assert invalid_reason(run_dir, {}, registry={}) == "broken calibration"
    (run_dir / "INVALID.txt").unlink()
    assert invalid_reason(
        run_dir,
        {"status": "invalid", "invalid_reason": "manual review"},
        registry={},
    ) == "manual review"
