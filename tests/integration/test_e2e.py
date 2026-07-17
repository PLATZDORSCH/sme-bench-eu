"""End-to-end integration tests with mock server in a dedicated thread."""

from __future__ import annotations

import asyncio
import contextlib
import json
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from aiohttp import web
from typer.testing import CliRunner

from sme_bench.cli import app
from tests.fixtures.mock_server import create_app

RUNNER = CliRunner()
SUITE = Path("tests/fixtures/test-suite")
CORE = Path("suites/sme-core-v0.1")


class _ThreadedServer:
    def __init__(self) -> None:
        self.base_url = ""
        self._loop: asyncio.AbstractEventLoop | None = None
        self._runner: web.AppRunner | None = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> str:
        self._thread.start()
        assert self._ready.wait(timeout=10), "mock server failed to start"
        return self.base_url

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._start())
        self._ready.set()
        self._loop.run_forever()

    async def _start(self) -> None:
        self._runner = web.AppRunner(create_app())
        await self._runner.setup()
        site = web.TCPSite(self._runner, "127.0.0.1", 0)
        await site.start()
        sockets = site._server.sockets  # type: ignore[union-attr]
        assert sockets
        port = sockets[0].getsockname()[1]
        self.base_url = f"http://127.0.0.1:{port}/v1"

    def stop(self) -> None:
        if self._loop is None:
            return

        async def _cleanup() -> None:
            if self._runner is not None:
                await self._runner.cleanup()

        fut = asyncio.run_coroutine_threadsafe(_cleanup(), self._loop)
        with contextlib.suppress(Exception):
            fut.result(timeout=5)
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._thread.join(timeout=5)


@pytest.fixture
def mock_base_url() -> Iterator[str]:
    server = _ThreadedServer()
    url = server.start()
    try:
        yield url
    finally:
        server.stop()


def test_validate_core_suite() -> None:
    result = RUNNER.invoke(app, ["validate", str(CORE)])
    assert result.exit_code == 0, result.output


def test_validate_test_suite() -> None:
    result = RUNNER.invoke(app, ["validate", str(SUITE)])
    assert result.exit_code == 0, result.output


def test_help_lists_commands() -> None:
    result = RUNNER.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("doctor", "list", "validate", "run", "report", "compare"):
        assert cmd in result.output


def test_full_run_and_resume(mock_base_url: str, tmp_path: Path) -> None:
    out = tmp_path / "run1"
    result = RUNNER.invoke(
        app,
        [
            "run",
            "--base-url",
            mock_base_url,
            "--model",
            "mock-model",
            "--suite",
            str(SUITE),
            "--repeats",
            "2",
            "--concurrency",
            "1",
            "--seed",
            "1",
            "--no-warmup",
            "--output",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (out / "metadata.json").exists()
    assert (out / "attempts.jsonl").exists()
    assert (out / "summary.json").exists()
    assert (out / "summary.de.md").exists()
    assert (out / "summary.en.md").exists()
    assert (out / "failures.de.md").exists()
    assert (out / "failures.en.md").exists()
    assert (out / "success.de.md").exists()
    assert (out / "success.en.md").exists()
    assert (out / "attempts.csv").exists()

    lines = [ln for ln in (out / "attempts.jsonl").read_text(encoding="utf-8").splitlines() if ln]
    assert len(lines) == 4
    meta = json.loads((out / "metadata.json").read_text(encoding="utf-8"))
    assert meta["status"] == "completed"
    assert "Authorization" not in (out / "attempts.jsonl").read_text(encoding="utf-8")

    result2 = RUNNER.invoke(
        app,
        [
            "run",
            "--base-url",
            mock_base_url,
            "--model",
            "mock-model",
            "--suite",
            str(SUITE),
            "--repeats",
            "2",
            "--no-warmup",
            "--resume",
            str(out),
        ],
    )
    assert result2.exit_code == 0, result2.output
    lines2 = [ln for ln in (out / "attempts.jsonl").read_text(encoding="utf-8").splitlines() if ln]
    assert len(lines2) == 4

    report = RUNNER.invoke(app, ["report", str(out), "--format", "all"])
    assert report.exit_code == 0


def test_doctor_cli(mock_base_url: str) -> None:
    result = RUNNER.invoke(
        app,
        ["doctor", "--base-url", mock_base_url, "--model", "mock-model"],
    )
    assert result.exit_code == 0, result.output
