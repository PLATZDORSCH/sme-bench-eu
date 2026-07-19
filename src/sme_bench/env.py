"""Load local ``.env`` into process environment (optional dependency)."""

from __future__ import annotations

import os
from pathlib import Path


def load_env_files() -> None:
    """Load ``.env`` from cwd then repo root.

    Non-empty existing environment variables win. Empty placeholders
    (e.g. ``OPENAI_API_KEY=`` already exported) are filled from ``.env``.
    """
    try:
        from dotenv import dotenv_values
    except ImportError:
        return

    cwd = Path.cwd()
    candidates = [cwd / ".env", Path(__file__).resolve().parents[2] / ".env"]
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen or not path.is_file():
            continue
        seen.add(resolved)
        for key, value in dotenv_values(path).items():
            if not key or value is None:
                continue
            if not os.environ.get(key):
                os.environ[key] = value
