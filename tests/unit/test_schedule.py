"""Longest-first scheduling for parallel runs."""

from __future__ import annotations

import random

from sme_bench.models import GenerationConfig
from sme_bench.runner import estimate_task_cost, schedule_tasks
from tests.unit.conftest import make_task


def test_schedule_concurrency_one_matches_seeded_shuffle() -> None:
    tasks = [
        make_task(id="de-order-extraction-001"),
        make_task(id="de-exp-cashflow-001"),
        make_task(id="de-adv-policy-001"),
        make_task(id="de-agentic-chain-email-001"),
    ]
    rng = random.Random(42)
    expected = list(tasks)
    rng.shuffle(expected)
    assert schedule_tasks(tasks, concurrency=1, seed=42) == expected


def test_schedule_concurrency_puts_expert_before_core() -> None:
    core = make_task(
        id="de-order-extraction-001",
        generation=GenerationConfig(max_tokens=200),
    )
    expert = make_task(
        id="de-exp-cashflow-001",
        generation=GenerationConfig(max_tokens=200),
    )
    ordered = schedule_tasks([core, expert], concurrency=2, seed=7)
    assert [task.id for task in ordered] == ["de-exp-cashflow-001", "de-order-extraction-001"]
    assert estimate_task_cost(expert) > estimate_task_cost(core)
