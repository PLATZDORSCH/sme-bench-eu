"""SME-Bench: Benchmark for SME business tasks on language models."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("sme-bench")
except PackageNotFoundError:  # pragma: no cover - editable / source tree
    __version__ = "0.4.0"

__all__ = ["__version__"]
