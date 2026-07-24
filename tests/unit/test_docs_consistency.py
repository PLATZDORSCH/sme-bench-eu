"""Documentation consistency: README suite counts and example file references."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from sme_bench.scorers.base import known_scorer_names
from sme_bench.task_loader import FULL_SUITE_IDS, load_full_benchmark, load_suite

ROOT = Path(__file__).resolve().parents[2]

EXPECTED_SUITE_COUNTS = {
    "sme-core-v0.1": 72,
    "sme-trades-v0.1": 22,
    "sme-ecommerce-v0.1": 22,
    "sme-financial-v0.1": 22,
    "sme-hospitality-v0.1": 24,
    "sme-logistics-v0.1": 20,
    "sme-chains-v0.1": 14,
}


def _readme_table_count(text: str, suite_id: str) -> int | None:
    """Parse the Cases column from a root README suite table row."""
    # e.g. | **SME Trades v0.1** | `suites/sme-trades-v0.1` | … | 22 |
    pattern = rf"\|[^\n]*`suites/{re.escape(suite_id)}`[^\n]*\|\s*(\d+)\s*\|"
    match = re.search(pattern, text)
    return int(match.group(1)) if match else None


def _full_count(text: str) -> int | None:
    pattern = r"\|\s*\*\*SME Full\*\*[^\n]*\|\s*(\d+)\s*\|"
    match = re.search(pattern, text)
    return int(match.group(1)) if match else None


@pytest.mark.parametrize("suite_id,expected", sorted(EXPECTED_SUITE_COUNTS.items()))
def test_suite_disk_counts_match_expected(suite_id: str, expected: int) -> None:
    loaded = load_suite(ROOT / "suites" / suite_id, known_scorers=known_scorer_names())
    assert len(loaded.tasks) == expected


def test_full_benchmark_count() -> None:
    loaded = load_full_benchmark(known_scorers=known_scorer_names())
    assert len(loaded.tasks) == 196
    assert set(FULL_SUITE_IDS) == set(EXPECTED_SUITE_COUNTS)


@pytest.mark.parametrize("readme_name", ["README.md", "README.de.md"])
def test_root_readme_suite_counts(readme_name: str) -> None:
    text = (ROOT / readme_name).read_text(encoding="utf-8")
    assert _full_count(text) == 196
    for suite_id, expected in EXPECTED_SUITE_COUNTS.items():
        found = _readme_table_count(text, suite_id)
        assert found == expected, f"{readme_name}: {suite_id} expected {expected}, got {found}"


@pytest.mark.parametrize("suite_id,expected", sorted(EXPECTED_SUITE_COUNTS.items()))
@pytest.mark.parametrize("readme_name", ["README.md", "README.de.md"])
def test_suite_readme_case_count(suite_id: str, expected: int, readme_name: str) -> None:
    path = ROOT / "suites" / suite_id / readme_name
    assert path.is_file(), path
    text = path.read_text(encoding="utf-8")
    # EN: | **Cases** | 22 (11 DE/EN pairs) |
    # DE: | **Fälle** | 22 (11 DE/EN-Paare) |
    match = re.search(r"\|\s*\*\*(?:Cases|Fälle)\*\*\s*\|\s*(\d+)\b", text)
    assert match, f"{path}: Cases/Fälle row not found"
    assert int(match.group(1)) == expected


@pytest.mark.parametrize("readme_name", ["README.md", "README.de.md"])
def test_readme_example_files_exist(readme_name: str) -> None:
    text = (ROOT / readme_name).read_text(encoding="utf-8")
    refs = re.findall(r"examples/[A-Za-z0-9_./-]+\.json", text)
    assert refs, f"{readme_name}: expected at least one examples/*.json reference"
    missing = [ref for ref in refs if not (ROOT / ref).is_file()]
    assert not missing, f"{readme_name}: missing example files: {missing}"


def test_glm_example_payload() -> None:
    path = ROOT / "examples" / "extra-body-glm-no-thinking.json"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "enable_thinking" in text
    assert "false" in text
