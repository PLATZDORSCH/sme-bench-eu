"""Machine-readable validity policy for benchmark runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def default_invalid_registry() -> Path:
    return Path("suites/compatibility/invalid-runs.json")


def load_invalid_runs(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Return invalid run records keyed by run id."""
    registry = path or default_invalid_registry()
    if not registry.exists():
        return {}
    raw = json.loads(registry.read_text(encoding="utf-8"))
    runs = raw.get("runs", {})
    if not isinstance(runs, dict):
        raise ValueError(f"Invalid run registry must contain an object at 'runs': {registry}")
    out: dict[str, dict[str, Any]] = {}
    for run_id, record in runs.items():
        if not isinstance(run_id, str) or not isinstance(record, dict):
            raise ValueError(f"Invalid run registry entry in {registry}")
        out[run_id] = dict(record)
    return out


def invalid_reason(
    run_dir: Path,
    metadata: dict[str, Any],
    *,
    registry: dict[str, dict[str, Any]] | None = None,
) -> str | None:
    """Return why a run is invalid, or ``None`` when it is eligible."""
    run_id = str(metadata.get("run_id") or run_dir.name)
    records = registry if registry is not None else load_invalid_runs()
    if run_id in records:
        return str(records[run_id].get("reason") or "Listed in invalid-run registry")
    marker = run_dir / "INVALID.txt"
    if marker.exists():
        return marker.read_text(encoding="utf-8").strip() or "INVALID.txt marker present"
    status = str(metadata.get("status") or "").casefold()
    if status in {"invalid", "excluded"}:
        return str(metadata.get("invalid_reason") or f"metadata status={status}")
    return None
