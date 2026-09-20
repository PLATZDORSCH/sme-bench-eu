"""Unit tests for Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sme_bench.models import Message, ScorerSpec, ToolCall
from tests.unit.conftest import make_task


def test_message_requires_content_or_fixture() -> None:
    with pytest.raises(ValidationError):
        Message(role="user")
    with pytest.raises(ValidationError):
        Message(role="user", content="a", fixture="b.txt")
    Message(role="user", content="a")
    Message(role="assistant", tool_calls=[ToolCall(name="lookup", arguments={"sku": "A"})])
    Message(role="tool", content="ok", tool_call_id="call_1")


def test_unknown_category_rejected() -> None:
    with pytest.raises(ValidationError):
        make_task(category="not-a-real-category")


def test_last_message_must_be_user_or_tool() -> None:
    with pytest.raises(ValidationError):
        make_task(messages=[Message(role="system", content="sys")])


def test_pass_threshold_and_weights() -> None:
    with pytest.raises(ValidationError):
        make_task(pass_threshold=1.5)
    with pytest.raises(ValidationError):
        make_task(scorers=[ScorerSpec(type="exact_match", weight=0)])
    with pytest.raises(ValidationError):
        make_task(scorers=[ScorerSpec(type="exact_match", weight=-1)])
