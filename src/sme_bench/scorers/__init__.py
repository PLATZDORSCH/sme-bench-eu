"""Built-in scorers package."""

from sme_bench.scorers.base import Scorer, get_scorer, known_scorer_names, register

__all__ = [
    "Scorer",
    "get_scorer",
    "known_scorer_names",
    "register",
]
