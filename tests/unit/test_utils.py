"""Unit tests for utility helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from sme_bench.utils import (
    extract_json_payload,
    percentile,
    redact_secrets,
    resolve_safe_path,
    sanitize_base_url_for_metadata,
)


def test_resolve_safe_path(tmp_path: Path) -> None:
    (tmp_path / "fixtures").mkdir()
    f = tmp_path / "fixtures" / "a.txt"
    f.write_text("x", encoding="utf-8")
    assert resolve_safe_path(tmp_path, "fixtures/a.txt") == f.resolve()
    with pytest.raises(ValueError):
        resolve_safe_path(tmp_path, "../outside.txt")


def test_redact_and_sanitize_url() -> None:
    text = "Authorization: Bearer sk-SECRETKEY123 and api_key=abc"
    red = redact_secrets(text)
    assert "sk-SECRETKEY123" not in red
    assert "Bearer sk-SECRETKEY123" not in red
    assert (
        sanitize_base_url_for_metadata("https://user:pass@api.example.com/v1?x=1")
        == "https://api.example.com/v1"
    )


def test_extract_json_variants() -> None:
    assert extract_json_payload('{"a":1}') == {"a": 1}
    assert extract_json_payload('```json\n{"a": 2}\n```') == {"a": 2}
    assert extract_json_payload('prefix {"a": 3} suffix') == {"a": 3}


def test_percentile() -> None:
    assert percentile([1, 2, 3, 4], 50) == pytest.approx(2.5)
    assert percentile([], 50) is None
