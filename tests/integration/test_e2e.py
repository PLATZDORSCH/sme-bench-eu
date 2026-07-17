"""End-to-end integration tests with mock server in a dedicated thread."""

from __future__ import annotations

import asyncio
import contextlib
import json
import shutil
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

SCORING_FIELDS = ("task_id", "repeat_index", "output_text", "effective_score", "passed")


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
        self.base_url = f"{site.name}/v1"

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


def _run_suite(mock_base_url: str, out: Path, *, seed: int = 1) -> None:
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
            str(seed),
            "--no-warmup",
            "--output",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output


def _scoring_snapshot(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows.append({key: row[key] for key in SCORING_FIELDS})
    return sorted(rows, key=lambda r: (str(r["task_id"]), int(r["repeat_index"])))  # type: ignore[arg-type]


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


def test_list_cmd() -> None:
    result = RUNNER.invoke(app, ["list", "--suite", str(SUITE)])
    assert result.exit_code == 0, result.output
    assert "de-test-inv" in result.output
    assert "en-test-inv" in result.output
    assert "de-DE" in result.output
    assert "en-GB" in result.output
    assert "Pairs: 1" in result.output
    assert "Tasks: 2" in result.output


@pytest.mark.parametrize(
    ("name", "setup"),
    [
        (
            "unknown_scorer",
            lambda suite_dir: (suite_dir / "cases/de-DE/bad.yaml").write_text(
                "schema_version: '1.0'\n"
                "review_status: draft\n"
                "data_classification: synthetic\n"
                "id: de-bad-001\n"
                "title: bad\n"
                "language: de-DE\n"
                "category: document_extraction\n"
                "task_type: invoice_extraction\n"
                "difficulty: normal\n"
                "risk: low\n"
                "tags: []\n"
                "messages:\n"
                "  - role: user\n"
                "    content: hi\n"
                "expected: {}\n"
                "scorers:\n"
                "  - type: not_a_real_scorer\n"
                "    weight: 1.0\n",
                encoding="utf-8",
            ),
        ),
        (
            "fixture_escape",
            lambda suite_dir: (suite_dir / "cases/de-DE/bad.yaml").write_text(
                "schema_version: '1.0'\n"
                "review_status: draft\n"
                "data_classification: synthetic\n"
                "id: de-bad-001\n"
                "title: bad\n"
                "language: de-DE\n"
                "category: document_extraction\n"
                "task_type: invoice_extraction\n"
                "difficulty: normal\n"
                "risk: low\n"
                "tags: []\n"
                "messages:\n"
                "  - role: user\n"
                "    fixture: ../outside.txt\n"
                "expected: {}\n"
                "scorers:\n"
                "  - type: exact_match\n"
                "    weight: 1.0\n"
                "    params:\n"
                "      expected: ok\n",
                encoding="utf-8",
            ),
        ),
        (
            "broken_yaml",
            lambda suite_dir: (suite_dir / "cases/de-DE/bad.yaml").write_text(
                "schema_version: '1.0'\n"
                "id: [unclosed\n",
                encoding="utf-8",
            ),
        ),
    ],
)
def test_validate_invalid_suite_exits_nonzero(
    tmp_path: Path, name: str, setup: object
) -> None:
    suite_dir = tmp_path / f"invalid-{name}"
    shutil.copytree(SUITE, suite_dir)
    setup(suite_dir)  # type: ignore[operator]
    result = RUNNER.invoke(app, ["validate", str(suite_dir)])
    assert result.exit_code == 1, result.output
    assert "ERROR" in result.output


def test_full_run_and_resume(mock_base_url: str, tmp_path: Path) -> None:
    out = tmp_path / "run1"
    _run_suite(mock_base_url, out)
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


def test_same_seed_produces_identical_scoring(mock_base_url: str, tmp_path: Path) -> None:
    run_a = tmp_path / "run-a"
    run_b = tmp_path / "run-b"
    _run_suite(mock_base_url, run_a, seed=42)
    _run_suite(mock_base_url, run_b, seed=42)
    assert _scoring_snapshot(run_a / "attempts.jsonl") == _scoring_snapshot(
        run_b / "attempts.jsonl"
    )


def test_compare_cmd(mock_base_url: str, tmp_path: Path) -> None:
    run_a = tmp_path / "run-a"
    run_b = tmp_path / "run-b"
    _run_suite(mock_base_url, run_a, seed=7)
    _run_suite(mock_base_url, run_b, seed=8)

    result = RUNNER.invoke(app, ["compare", str(run_a), str(run_b)])
    assert result.exit_code == 0, result.output
    assert "SME Core Score" in result.output
    assert "Attempt Pass Rate" in result.output

    meta_b = json.loads((run_b / "metadata.json").read_text(encoding="utf-8"))
    meta_b["suite_hash"] = "different-hash"
    (run_b / "metadata.json").write_text(json.dumps(meta_b), encoding="utf-8")
    mismatch = RUNNER.invoke(app, ["compare", str(run_a), str(run_b)])
    assert mismatch.exit_code == 1
    assert "Suite hashes differ" in mismatch.output

    allowed = RUNNER.invoke(
        app, ["compare", str(run_a), str(run_b), "--allow-suite-mismatch"]
    )
    assert allowed.exit_code == 0, allowed.output


def test_doctor_cli(mock_base_url: str) -> None:
    result = RUNNER.invoke(
        app,
        ["doctor", "--base-url", mock_base_url, "--model", "mock-model"],
    )
    assert result.exit_code == 0, result.output
