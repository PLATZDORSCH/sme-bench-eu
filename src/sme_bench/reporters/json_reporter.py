"""JSON summary reporter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_summary_json(path: Path, summary: dict[str, Any]) -> None:
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_summary_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("summary.json must contain an object")
    return data
