"""Suite audit and script idempotency gates."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from sme_bench.scorers.base import get_scorer, known_scorer_names
from sme_bench.task_loader import FULL_SUITE_IDS, load_full_benchmark, load_suite

ROOT = Path(__file__).resolve().parents[2]


def _load_script_module(name: str):
    import importlib.util

    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_full_benchmark_baseline_count_and_audits() -> None:
    loaded = load_full_benchmark(known_scorers=known_scorer_names())
    errors = [i for i in loaded.issues if i.severity == "error"]
    assert not errors, "\n".join(f"{e.path}: {e.message}" for e in errors[:20])
    assert len(loaded.member_suites) == len(FULL_SUITE_IDS)
    assert len(loaded.tasks) == 196
    assert len({t.id for t in loaded.tasks}) == 196
    assert loaded.manifest.version == "0.10.3"
    candidates = [
        task for task in loaded.tasks if {"noise-variant", "edge-variant"}.intersection(task.tags)
    ]
    assert len(candidates) == 40
    assert all(task.review_status == "approved" for task in candidates)
    assert all(
        {"pair-reviewed", "golden-reviewed", "reference-calibrated"} <= set(task.tags)
        for task in candidates
    )

    releases = json.loads(
        (ROOT / "suites" / "compatibility" / "releases.json").read_text(encoding="utf-8")
    )
    assert "0.3.0" in releases["released"]
    assert "0.4.1" in releases["released"]
    assert "0.4.0" in releases["released"]
    assert "0.4.3" in releases["released"]
    assert "0.5.0" in releases["released"]
    assert "0.6.0" in releases["released"]
    assert "0.7.0" in releases["released"]
    assert "0.8.0" in releases["released"]
    assert "0.10.3" in releases["released"]
    assert "0.4.1" not in releases["draft"]

    calibration = json.loads(
        (ROOT / "suites" / "compatibility" / "calibration-0.4.0.json").read_text(encoding="utf-8")
    )
    assert calibration["candidate_count"] == 40
    assert calibration["suite_version"] == "0.4.0"
    # The manifest is the immutable record of the 0.4.0 calibration run. Content
    # 0.9.0 rewrote every prompt to state the language requirement, so its input
    # fingerprints have moved on and are no longer expected to match. What must
    # still hold is that the calibrated *candidate set* is the set we ship.
    assert set(calibration["candidate_input_fingerprints"]) == {task.id for task in candidates}
    assert len(calibration["models"]) == 2
    assert all(model["attempts"] == 40 for model in calibration["models"])
    assert all(model["passed"] >= 36 for model in calibration["models"])


def test_positive_weights_sum_to_one() -> None:
    loaded = load_full_benchmark(known_scorers=known_scorer_names())
    for task in loaded.tasks:
        positive = [s.weight for s in task.scorers if s.weight > 0]
        assert positive
        assert abs(sum(positive) - 1.0) < 1e-6, task.id


LANGUAGE_INSTRUCTIONS = {
    "de-DE": ("Formuliere alle Textwerte auf Deutsch", "Antworte auf Deutsch."),
    "en-GB": ("Write all text values in English", "Respond in English."),
}


def test_every_case_states_and_checks_its_language() -> None:
    """Content 0.9.0 contract: the prompt asks for the language and a scorer checks it."""
    loaded = load_full_benchmark(known_scorers=known_scorer_names())
    for task in loaded.tasks:
        specs = [scorer for scorer in task.scorers if scorer.type == "language"]
        assert len(specs) == 1, task.id
        # A positive weight would renormalise every other scorer and dilute real
        # errors; must_pass is what turns the check into a gate.
        assert specs[0].weight == 0.0, task.id
        assert specs[0].must_pass, task.id

        system = next(m.content or "" for m in task.messages if m.role == "system")
        expected = LANGUAGE_INSTRUCTIONS[task.language]
        assert any(phrase in system for phrase in expected), task.id


def test_expected_answers_pass_their_own_language_scorer() -> None:
    """A case must never grade its own canonical answer as the wrong language."""
    loaded = load_full_benchmark(known_scorers=known_scorer_names())
    scorer = get_scorer("language")
    for task in loaded.tasks:
        if task.expected is None:
            continue
        spec = next(s for s in task.scorers if s.type == "language")
        payload = json.loads(json.dumps(task.expected, ensure_ascii=False, default=str))
        result = scorer.score(
            task=task,
            output_text=json.dumps(payload, ensure_ascii=False),
            parsed_output=payload,
            spec=spec,
        )
        assert result.passed, f"{task.id}: {result.details}"


def test_no_duplicate_scorers() -> None:
    loaded = load_full_benchmark(known_scorers=known_scorer_names())
    for task in loaded.tasks:
        keys = [
            json.dumps(
                {
                    "type": scorer.type,
                    "weight": scorer.weight,
                    "critical": scorer.critical,
                    "must_pass": scorer.must_pass,
                    "params": scorer.params,
                },
                sort_keys=True,
                default=str,
            )
            for scorer in task.scorers
        ]
        assert len(keys) == len(set(keys)), task.id


def test_pii_prompts_do_not_contain_answer_like_label_sets() -> None:
    loaded = load_full_benchmark(known_scorers=known_scorer_names())
    tasks = {
        task.id: task
        for task in loaded.tasks
        if task.pair_id in {"pii-detection-001", "pii-detection-002", "pii-detection-003"}
    }
    assert len(tasks) == 6
    for task in tasks.values():
        system = next(message.content for message in task.messages if message.role == "system")
        assert system is not None
        assert '"pii_types":["name","email"]' not in system
        assert '"pii_types":[...]' in system
        if task.pair_id == "pii-detection-002":
            assert "--" in system
            assert "ignor" in system.casefold()


def test_migrate_script_idempotent(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # Run against an isolated suite copy so a failed idempotency check cannot
    # mutate the developer's working tree.
    mod = _load_script_module("migrate_suite_cases")
    shutil.copytree(ROOT / "suites", tmp_path / "suites")
    mod.ROOT = tmp_path
    mod.SUITES = tmp_path / "suites"
    mod.main([])
    capsys.readouterr()
    mod.main([])
    assert "Done: 0 cases" in capsys.readouterr().out


def test_expand_refuses_source_overwrite(tmp_path: Path) -> None:
    """Regression: fixture stem without -001 must still get a distinct -002 path."""
    mod = _load_script_module("expand_domain_variants")

    assert mod._variant_fixture_rel("fixtures/order/de-order.txt", "002") == (
        "fixtures/order/de-order-002.txt"
    )
    src = tmp_path / "de-order.txt"
    src.write_text("SKU-A100 qty 1\n", encoding="utf-8")
    before = src.read_bytes()
    target = tmp_path / "de-order-002.txt"
    mod._write_noise_fixture(src, target, edge=False)
    assert src.read_bytes() == before
    assert target.exists()
    assert "SKU-A100" in target.read_text(encoding="utf-8")
    assert target.read_text(encoding="utf-8") != src.read_text(encoding="utf-8")


def test_expansion_is_idempotent_and_rejects_stale_case(tmp_path: Path) -> None:
    mod = _load_script_module("expand_domain_variants")
    mod.ROOT = tmp_path
    suite = tmp_path / "suites" / "sme-test-v0.1"
    case_dir = suite / "cases" / "de-DE"
    fixture_dir = suite / "fixtures"
    case_dir.mkdir(parents=True)
    fixture_dir.mkdir()
    source_fixture = fixture_dir / "source.txt"
    source_fixture.write_text("Fakt A\n", encoding="utf-8")
    source_bytes = source_fixture.read_bytes()
    (case_dir / "de-test-001.yaml").write_text(
        """
id: de-test-001
pair_id: test-001
title: Test
language: de-DE
difficulty: normal
review_status: approved
tags: []
messages:
  - role: user
    fixture: fixtures/source.txt
""".lstrip(),
        encoding="utf-8",
    )

    assert mod.expand_suite("sme-test-v0.1", variants=("002",)) == 1
    assert mod.expand_suite("sme-test-v0.1", variants=("002",)) == 0
    assert source_fixture.read_bytes() == source_bytes

    target_case = case_dir / "de-test-002.yaml"
    stale = mod._load(target_case)
    stale["title"] = "stale generated title"
    mod._dump(target_case, stale)
    with pytest.raises(RuntimeError, match="Case collision"):
        mod.expand_suite("sme-test-v0.1", variants=("002",))


def test_migration_preserves_semantically_distinct_same_type_scorers() -> None:
    mod = _load_script_module("migrate_suite_cases")
    scorers = [
        {"type": "contains", "weight": 0.5, "params": {"terms": ["alpha"]}},
        {"type": "contains", "weight": 0.5, "params": {"terms": ["beta"]}},
    ]
    assert mod._dedupe_scorers(scorers) == scorers


def test_baseline_export_is_pinned_and_byte_idempotent(tmp_path: Path) -> None:
    output = tmp_path / "baseline.json"
    command = [
        sys.executable,
        str(ROOT / "scripts" / "export_baseline_manifest.py"),
        "--ref",
        "9ec61a5",
        "--output",
        str(output),
    ]
    subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
    first = output.read_bytes()
    subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
    assert output.read_bytes() == first
    payload = json.loads(first)
    assert payload["source_ref"] == "9ec61a5"
    assert len(payload["input_fingerprints"]) == 156


def test_core_suite_loads_clean() -> None:
    loaded = load_suite(
        ROOT / "suites" / "sme-core-v0.1",
        known_scorers=known_scorer_names(),
    )
    errors = [i for i in loaded.issues if i.severity == "error"]
    assert not errors, "\n".join(f"{e.path}: {e.message}" for e in errors[:20])
    assert len(loaded.tasks) == 72
