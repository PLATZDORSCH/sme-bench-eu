"""Minimal OpenAI-compatible mock server for tests."""

from __future__ import annotations

import asyncio
import json

from aiohttp import web


def _sse(data: str) -> bytes:
    return f"data: {data}\n\n".encode()


async def models_handler(request: web.Request) -> web.Response:
    return web.json_response({"data": [{"id": "mock-model", "object": "model"}]})


async def chat_handler(request: web.Request) -> web.Response:
    body = await request.json()
    messages = body.get("messages") or []
    user = ""
    for msg in messages:
        if msg.get("role") == "user":
            user = msg.get("content") or ""

    # Deterministic canned responses based on prompt cues
    if "pong" in user.lower() or user.strip().lower() == "ping":
        content = "pong"
    elif "RE-2026-1048" in user or "invoice" in user.lower() or "Rechnung" in user:
        content = json.dumps(
            {
                "invoice_number": "RE-2026-1048",
                "supplier": "Nordwerk GmbH",
                "currency": "EUR",
                "net_amount": 1000.0,
                "vat_rate": 0.19,
                "vat_amount": 190.0,
                "gross_amount": 1190.0,
                "due_date": "2026-08-14",
            }
        )
    elif "missing_fields" in (messages[0].get("content") or "") or "delivery_address" in (
        messages[0].get("content") or ""
    ):
        content = json.dumps({"missing_fields": ["delivery_address", "budget"]})
    elif "top_sku" in (messages[0].get("content") or "") or "SKU-100" in user:
        content = json.dumps(
            {"top_sku": "SKU-200", "total_revenue": 570.0, "low_stock": ["SKU-100", "SKU-300"]}
        )
    elif "classify" in (messages[0].get("content") or "").lower() or "category one of" in (
        messages[0].get("content") or ""
    ):
        content = json.dumps({"category": "technical", "priority": "urgent"})
    else:
        # Generic JSON echo for test-suite tasks
        content = json.dumps({"ok": True, "echo": user[:40]})

    response_format = body.get("response_format")
    if (
        isinstance(response_format, dict)
        and response_format.get("type") == "json_object"
        and not content.strip().startswith("{")
    ):
        content = json.dumps({"text": content})

    async def stream() -> web.StreamResponse:
        resp = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
            },
        )
        await resp.prepare(request)
        # Optional empty deltas / reasoning before content
        await resp.write(
            _sse(
                json.dumps(
                    {
                        "id": "chatcmpl-mock",
                        "choices": [{"delta": {"role": "assistant"}, "index": 0}],
                    }
                )
            )
        )
        await resp.write(
            _sse(json.dumps({"choices": [{"delta": {"reasoning_content": "think"}, "index": 0}]}))
        )
        # Split content across chunks to exercise buffering
        mid = max(1, len(content) // 2)
        for part in (content[:mid], content[mid:]):
            if not part:
                continue
            await resp.write(
                _sse(json.dumps({"choices": [{"delta": {"content": part}, "index": 0}]}))
            )
            await asyncio.sleep(0)
        await resp.write(
            _sse(
                json.dumps(
                    {
                        "choices": [{"delta": {}, "finish_reason": "stop", "index": 0}],
                        "usage": {
                            "prompt_tokens": 12,
                            "completion_tokens": max(1, len(content.split())),
                            "total_tokens": 12 + max(1, len(content.split())),
                        },
                    }
                )
            )
        )
        await resp.write(b"data: [DONE]\n\n")
        await resp.write_eof()
        return resp

    # Special status injection via model name suffix for unit tests
    model = str(body.get("model") or "")
    if model.endswith(":429"):
        return web.Response(status=429, text="rate limited")
    if model.endswith(":500"):
        return web.Response(status=500, text="server boom Authorization: Bearer sk-SECRETKEY123")

    return await stream()


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/v1/models", models_handler)
    app.router.add_post("/v1/chat/completions", chat_handler)
    return app


async def start_mock_server(host: str = "127.0.0.1", port: int = 0) -> tuple[web.AppRunner, str]:
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    return runner, f"{site.name}/v1"


if __name__ == "__main__":
    web.run_app(create_app(), host="127.0.0.1", port=8765)
