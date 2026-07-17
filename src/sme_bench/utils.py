"""Utility helpers for paths, hashing, redaction, and JSON extraction."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

_SECRET_PATTERNS = [
    re.compile(r"(?i)(authorization\s*[:=]\s*['\"]?)bearer\s+[^\s'\"]+", re.IGNORECASE),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*['\"]?)[^\s'\"]+", re.IGNORECASE),
    re.compile(r"(?i)(x-api-key\s*[:=]\s*['\"]?)[^\s'\"]+", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_-]{10,}"),
]


def normalize_base_url(base_url: str) -> str:
    """Normalize an OpenAI-compatible base URL (no trailing slash)."""
    url = base_url.strip().rstrip("/")
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid base URL: {base_url}")
    return url


def sanitize_base_url_for_metadata(base_url: str) -> str:
    """Strip userinfo and query parameters before persisting."""
    parsed = urlparse(normalize_base_url(base_url))
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return urlunparse((parsed.scheme, netloc, parsed.path.rstrip("/"), "", "", ""))


def redact_secrets(text: str) -> str:
    """Redact likely API keys and authorization headers from text."""
    redacted = text
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(
            lambda m: (m.group(1) if m.lastindex else "") + "[REDACTED]", redacted
        )
    return redacted


def resolve_safe_path(base_dir: Path, relative: str) -> Path:
    """Resolve a relative path under base_dir, rejecting directory traversal."""
    base = base_dir.resolve()
    candidate = (base / relative).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise ValueError(f"Path escapes suite directory: {relative}") from exc
    return candidate


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_suite_hash(suite_dir: Path, task_ids: list[str]) -> str:
    """Deterministic hash over suite.yaml and sorted task file contents."""
    digest = hashlib.sha256()
    suite_yaml = suite_dir / "suite.yaml"
    digest.update(suite_yaml.read_bytes())
    for task_id in sorted(task_ids):
        digest.update(task_id.encode("utf-8"))
    # Include case file hashes in sorted path order for stability
    case_files = (
        sorted((suite_dir / "cases").rglob("*.yaml")) if (suite_dir / "cases").exists() else []
    )
    for path in case_files:
        digest.update(path.relative_to(suite_dir).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def extract_json_payload(text: str) -> Any:
    """Extract pure JSON or a single Markdown fenced JSON code block."""
    stripped = text.strip()
    if not stripped:
        raise ValueError("Empty output; expected JSON")

    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped, re.IGNORECASE)
    if fence:
        candidate = fence.group(1).strip()
        return json.loads(candidate)

    # Try whole string, then first {...} or [...]
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    for opener, closer in (("{", "}"), ("[", "]")):
        start = stripped.find(opener)
        end = stripped.rfind(closer)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(stripped[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("Could not extract valid JSON from model output")


def get_by_path(data: Any, path: str) -> Any:
    """Resolve dotted path into nested dicts/lists."""
    current = data
    for part in path.split("."):
        if isinstance(current, dict):
            if part not in current:
                raise KeyError(path)
            current = current[part]
        elif isinstance(current, list):
            index = int(part)
            current = current[index]
        else:
            raise KeyError(path)
    return current


def percentile(values: list[float], p: float) -> float | None:
    """Nearest-rank percentile for p in [0, 100]."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (p / 100.0) * (len(ordered) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def suite_path_for_metadata(suite_dir: Path) -> str:
    """Store suite path relative to cwd when possible."""
    resolved = suite_dir.resolve()
    try:
        return str(resolved.relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(resolved)


def resolve_suite_path(meta: dict[str, Any]) -> Path | None:
    """Resolve suite directory from run metadata."""
    raw = meta.get("suite_path")
    if raw:
        path = Path(str(raw))
        if path.is_dir():
            return path
    suite_id = meta.get("suite_id")
    if suite_id and suite_id != "sme-full":
        candidate = Path("suites") / str(suite_id)
        if candidate.is_dir():
            return candidate
    return None
