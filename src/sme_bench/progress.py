"""Async-safe progress event emitter (JSONL)."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TextIO


class ProgressEmitter:
    def __init__(self, target: str | None) -> None:
        self.target = target
        self._lock = asyncio.Lock()
        self._warned = False
        self._fp: TextIO | None = None
        self._is_stdout = False
        if target is None:
            return
        if target == "-":
            self._fp = sys.stdout
            self._is_stdout = True
        else:
            path = Path(target)
            path.parent.mkdir(parents=True, exist_ok=True)
            self._fp = path.open("a", encoding="utf-8")

    @property
    def redirects_status_to_stderr(self) -> bool:
        return self._is_stdout

    async def emit(self, event_type: str, run_id: str, **payload: Any) -> None:
        if self._fp is None:
            return
        event = {
            "schema": "sme-bench-progress.v1",
            "type": event_type,
            "ts": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "run_id": run_id,
            **payload,
        }
        line = json.dumps(event, ensure_ascii=False)
        async with self._lock:
            try:
                self._fp.write(line + "\n")
                self._fp.flush()
            except OSError as exc:
                if not self._warned:
                    self._warned = True
                    print(f"Warning: progress emit failed: {exc}", file=sys.stderr)

    def close(self) -> None:
        if self._fp is not None and not self._is_stdout:
            self._fp.close()
            self._fp = None
