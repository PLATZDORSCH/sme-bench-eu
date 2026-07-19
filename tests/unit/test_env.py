"""Tests for .env loading."""

from __future__ import annotations

import os
from pathlib import Path

from sme_bench.env import load_env_files


def test_load_env_fills_empty_placeholder(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "OPENAI_API_KEY=sk-from-file\nNEBIUS_API_KEY=nebius-from-file\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "")  # empty placeholder
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)

    load_env_files()

    assert os.environ.get("OPENAI_API_KEY") == "sk-from-file"
    assert os.environ.get("NEBIUS_API_KEY") == "nebius-from-file"


def test_load_env_does_not_override_nonempty(tmp_path: Path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=sk-from-file\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-shell")

    load_env_files()

    assert os.environ["OPENAI_API_KEY"] == "sk-from-shell"
