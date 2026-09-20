"""Export Pydantic models to JSON Schema files under schemas/."""

from __future__ import annotations

import json
from pathlib import Path

from sme_bench.models import AttemptResult, BenchmarkTask

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    out = ROOT / "schemas"
    out.mkdir(exist_ok=True)
    (out / "task.schema.json").write_text(
        json.dumps(BenchmarkTask.model_json_schema(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out / "result.schema.json").write_text(
        json.dumps(AttemptResult.model_json_schema(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {out / 'task.schema.json'} and {out / 'result.schema.json'}")


if __name__ == "__main__":
    main()
