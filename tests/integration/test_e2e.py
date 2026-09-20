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
    for cmd in ("doctor", "list", "validate", "run", "report", "compare", "saturation"):
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
                "schema_version: '1.0'\nid: [unclosed\n",
                encoding="utf-8",
            ),
        ),
    ],
)
def test_validate_invalid_suite_exits_nonzero(tmp_path: Path, name: str, setup: object) -> None:
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
    assert "SME Readiness Score" in result.output
    assert "SME Core Score" in result.output
    assert "Attempt Pass Rate" in result.output
    assert "Modellvergleich" in result.output

    meta_b = json.loads((run_b / "metadata.json").read_text(encoding="utf-8"))
    meta_b["suite_hash"] = "different-hash"
    (run_b / "metadata.json").write_text(json.dumps(meta_b), encoding="utf-8")
    mismatch = RUNNER.invoke(app, ["compare", str(run_a), str(run_b)])
    assert mismatch.exit_code == 1
    assert "Suite hashes differ" in mismatch.output

    allowed = RUNNER.invoke(app, ["compare", str(run_a), str(run_b), "--allow-suite-mismatch"])
    assert allowed.exit_code == 0, allowed.output


def test_tool_case_against_mock(mock_base_url: str, tmp_path: Path) -> None:
    suite = tmp_path / "tool-suite"
    (suite / "cases" / "de-DE").mkdir(parents=True)
    (suite / "cases" / "en-GB").mkdir(parents=True)
    (suite / "suite.yaml").write_text(
        "schema_version: '1.0'\n"
        "id: tool-suite\n"
        "name: Tool suite\n"
        "version: 0.1.0\n"
        "languages: [de-DE, en-GB]\n"
        "case_globs: ['cases/**/*.yaml']\n",
        encoding="utf-8",
    )
    case = """
schema_version: '1.0'
id: {tid}
pair_id: tool-stock-001
title: Stock lookup
language: {lang}
category: tool_use
task_type: stock_lookup
difficulty: normal
risk: low
review_status: draft
data_classification: synthetic
tags: []
messages:
  - role: system
    content: {sys}
  - role: user
    content: SKU-1 Bestand?
tools:
  - name: get_stock
    description: Lagerbestand
    parameters:
      type: object
      properties:
        sku: {{type: string}}
      required: [sku]
tool_choice: required
generation:
  max_tokens: 128
  temperature: 0
  response_format: tool_call
expected:
  name: get_stock
  arguments:
    sku: SKU-1
scorers:
  - type: tool_call
    weight: 1.0
    params:
      name: get_stock
      arguments_fields: [sku]
      exactly_one: true
  - type: language
    weight: 0
    must_pass: true
pass_threshold: 0.85
partial_threshold: 0.65
""".strip()
    (suite / "cases/de-DE/de-tool-stock-001.yaml").write_text(
        case.format(tid="de-tool-stock-001", lang="de-DE", sys="Antworte auf Deutsch."),
        encoding="utf-8",
    )
    (suite / "cases/en-GB/en-tool-stock-001.yaml").write_text(
        case.format(tid="en-tool-stock-001", lang="en-GB", sys="Respond in English."),
        encoding="utf-8",
    )
    out = tmp_path / "run"
    result = RUNNER.invoke(
        app,
        [
            "run",
            "--base-url",
            mock_base_url,
            "--model",
            "mock-model",
            "--suite",
            str(suite),
            "--repeats",
            "1",
            "--no-warmup",
            "--output",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    rows = [
        json.loads(line)
        for line in (out / "attempts.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rows
    assert all(row["passed"] for row in rows)
    assert all(row["tool_calls"][0]["name"] == "get_stock" for row in rows)


def test_tool_env_loop_two_turns(mock_base_url: str, tmp_path: Path) -> None:
    suite = tmp_path / "tool-loop"
    (suite / "cases/de-DE").mkdir(parents=True)
    (suite / "cases/en-GB").mkdir(parents=True)
    (suite / "suite.yaml").write_text(
        "schema_version: '1.0'\n"
        "id: tool-loop\n"
        "name: Tool loop\n"
        "version: 0.1.0\n"
        "languages: [de-DE, en-GB]\n"
        "case_globs: ['cases/**/*.yaml']\n",
        encoding="utf-8",
    )
    case = """
schema_version: '1.0'
id: {tid}
pair_id: tool-loop-001
title: Live stock loop
language: {lang}
category: tool_use
task_type: stock_lookup
difficulty: normal
risk: low
review_status: draft
data_classification: synthetic
tags: []
messages:
  - role: system
    content: {sys}
  - role: user
    content: SKU-1 Bestand?
tools:
  - name: get_stock
    description: Lagerbestand
    parameters:
      type: object
      properties:
        sku: {{type: string}}
      required: [sku]
tool_choice: auto
tool_env:
  max_turns: 4
  noise: false
  handlers:
    - tool: get_stock
      response: {{qty: 14, sku: SKU-1}}
generation:
  max_tokens: 128
  temperature: 0
  response_format: text
expected:
  tool_calls:
    - name: get_stock
      arguments: {{sku: SKU-1}}
scorers:
  - type: trace_calls
    weight: 0.5
    params:
      calls:
        - name: get_stock
  - type: contains
    weight: 0.5
    params:
      terms: ['14']
      case_insensitive: true
pass_threshold: 0.85
partial_threshold: 0.65
""".strip()
    (suite / "cases/de-DE/de-tool-loop-001.yaml").write_text(
        case.format(tid="de-tool-loop-001", lang="de-DE", sys="Antworte auf Deutsch."),
        encoding="utf-8",
    )
    (suite / "cases/en-GB/en-tool-loop-001.yaml").write_text(
        case.format(tid="en-tool-loop-001", lang="en-GB", sys="Respond in English."),
        encoding="utf-8",
    )
    out = tmp_path / "run-loop"
    result = RUNNER.invoke(
        app,
        [
            "run",
            "--base-url",
            mock_base_url,
            "--model",
            "mock-model",
            "--suite",
            str(suite),
            "--repeats",
            "1",
            "--no-warmup",
            "--output",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    rows = [
        json.loads(line)
        for line in (out / "attempts.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rows
    assert all(row["turns_used"] >= 2 for row in rows)
    assert all(row["tool_trace"] for row in rows)
    assert all(row["passed"] for row in rows)
    meta = json.loads((out / "metadata.json").read_text(encoding="utf-8"))
    assert "capabilities" in (meta.get("runtime") or {})


def test_doctor_cli(mock_base_url: str) -> None:
    result = RUNNER.invoke(
        app,
        ["doctor", "--base-url", mock_base_url, "--model", "mock-model"],
    )
    assert result.exit_code == 0, result.output
