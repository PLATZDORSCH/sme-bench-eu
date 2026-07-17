"""Unit tests for reporters and dashboard."""

from __future__ import annotations

import re
from io import StringIO
from pathlib import Path

from rich.console import Console

from sme_bench.dashboard import RunDashboard, use_dashboard
from sme_bench.models import AttemptResult, ScorerSpec
from sme_bench.reporters.catalog import write_case_catalog
from sme_bench.reporters.console import print_summary
from sme_bench.reporters.failures import write_failures_markdown, write_success_markdown
from sme_bench.reporters.markdown import write_summary_markdown
from sme_bench.reporters.task_docs import critical_checks, task_variant
from tests.unit.conftest import make_task


def test_case_catalog_and_failures_report(tmp_path: Path) -> None:
    task = make_task(
        id="de-pii-detection-001",
        title="PII erkennen",
        risk="critical",
        scorers=[
            ScorerSpec(type="set_equality", weight=0.8, critical=True, params={"field": "pii_types"}),
            ScorerSpec(
                type="forbidden_terms",
                weight=0,
                critical=True,
                params={"terms": ["geheim"]},
            ),
        ],
    )
    assert task_variant(task.id) == "001"
    assert critical_checks(task)

    catalog_path = tmp_path / "CASES.md"
    write_case_catalog(catalog_path, [task], suite_id="test", suite_version="0.0")
    text = catalog_path.read_text(encoding="utf-8")
    assert "de-pii-detection-001" in text
    assert "Case catalogue" in text
    assert "K.O." in text

    ok = AttemptResult(
        task_id=task.id,
        language="de-DE",
        category="privacy_security",
        task_type="pii_detection",
        difficulty="normal",
        risk="critical",
        repeat_index=0,
        passed=True,
        effective_score=1.0,
    )
    bad = AttemptResult(
        task_id=task.id,
        language="de-DE",
        category="privacy_security",
        task_type="pii_detection",
        difficulty="normal",
        risk="critical",
        repeat_index=1,
        passed=False,
        partial=False,
        critical_failure=True,
        effective_score=0.0,
        output_text='{"pii_types": ["email"]}',
        score_results=[
            {
                "scorer": "set_equality",
                "score": 0.25,
                "passed": False,
                "critical_failure": True,
                "message": "Set mismatch",
            }
        ],
    )
    failures_path = tmp_path / "failures.de.md"
    write_failures_markdown(
        failures_path,
        [ok, bad],
        model="test-model",
        suite_id="test",
        tasks_by_id={task.id: task},
        lang="de",
    )
    fail_text = failures_path.read_text(encoding="utf-8")
    assert "Kritische Fehler" in fail_text
    assert "set_equality" in fail_text
    assert "**Aufgabe (System):**" in fail_text
    assert "**Erwartetes Ergebnis:**" in fail_text
    assert "**Modellausgabe:**" in fail_text
    assert '{"pii_types": ["email"]}' in fail_text

    failures_en = tmp_path / "failures.en.md"
    write_failures_markdown(
        failures_en,
        [ok, bad],
        model="test-model",
        suite_id="test",
        tasks_by_id={task.id: task},
        lang="en",
    )
    fail_en = failures_en.read_text(encoding="utf-8")
    assert "Critical failures" in fail_en
    assert "**Task (system):**" in fail_en
    assert "**Model output:**" in fail_en

    ok2 = ok.model_copy(update={"repeat_index": 1, "output_text": '{"pii_types":["name"]}'})
    success_path = tmp_path / "success.de.md"
    write_success_markdown(
        success_path,
        [ok, ok2],
        model="test-model",
        suite_id="test",
        tasks_by_id={task.id: task},
        lang="de",
    )
    success_text = success_path.read_text(encoding="utf-8")
    assert "Bestanden" in success_text
    assert "**Aufgabe (User):**" in success_text
    assert "**Erwartetes Ergebnis:**" in success_text
    assert "**Modellausgabe:**" in success_text


def test_print_summary_includes_tps() -> None:
    summary = {
        "sme_core_score": 90.0,
        "overall": {
            "attempt_pass_rate": 0.8,
            "attempt_partial_rate": 0.1,
            "reliable_pass_rate": 0.75,
            "critical_failure_rate": 0.0,
            "infrastructure_error_rate": 0.0,
            "mean_generation_tps": 42.5,
        },
        "by_language": {
            "de-DE": {
                "attempt_pass_rate": 0.8,
                "reliable_pass_rate": 0.75,
                "mean_effective_score": 0.9,
                "critical_failure_rate": 0.0,
                "latency_p95": 1.2,
                "mean_generation_tps": 40.0,
            }
        },
    }
    buffer = StringIO()
    console = Console(file=buffer, width=120, force_terminal=True, highlight=False)
    print_summary(summary, model="test-model", suite_label="Test Suite", console=console)
    text = buffer.getvalue()
    assert "Output tokens/s" in text
    assert "42.5 tok/s" in text
    assert "40.0" in text


def test_write_summary_markdown_includes_tps(tmp_path: Path) -> None:
    summary = {
        "suite_id": "test",
        "suite_version": "0.1",
        "sme_core_score": 90.0,
        "overall": {
            "attempt_pass_rate": 0.8,
            "attempt_partial_rate": 0.1,
            "reliable_pass_rate": 0.75,
            "critical_failure_rate": 0.0,
            "infrastructure_error_rate": 0.0,
            "mean_generation_tps": 55.0,
        },
        "by_language": {
            "en-GB": {
                "attempt_pass_rate": 0.8,
                "reliable_pass_rate": 0.75,
                "mean_effective_score": 0.9,
                "critical_failure_rate": 0.0,
                "latency_p95": 1.0,
                "mean_generation_tps": 55.0,
            }
        },
        "by_category": {},
        "language_parity": {},
    }
    path = tmp_path / "summary.de.md"
    write_summary_markdown(path, summary, model="test-model", lang="de")
    text = path.read_text(encoding="utf-8")
    assert "Output tokens/s (Ø): 55.0 tok/s" in text
    assert "| Tok/s |" in text

    path_en = tmp_path / "summary.en.md"
    write_summary_markdown(path_en, summary, model="test-model", lang="en")
    text_en = path_en.read_text(encoding="utf-8")
    assert "Output tokens/s (avg): 55.0 tok/s" in text_en
    assert "## By language" in text_en


def test_run_dashboard_render() -> None:
    buffer = StringIO()
    console = Console(file=buffer, width=100, force_terminal=True, highlight=False)
    dash = RunDashboard(console, model="m", suite_label="Suite", total=10)
    dash.add_line("[1/10] task-a  [bold green]passed[/bold green]")
    dash.update_counts(
        {"passed": 1, "partial": 0, "failed": 0, "critical": 0, "infra": 0, "done": 1},
        mean_tps=88.0,
    )
    console.print(dash.render())
    # Rich splits adjacent glyphs/numbers into separate styled spans, and whether
    # ANSI codes are emitted depends on terminal/color detection (differs across
    # local vs CI). Strip escape sequences so substring checks are environment-agnostic.
    text = re.sub(r"\x1b\[[0-9;]*m", "", buffer.getvalue())
    assert "✓ 1" in text
    assert "Output tok/s" in text
    assert "88.0" in text
    assert "task-a" in text

    assert use_dashboard(console, None) is True
    assert use_dashboard(console, True) is True
    assert use_dashboard(console, False) is False
    non_tty = Console(file=StringIO(), force_terminal=False)
    assert use_dashboard(non_tty, None) is False
