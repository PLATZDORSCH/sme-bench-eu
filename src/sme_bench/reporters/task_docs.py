"""Human-readable documentation helpers for benchmark tasks."""

from __future__ import annotations

from typing import Any

from sme_bench.models import BenchmarkTask, ScorerSpec
from sme_bench.reporters.i18n import (
    RISK_LABELS,
    TASK_TYPE_LABELS,
    VARIANT_LABELS,
    Lang,
)


def task_variant(task_id: str) -> str:
    suffix = task_id.rsplit("-", 1)[-1]
    return suffix if suffix.isdigit() and len(suffix) == 3 else "?"


def system_prompt_summary(task: BenchmarkTask, *, max_len: int = 200) -> str:
    for msg in task.messages:
        if msg.role == "system" and msg.content:
            text = " ".join(msg.content.split())
            if len(text) > max_len:
                return text[: max_len - 1] + "…"
            return text
    return "—"


def critical_checks(task: BenchmarkTask, *, lang: Lang = "de") -> list[str]:
    checks: list[str] = []
    ko = "K.-o." if lang == "de" else "K.O."
    forbidden = "Verboten" if lang == "de" else "Forbidden"
    for spec in task.scorers:
        if spec.type == "forbidden_terms":
            terms = spec.params.get("terms") or []
            if terms:
                label = ko if spec.critical else forbidden
                checks.append(f"{label}: {', '.join(str(t) for t in terms)}")
        elif spec.critical:
            detail = _scorer_detail(spec, lang=lang)
            checks.append(f"{ko}: `{spec.type}`{detail}")
    return checks


def _scorer_detail(spec: ScorerSpec, *, lang: Lang = "de") -> str:
    if spec.type == "set_equality":
        field = spec.params.get("field")
        if not field:
            return ""
        return f" (Feld `{field}`)" if lang == "de" else f" (field `{field}`)"
    if spec.type == "classification":
        expected = spec.params.get("expected")
        field = spec.params.get("field")
        if field and expected is not None:
            return f" (`{field}` = {expected})"
    if spec.type == "contains":
        terms = spec.params.get("terms") or []
        if terms:
            shown = ", ".join(str(t) for t in terms[:4])
            more = "…" if len(terms) > 4 else ""
            prefix = "Pflicht" if lang == "de" else "required"
            return f" ({prefix}: {shown}{more})"
    return ""


def scorer_summary(task: BenchmarkTask, *, lang: Lang = "de") -> list[str]:
    lines: list[str] = []
    crit_word = "kritisch" if lang == "de" else "critical"
    for spec in task.scorers:
        if spec.weight <= 0 and spec.type != "forbidden_terms":
            continue
        weight = f"{spec.weight:.0%}".replace("%", " %")
        crit = f", **{crit_word}**" if spec.critical else ""
        lines.append(f"- `{spec.type}` ({weight}{crit}){_scorer_detail(spec, lang=lang)}")
    return lines


def task_brief(task: BenchmarkTask, *, lang: Lang = "de") -> dict[str, Any]:
    variant = task_variant(task.id)
    labels = TASK_TYPE_LABELS[lang]
    risks = RISK_LABELS[lang]
    variants = VARIANT_LABELS[lang]
    return {
        "id": task.id,
        "title": task.title,
        "language": task.language,
        "pair_id": task.pair_id,
        "task_type": task.task_type,
        "task_type_label": labels.get(task.task_type, task.task_type),
        "category": task.category,
        "difficulty": task.difficulty,
        "risk": task.risk,
        "risk_label": risks.get(task.risk, task.risk),
        "variant": variant,
        "variant_label": variants.get(variant, variant),
        "pass_threshold": task.pass_threshold,
        "system_prompt": system_prompt_summary(task),
        "critical_checks": critical_checks(task, lang=lang),
        "scorers": scorer_summary(task, lang=lang),
        "has_critical_scorer": any(s.critical for s in task.scorers)
        or any(s.type == "forbidden_terms" for s in task.scorers),
    }
