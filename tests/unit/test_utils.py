"""Unit tests for utility helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from sme_bench.utils import (
    extract_json_payload,
    is_thinking_dump,
    percentile,
    redact_secrets,
    resolve_safe_path,
    sanitize_base_url_for_metadata,
    separate_thinking_content,
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


def test_extract_json_skips_non_json_fence_in_thinking() -> None:
    """Quoted source fences in CoT must not block a later JSON fence/object."""
    text = """Here's a thinking process:

Source:
```
Hinweis: Nicht als „bereits bezahlt“ markieren.
```

Construct:
```json
{"invoice_number": "FR-1", "net_amount": 10}
```

Final: {"invoice_number": "FR-1", "net_amount": 10}
"""
    assert extract_json_payload(text) == {"invoice_number": "FR-1", "net_amount": 10}


def test_extract_json_prefers_complete_object_over_late_draft() -> None:
    text = (
        'final {"pii_types": ["name", "phone", "email", "iban"]}\n'
        'oops draft {"pii_types": ["name", "email"]}'
    )
    assert extract_json_payload(text) == {"pii_types": ["name", "phone", "email", "iban"]}


def test_extract_json_prefers_last_top_level_object() -> None:
    text = (
        'draft {"pii_types": ["name"]}\n'
        'then list ["name", "email"]\n'
        'final {"pii_types": ["name", "email", "phone"]}'
    )
    assert extract_json_payload(text) == {"pii_types": ["name", "email", "phone"]}


def test_extract_json_nested_order_object_not_item_fragment() -> None:
    text = (
        'thinking {"sku": "A", "qty": 1}\n'
        '{"customer": "Acme", "items": [{"sku": "PAL-100", "qty": 12}, '
        '{"sku": "BOX-22", "qty": 4}]}'
    )
    data = extract_json_payload(text)
    assert data["customer"] == "Acme"
    assert len(data["items"]) == 2


def test_extract_json_prefers_answer_over_prompt_anti_example() -> None:
    """2-key CoT anti-examples must not beat a 1-key final answer (PII cases)."""
    text = (
        "Here's a thinking process:\n"
        'Wrong format is {"type": "name", "value": "..."}.\n'
        'Final: {"pii_types": ["name", "email", "phone", "iban"]}\n'
    )
    assert extract_json_payload(text) == {
        "pii_types": ["name", "email", "phone", "iban"]
    }


def test_separate_thinking_tags() -> None:
    open_t, close_t = "<" + "think" + ">", "</" + "think" + ">"
    text = f'{open_t}step 1{close_t}\n{{"category": "billing"}}'
    answer, reasoning = separate_thinking_content(text)
    assert answer == '{"category": "billing"}'
    assert reasoning == "step 1"


def test_separate_thinking_qwen35_close_only_prefix() -> None:
    """Qwen3.5+: open tag in prompt; generation is reasoning + close + answer."""
    close_t = "</" + "think" + ">"
    text = f'step-by-step here\n{close_t}\n\n{{"category": "billing"}}'
    answer, reasoning = separate_thinking_content(text)
    assert answer == '{"category": "billing"}'
    assert reasoning == "step-by-step here"


def test_separate_thinking_does_not_fish_json_from_think_block() -> None:
    """When nothing follows the delimiter, do not pull mid-CoT JSON as the answer."""
    open_t, close_t = "<" + "think" + ">", "</" + "think" + ">"
    text = f'{open_t}draft {{"type": "name", "value": "..."}} and done{close_t}\n'
    answer, reasoning = separate_thinking_content(text)
    assert answer == ""
    assert reasoning is not None
    assert "type" in reasoning


def test_separate_thinking_plain_prefix_recovers_json() -> None:
    text = (
        "Here's a thinking process:\n\n"
        "1. Analyze\n"
        'Wrong: {"type": "name", "value": "..."}\n'
        'Output: `{"category": "technical", "priority": "urgent"}`\n'
        "Done."
    )
    answer, reasoning = separate_thinking_content(text)
    assert reasoning is not None and reasoning.startswith("Here's a thinking")
    assert extract_json_payload(answer) == {"category": "technical", "priority": "urgent"}


def test_separate_thinking_noop_on_clean_json() -> None:
    text = '{"a": 1}'
    answer, reasoning = separate_thinking_content(text)
    assert answer == text
    assert reasoning is None


def test_is_thinking_dump() -> None:
    assert is_thinking_dump("Here's a thinking process:\n1. …")
    close_t = "</" + "think" + ">"
    assert is_thinking_dump(f"foo {close_t} bar")
    assert not is_thinking_dump('{"a": 1}')


def test_percentile() -> None:
    assert percentile([1, 2, 3, 4], 50) == pytest.approx(2.5)
    assert percentile([], 50) is None
