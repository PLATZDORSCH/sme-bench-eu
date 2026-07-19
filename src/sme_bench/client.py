"""Async OpenAI-compatible chat completions client with SSE streaming."""

from __future__ import annotations

import asyncio
import json
import os
import random
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import aiohttp

from sme_bench.models import RequestResult
from sme_bench.utils import normalize_base_url, redact_secrets


def _text_from_content_field(value: Any) -> str:
    """Normalize OpenAI ``content`` which may be a string or multimodal parts."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
                elif item.get("type") == "text" and isinstance(item.get("content"), str):
                    parts.append(item["content"])
        return "".join(parts)
    return ""


def _reasoning_from_delta(delta: dict[str, Any]) -> str:
    for key in ("reasoning_content", "reasoning"):
        value = delta.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def uses_max_completion_tokens(model: str) -> bool:
    """Return True for OpenAI models that reject ``max_tokens``.

    Newer chat models (GPT-5, GPT-4.1, GPT-4o, o-series) require
    ``max_completion_tokens`` instead. Local OpenAI-compatible servers
    (Ollama, vLLM, …) keep using ``max_tokens``.
    """
    name = model.strip().lower().rsplit("/", maxsplit=1)[-1]
    return name.startswith(("o1", "o3", "o4", "gpt-5", "gpt-4.1", "gpt-4o", "chatgpt-4o"))


def omits_temperature(model: str) -> bool:
    """Return True when the API rejects non-default ``temperature``.

    GPT-5 and o-series only allow the default (typically 1). Sending
    ``temperature: 0`` causes ``invalid_request_error``. Other models
    keep receiving the suite value (usually 0) for reproducibility.
    """
    name = model.strip().lower().rsplit("/", maxsplit=1)[-1]
    return name.startswith(("o1", "o3", "o4", "gpt-5"))


class OpenAICompatibleClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key_env: str = "OPENAI_API_KEY",
        timeout: float = 120.0,
        retries: int = 1,
    ) -> None:
        self.base_url = normalize_base_url(base_url)
        self.api_key_env = api_key_env
        self.timeout = timeout
        self.retries = retries
        self._session: aiohttp.ClientSession | None = None

    def _api_key(self) -> str:
        """Return the API key from ``api_key_env`` only (no silent fallbacks)."""
        value = os.environ.get(self.api_key_env)
        if value:
            return value
        return "EMPTY"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": "application/json",
        }

    async def __aenter__(self) -> OpenAICompatibleClient:
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self._session = aiohttp.ClientSession(timeout=timeout, headers=self._headers())
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None:
            raise RuntimeError("Client session not started; use async with")
        return self._session

    async def list_models(self) -> dict[str, Any]:
        url = f"{self.base_url}/models"
        async with self.session.get(url) as resp:
            text = await resp.text()
            if resp.status >= 400:
                raise RuntimeError(f"models endpoint HTTP {resp.status}: {redact_secrets(text)}")
            data = json.loads(text)
            if not isinstance(data, dict):
                raise RuntimeError("models endpoint returned non-object JSON")
            return data

    async def chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.0,
        seed: int | None = None,
        response_format: str | None = None,
        extra_body: dict[str, Any] | None = None,
        on_first_response: Any | None = None,
        on_first_token: Any | None = None,
    ) -> RequestResult:
        limit_key = (
            "max_completion_tokens" if uses_max_completion_tokens(model) else "max_tokens"
        )
        skip_temperature = omits_temperature(model)
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            limit_key: max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if not skip_temperature:
            payload["temperature"] = temperature
        if seed is not None:
            payload["seed"] = seed
        if response_format == "json":
            payload["response_format"] = {"type": "json_object"}
        if extra_body:
            for key, value in extra_body.items():
                if key in {"model", "messages", "stream"}:
                    continue
                # Remap token-limit aliases so callers never send both fields.
                if key in {"max_tokens", "max_completion_tokens"}:
                    payload[limit_key] = value
                    continue
                if key == "temperature" and skip_temperature:
                    continue
                payload[key] = value
        payload.pop("max_tokens" if limit_key == "max_completion_tokens" else "max_completion_tokens", None)
        if skip_temperature:
            payload.pop("temperature", None)

        attempt = 0
        last_result: RequestResult | None = None
        while attempt <= self.retries:
            attempt += 1
            result = await self._stream_once(
                payload=payload,
                attempt=attempt,
                on_first_response=on_first_response,
                on_first_token=on_first_token,
            )
            last_result = result
            if result.error_type is None:
                return result
            retryable = result.http_status in {429, 502, 503, 504} or result.error_type in {
                "transport_error",
                "timeout",
            }
            if not retryable or attempt > self.retries:
                return result
            backoff = (2 ** (attempt - 1)) * 0.25 + random.uniform(0, 0.1)
            await asyncio.sleep(backoff)
        assert last_result is not None
        return last_result

    async def _stream_once(
        self,
        *,
        payload: dict[str, Any],
        attempt: int,
        on_first_response: Any | None,
        on_first_token: Any | None,
    ) -> RequestResult:
        request_id = str(uuid.uuid4())
        started_at = datetime.now(UTC)
        start_mono = time.monotonic()
        result = RequestResult(
            request_id=request_id,
            started_at=started_at,
            start_monotonic=start_mono,
            attempts=attempt,
        )
        url = f"{self.base_url}/chat/completions"
        buffer = ""
        content_parts: list[str] = []
        reasoning_parts: list[str] = []

        try:
            async with self.session.post(url, json=payload) as resp:
                result.http_status = resp.status
                if result.first_response_monotonic is None:
                    result.first_response_monotonic = time.monotonic()
                    if on_first_response:
                        await _maybe_await(on_first_response)
                if resp.status >= 400:
                    body = await resp.text()
                    result.end_monotonic = time.monotonic()
                    result.completed_at = datetime.now(UTC)
                    result.error_type = "http_error"
                    result.error_message = redact_secrets(body)[:2000]
                    return result

                async for raw in resp.content.iter_any():
                    buffer += raw.decode("utf-8", errors="replace")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip("\r")
                        if not line:
                            continue
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].lstrip()
                        if data == "[DONE]":
                            buffer = ""
                            break
                        try:
                            event = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        self._consume_event(
                            event,
                            result=result,
                            content_parts=content_parts,
                            reasoning_parts=reasoning_parts,
                            on_first_token=on_first_token,
                        )
                # Flush remaining buffer lines
                if buffer.strip():
                    for line in buffer.split("\n"):
                        line = line.strip("\r")
                        if line.startswith("data:"):
                            data = line[5:].lstrip()
                            if data != "[DONE]":
                                try:
                                    event = json.loads(data)
                                    self._consume_event(
                                        event,
                                        result=result,
                                        content_parts=content_parts,
                                        reasoning_parts=reasoning_parts,
                                        on_first_token=on_first_token,
                                    )
                                except json.JSONDecodeError:
                                    pass
        except TimeoutError:
            result.error_type = "timeout"
            result.error_message = "Request timed out"
        except aiohttp.ClientError as exc:
            result.error_type = "transport_error"
            result.error_message = redact_secrets(str(exc))
        except Exception as exc:  # noqa: BLE001 - capture unexpected transport issues
            result.error_type = "transport_error"
            result.error_message = redact_secrets(str(exc))

        content_text = "".join(content_parts)
        reasoning_text = "".join(reasoning_parts)
        # Some GLM/Nebius deployments put the visible answer only in
        # reasoning_* while delta.content stays empty/null.
        if content_text:
            result.output_text = content_text
        elif reasoning_text:
            result.output_text = reasoning_text
        else:
            result.output_text = ""
        if reasoning_text:
            result.reasoning_text = reasoning_text
        result.end_monotonic = time.monotonic()
        result.completed_at = datetime.now(UTC)
        return result

    def _note_token(
        self,
        *,
        result: RequestResult,
        on_first_token: Any | None,
        content_parts: list[str],
    ) -> None:
        if result.first_token_monotonic is None:
            result.first_token_monotonic = time.monotonic()
            result.token_timestamps.append(result.first_token_monotonic)
        else:
            result.token_timestamps.append(time.monotonic())
        if on_first_token and len(content_parts) == 1:
            result.__dict__["_first_token_cb"] = on_first_token

    def _consume_event(
        self,
        event: dict[str, Any],
        *,
        result: RequestResult,
        content_parts: list[str],
        reasoning_parts: list[str],
        on_first_token: Any | None,
    ) -> None:
        if "usage" in event and event["usage"]:
            usage = event["usage"]
            result.prompt_tokens = usage.get("prompt_tokens", result.prompt_tokens)
            result.completion_tokens = usage.get("completion_tokens", result.completion_tokens)

        choices = event.get("choices") or []
        if not choices:
            return
        choice = choices[0]
        if choice.get("finish_reason"):
            result.finish_reason = choice["finish_reason"]

        delta = choice.get("delta") or {}
        message = choice.get("message") or {}

        reasoning = _reasoning_from_delta(delta) or _reasoning_from_delta(message)
        if reasoning:
            reasoning_parts.append(reasoning)
            # Count reasoning tokens for TTFT when content is empty (GLM).
            if not content_parts and result.first_token_monotonic is None:
                result.first_token_monotonic = time.monotonic()
                result.token_timestamps.append(result.first_token_monotonic)

        for source in (delta, message):
            chunk = _text_from_content_field(source.get("content"))
            if not chunk:
                continue
            content_parts.append(chunk)
            self._note_token(
                result=result, on_first_token=on_first_token, content_parts=content_parts
            )


async def _maybe_await(cb: Any) -> None:
    result = cb()
    if asyncio.iscoroutine(result):
        await result


async def run_doctor(
    *,
    base_url: str,
    model: str,
    api_key_env: str = "OPENAI_API_KEY",
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Probe endpoint health without creating benchmark artifacts."""
    report: dict[str, Any] = {
        "base_url": normalize_base_url(base_url),
        "model": model,
        "reachable": False,
        "models_ok": False,
        "chat_ok": False,
        "streaming_ok": False,
        "first_token_ok": False,
        "usage_available": False,
        "latency_s": None,
        "error": None,
    }
    try:
        async with OpenAICompatibleClient(
            base_url=base_url, api_key_env=api_key_env, timeout=timeout, retries=0
        ) as client:
            report["reachable"] = True
            try:
                await client.list_models()
                report["models_ok"] = True
            except Exception as exc:  # noqa: BLE001
                report["models_error"] = redact_secrets(str(exc))

            result = await client.chat_completion(
                model=model,
                messages=[{"role": "user", "content": "Reply with the single word: pong"}],
                max_tokens=64,
                temperature=0,
            )
            report["latency_s"] = result.total_latency
            if result.error_type:
                report["error"] = result.error_message
            else:
                report["streaming_ok"] = True
                report["usage_available"] = result.prompt_tokens is not None
                report["sample_output"] = (result.output_text or "")[:80]
                report["first_token_ok"] = result.first_token_monotonic is not None
                # Require visible model text — empty streams are not healthy.
                if (result.output_text or "").strip():
                    report["chat_ok"] = True
                else:
                    report["error"] = (
                        "Stream completed without visible content "
                        "(empty delta.content / reasoning fallback)"
                    )
    except Exception as exc:  # noqa: BLE001
        report["error"] = redact_secrets(str(exc))
    return report
