"""JSON Schema scorer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from sme_bench.models import BenchmarkTask, ScoreResult, ScorerSpec
from sme_bench.scorers.base import register
from sme_bench.utils import extract_json_payload


@register
class JsonSchemaScorer:
    name = "json_schema"

    def score(
        self,
        *,
        task: BenchmarkTask,
        output_text: str,
        parsed_output: Any | None,
        spec: ScorerSpec,
    ) -> ScoreResult:
        schema_ref = spec.params.get("schema")
        if not schema_ref:
            return ScoreResult(
                scorer=self.name,
                score=0.0,
                passed=False,
                message="Missing schema parameter",
            )

        data = parsed_output
        if data is None:
            try:
                data = extract_json_payload(output_text)
            except (ValueError, json.JSONDecodeError) as exc:
                return ScoreResult(
                    scorer=self.name,
                    score=0.0,
                    passed=False,
                    critical_failure=bool(spec.critical),
                    message=f"Invalid JSON: {exc}",
                )

        coerce_scalar_fields = list(spec.params.get("coerce_scalar_fields") or [])
        if isinstance(data, dict):
            for field_name in coerce_scalar_fields:
                value = data.get(field_name)
                if value is not None and not isinstance(value, list):
                    data = {**data, field_name: [value]}

        # Schema path is relative to suite; caller may pass absolute via _suite_dir
        suite_dir = spec.params.get("_suite_dir")
        schema_path = Path(schema_ref)
        if not schema_path.is_absolute():
            if suite_dir:
                schema_path = Path(suite_dir) / schema_ref
            else:
                # Fall back: schema embedded inline as dict
                schema_obj = spec.params.get("schema_object")
                if schema_obj is None:
                    return ScoreResult(
                        scorer=self.name,
                        score=0.0,
                        passed=False,
                        message=f"Cannot resolve schema path: {schema_ref}",
                    )
                schema = schema_obj
                schema_path = None  # type: ignore[assignment]

        if schema_path is not None:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))

        validator = Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
        if errors:
            messages = [e.message for e in errors[:5]]
            return ScoreResult(
                scorer=self.name,
                score=0.0,
                passed=False,
                critical_failure=bool(spec.critical),
                message="; ".join(messages),
                details={"error_count": len(errors)},
            )
        return ScoreResult(scorer=self.name, score=1.0, passed=True)
