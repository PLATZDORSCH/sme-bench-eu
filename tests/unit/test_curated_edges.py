"""Golden checks for curated domain edge cases."""

from __future__ import annotations

import json

import pytest

from sme_bench.scorers.base import known_scorer_names
from sme_bench.scoring import evaluate_attempt
from sme_bench.task_loader import load_full_benchmark

EDGE_GOLDENS = {
    "de-tr-grounded-003": ("Verschleiß und falsche Nutzung", "H-2", "14 Tage", "H-1"),
    "en-tr-grounded-003": ("wear and incorrect use", "H-2", "14 days", "H-1"),
    "de-ec-grounded-003": (
        "Hygienartikel und getragene Schuhe mit Nutzungsspuren",
        "R-3",
        "14",
        "R-2",
    ),
    "en-ec-grounded-003": (
        "hygiene products and worn shoes with signs of use",
        "R-3",
        "14",
        "R-2",
    ),
    "de-fi-grounded-003": ("7%", "V-2", "19%", "V-1"),
    "en-fi-grounded-003": ("7%", "V-2", "19%", "V-1"),
    "de-ho-grounded-003": ("25 EUR pro Person", "H-2", "12:00", "H-1"),
    "en-ho-grounded-003": ("EUR 25 per person", "H-2", "12:00", "H-1"),
    "de-lo-grounded-003": ("nächster Werktag", "L-2", "2-4", "L-1"),
    "en-lo-grounded-003": ("next business day", "L-2", "2-4", "L-1"),
}


def _candidate_golden_output(task) -> str:
    if task.task_type == "meeting_actions":
        return json.dumps({"actions": task.expected["actions"]}, default=str)
    if task.task_type == "order_extraction":
        return json.dumps(
            {
                key: task.expected[key]
                for key in ("customer", "currency", "items")
                if key in task.expected
            },
            default=str,
        )
    if task.task_type == "grounded_qa":
        return json.dumps(
            {"answer": task.expected["answer"], "citations": task.expected["citations"]},
            default=str,
        )
    if task.task_type == "customer_reply":
        contains = next(scorer for scorer in task.scorers if scorer.type == "contains")
        terms = " ".join(str(term) for term in contains.params["terms"])
        return (
            f"Confirmed details: {terms}. Please review this complete response carefully and "
            "contact our team if you need any further factual clarification about the request."
        )
    raise AssertionError(f"No candidate golden builder for {task.id}")


def test_all_candidate_variants_have_positive_golden() -> None:
    loaded = load_full_benchmark(known_scorers=known_scorer_names())
    candidates = [
        task
        for task in loaded.tasks
        if {"noise-variant", "edge-variant"}.intersection(task.tags)
    ]
    assert len(candidates) == 40
    for task in candidates:
        output = _candidate_golden_output(task)
        _, _, _, passed, _, _, _ = evaluate_attempt(task, output)
        assert passed, task.id


@pytest.mark.parametrize("task_id", EDGE_GOLDENS)
def test_curated_edge_positive_and_old_answer_negative(task_id: str) -> None:
    loaded = load_full_benchmark(known_scorers=known_scorer_names())
    task = next(task for task in loaded.tasks if task.id == task_id)
    answer, citation, old_answer, old_citation = EDGE_GOLDENS[task_id]

    positive = json.dumps({"answer": answer, "citations": [citation]}, ensure_ascii=False)
    _, _, _, passed, _, _, _ = evaluate_attempt(task, positive)
    assert passed

    stale = json.dumps(
        {"answer": old_answer, "citations": [old_citation]},
        ensure_ascii=False,
    )
    _, _, _, passed, _, _, _ = evaluate_attempt(task, stale)
    assert not passed

    assert task.review_status == "approved"
    assert {"pair-reviewed", "golden-reviewed", "reference-calibrated"} <= set(task.tags)
