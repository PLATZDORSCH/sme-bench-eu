"""Scorer protocol and registry."""

from __future__ import annotations

from typing import Any, Protocol, TypeVar

from sme_bench.models import BenchmarkTask, ScoreResult, ScorerSpec

_LOADED = False


class Scorer(Protocol):
    name: str

    def score(
        self,
        *,
        task: BenchmarkTask,
        output_text: str,
        parsed_output: Any | None,
        spec: ScorerSpec,
    ) -> ScoreResult: ...


_REGISTRY: dict[str, Scorer] = {}
T = TypeVar("T")


def register(scorer_cls: type[T]) -> type[T]:
    """Register a scorer class by instantiating it once."""
    instance: Any = scorer_cls()
    name = getattr(instance, "name", None)
    if not isinstance(name, str):
        raise TypeError(f"Scorer {scorer_cls!r} must define a string 'name'")
    _REGISTRY[name] = instance
    return scorer_cls


def _ensure_scorers_loaded() -> None:
    global _LOADED
    if _LOADED:
        return
    # Import for registration side effects
    from sme_bench.scorers import (  # noqa: F401
        citations,
        classification,
        contains,
        exact_match,
        forbidden_terms,
        json_fields,
        json_schema,
        numeric,
        regex,
        set_equality,
    )

    _LOADED = True


def get_scorer(name: str) -> Scorer:
    _ensure_scorers_loaded()
    if name not in _REGISTRY:
        raise KeyError(f"Unknown scorer: {name}")
    return _REGISTRY[name]


def known_scorer_names() -> set[str]:
    _ensure_scorers_loaded()
    return set(_REGISTRY)
