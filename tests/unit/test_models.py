"""Unit tests for Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sme_bench.models import Message, ScorerSpec
from tests.unit.conftest import make_task


def test_message_requires_content_or_fixture() -> None:
    with pytest.raises(ValidationError):
        Message(role="user")
    with pytest.raises(ValidationError):
        Message(role="user", content="a", fixture="b.txt")
    Message(role="user", content="a")


def test_pass_threshold_and_weights() -> None:
    with pytest.raises(ValidationError):
        make_task(pass_threshold=1.5)
    with pytest.raises(ValidationError):
        make_task(scorers=[ScorerSpec(type="exact_match", weight=0)])
    with pytest.raises(ValidationError):
        make_task(scorers=[ScorerSpec(type="exact_match", weight=-1)])
