"""Trace scorers for live tool loops."""

from __future__ import annotations

from sme_bench.models import ScorerSpec, ToolCall, ToolTraceEntry
from sme_bench.scoring import evaluate_attempt
from tests.unit.conftest import make_task


def _trace(*names: str, phases: list[int] | None = None) -> list[ToolTraceEntry]:
    entries: list[ToolTraceEntry] = []
    for idx, name in enumerate(names):
        phase = phases[idx] if phases else 0
        entries.append(
            ToolTraceEntry(
                call=ToolCall(name=name, arguments={}),
                result={"ok": True},
                turn_index=idx,
                phase=phase,
            )
        )
    return entries


def test_trace_calls_dependency_order() -> None:
    task = make_task(
        expected={"tool_calls": [{"name": "find_contact"}, {"name": "send_email"}]},
        scorers=[
            ScorerSpec(
                type="trace_calls",
                weight=1.0,
                params={"order": "dependency", "dependencies": [["find_contact", "send_email"]]},
            )
        ],
    )
    _r, _w, _e, passed, _p, critical, _parsed = evaluate_attempt(
        task, "sent", tool_trace=_trace("find_contact", "send_email")
    )
    assert passed and not critical
    _r, _w, _e, passed, _p, critical, _parsed = evaluate_attempt(
        task, "sent", tool_trace=_trace("send_email", "find_contact")
    )
    assert not passed


def test_trace_calls_matches_string_arguments_from_server() -> None:
    """vLLM/OpenAI stream ``arguments`` as a JSON string; expected args must still match."""
    task = make_task(
        expected={
            "tool_calls": [
                {"name": "find_contact", "arguments": {"name": "Priya"}},
                {"name": "send_email", "arguments": {"to": "priya@example.com"}},
            ]
        },
        scorers=[ScorerSpec(type="trace_calls", weight=1.0, params={"order": "dependency"})],
    )
    trace = [
        ToolTraceEntry(
            call=ToolCall(name="find_contact", arguments='{"name": "Priya"}'),
            result={"email": "priya@example.com"},
            turn_index=0,
        ),
        ToolTraceEntry(
            call=ToolCall(
                name="send_email",
                arguments='{"to": "priya@example.com", "subject": "Q3"}',
            ),
            result={"status": "sent"},
            turn_index=1,
        ),
    ]
    results, _w, _e, passed, _p, _c, _parsed = evaluate_attempt(task, "sent", tool_trace=trace)
    assert passed, results[0].message
    # Wrong argument value must still be detected.
    trace[0].call.arguments = '{"name": "Someone"}'
    results, _w, _e, passed, _p, _c, _parsed = evaluate_attempt(task, "sent", tool_trace=trace)
    assert not passed
    assert "find_contact" in (results[0].message or "")


def test_trace_exactly_once_ignores_failed_first_call() -> None:
    task = make_task(
        scorers=[
            ScorerSpec(type="trace_exactly_once", weight=1.0, params={"name": "create_booking"})
        ]
    )
    trace = [
        ToolTraceEntry(
            call=ToolCall(name="create_booking", arguments={}),
            result={"error": "busy"},
            turn_index=0,
            error=True,
        ),
        ToolTraceEntry(
            call=ToolCall(name="create_booking", arguments={}),
            result={"id": "bk-2"},
            turn_index=1,
        ),
    ]
    _r, _w, _e, passed, _p, _c, _parsed = evaluate_attempt(task, "booked", tool_trace=trace)
    assert passed


def test_trace_no_fabrication() -> None:
    task = make_task(
        scorers=[
            ScorerSpec(
                type="trace_no_fabrication",
                weight=1.0,
                critical=True,
                params={"forbidden": ["INV-FAKE"]},
            )
        ]
    )
    _r, _w, _e, passed, _p, critical, _parsed = evaluate_attempt(task, "Invoice INV-FAKE canceled")
    assert not passed and critical
    _r, _w, _e, passed, _p, critical, _parsed = evaluate_attempt(task, "Could not cancel")
    assert passed and not critical


def test_trace_phase_rejects_early_write() -> None:
    task = make_task(
        scorers=[
            ScorerSpec(
                type="trace_phase",
                weight=1.0,
                critical=True,
                params={"name": "create_event", "min_phase": 1},
            )
        ]
    )
    _r, _w, _e, passed, _p, critical, _parsed = evaluate_attempt(
        task, "created", tool_trace=_trace("create_event", phases=[0])
    )
    assert not passed and critical
    _r, _w, _e, passed, _p, critical, _parsed = evaluate_attempt(
        task, "created", tool_trace=_trace("create_event", phases=[1])
    )
    assert passed and not critical
