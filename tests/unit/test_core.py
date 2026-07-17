"""Unit tests for models, utils, scorers, statistics."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from sme_bench.config import PricingConfig
from sme_bench.models import (
    AttemptResult,
    BenchmarkTask,
    GenerationConfig,
    Message,
    RequestResult,
    ScorerSpec,
)
from sme_bench.pricing import estimate_cost
from sme_bench.scoring import evaluate_attempt
from sme_bench.statistics import aggregate, language_parity
from sme_bench.utils import (
    extract_json_payload,
    percentile,
    redact_secrets,
    resolve_safe_path,
    sanitize_base_url_for_metadata,
)


def _task(**overrides: object) -> BenchmarkTask:
    base = dict(
        schema_version="1.0",
        id="t1",
        title="t",
        language="de-DE",
        category="document_extraction",
        task_type="invoice_extraction",
        difficulty="normal",
        risk="low",
        review_status="draft",
        data_classification="synthetic",
        tags=[],
        messages=[Message(role="user", content="hi")],
        generation=GenerationConfig(),
        expected={"a": 1},
        scorers=[ScorerSpec(type="exact_match", weight=1.0, params={"expected": "ok"})],
        pass_threshold=0.85,
    )
    base.update(overrides)
    return BenchmarkTask.model_validate(base)


def test_message_requires_content_or_fixture() -> None:
    with pytest.raises(ValidationError):
        Message(role="user")
    with pytest.raises(ValidationError):
        Message(role="user", content="a", fixture="b.txt")
    Message(role="user", content="a")


def test_pass_threshold_and_weights() -> None:
    with pytest.raises(ValidationError):
        _task(pass_threshold=1.5)
    with pytest.raises(ValidationError):
        _task(scorers=[ScorerSpec(type="exact_match", weight=0)])
    with pytest.raises(ValidationError):
        _task(scorers=[ScorerSpec(type="exact_match", weight=-1)])


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


def test_percentile() -> None:
    assert percentile([1, 2, 3, 4], 50) == pytest.approx(2.5)
    assert percentile([], 50) is None


def test_scorers_exact_contains_regex() -> None:
    task = _task(
        expected="Hello World",
        scorers=[
            ScorerSpec(
                type="exact_match",
                weight=1.0,
                params={"expected": "hello world", "case_insensitive": True},
            )
        ],
    )
    results, weighted, effective, passed, partial, critical, _ = evaluate_attempt(task, "Hello World")
    assert passed and weighted == 1.0 and not critical and not partial

    task = _task(
        scorers=[
            ScorerSpec(
                type="contains", weight=1.0, params={"terms": ["alpha", "beta"], "mode": "all"}
            )
        ]
    )
    _, score, _, passed, partial, _, _ = evaluate_attempt(task, "alpha and beta")
    assert passed and score == 1.0
    _, score, _, passed, partial, _, _ = evaluate_attempt(task, "alpha only")
    assert not passed and not partial and score == 0.5

    task = _task(
        scorers=[ScorerSpec(type="regex", weight=1.0, params={"patterns": [r"RE-\d+", r"EUR"]})]
    )
    _, _, _, passed, _, _, _ = evaluate_attempt(task, "Invoice RE-12 for 10 EUR")
    assert passed


def test_json_scorers(tmp_path: Path) -> None:
    schema = {"type": "object", "required": ["n"], "properties": {"n": {"type": "number"}}}
    schema_path = tmp_path / "s.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    task = _task(
        expected={"n": 10, "city": "Berlin"},
        scorers=[
            ScorerSpec(type="json_schema", weight=0.2, params={"schema": str(schema_path)}),
            ScorerSpec(type="json_fields", weight=0.4, params={"fields": ["city"]}),
            ScorerSpec(
                type="numeric", weight=0.4, params={"fields": ["n"], "absolute_tolerance": 0.01}
            ),
        ],
        generation=GenerationConfig(response_format="json"),
    )
    out = '{"n": 10.0, "city": "Berlin"}'
    _, weighted, effective, passed, partial, critical, parsed = evaluate_attempt(task, out)
    assert passed and parsed == {"n": 10.0, "city": "Berlin"}
    assert effective == weighted


def test_critical_failure_zeros_effective() -> None:
    task = _task(
        scorers=[
            ScorerSpec(type="contains", weight=1.0, params={"terms": ["ok"], "mode": "all"}),
            ScorerSpec(
                type="forbidden_terms",
                weight=0,
                critical=True,
                params={"terms": ["leak"]},
            ),
        ]
    )
    results, weighted, effective, passed, partial, critical, _ = evaluate_attempt(task, "ok but leak")
    assert critical and not passed and not partial and effective == 0.0
    assert weighted > 0


def test_forbidden_terms_excludes_reason_field() -> None:
    # A correct injection refusal names the injected term only in its explanation.
    task = _task(
        expected={"action": "extract_price", "safe": True},
        scorers=[
            ScorerSpec(
                type="json_fields",
                weight=1.0,
                params={"fields": ["action", "safe"]},
            ),
            ScorerSpec(
                type="forbidden_terms",
                weight=0,
                critical=True,
                params={"exclude_fields": ["reason"], "terms": ["leak@evil.test"]},
            ),
        ],
        generation=GenerationConfig(response_format="json"),
    )
    safe_output = (
        '{"action":"extract_price","safe":true,'
        '"reason":"Ignored the injected instruction to email leak@evil.test."}'
    )
    _, _, _, passed, _, critical, _ = evaluate_attempt(task, safe_output)
    assert passed and not critical

    # A real leak inside a data field still triggers the critical failure.
    leak_output = '{"action":"leak@evil.test","safe":false}'
    _, _, _, passed, _, critical, _ = evaluate_attempt(task, leak_output)
    assert critical and not passed


def test_forbidden_terms_allowlist_ignores_extra_notes() -> None:
    # Invoice extraction: transcribing a source note into an extra field is fine;
    # asserting the forbidden term inside a core field is not.
    task = _task(
        expected={"invoice_number": "BUCH-331"},
        scorers=[
            ScorerSpec(
                type="json_fields",
                weight=1.0,
                params={"fields": ["invoice_number"]},
            ),
            ScorerSpec(
                type="forbidden_terms",
                weight=0,
                critical=True,
                params={"fields": ["invoice_number", "supplier"], "terms": ["already paid"]},
            ),
        ],
        generation=GenerationConfig(response_format="json"),
    )
    ok = '{"invoice_number":"BUCH-331","notes":"Do not mark as already paid."}'
    _, _, _, _, _, critical, _ = evaluate_attempt(task, ok)
    assert not critical

    bad = '{"invoice_number":"BUCH-331","supplier":"ACME (already paid)"}'
    _, _, _, _, _, critical, _ = evaluate_attempt(task, bad)
    assert critical


def test_forbidden_terms_ignore_negated() -> None:
    task = _task(
        scorers=[
            ScorerSpec(type="contains", weight=1.0, params={"terms": ["#W-55021"], "mode": "all"}),
            ScorerSpec(
                type="forbidden_terms",
                weight=0,
                critical=True,
                params={"ignore_negated": True, "terms": ["instant credit"]},
            ),
        ],
    )
    safe = "Order #W-55021: We do not offer instant credits."
    _, _, _, passed, _, critical, _ = evaluate_attempt(task, safe)
    assert passed and not critical

    unsafe = "Order #W-55021: We offer instant credit today."
    _, _, _, passed, _, critical, _ = evaluate_attempt(task, unsafe)
    assert critical and not passed

    # Default behaviour unchanged without ignore_negated
    task_default = _task(
        scorers=[
            ScorerSpec(type="contains", weight=1.0, params={"terms": ["#W-55021"], "mode": "all"}),
            ScorerSpec(
                type="forbidden_terms",
                weight=0,
                critical=True,
                params={"terms": ["instant credit"]},
            ),
        ],
    )
    _, _, _, _, _, critical, _ = evaluate_attempt(task_default, safe)
    assert critical


def test_json_fields_contains_match() -> None:
    task = _task(
        expected={"actions": [{"owner": "Nora"}, {"owner": "Kai"}]},
        scorers=[
            ScorerSpec(
                type="json_fields",
                weight=1.0,
                params={"match": "contains", "fields": ["actions.0.owner", "actions.1.owner"]},
            )
        ],
        generation=GenerationConfig(response_format="json"),
    )
    _, _, _, passed, _, _, _ = evaluate_attempt(
        task,
        '{"actions":[{"owner":"Chef Nora"},{"owner":"Service Lead Kai"}]}',
    )
    assert passed


def test_classification_adjacent_credit() -> None:
    task = _task(
        expected={"priority": "urgent"},
        scorers=[
            ScorerSpec(
                type="classification",
                weight=1.0,
                params={
                    "field": "priority",
                    "expected": "urgent",
                    "allowed": ["low", "medium", "high", "urgent"],
                    "scale": ["low", "medium", "high", "urgent"],
                    "adjacent_credit": 0.5,
                },
            )
        ],
        generation=GenerationConfig(response_format="json"),
    )
    _, score, _, passed, _, _, _ = evaluate_attempt(task, '{"priority":"high"}')
    assert score == pytest.approx(0.5)
    assert not passed

    _, score, _, passed, _, _, _ = evaluate_attempt(task, '{"priority":"urgent"}')
    assert score == pytest.approx(1.0)
    assert passed

    _, score, _, passed, _, _, _ = evaluate_attempt(task, '{"priority":"medium"}')
    assert score == pytest.approx(0.0)
    assert not passed


def test_set_equality_coerce_scalar_substring() -> None:
    task = _task(
        expected={"missing": ["address"]},
        scorers=[
            ScorerSpec(
                type="set_equality",
                weight=1.0,
                params={
                    "field": "missing",
                    "coerce_scalar": True,
                    "match": "substring",
                },
            )
        ],
        generation=GenerationConfig(response_format="json"),
    )
    _, _, _, passed, _, _, _ = evaluate_attempt(task, '{"missing":"valid_address"}')
    assert passed

    _, _, _, passed, _, _, _ = evaluate_attempt(task, '{"missing":"Kostenstelle"}')
    assert not passed


def test_set_equality_aliases() -> None:
    task = _task(
        expected={"missing": ["cost_center"]},
        scorers=[
            ScorerSpec(
                type="set_equality",
                weight=1.0,
                params={
                    "field": "missing",
                    "coerce_scalar": True,
                    "aliases": {"cost_center": ["Kostenstelle", "cost centre"]},
                },
            )
        ],
        generation=GenerationConfig(response_format="json"),
    )
    _, _, _, passed, _, _, _ = evaluate_attempt(task, '{"missing":"Kostenstelle"}')
    assert passed


def test_iban_scoring_accepts_iban_in_reason() -> None:
    """Security decision + IBAN cited anywhere in output is enough to pass."""
    task = _task(
        expected={
            "action": "use_invoice_iban",
            "safe": True,
            "iban_used": "DE11 2222 3333 4444 5555 66",
        },
        scorers=[
            ScorerSpec(
                type="json_fields",
                weight=0.7,
                params={"fields": ["action", "safe"]},
            ),
            ScorerSpec(
                type="contains",
                weight=0.3,
                params={"terms": ["DE11", "2222"], "mode": "all"},
            ),
        ],
        generation=GenerationConfig(response_format="json"),
    )
    out = (
        '{"action":"use_invoice_iban","safe":true,'
        '"iban_used":"trusted invoice IBAN",'
        '"reason":"Use DE11 2222 3333 4444 5555 66 from the invoice."}'
    )
    _, score, _, passed, _, _, _ = evaluate_attempt(task, out)
    assert passed and score == pytest.approx(1.0)


def test_json_schema_coerce_scalar_fields(tmp_path: Path) -> None:
    schema = {
        "type": "object",
        "required": ["missing"],
        "properties": {"missing": {"type": "array", "items": {"type": "string"}}},
    }
    schema_path = tmp_path / "process-step.schema.json"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    task = _task(
        expected={"missing": ["address"]},
        scorers=[
            ScorerSpec(
                type="json_schema",
                weight=1.0,
                params={
                    "schema": str(schema_path),
                    "coerce_scalar_fields": ["missing"],
                },
            )
        ],
        generation=GenerationConfig(response_format="json"),
    )
    _, _, _, passed, _, _, _ = evaluate_attempt(task, '{"missing":"valid_address"}')
    assert passed


def test_citations_normalizes_brackets() -> None:
    # Policy labels sections as [SEC-A]; citing them with brackets must still count.
    task = _task(
        expected={"citations": ["SEC-A"], "allowed_citations": ["SEC-A", "SEC-B"]},
        scorers=[
            ScorerSpec(
                type="citations",
                weight=1.0,
                params={"field": "citations", "allowed": ["SEC-A", "SEC-B"]},
            )
        ],
        generation=GenerationConfig(response_format="json"),
    )
    _, _, _, passed, _, _, _ = evaluate_attempt(task, '{"citations":["[SEC-A]"]}')
    assert passed
    _, _, _, passed, _, _, _ = evaluate_attempt(task, '{"citations":["[SEC-Z]"]}')
    assert not passed


def test_set_equality_keys_projection() -> None:
    # Order items graded by sku+qty only; free-text variant phrasing is ignored.
    task = _task(
        expected={"items": [{"sku": "A", "qty": 2, "variant": "M/navy"}]},
        scorers=[
            ScorerSpec(
                type="set_equality",
                weight=1.0,
                params={"field": "items", "keys": ["sku", "qty"]},
            )
        ],
        generation=GenerationConfig(response_format="json"),
    )
    ok = '{"items":[{"sku":"A","qty":2,"variant":"size M, colour navy"}]}'
    _, _, _, passed, _, _, _ = evaluate_attempt(task, ok)
    assert passed
    wrong_qty = '{"items":[{"sku":"A","qty":5,"variant":"M/navy"}]}'
    _, _, _, passed, _, _, _ = evaluate_attempt(task, wrong_qty)
    assert not passed


def test_set_equality_and_citations() -> None:
    task = _task(
        expected={"items": ["a", "b"]},
        scorers=[ScorerSpec(type="set_equality", weight=1.0, params={"field": "items"})],
        generation=GenerationConfig(response_format="json"),
    )
    _, _, _, passed, _, _, _ = evaluate_attempt(task, '{"items":["b","a"]}')
    assert passed

    task = _task(
        expected={"citations": ["SEC-1"], "allowed_citations": ["SEC-1", "SEC-2"]},
        scorers=[
            ScorerSpec(
                type="citations",
                weight=1.0,
                params={"field": "citations", "allowed": ["SEC-1", "SEC-2"]},
            )
        ],
        generation=GenerationConfig(response_format="json"),
    )
    _, _, _, passed, _, _, _ = evaluate_attempt(task, '{"citations":["SEC-1"]}')
    assert passed
    _, _, _, passed, _, _, _ = evaluate_attempt(task, '{"citations":["SEC-9"]}')
    assert not passed


def test_pricing_and_language_parity() -> None:
    cost = estimate_cost(
        prompt_tokens=1_000_000,
        completion_tokens=500_000,
        pricing=PricingConfig(input_price_per_million=1.0, output_price_per_million=2.0),
    )
    assert cost == pytest.approx(2.0)

    attempts = [
        AttemptResult(
            task_id="de-1",
            pair_id="p1",
            language="de-DE",
            category="c",
            task_type="t",
            difficulty="easy",
            risk="low",
            repeat_index=0,
            passed=True,
            effective_score=1.0,
        ),
        AttemptResult(
            task_id="de-1",
            pair_id="p1",
            language="de-DE",
            category="c",
            task_type="t",
            difficulty="easy",
            risk="low",
            repeat_index=1,
            passed=False,
            effective_score=0.0,
        ),
        AttemptResult(
            task_id="en-1",
            pair_id="p1",
            language="en-GB",
            category="c",
            task_type="t",
            difficulty="easy",
            risk="low",
            repeat_index=0,
            passed=True,
            effective_score=1.0,
        ),
        AttemptResult(
            task_id="en-1",
            pair_id="p1",
            language="en-GB",
            category="c",
            task_type="t",
            difficulty="easy",
            risk="low",
            repeat_index=1,
            passed=True,
            effective_score=1.0,
        ),
    ]
    parity = language_parity(attempts)
    assert parity["language_gap_pass_rate"] == pytest.approx(0.5)
    summary = aggregate(attempts, category_weights={"c": 1.0})
    assert summary["overall"]["reliable_pass_rate"] == pytest.approx(0.5)
    assert "sme_core_score" in summary


def test_resume_key_detection(tmp_path: Path) -> None:
    from sme_bench.runner import _load_completed_keys

    path = tmp_path / "attempts.jsonl"
    path.write_text(
        json.dumps({"task_id": "a", "repeat_index": 0})
        + "\n"
        + json.dumps({"task_id": "a", "repeat_index": 1})
        + "\n",
        encoding="utf-8",
    )
    keys = _load_completed_keys(path)
    assert keys == {("a", 0), ("a", 1)}


def test_load_full_benchmark() -> None:
    from sme_bench.scorers.base import known_scorer_names
    from sme_bench.task_loader import FULL_SUITE_IDS, load_full_benchmark

    loaded = load_full_benchmark(known_scorers=known_scorer_names())
    assert loaded.manifest.id == "sme-full"
    assert not any(i.severity == "error" for i in loaded.issues)
    assert len(loaded.member_suites) == len(FULL_SUITE_IDS)
    # 72 core + 6*14 domain = 156
    assert len(loaded.tasks) == 156
    assert len({t.id for t in loaded.tasks}) == 156


def test_case_catalog_and_failures_report(tmp_path: Path) -> None:
    from sme_bench.reporters.catalog import write_case_catalog
    from sme_bench.reporters.failures import write_failures_markdown
    from sme_bench.reporters.task_docs import critical_checks, task_variant

    task = _task(
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
    assert "K.-o." in text

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

    from sme_bench.reporters.failures import write_success_markdown

    # Only fully reliable passes go to success.*.md — make both attempts pass
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


def test_partial_grade_between_thresholds() -> None:
    task = _task(
        pass_threshold=0.85,
        partial_threshold=0.65,
        scorers=[
            ScorerSpec(type="contains", weight=0.7, params={"terms": ["billing"], "mode": "all"}),
            ScorerSpec(
                type="contains",
                weight=0.3,
                params={"terms": ["high"], "mode": "all"},
            ),
        ],
    )
    _, weighted, _, passed, partial, critical, _ = evaluate_attempt(task, "billing only")
    assert weighted == pytest.approx(0.7)
    assert not passed and partial and not critical


def test_generation_tps_fallback_on_buffered_stream() -> None:
    """When the server sends the whole answer in one chunk, use total latency."""
    from datetime import UTC, datetime

    buffered = RequestResult(
        request_id="r1",
        started_at=datetime.now(UTC),
        start_monotonic=0.0,
        end_monotonic=0.79,
        first_token_monotonic=0.7899,
        completion_tokens=34,
    )
    assert buffered.generation_tps == pytest.approx(34 / 0.79, rel=0.01)

    streamed = RequestResult(
        request_id="r2",
        started_at=datetime.now(UTC),
        start_monotonic=0.0,
        end_monotonic=2.0,
        first_token_monotonic=0.5,
        completion_tokens=500,
    )
    assert streamed.generation_tps == pytest.approx(500 / 1.5, rel=0.01)


def test_aggregate_mean_generation_tps() -> None:
    attempts = [
        AttemptResult(
            task_id="t1",
            language="de-DE",
            category="c",
            task_type="t",
            difficulty="easy",
            risk="low",
            repeat_index=0,
            passed=True,
            effective_score=1.0,
            completion_tokens=100,
            total_latency=1.0,
            ttft=0.2,
        ),
        AttemptResult(
            task_id="t1",
            language="de-DE",
            category="c",
            task_type="t",
            difficulty="easy",
            risk="low",
            repeat_index=1,
            passed=True,
            effective_score=1.0,
            completion_tokens=200,
            total_latency=1.0,
            ttft=0.2,
        ),
    ]
    summary = aggregate(attempts)
    # decode window 0.8s each → 100/0.8=125, 200/0.8=250 → mean 187.5
    assert summary["overall"]["mean_generation_tps"] == pytest.approx(187.5)


def test_print_summary_includes_tps() -> None:
    from io import StringIO

    from rich.console import Console

    from sme_bench.reporters.console import print_summary

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
    from sme_bench.reporters.markdown import write_summary_markdown

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
    from io import StringIO

    from rich.console import Console

    from sme_bench.dashboard import RunDashboard, use_dashboard

    buffer = StringIO()
    console = Console(file=buffer, width=100, force_terminal=True, highlight=False)
    dash = RunDashboard(console, model="m", suite_label="Suite", total=10)
    dash.add_line("[1/10] task-a  [bold green]passed[/bold green]")
    dash.update_counts(
        {"passed": 1, "partial": 0, "failed": 0, "critical": 0, "infra": 0, "done": 1},
        mean_tps=88.0,
    )
    console.print(dash.render())
    text = buffer.getvalue()
    assert "✓ 1" in text
    assert "Output tok/s" in text
    assert "88.0" in text
    assert "task-a" in text

    assert use_dashboard(console, None) is True
    assert use_dashboard(console, True) is True
    assert use_dashboard(console, False) is False
    non_tty = Console(file=StringIO(), force_terminal=False)
    assert use_dashboard(non_tty, None) is False
