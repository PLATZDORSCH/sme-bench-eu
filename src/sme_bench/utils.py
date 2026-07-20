"""Utility helpers for paths, hashing, redaction, and JSON extraction."""

from __future__ import annotations

import hashlib
import json
import re
from json import JSONDecoder
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

_SECRET_PATTERNS = [
    re.compile(r"(?i)(authorization\s*[:=]\s*['\"]?)bearer\s+[^\s'\"]+", re.IGNORECASE),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*['\"]?)[^\s'\"]+", re.IGNORECASE),
    re.compile(r"(?i)(x-api-key\s*[:=]\s*['\"]?)[^\s'\"]+", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_-]{10,}"),
]

# Qwen / vLLM thinking delimiters leaked into ``content``.
# Qwen3.5+: ``<think>`` is often already in the prompt; generation emits
# ``…reasoning…</think>\n\nanswer``. Older templates emit a full pair.
_THINK_TAG_RE = re.compile(
    r"<think>([\s\S]*?)</think\s*>",
    re.IGNORECASE,
)
_THINK_CLOSE_RE = re.compile(r"</think\s*>", re.IGNORECASE)
# Some chat templates use redacted_* synonyms.
_REDACTED_THINK_TAG_RE = re.compile(
    r"<redacted_thinking>([\s\S]*?)</redacted_thinking\s*>",
    re.IGNORECASE,
)
_REDACTED_THINK_CLOSE_RE = re.compile(r"</redacted_thinking\s*>", re.IGNORECASE)
# Plain-text CoT dumps (some proxies put thinking in content, not reasoning_*).
_THINKING_PREFIX_RE = re.compile(
    r"(?is)^\s*(?:"
    r"here'?s\s+a\s+thinking\s+process\s*:"
    r"|thinking\s+process\s*:"
    r"|let\s+me\s+think\s+(?:step\s+by\s+step\s+)?:?"
    r")"
)


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


def _iter_json_spans(text: str) -> list[tuple[int, int, Any]]:
    """Return ``(start, end, value)`` for every successful ``raw_decode`` from ``{``/``[``."""
    decoder = JSONDecoder()
    spans: list[tuple[int, int, Any]] = []
    for index, char in enumerate(text):
        if char not in "{[":
            continue
        try:
            value, end = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            continue
        spans.append((index, end, value))
    return spans


def _last_top_level_json(text: str) -> Any | None:
    """Best top-level JSON value in *text* (prefer complete answers over fragments).

    Nested objects found by scanning every ``{`` are discarded when their span is
    strictly contained in another successful parse. Among remaining top-level
    dicts we rank by serialized size first (complete answers beat short CoT
    drafts / prompt anti-examples like ``{"type":"name","value":"..."}``), then
    by later position. Key count is intentionally not used — a 2-key anti-example
    must not beat a 1-key final answer. If there is no dict, the last top-level
    value is used.
    """
    spans = _iter_json_spans(text)
    if not spans:
        return None
    top_level = [
        (start, end, value)
        for start, end, value in spans
        if not any(s < start and end < e for s, e, _ in spans)
    ]
    if not top_level:
        return None
    objects = [item for item in top_level if isinstance(item[2], dict)]
    if objects:

        def _rank(item: tuple[int, int, Any]) -> tuple[int, int]:
            start, _end, value = item
            assert isinstance(value, dict)
            return (
                len(json.dumps(value, ensure_ascii=False)),
                start,
            )

        return max(objects, key=_rank)[2]
    return top_level[-1][2]


def extract_json_payload(text: str) -> Any:
    """Extract JSON from model output (raw, fenced, or embedded in prose/CoT)."""
    stripped = text.strip()
    if not stripped:
        raise ValueError("Empty output; expected JSON")

    # Prefer ```json fences, then other fences; fall through on parse errors so a
    # quoted source fence in chain-of-thought does not block a later JSON fence.
    fence_matches = list(
        re.finditer(r"```(?:json)?\s*([\s\S]*?)\s*```", stripped, re.IGNORECASE)
    )
    fence_matches.sort(
        key=lambda m: (0 if m.group(0).lstrip("`").lower().startswith("json") else 1, m.start())
    )
    for match in fence_matches:
        candidate = match.group(1).strip()
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    embedded = _last_top_level_json(stripped)
    if embedded is not None:
        return embedded

    raise ValueError("Could not extract valid JSON from model output")


def is_thinking_dump(text: str) -> bool:
    """True when *text* looks like a leaked chain-of-thought dump."""
    if not text or not text.strip():
        return False
    if _THINKING_PREFIX_RE.match(text):
        return True
    lower = text.lower()
    return (
        "<think>" in lower
        or "</think>" in lower
        or "<redacted_thinking>" in lower
        or "</redacted_thinking>" in lower
    )


def _strip_paired_think_blocks(text: str) -> tuple[str, list[str]]:
    """Remove paired think/redacted blocks; return ``(remainder, reasoning_chunks)``."""
    reasoning_parts: list[str] = []
    remainder = text
    for pattern in (_THINK_TAG_RE, _REDACTED_THINK_TAG_RE):
        while True:
            match = pattern.search(remainder)
            if not match:
                break
            chunk = match.group(1).strip()
            if chunk:
                reasoning_parts.append(chunk)
            remainder = (remainder[: match.start()] + remainder[match.end() :]).strip()
    return remainder, reasoning_parts


def _split_on_think_close(text: str) -> tuple[str, str] | None:
    """Qwen3.5+ prefix format: reasoning before first close tag, answer after."""
    for close_re in (_THINK_CLOSE_RE, _REDACTED_THINK_CLOSE_RE):
        match = close_re.search(text)
        if match:
            return text[: match.start()].strip(), text[match.end() :].strip()
    return None


def separate_thinking_content(text: str) -> tuple[str, str | None]:
    """Split leaked chain-of-thought from the scorable answer.

    Returns ``(answer, reasoning)``. ``reasoning`` is ``None`` when no thinking
    markers are present. Prefer delimiter split (like vLLM ``qwen3`` parser /
    Platzdorsch gateway ``reasoning_content``): the answer is whatever remains
    *after* the thinking block — never a mid-CoT JSON fragment.

    Handles:

    - Paired ``<think>...</think>`` / ``<redacted_thinking>...</redacted_thinking>``
    - Qwen3.5+ close-only generation (``…</think>\\n\\nanswer``)
    - Plain-text dumps starting with ``Here's a thinking process:`` (last-resort
      JSON recovery via :func:`extract_json_payload` size ranking, not key count)
    """
    if not text:
        return "", None

    remainder, reasoning_parts = _strip_paired_think_blocks(text)
    close_split = _split_on_think_close(remainder)
    if close_split is not None:
        before, after = close_split
        if before:
            reasoning_parts.append(before)
        remainder = after

    if reasoning_parts:
        reasoning = "\n\n".join(reasoning_parts)
        answer = remainder.strip()
        # Do not fish JSON out of the thinking block when no post-delimiter answer
        # was emitted — that is what caused anti-example false failures.
        return answer, reasoning

    if _THINKING_PREFIX_RE.match(text):
        # Prose CoT without Qwen delimiters (proxy leak). Recover best final JSON.
        try:
            recovered = extract_json_payload(text)
        except ValueError:
            return text, text
        return json.dumps(recovered, ensure_ascii=False), text

    return text, None


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
