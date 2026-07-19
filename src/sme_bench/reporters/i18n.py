"""Report localisation (German / English)."""

from __future__ import annotations

from typing import Literal

Lang = Literal["de", "en"]
REPORT_LANGS: tuple[Lang, ...] = ("de", "en")

TASK_TYPE_LABELS: dict[Lang, dict[str, str]] = {
    "de": {
        "invoice_extraction": "Rechnungsdaten extrahieren",
        "order_extraction": "Bestellung erfassen",
        "support_routing": "Support-Ticket klassifizieren",
        "missing_information": "Fehlende Angaben erkennen",
        "customer_reply": "Kundenantwort formulieren",
        "offer_comparison": "Angebote vergleichen",
        "product_normalization": "Produktattribute normalisieren",
        "csv_analysis": "CSV-Daten auswerten",
        "meeting_actions": "Meeting-Aufgaben extrahieren",
        "grounded_qa": "Richtlinienfrage beantworten (mit Quellen)",
        "pii_detection": "Personenbezogene Daten erkennen",
        "prompt_injection": "Prompt-Injection ignorieren",
        "process_readiness": "Prozessbereitschaft prüfen",
        "process_next_step": "Nächsten Prozessschritt wählen",
        "payment_integrity": "Zahlungsintegrität prüfen",
    },
    "en": {
        "invoice_extraction": "Extract invoice data",
        "order_extraction": "Capture order",
        "support_routing": "Classify support ticket",
        "missing_information": "Detect missing information",
        "customer_reply": "Draft customer reply",
        "offer_comparison": "Compare offers",
        "product_normalization": "Normalise product attributes",
        "csv_analysis": "Analyse CSV data",
        "meeting_actions": "Extract meeting actions",
        "grounded_qa": "Answer from policy (with citations)",
        "pii_detection": "Detect personal data",
        "prompt_injection": "Ignore prompt injection",
        "process_readiness": "Check process readiness",
        "process_next_step": "Choose next process step",
        "payment_integrity": "Check payment integrity",
    },
}

RISK_LABELS: dict[Lang, dict[str, str]] = {
    "de": {
        "low": "Niedrig — fachlicher Fehler, keine unmittelbare Schadenswirkung",
        "medium": "Mittel — Prozessfehler mit Geschäftsauswirkung",
        "high": "Hoch — Halluzination oder falsche Zusage möglich",
        "critical": "Kritisch — Datenschutz/Sicherheit; Scorer-Fehler → Score 0",
    },
    "en": {
        "low": "Low — factual error, no immediate harm",
        "medium": "Medium — process error with business impact",
        "high": "High — hallucination or false commitment possible",
        "critical": "Critical — privacy/security; scorer failure → score 0",
    },
}

VARIANT_LABELS: dict[Lang, dict[str, str]] = {
    "de": {
        "001": "Basis — klares Format",
        "002": "Rauschen — Forwards, Chats, Alternativformate",
        "003": "Härtefall — Sonderregeln, Randbedingungen",
    },
    "en": {
        "001": "Baseline — clear format",
        "002": "Noise — forwards, chats, alternate formats",
        "003": "Hard case — special rules, edge conditions",
    },
}

SUMMARY: dict[Lang, dict[str, str]] = {
    "de": {
        "title": "SME-Bench Report — {model}",
        "suite": "Suite: `{suite_id}` {suite_version}",
        "core_score": "SME Core Score: {score:.1f} / 100",
        "rank_score": "**SME Rank Score: {score:.1f} / 100**",
        "attempt_pass": "Attempt Pass Rate: {value}",
        "attempt_partial": "Attempt Partial Rate: {value}",
        "reliable_pass": "Reliable Pass Rate: {value}",
        "critical_rate": "Critical Failure Rate: {value}",
        "infra_rate": "Infrastructure Error Rate: {value}",
        "tps": "Output tokens/s (Ø): {value} tok/s",
        "by_language": "## Nach Sprache",
        "lang_header": "| Sprache | Pass | Reliable | Score | Critical | p95 Latenz | Tok/s |",
        "by_category": "## Nach Kategorie",
        "cat_header": "| Kategorie | Pass | Reliable | Score | Critical |",
        "parity": "## Sprachparität",
        "parity_pass": "- EN−DE Pass-Differenz: {value}",
        "parity_score": "- EN−DE Score-Differenz: {value}",
        "parity_pair": "- Pair-Konsistenz: {value}",
    },
    "en": {
        "title": "SME-Bench Report — {model}",
        "suite": "Suite: `{suite_id}` {suite_version}",
        "core_score": "SME Core Score: {score:.1f} / 100",
        "rank_score": "**SME Rank Score: {score:.1f} / 100**",
        "attempt_pass": "Attempt Pass Rate: {value}",
        "attempt_partial": "Attempt Partial Rate: {value}",
        "reliable_pass": "Reliable Pass Rate: {value}",
        "critical_rate": "Critical Failure Rate: {value}",
        "infra_rate": "Infrastructure Error Rate: {value}",
        "tps": "Output tokens/s (avg): {value} tok/s",
        "by_language": "## By language",
        "lang_header": "| Language | Pass | Reliable | Score | Critical | p95 latency | Tok/s |",
        "by_category": "## By category",
        "cat_header": "| Category | Pass | Reliable | Score | Critical |",
        "parity": "## Language parity",
        "parity_pass": "- EN−DE pass gap: {value}",
        "parity_score": "- EN−DE score gap: {value}",
        "parity_pair": "- Pair consistency: {value}",
    },
}

FAILURES: dict[Lang, dict[str, str]] = {
    "de": {
        "title": "# Fehlerreport — {model}",
        "suite": "- Suite: `{suite_id}` {suite_version}",
        "full_pass": "- Fälle voll bestanden (≥85 %): **{n}/{total}**",
        "partial": "- Fälle teilweise (65–84 %): **{n}/{total}**",
        "hard_fail": "- Fälle hart fehlgeschlagen (<65 %): **{n}/{total}**",
        "critical_attempts": "- Kritische Fehler (Versuche): **{n}**",
        "intro": (
            "> Pro Fall: **Aufgabe**, **erwartetes Ergebnis**, **Modellausgabe** und Scorer-Details.\n"
            "> Bestanden ≥ Pass-Schwelle · Teilweise = 65–84 % · Fail < 65 % · Kritisch = kritischer Scorer."
        ),
        "see_also": (
            "Siehe auch `success.{lang}.md` für bestandene Fälle und `CASES.md` für Fallbeschreibungen."
        ),
        "all_passed": "Alle Fälle in allen Wiederholungen vollständig bestanden.",
        "section_critical": "## Kritische Fehler",
        "section_fail": "## Fehlgeschlagen",
        "section_partial": "## Teilweise bestanden",
        "partial_blurb": "Größtenteils korrekt, aber unter der Pass-Schwelle.",
        "status_infra": "INFRA",
        "status_critical": "KRITISCH",
        "status_pass": "PASS",
        "status_partial": "TEILWEISE",
        "status_fail": "FAIL",
        "ko": " **kritisch**",
        "infra_line": "- **Infrastruktur:** {error}",
        "required_contains": "Pflichtinhalte (contains): {terms}",
        "forbidden": "Verboten: {terms}",
        "no_expected": "—(kein strukturiertes `expected`)",
        "task_missing": (
            "**Aufgabe:** _(Suite-Definition nicht geladen — `report` mit Suite-Pfad ausführen)_"
        ),
        "expected_label": "**Erwartetes Ergebnis:**",
        "task_system": "**Aufgabe (System):**",
        "task_user": "**Aufgabe (User):**",
        "model_output": "**Modellausgabe:**",
        "empty_infra": "(keine Ausgabe / Infrastrukturfehler)",
        "empty_output": "(leere Modellausgabe)",
        "outcome_pass": "bestanden",
        "outcome_partial": "teilweise",
        "outcome_fail": "fehlgeschlagen",
        "outcome_critical": "kritisch",
        "result_line": (
            "- **Ergebnis:** {passed}/{attempts} pass · {partial}/{attempts} teilweise · "
            "Mittel-Score {mean:.2f} · **{outcome}**"
        ),
        "meta_line": "- **Typ:** {task_type} · **Sprache:** {language} · **Risiko:** {risk}",
        "critical_what": "- **Was kritisch ist:**",
        "repeat": "**Wiederholung {n}** — {status} (Score {score:.2f})",
        "below_partial": "- Gewichteter Score {score:.2f} unter Teilweise-Schwelle",
        "expected_heading": "**Erwartetes Ergebnis:**",
    },
    "en": {
        "title": "# Failure report — {model}",
        "suite": "- Suite: `{suite_id}` {suite_version}",
        "full_pass": "- Cases fully passed (≥85 %): **{n}/{total}**",
        "partial": "- Cases partially passed (65–84 %): **{n}/{total}**",
        "hard_fail": "- Cases hard-failed (<65 %): **{n}/{total}**",
        "critical_attempts": "- Critical failures (attempts): **{n}**",
        "intro": (
            "> Per case: **task**, **expected result**, **model output**, and scorer details.\n"
            "> Passed ≥ pass threshold · Partial = 65–84 % · Fail < 65 % · Critical = critical scorer."
        ),
        "see_also": (
            "See also `success.{lang}.md` for passed cases and `CASES.md` for case descriptions."
        ),
        "all_passed": "All cases fully passed in every repeat.",
        "section_critical": "## Critical failures",
        "section_fail": "## Failed",
        "section_partial": "## Partially passed",
        "partial_blurb": "Mostly correct, but below the pass threshold.",
        "status_infra": "INFRA",
        "status_critical": "CRITICAL",
        "status_pass": "PASS",
        "status_partial": "PARTIAL",
        "status_fail": "FAIL",
        "ko": " **critical**",
        "infra_line": "- **Infrastructure:** {error}",
        "required_contains": "Required content (contains): {terms}",
        "forbidden": "Forbidden: {terms}",
        "no_expected": "—(no structured `expected`)",
        "task_missing": (
            "**Task:** _(suite definition not loaded — run `report` with suite path)_"
        ),
        "expected_label": "**Expected result:**",
        "task_system": "**Task (system):**",
        "task_user": "**Task (user):**",
        "model_output": "**Model output:**",
        "empty_infra": "(no output / infrastructure error)",
        "empty_output": "(empty model output)",
        "outcome_pass": "passed",
        "outcome_partial": "partial",
        "outcome_fail": "failed",
        "outcome_critical": "critical",
        "result_line": (
            "- **Result:** {passed}/{attempts} pass · {partial}/{attempts} partial · "
            "mean score {mean:.2f} · **{outcome}**"
        ),
        "meta_line": "- **Type:** {task_type} · **Language:** {language} · **Risk:** {risk}",
        "critical_what": "- **What is critical:**",
        "repeat": "**Repeat {n}** — {status} (score {score:.2f})",
        "below_partial": "- Weighted score {score:.2f} below partial threshold",
        "expected_heading": "**Expected result:**",
    },
}

SUCCESS: dict[Lang, dict[str, str]] = {
    "de": {
        "title": "# Erfolgsreport — {model}",
        "suite": "- Suite: `{suite_id}` {suite_version}",
        "full_pass": (
            "- Fälle voll bestanden (≥85 % in allen Wiederholungen): **{n}/{total}**"
        ),
        "intro": (
            "> Pro Fall: **Aufgabe**, **erwartetes Ergebnis** und **Modellausgabe** "
            "(wie in `failures.{lang}.md`)."
        ),
        "none": "Keine Fälle vollständig in allen Wiederholungen bestanden.",
        "see_failures": "Siehe `failures.{lang}.md` für Fehler- und Teilweise-Fälle.",
        "section": "## Bestanden",
    },
    "en": {
        "title": "# Success report — {model}",
        "suite": "- Suite: `{suite_id}` {suite_version}",
        "full_pass": (
            "- Cases fully passed (≥85 % in every repeat): **{n}/{total}**"
        ),
        "intro": (
            "> Per case: **task**, **expected result**, and **model output** "
            "(same layout as `failures.{lang}.md`)."
        ),
        "none": "No cases fully passed in every repeat.",
        "see_failures": "See `failures.{lang}.md` for failed and partial cases.",
        "section": "## Passed",
    },
}


def report_path(stem: str, lang: Lang, *, directory: str | None = None) -> str:
    """Return ``summary.de.md``-style filename (optionally under a directory)."""
    name = f"{stem}.{lang}.md"
    return f"{directory.rstrip('/')}/{name}" if directory else name
