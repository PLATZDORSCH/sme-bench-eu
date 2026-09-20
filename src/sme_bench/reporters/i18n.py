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
        "payment_reconciliation": "Zahlungen abstimmen",
        "stock_lookup": "Bestand abfragen",
        "appointment_booking": "Termin buchen",
        "crm_update": "CRM aktualisieren",
        "ticket_create": "Ticket anlegen",
        "refund_policy": "Erstattung nach Policy",
        "no_tool_needed": "Kein Tool nötig",
        "tool_hallucination": "Halluziniertes Tool ablehnen",
        "tool_result_answer": "Antwort aus Tool-Ergebnis",
        "order_revision": "Bestellung revidieren",
        "clarification": "Rückfrage stellen",
        "escalation": "Eskalieren",
        "contradiction": "Widerspruch auflösen",
        "callback_followup": "Rückruf nachfassen",
        "multi_issue": "Mehrere Anliegen trennen",
        "complaint_tone": "Beschwerde erkennen",
        "contract_qa": "Vertrag befragen",
        "thread_qa": "Mail-Thread befragen",
        "tool_chain": "Tool-Kette",
        "error_recovery": "Fehlerbehandlung",
        "exactly_once": "Genau-einmal-Buchung",
        "authorize_write": "Schreiben nach Freigabe",
        "pagination": "Pagination",
        "toolset_crowded": "Tool-Auswahl im großen Namespace",
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
        "payment_reconciliation": "Reconcile payments",
        "stock_lookup": "Look up stock",
        "appointment_booking": "Book appointment",
        "crm_update": "Update CRM",
        "ticket_create": "Create ticket",
        "refund_policy": "Refund under policy",
        "no_tool_needed": "No tool needed",
        "tool_hallucination": "Reject hallucinated tool",
        "tool_result_answer": "Answer from tool result",
        "order_revision": "Revise order",
        "clarification": "Ask a clarifying question",
        "escalation": "Escalate",
        "contradiction": "Resolve contradiction",
        "callback_followup": "Follow up on callback",
        "multi_issue": "Split multiple issues",
        "complaint_tone": "Detect complaint tone",
        "contract_qa": "Query a contract",
        "thread_qa": "Query a mail thread",
        "tool_chain": "Tool chain",
        "error_recovery": "Error recovery",
        "exactly_once": "Exactly-once booking",
        "authorize_write": "Write after authorization",
        "pagination": "Pagination",
        "toolset_crowded": "Tool selection in a large namespace",
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
        "rank_score": "**SME Readiness Score: {score:.1f} / 100**",
        "readiness_tier": "Eignungsstufe: {tier}",
        "readiness_reason": "Gründe: {reasons}",
        "tier_ready": "einsatzbereit",
        "tier_supervised": "mit Aufsicht",
        "tier_not_recommended": "nicht empfohlen",
        "tier_inconclusive": "nicht aussagekräftig",
        "reason_critical_failures": "kritische Fehler",
        "reason_language_break": "Sprachbruch",
        "reason_low_completion": "Completion Rate unter 95 %",
        "reason_score_ready": "Score ≥ 95",
        "reason_score_supervised": "Score 85–95",
        "reason_score_not_recommended": "Score unter 85",
        "attempt_pass": "Attempt Pass Rate: {value}",
        "attempt_partial": "Attempt Partial Rate: {value}",
        "reliable_pass": "Reliable Pass Rate: {value}",
        "mostly_pass": "Überwiegend erfolgreich (die meisten Repeats, aber nicht alle): {value}",
        "unreliable_pass": "Unzuverlässig erfolgreich (einige, nicht alle Repeats): {value}",
        "critical_rate": "Critical Failure Rate: {value}",
        "infra_rate": "Infrastructure Error Rate: {value}",
        "completion_rate": "Completion Rate (bewertet): {value}",
        "graded_pass": "Attempt Pass Rate (bewertet): {value}",
        "completion_warn": "Warnung: Completion Rate unter 95 % — Runs sind nicht voll vergleichbar.",
        "toolset_delta": "## Toolset-Delta (crowded − small)",
        "toolset_header": "| Paar | Sprache | Small | Crowded | Delta |",
        "toolset_mean": "- Mittleres Delta: {value}",
        "language_rate": "Sprachtreue (Antwort in Fallsprache): {value}",
        "tps": "Output tokens/s (Ø): {value} tok/s",
        "format_only": "Nur-Format-Fehler: {value}",
        "ttft_cold": "TTFT kalt (repeat 0) p50: {value} s",
        "ttfa": "TTFA (erster Antwort-Token) p50: {value} s",
        "baseline": "Latenz-Baseline (Warmup): {value} s",
        "runtime": "Runtime: Engine {engine}, Hardware {hardware}, Quantisierung {quantization}",
        "by_prompt": "## Nach Prompt-Größe",
        "prompt_header": "| Bucket | Pass | Reliable | Score | Tok/s |",
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
        "rank_score": "**SME Readiness Score: {score:.1f} / 100**",
        "readiness_tier": "Readiness tier: {tier}",
        "readiness_reason": "Reasons: {reasons}",
        "tier_ready": "ready",
        "tier_supervised": "supervised",
        "tier_not_recommended": "not recommended",
        "tier_inconclusive": "inconclusive",
        "reason_critical_failures": "critical failures",
        "reason_language_break": "language break",
        "reason_low_completion": "completion rate below 95%",
        "reason_score_ready": "score ≥ 95",
        "reason_score_supervised": "score 85–95",
        "reason_score_not_recommended": "score below 85",
        "attempt_pass": "Attempt Pass Rate: {value}",
        "attempt_partial": "Attempt Partial Rate: {value}",
        "reliable_pass": "Reliable Pass Rate: {value}",
        "mostly_pass": "Mostly successful (most repeats, but not all): {value}",
        "unreliable_pass": "Unreliably successful (some but not all repeats): {value}",
        "critical_rate": "Critical Failure Rate: {value}",
        "infra_rate": "Infrastructure Error Rate: {value}",
        "completion_rate": "Completion rate (graded): {value}",
        "graded_pass": "Attempt pass rate (graded): {value}",
        "completion_warn": "Warning: completion rate below 95% — runs are not fully comparable.",
        "toolset_delta": "## Toolset delta (crowded − small)",
        "toolset_header": "| Pair | Language | Small | Crowded | Delta |",
        "toolset_mean": "- Mean delta: {value}",
        "language_rate": "Language compliance (answer in case language): {value}",
        "tps": "Output tokens/s (avg): {value} tok/s",
        "format_only": "Format-only failures: {value}",
        "ttft_cold": "Cold TTFT (repeat 0) p50: {value} s",
        "ttfa": "TTFA (first answer token) p50: {value} s",
        "baseline": "Latency baseline (warmup): {value} s",
        "runtime": "Runtime: engine {engine}, hardware {hardware}, quantization {quantization}",
        "by_prompt": "## By prompt size",
        "prompt_header": "| Bucket | Pass | Reliable | Score | Tok/s |",
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
        "mostly": "- Fälle überwiegend erfolgreich (die meisten Repeats, aber nicht alle): **{n}/{total}**",
        "partial": "- Fälle teilweise (65–84 %): **{n}/{total}**",
        "unreliable": "- Fälle unzuverlässig (einige, nicht alle Repeats): **{n}/{total}**",
        "hard_fail": "- Fälle hart fehlgeschlagen (0 Repeats bestanden): **{n}/{total}**",
        "critical_attempts": "- Kritische Fehler (Versuche): **{n}**",
        "intro": (
            "> Pro Fall: **Aufgabe**, **erwartetes Ergebnis**, **Modellausgabe** und Scorer-Details.\n"
            "> Bestanden ≥ Pass-Schwelle · Teilweise = 65–84 % in allen Repeats · "
            "Überwiegend = die meisten Repeats, aber nicht alle · Unzuverlässig = einige, nicht alle Repeats · "
            "Fail = kein Pass · Kritisch = kritischer Scorer."
        ),
        "see_also": (
            "Siehe auch `success.{lang}.md` für bestandene Fälle und die Suite-Kataloge "
            "unter `suites/*/CASES.md` für Fallbeschreibungen."
        ),
        "all_passed": "Alle Fälle in allen Wiederholungen vollständig bestanden.",
        "section_critical": "## Kritische Fehler",
        "section_fail": "## Fehlgeschlagen",
        "section_mostly": "## Überwiegend erfolgreich",
        "mostly_blurb": "Die meisten Repeats vollständig bestanden, aber nicht alle.",
        "section_unreliable": "## Unzuverlässig",
        "unreliable_blurb": (
            "Mindestens ein Repeat vollständig bestanden, aber nicht genug für zuverlässig."
        ),
        "section_partial": "## Teilweise bestanden",
        "partial_blurb": "Größtenteils korrekt, aber unter der Pass-Schwelle.",
        "status_infra": "INFRA",
        "status_excluded": "AUSGESCHLOSSEN",
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
        "empty_output_token_limit": "(keine finale Ausgabe – Reasoning/Tokenlimit erreicht)",
        "outcome_pass": "bestanden",
        "outcome_mostly": "überwiegend erfolgreich",
        "outcome_partial": "teilweise",
        "outcome_unreliable": "unzuverlässig",
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
        "mostly": "- Cases mostly successful (most repeats, but not all): **{n}/{total}**",
        "partial": "- Cases partially passed (65–84 %): **{n}/{total}**",
        "unreliable": "- Cases unreliable (some but not all repeats): **{n}/{total}**",
        "hard_fail": "- Cases hard-failed (0 repeats passed): **{n}/{total}**",
        "critical_attempts": "- Critical failures (attempts): **{n}**",
        "intro": (
            "> Per case: **task**, **expected result**, **model output**, and scorer details.\n"
            "> Passed ≥ pass threshold · Partial = 65–84 % in every repeat · "
            "Mostly successful = most repeats, but not all · Unreliable = some but not all repeats · "
            "Fail = no pass · Critical = critical scorer."
        ),
        "see_also": (
            "See also `success.{lang}.md` for passed cases and the suite catalogues "
            "under `suites/*/CASES.md` for case descriptions."
        ),
        "all_passed": "All cases fully passed in every repeat.",
        "section_critical": "## Critical failures",
        "section_fail": "## Failed",
        "section_mostly": "## Mostly successful",
        "mostly_blurb": "Most repeats fully passed, but not all.",
        "section_unreliable": "## Unreliable",
        "unreliable_blurb": (
            "At least one repeat fully passed, but not enough for a reliable pass."
        ),
        "section_partial": "## Partially passed",
        "partial_blurb": "Mostly correct, but below the pass threshold.",
        "status_infra": "INFRA",
        "status_excluded": "EXCLUDED",
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
        "empty_output_token_limit": "(no final output – reasoning/token limit reached)",
        "outcome_pass": "passed",
        "outcome_mostly": "mostly successful",
        "outcome_partial": "partial",
        "outcome_unreliable": "unreliable",
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
        "full_pass": ("- Fälle voll bestanden (≥85 % in allen Wiederholungen): **{n}/{total}**"),
        "intro": (
            "> Pro Fall: **Aufgabe**, **erwartetes Ergebnis** und **Modellausgabe** "
            "(wie in `failures.{lang}.md`)."
        ),
        "none": "Keine Fälle vollständig in allen Wiederholungen bestanden.",
        "see_failures": (
            "Siehe `failures.{lang}.md` für Fehler-, Unzuverlässig- und Teilweise-Fälle."
        ),
        "section": "## Bestanden",
    },
    "en": {
        "title": "# Success report — {model}",
        "suite": "- Suite: `{suite_id}` {suite_version}",
        "full_pass": ("- Cases fully passed (≥85 % in every repeat): **{n}/{total}**"),
        "intro": (
            "> Per case: **task**, **expected result**, and **model output** "
            "(same layout as `failures.{lang}.md`)."
        ),
        "none": "No cases fully passed in every repeat.",
        "see_failures": ("See `failures.{lang}.md` for failed, unreliable, and partial cases."),
        "section": "## Passed",
    },
}


def report_path(stem: str, lang: Lang, *, directory: str | None = None) -> str:
    """Return ``summary.de.md``-style filename (optionally under a directory)."""
    name = f"{stem}.{lang}.md"
    return f"{directory.rstrip('/')}/{name}" if directory else name
