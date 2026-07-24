"""Central validation for scorer parameter specs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from sme_bench.models import ScorerSpec

_BOOL_PARAMS = frozenset(
    {
        "case_insensitive",
        "critical",
        "coerce_scalar",
        "ignore_order",
        "require_unique",
        "require_nonempty",
        "exact_set",
        "ignore_negated",
        "forbid_bullet_only",
        "word_boundaries",
    }
)
_INT_PARAMS = frozenset({"min_count", "max_count", "min_words", "min_sentences"})
_FLOAT_PARAMS = frozenset(
    {"tolerance", "relative_tolerance", "absolute_tolerance", "adjacent_credit"}
)
_STR_PARAMS = frozenset(
    {
        "field",
        "mode",
        "match",
        "schema",
        "expected",
        "normalize",
    }
)

_SCORER_PARAMS: dict[str, set[str]] = {
    "contains": {
        "terms",
        "required",
        "mode",
        "case_insensitive",
        "field",
        "fields",
        "word_boundaries",
        "min_count",
        "max_count",
    },
    "citations": {
        "field",
        "allowed",
        "require_nonempty",
        "exact_set",
        "require_unique",
        "max_count",
        "expected",
    },
    "set_equality": {
        "field",
        "ignore_order",
        "coerce_scalar",
        "match",
        "keys",
        "aliases",
        "key_aliases",
        "key_match",
    },
    "json_fields": {
        "fields",
        "case_insensitive",
        "match",
        "normalize",
        "patterns",
        "field_normalize",
        "field_aliases",
    },
    "text_structure": {
        "field",
        "min_words",
        "min_sentences",
        "forbid_bullet_only",
    },
    "exact_match": {"expected", "case_insensitive"},
    "regex": {"pattern", "patterns", "case_insensitive"},
    "numeric": {
        "field",
        "fields",
        "expected",
        "tolerance",
        "relative_tolerance",
        "absolute_tolerance",
    },
    "json_schema": {"schema", "_suite_dir", "coerce_scalar_fields"},
    "forbidden_terms": {
        "terms",
        "ignore_negated",
        "exclude_fields",
        "fields",
        "mode",
        "case_insensitive",
    },
    "classification": {
        "field",
        "expected",
        "labels",
        "allowed",
        "scale",
        "adjacent_credit",
        "case_insensitive",
    },
}

_JSON_NORMALIZE_MODES = frozenset(
    {"iban", "whitespace", "text", "percent", "range", "terminal_punctuation"}
)


@dataclass
class ScorerValidationIssue:
    path: str
    message: str
    severity: str = "warning"


def validate_scorer_spec(
    spec: ScorerSpec,
    *,
    path: str,
    strict: bool = False,
) -> list[ScorerValidationIssue]:
    """Validate scorer params; warnings by default, errors when strict=True."""
    issues: list[ScorerValidationIssue] = []
    known = _SCORER_PARAMS.get(spec.type)
    if known is None:
        return issues

    unknown = set(spec.params) - known - {"_suite_dir"}
    if unknown:
        issues.append(
            ScorerValidationIssue(
                path=path,
                message=f"Unknown params for scorer '{spec.type}': {sorted(unknown)}",
                severity="error" if strict else "warning",
            )
        )

    list_params: dict[str, tuple[str, ...]] = {
        "citations": ("allowed", "expected"),
        "set_equality": ("keys",),
        "json_fields": ("fields",),
        "numeric": ("fields",),
        "classification": ("labels", "allowed", "scale"),
        "forbidden_terms": ("terms", "fields", "exclude_fields"),
        "regex": ("patterns",),
        "json_schema": ("coerce_scalar_fields",),
    }
    dict_params: dict[str, tuple[str, ...]] = {
        "set_equality": ("aliases", "key_aliases", "key_match"),
        "json_fields": ("patterns", "field_normalize", "field_aliases"),
    }
    for key in list_params.get(spec.type, ()):
        value = spec.params.get(key)
        if value is not None and not isinstance(value, list):
            issues.append(_type_issue(path, spec.type, key, "list", value, strict))
    for key in dict_params.get(spec.type, ()):
        value = spec.params.get(key)
        if value is not None and not isinstance(value, dict):
            issues.append(_type_issue(path, spec.type, key, "object", value, strict))

    string_list_params = {
        "citations": ("allowed", "expected"),
        "set_equality": ("keys",),
        "json_fields": ("fields",),
        "numeric": ("fields",),
        "classification": ("labels", "allowed", "scale"),
        "forbidden_terms": ("fields", "exclude_fields"),
        "regex": ("patterns",),
        "json_schema": ("coerce_scalar_fields",),
    }
    for key in string_list_params.get(spec.type, ()):
        value = spec.params.get(key)
        if isinstance(value, list) and any(not isinstance(item, str) for item in value):
            issues.append(
                ScorerValidationIssue(
                    path=path,
                    message=f"scorer '{spec.type}' param '{key}' must contain only strings",
                    severity="error" if strict else "warning",
                )
            )

    for key, value in spec.params.items():
        if key in _BOOL_PARAMS and not isinstance(value, bool):
            issues.append(_type_issue(path, spec.type, key, "bool", value, strict))
        elif key in _INT_PARAMS and not isinstance(value, int):
            issues.append(_type_issue(path, spec.type, key, "int", value, strict))
        elif key in _FLOAT_PARAMS and not isinstance(value, (int, float)):
            issues.append(_type_issue(path, spec.type, key, "number", value, strict))
        elif (
            key in _STR_PARAMS
            and value is not None
            and not isinstance(value, str)
            and not (
                spec.type in {"classification", "numeric", "exact_match"} and key == "expected"
            )
        ):
            issues.append(_type_issue(path, spec.type, key, "str", value, strict))

    if spec.type == "contains":
        mode = spec.params.get("mode", "all")
        if mode not in {"all", "any"}:
            issues.append(
                ScorerValidationIssue(
                    path=path,
                    message=f"contains.mode must be 'all' or 'any', got {mode!r}",
                    severity="error" if strict else "warning",
                )
            )
    if spec.type == "forbidden_terms":
        mode = spec.params.get("mode", "terms")
        if mode not in {"terms", "claims"}:
            issues.append(
                ScorerValidationIssue(
                    path=path,
                    message=f"forbidden_terms.mode must be 'terms' or 'claims', got {mode!r}",
                    severity="error" if strict else "warning",
                )
            )
    if spec.type == "json_fields":
        normalize = spec.params.get("normalize")
        if normalize is not None and normalize not in _JSON_NORMALIZE_MODES:
            issues.append(
                ScorerValidationIssue(
                    path=path,
                    message=(
                        "json_fields.normalize must be one of "
                        f"{sorted(_JSON_NORMALIZE_MODES)}, got {normalize!r}"
                    ),
                    severity="error" if strict else "warning",
                )
            )
        field_normalize = spec.params.get("field_normalize") or {}
        if isinstance(field_normalize, dict):
            for field, mode in field_normalize.items():
                if mode not in _JSON_NORMALIZE_MODES:
                    issues.append(
                        ScorerValidationIssue(
                            path=path,
                            message=(
                                f"json_fields.field_normalize[{field!r}] must be one of "
                                f"{sorted(_JSON_NORMALIZE_MODES)}, got {mode!r}"
                            ),
                            severity="error" if strict else "warning",
                        )
                    )
        patterns = spec.params.get("patterns")
        if isinstance(patterns, dict):
            for field, pattern in patterns.items():
                if not isinstance(field, str) or not isinstance(pattern, str):
                    issues.append(
                        ScorerValidationIssue(
                            path=path,
                            message="json_fields.patterns must map string fields to regex strings",
                            severity="error" if strict else "warning",
                        )
                    )
                    continue
                try:
                    re.compile(pattern)
                except re.error as exc:
                    issues.append(
                        ScorerValidationIssue(
                            path=path,
                            message=f"Invalid regex for json_fields.patterns[{field!r}]: {exc}",
                            severity="error" if strict else "warning",
                        )
                    )
        field_aliases = spec.params.get("field_aliases")
        if isinstance(field_aliases, dict):
            for field, aliases in field_aliases.items():
                if (
                    not isinstance(field, str)
                    or not isinstance(aliases, list)
                    or any(not isinstance(alias, str) for alias in aliases)
                ):
                    issues.append(
                        ScorerValidationIssue(
                            path=path,
                            message=(
                                "json_fields.field_aliases must map string fields "
                                "to lists of strings"
                            ),
                            severity="error" if strict else "warning",
                        )
                    )
    if spec.type == "set_equality":
        key_aliases = spec.params.get("key_aliases")
        if key_aliases is not None and not isinstance(key_aliases, dict):
            issues.append(
                ScorerValidationIssue(
                    path=path,
                    message="set_equality.key_aliases must be an object of field→alias maps",
                    severity="error" if strict else "warning",
                )
            )
    if spec.type == "classification":
        scale = spec.params.get("scale")
        if scale is not None and not isinstance(scale, list):
            issues.append(
                ScorerValidationIssue(
                    path=path,
                    message="classification.scale must be a list",
                    severity="error" if strict else "warning",
                )
            )
        credit = spec.params.get("adjacent_credit")
        if credit is not None and (
            not isinstance(credit, (int, float)) or not (0.0 <= float(credit) <= 1.0)
        ):
            issues.append(
                ScorerValidationIssue(
                    path=path,
                    message="classification.adjacent_credit must be a number in [0, 1]",
                    severity="error" if strict else "warning",
                )
            )
    if spec.type == "numeric":
        for key in ("tolerance", "relative_tolerance", "absolute_tolerance"):
            value = spec.params.get(key)
            if value is not None and not isinstance(value, (int, float)):
                issues.append(_type_issue(path, spec.type, key, "number", value, strict))
        fields = spec.params.get("fields")
        if fields is not None and not isinstance(fields, list):
            issues.append(
                ScorerValidationIssue(
                    path=path,
                    message="numeric.fields must be a list",
                    severity="error" if strict else "warning",
                )
            )
    if spec.type == "regex":
        raw_patterns: list[Any] = []
        pattern = spec.params.get("pattern")
        if pattern is not None:
            raw_patterns.append(pattern)
        patterns = spec.params.get("patterns")
        if isinstance(patterns, list):
            raw_patterns.extend(patterns)
        for pattern_value in raw_patterns:
            if not isinstance(pattern_value, str):
                issues.append(
                    _type_issue(
                        path,
                        spec.type,
                        "pattern",
                        "str",
                        pattern_value,
                        strict,
                    )
                )
                continue
            try:
                re.compile(pattern_value)
            except re.error as exc:
                issues.append(
                    ScorerValidationIssue(
                        path=path,
                        message=f"Invalid regex for regex scorer: {exc}",
                        severity="error" if strict else "warning",
                    )
                )
    return issues


def _type_issue(
    path: str,
    scorer: str,
    key: str,
    expected: str,
    value: Any,
    strict: bool,
) -> ScorerValidationIssue:
    return ScorerValidationIssue(
        path=path,
        message=(
            f"scorer '{scorer}' param '{key}' should be {expected}, got {type(value).__name__}"
        ),
        severity="error" if strict else "warning",
    )
