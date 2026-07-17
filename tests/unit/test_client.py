"""Client tests against local mock SSE server."""

from __future__ import annotations

import pytest

from sme_bench.client import OpenAICompatibleClient, run_doctor
from tests.fixtures.mock_server import start_mock_server


@pytest.fixture
async def mock_base_url():
    runner, base_url = await start_mock_server()
    try:
        yield base_url
    finally:
        await runner.cleanup()


@pytest.mark.asyncio
async def test_streaming_and_usage(mock_base_url: str) -> None:
    async with OpenAICompatibleClient(base_url=mock_base_url, retries=0) as client:
        result = await client.chat_completion(
            model="mock-model",
            messages=[{"role": "user", "content": "Reply with the single word: pong"}],
            max_tokens=16,
        )
    assert result.error_type is None
    assert "pong" in result.output_text.lower()
    assert result.first_response_monotonic is not None
    assert result.first_token_monotonic is not None
    assert result.ttfr is not None and result.ttft is not None
    assert result.prompt_tokens == 12
    assert result.reasoning_text == "think"


@pytest.mark.asyncio
async def test_http_429_retry(mock_base_url: str) -> None:
    async with OpenAICompatibleClient(base_url=mock_base_url, retries=1) as client:
        result = await client.chat_completion(
            model="mock-model:429",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=8,
        )
    assert result.http_status == 429
    assert result.attempts == 2
    assert result.error_type == "http_error"


@pytest.mark.asyncio
async def test_http_500_redacts_secrets(mock_base_url: str) -> None:
    async with OpenAICompatibleClient(base_url=mock_base_url, retries=0) as client:
        result = await client.chat_completion(
            model="mock-model:500",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=8,
        )
    assert result.http_status == 500
    assert result.error_message is not None
    assert "sk-SECRETKEY123" not in result.error_message


@pytest.mark.asyncio
async def test_doctor(mock_base_url: str) -> None:
    report = await run_doctor(base_url=mock_base_url, model="mock-model")
    assert report["chat_ok"] is True
    assert report["streaming_ok"] is True
    assert report["first_token_ok"] is True
