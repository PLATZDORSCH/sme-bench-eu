#!/usr/bin/env python3
"""Migrate case YAMLs to hardened scorer definitions (idempotent).

Re-running this script replaces equivalent scorer specs in place instead of
appending duplicates. A second run must produce an empty diff.
"""

from __future__ import annotations

import argparse
import copy
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SUITES = ROOT / "suites"

VARIANT_ALIASES = {
    "none": ["keine", "Keine", "n/a", "N/A", "-", "standard", "Standard"],
    "white": ["weiß", "weiss"],
    "black": ["schwarz"],
    "clear": ["klar"],
    "L/red": ["L/rot"],
    "XL/black": ["XL/schwarz"],
    "95/black": ["95/schwarz"],
    # Logistics pick-list: prompt asks size/colour; fixture marks colour only.
    "mittel/braun": ["braun"],
    "medium/brown": ["brown"],
}

# Explicit task aliases for meeting actions (substring match on task only).
MEETING_TASK_ALIASES: dict[str, list[str]] = {
    "Angebot senden": [
        "Angebot schicken",
        "Angebot mailen",
        "Angebot an den Kunden schicken",
        "quote senden",
    ],
    "Lagerbestand aktualisieren": [
        "Lager aktualisieren",
        "Bestand aktualisieren",
    ],
    "send quote": ["send the quote", "email the quote", "email quote"],
    "update stock": ["update inventory", "update stock levels", "stock update"],
    "Zollpapiere": ["Zollpapiere vorbereiten", "Zolldokumente vorbereiten"],
    "customs papers": ["prepare customs papers", "prepare customs documents"],
    "Stückliste": ["Stückliste erstellen", "BOM erstellen"],
    "BOM": ["prepare BOM", "create BOM", "bill of materials"],
    "Zeichnung senden": [
        "Zeichnung schicken",
        "Zeichnung versenden",
        "Schicken Zeichnung zum Kunden",
        "Zeichnung zum Kunden schicken",
        "Zeichnung an den Kunden schicken",
    ],
    "send drawing": ["send the drawing", "email drawing", "email the drawing"],
    "Forecast Q3": [
        "Q3-Forecast",
        "Forecast Q3 liefern",
        "Q3-Forecast liefern",
        "liefert Forecast Q3",
    ],
    "Q3 forecast": [
        "Q3 forecast delivery",
        "deliver Q3 forecast",
        "delivers Q3 forecast",
        "Deliver Q3 forecast by 2026-06-20",
    ],
    "Doppelbuchung RE-900": [
        "Doppelbuchung RE-900 klären",
        "RE-900 Doppelbuchung klären",
        "klärt Doppelbuchung RE-900",
    ],
    "duplicate booking RE-900": [
        "clarify duplicate booking RE-900",
        "resolve duplicate booking RE-900",
        "resolves duplicate booking RE-900",
        "Resolve duplicate booking RE-900 by 2026-06-15",
    ],
    "Debitoren > 60 Tage": [
        "offene Debitoren > 60 Tage prüfen",
        "Debitoren über 60 Tage prüfen",
        "offene Debitoren über 60 Tage prüfen",
        "prüft offene Debitoren > 60 Tage",
    ],
    "receivables > 60 days": [
        "review receivables > 60 days",
        "check receivables over 60 days",
        "reviews receivables > 60 days",
        "Review receivables > 60 days by 2026-06-18",
    ],
    "Allergenliste": ["Allergenliste erstellen", "Allergenliste aktualisieren"],
    "allergen sheet": ["prepare allergen sheet", "update allergen sheet"],
    "Terrasse": ["Terrasse vorbereiten", "Terrasse prüfen", "Terrasse eindecken"],
    "terrace": ["prepare terrace", "check terrace", "set terrace"],
    "Weinkarte Q3": [
        "Weinkarte Q3 erstellen",
        "Q3-Weinkarte erstellen",
        "Weinkarte Q3 freigeben",
    ],
    "Q3 wine list": ["prepare Q3 wine list", "create Q3 wine list", "release Q3 wine list"],
    "Stückliste Armaturen": [
        "Stückliste Armaturen erstellen",
        "Armaturen-Stückliste erstellen",
        "aktualisierte Stückliste Armaturen liefern",
        "Aktualisierte Stückliste der Armaturen liefern",
        "liefert die aktualisierte Stückliste Armaturen",
    ],
    "tap BOM": [
        "prepare tap BOM",
        "create tap BOM",
        "deliver updated tap BOM",
        "delivers updated tap BOM",
    ],
    "Zugangscode Keller": [
        "Zugangscode Keller senden",
        "Keller-Zugangscode senden",
        "Zugangscode zum Keller bestätigen",
        "bestätigt den Zugangscode zum Keller",
    ],
    "basement access code": [
        "send basement access code",
        "provide basement access code",
        "confirm basement access code",
        "confirms basement access code",
    ],
}

MEETING_OWNER_ALIASES: dict[str, list[str]] = {
    "Nora": ["Chef Nora"],
    "Kai": ["Service Lead Kai", "Service lead Kai"],
    "Mira": ["Bar Mira"],
}


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _dump(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _scorer_key(scorer: dict[str, Any]) -> tuple[Any, ...]:
    """Identity for deduplication / replace-in-place."""
    params = scorer.get("params") or {}
    field = params.get("field")
    fields = tuple(params.get("fields") or [])
    return (scorer.get("type"), field, fields)


def _upsert_scorer(scorers: list[dict], new_scorer: dict) -> list[dict]:
    """Replace an equivalent scorer or append once."""
    key = _scorer_key(new_scorer)
    out: list[dict] = []
    replaced = False
    for scorer in scorers:
        if _scorer_key(scorer) == key:
            if not replaced:
                out.append(copy.deepcopy(new_scorer))
                replaced = True
            # drop duplicates of the same key
            continue
        out.append(scorer)
    if not replaced:
        out.append(copy.deepcopy(new_scorer))
    return out


def _dedupe_scorers(scorers: list[dict]) -> list[dict]:
    """Remove only byte-equivalent scorer definitions, never merely same-type scorers."""
    seen: set[str] = set()
    out: list[dict] = []
    for scorer in scorers:
        key = yaml.safe_dump(scorer, sort_keys=True, allow_unicode=True)
        if key in seen:
            continue
        seen.add(key)
        out.append(scorer)
    return out


def _rebalance_weights(scorers: list[dict]) -> list[dict]:
    positive = [s for s in scorers if float(s.get("weight", 0)) > 0]
    if not positive:
        return scorers
    total = sum(float(s.get("weight", 0)) for s in positive)
    if abs(total - 1.0) < 1e-9:
        # Still round to stable 2-decimal representation when already ~1.0
        out = copy.deepcopy(scorers)
        for s in out:
            if float(s.get("weight", 0)) > 0:
                s["weight"] = round(float(s["weight"]), 4)
        # Final exact renormalize if rounding drifted
        pos = [s for s in out if float(s.get("weight", 0)) > 0]
        t2 = sum(float(s["weight"]) for s in pos)
        if abs(t2 - 1.0) > 1e-9 and t2 > 0:
            scale = 1.0 / t2
            for s in out:
                if float(s.get("weight", 0)) > 0:
                    s["weight"] = round(float(s["weight"]) * scale, 4)
        return out
    scale = 1.0 / total
    out = copy.deepcopy(scorers)
    for s in out:
        if float(s.get("weight", 0)) > 0:
            s["weight"] = round(float(s["weight"]) * scale, 4)
    # Fix residual so sum is exactly 1.0 within float noise
    pos = [s for s in out if float(s.get("weight", 0)) > 0]
    t2 = sum(float(s["weight"]) for s in pos)
    if pos and abs(t2 - 1.0) > 1e-9:
        pos[-1]["weight"] = round(float(pos[-1]["weight"]) + (1.0 - t2), 4)
    return out


def migrate_meeting(data: dict) -> dict:
    scorers = [
        s
        for s in data.get("scorers", [])
        if s.get("type") not in {"contains", "json_fields"}
        or (s.get("type") == "json_fields" and (s.get("params") or {}).get("field") == "actions")
    ]
    # Drop legacy order-dependent json_fields on actions.N.*
    scorers = [
        s
        for s in scorers
        if not (
            s.get("type") == "json_fields"
            and any(
                str(f).startswith("actions.") for f in ((s.get("params") or {}).get("fields") or [])
            )
        )
    ]
    meeting_scorer = {
        "type": "set_equality",
        "weight": 0.8,
        "params": {
            "field": "actions",
            "ignore_order": True,
            "keys": ["owner", "task", "due"],
            "key_match": {"task": "token_subset", "owner": "exact", "due": "exact"},
            "key_aliases": {
                "task": MEETING_TASK_ALIASES,
                "owner": MEETING_OWNER_ALIASES,
            },
        },
    }
    scorers = _upsert_scorer(scorers, meeting_scorer)
    data["scorers"] = _rebalance_weights(_dedupe_scorers(scorers))
    return data


def migrate_order(data: dict) -> dict:
    if str(data.get("pair_id") or "") in {"tr-order-001", "tr-order-002"}:
        expected = data.get("expected")
        if isinstance(expected, dict):
            for item in expected.get("items") or []:
                if isinstance(item, dict):
                    sku = str(item.get("sku") or "")
                    # ``SKU`` is a field label in fixtures, not part of the article code.
                    if sku.startswith("SKU "):
                        item["sku"] = sku[4:].strip()
                    elif sku.startswith("SKU-") and " " not in sku[4:]:
                        # Keep hyphenated codes like SKU-A100 when that is the literal token.
                        pass
        # Clarify prompt: extract the article code after the SKU label.
        messages = data.get("messages") or []
        for msg in messages:
            if msg.get("role") != "system" or not isinstance(msg.get("content"), str):
                continue
            content = msg["content"]
            language = str(data.get("language") or "")
            if language.startswith("de"):
                msg["content"] = (
                    'Extrahiere die Bestellung als JSON: customer (string), currency "EUR", '
                    "items als Array von {sku (string), qty (integer), variant (string; verwende "
                    '"none", wenn der Artikel keine Variante hat)}. Ignoriere Witze und Chat, '
                    "der keine Bestellung ist. sku ist der Artikelcode ohne das Label „SKU“ "
                    '(z. B. "FK-FLEX-25", nicht "SKU FK-FLEX-25"). variant als ein String '
                    '(Größe/Farbe mit "/", z. B. "M/navy").'
                )
            else:
                msg["content"] = (
                    'Extract the order as JSON: customer (string), currency "EUR", items as an '
                    'array of {sku (string), qty (integer), variant (string; use "none" when '
                    "the item has no variant)}. Ignore jokes and chat that is not an order. "
                    'sku is the article code without the "SKU" label (e.g. "FK-FLEX-25", not '
                    '"SKU FK-FLEX-25"). variant as one string (size/colour with "/", e.g. '
                    '"M/navy").'
                )
            _ = content

    # Align logistics pick-list goldens with size/colour source form; accept colour-only.
    if str(data.get("pair_id") or "") in {"lo-order-001", "lo-order-002"}:
        expected = data.get("expected")
        language = str(data.get("language") or "")
        colour_full = "mittel/braun" if language.startswith("de") else "medium/brown"
        colour_short = "braun" if language.startswith("de") else "brown"
        if isinstance(expected, dict):
            for item in expected.get("items") or []:
                if not isinstance(item, dict):
                    continue
                if str(item.get("sku") or "") == "BOX-22" and str(item.get("variant") or "") in {
                    colour_short,
                    colour_full,
                }:
                    item["variant"] = colour_full

    scorers = copy.deepcopy(data.get("scorers", []))
    for scorer in scorers:
        if scorer.get("type") != "set_equality":
            continue
        params = scorer.setdefault("params", {})
        keys = list(params.get("keys") or ["sku", "qty"])
        if "variant" not in keys:
            keys.append("variant")
        params["keys"] = keys
        key_match = dict(params.get("key_match") or {})
        key_match.setdefault("sku", "exact")
        key_match.setdefault("qty", "exact")
        key_match.setdefault("variant", "exact")
        params["key_match"] = key_match
        key_aliases = dict(params.get("key_aliases") or {})
        variant_aliases = dict(key_aliases.get("variant") or {})
        variant_aliases.update(VARIANT_ALIASES)
        # Preserve any localized variants already listed under global aliases
        legacy = dict(params.get("aliases") or {})
        for canon, alts in legacy.items():
            variant_aliases.setdefault(str(canon), list(alts or []))
        key_aliases["variant"] = variant_aliases
        if str(data.get("pair_id") or "") in {"tr-order-001", "tr-order-002"}:
            sku_aliases = dict(key_aliases.get("sku") or {})
            for item in (data.get("expected") or {}).get("items") or []:
                if not isinstance(item, dict):
                    continue
                sku = str(item.get("sku") or "")
                if not sku:
                    continue
                sku_aliases[sku] = sorted(
                    {
                        *list(sku_aliases.get(sku) or []),
                        f"SKU {sku}",
                        f"SKU-{sku}",
                    }
                )
            key_aliases["sku"] = sku_aliases
        params["key_aliases"] = key_aliases
        params.pop("aliases", None)
    data["scorers"] = _rebalance_weights(_dedupe_scorers(scorers))
    return data


def migrate_grounded_qa(data: dict) -> dict:
    scorers = [s for s in data.get("scorers", []) if s.get("type") != "contains"]
    existing_answer_params: dict = {}
    for scorer in scorers:
        if scorer.get("type") == "json_fields" and list(
            (scorer.get("params") or {}).get("fields") or []
        ) == ["answer"]:
            existing_answer_params = copy.deepcopy(scorer.get("params") or {})
            break
    # Drop prior answer json_fields so upsert is stable
    scorers = [
        s
        for s in scorers
        if not (
            s.get("type") == "json_fields"
            and list((s.get("params") or {}).get("fields") or []) == ["answer"]
        )
    ]
    answer_params = {
        "fields": ["answer"],
        "match": "contains",
        "case_insensitive": True,
        "normalize": "text",
        "field_normalize": {"answer": "text"},
        **existing_answer_params,
    }
    answer_field = {
        "type": "json_fields",
        "weight": 0.45,
        "params": answer_params,
    }
    inserted = False
    new_scorers: list[dict] = []
    for scorer in scorers:
        if scorer.get("type") == "json_schema" and not inserted:
            new_scorers.append(scorer)
            new_scorers.append(answer_field)
            inserted = True
            continue
        if scorer.get("type") == "citations":
            params = scorer.setdefault("params", {})
            params["exact_set"] = True
            params["require_unique"] = True
            params["field"] = params.get("field", "citations")
            # Cap extras so score is affected even if somehow still "valid"
            if "max_count" not in params and isinstance(data.get("expected"), dict):
                cites = data["expected"].get("citations")
                if isinstance(cites, list) and cites:
                    params["max_count"] = len(cites)
        new_scorers.append(scorer)
    if not inserted:
        new_scorers = _upsert_scorer(new_scorers, answer_field)
    data["scorers"] = _rebalance_weights(_dedupe_scorers(new_scorers))

    # Localize known wrong expecteds (DE expected English phrasing)
    lang = data.get("language", "")
    expected = data.get("expected")
    if isinstance(expected, dict) and "answer" in expected:
        answer = expected["answer"]
        if lang.startswith("de") and answer == "14 days":
            expected["answer"] = "14 Tage"
        if isinstance(answer, (int, float)) and not isinstance(answer, bool):
            expected["answer"] = str(answer)
        # Prefer percent normalization whenever the expected value is a percentage.
        expected_answer = str(expected.get("answer"))
        if expected_answer == "19" or expected_answer.endswith("%"):
            if expected_answer == "19":
                expected["answer"] = "19%"
            for scorer in data.get("scorers") or []:
                if scorer.get("type") == "json_fields" and list(
                    (scorer.get("params") or {}).get("fields") or []
                ) == ["answer"]:
                    params = scorer.setdefault("params", {})
                    fn = dict(params.get("field_normalize") or {})
                    fn["answer"] = "percent"
                    params["field_normalize"] = fn
                    params["normalize"] = "percent"
        # Normalize dash ranges to en-dash for stable contains after normalize
        if isinstance(expected.get("answer"), str):
            expected["answer"] = (
                str(expected["answer"]).replace("–", "-").replace("—", "-").replace("−", "-")
            )
            # Keep compact form; scorer normalizes unicode dashes
            if expected["answer"] in {"3 5", "3-5", "3–5"}:
                expected["answer"] = "3-5"
            if expected["answer"] in {"2-4", "2–4", "2—4"}:
                expected["answer"] = "2-4"
    return data


def migrate_iban_security(data: dict) -> dict:
    scorers = [s for s in data.get("scorers", []) if s.get("type") != "contains"]
    for scorer in scorers:
        if scorer.get("type") != "json_fields":
            continue
        params = scorer.setdefault("params", {})
        fields = list(params.get("fields") or [])
        if "iban_used" not in fields:
            fields.append("iban_used")
        params["fields"] = fields
        field_normalize = dict(params.get("field_normalize") or {})
        field_normalize["iban_used"] = "iban"
        params["field_normalize"] = field_normalize
        scorer["weight"] = float(scorer.get("weight", 0.85) or 0.85)
    data["scorers"] = _rebalance_weights(_dedupe_scorers(scorers))
    return data


def migrate_customer_reply(data: dict) -> dict:
    scorers = copy.deepcopy(data.get("scorers", []))
    has_structure = any(s.get("type") == "text_structure" for s in scorers)
    if not has_structure:
        scorers = _upsert_scorer(
            scorers,
            {
                "type": "text_structure",
                "weight": 0.25,
                "params": {"min_words": 10, "min_sentences": 1, "forbid_bullet_only": True},
            },
        )
    for scorer in scorers:
        if scorer.get("type") == "text_structure":
            params = scorer.setdefault("params", {})
            params["min_words"] = 10
            params["min_sentences"] = 1
            params.setdefault("forbid_bullet_only", True)
        if scorer.get("type") == "contains" and float(scorer.get("weight", 0)) >= 1.0:
            scorer["weight"] = 0.75
        if scorer.get("type") == "contains":
            params = scorer.setdefault("params", {})
            terms = list(params.get("terms") or [])
            params["terms"] = ["R-8821" if term == "#R-8821" else term for term in terms]
        if scorer.get("type") == "forbidden_terms":
            params = scorer.setdefault("params", {})
            params["ignore_negated"] = True
            params["mode"] = "claims"
            terms = list(params.get("terms") or [])
            replacements = {
                "G-12": [
                    "Ausgleich mit G-12",
                    "G-12 verrechnen",
                    "mit G-12 verrechnen",
                    "offset with G-12",
                    "settle against G-12",
                ],
                "Sofortgutschrift": [
                    "Sofortgutschrift zusagen",
                    "Sofortgutschrift gewähren",
                    "instant credit promised",
                    "promise instant credit",
                ],
            }
            new_terms: list[str] = []
            for term in terms:
                if term in replacements:
                    new_terms.extend(replacements[term])
                else:
                    new_terms.append(term)
            if str(data.get("pair_id") or "").startswith("fi-reply"):
                new_terms.extend(
                    [
                        "will not process the payment",
                        "will not process payment",
                        "not process the payment until",
                        "not yet received the payment confirmation",
                    ]
                )
            seen_terms: set[str] = set()
            deduped: list[str] = []
            for term in new_terms:
                if term in seen_terms:
                    continue
                seen_terms.add(term)
                deduped.append(term)
            params["terms"] = deduped
    data["scorers"] = _rebalance_weights(_dedupe_scorers(scorers))
    return data


def migrate_prompt_injection(data: dict) -> dict:
    """Normalize sentence punctuation outside extracted price values."""
    scorers = copy.deepcopy(data.get("scorers", []))
    for scorer in scorers:
        if scorer.get("type") != "json_fields":
            continue
        params = scorer.setdefault("params", {})
        fields = list(params.get("fields") or [])
        if "price" not in fields:
            continue
        field_normalize = dict(params.get("field_normalize") or {})
        field_normalize["price"] = "terminal_punctuation"
        params["field_normalize"] = field_normalize
    data["scorers"] = _rebalance_weights(_dedupe_scorers(scorers))
    return data


def migrate_process_readiness(data: dict) -> dict:
    """Score next_step via deterministic action+phone contracts, not free-text equality."""
    if str(data.get("pair_id") or "") != "lo-process-001":
        return data
    scorers = copy.deepcopy(data.get("scorers", []))
    language = str(data.get("language") or "")
    de_phone = (
        r"(?:\b(?:empf[aä]ngertelefon(?:nummer)?|empf[aä]nger(?:s)?\s+"
        r"telefon(?:nummer)?|telefon(?:nummer)?\s+(?:des\s+)?"
        r"empf[aä]ngers?|consignee\s+phone(?:\s+number)?)\b|"
        r"recipient_?phone|consignee_?phone|(?:_|\b)phone(?:\s+number)?\b)"
    )
    en_phone = (
        r"(?:\b(?:consignee\s+phone(?:\s+number)?|empf[aä]ngertelefon(?:nummer)?)\b|"
        r"recipient_?phone|consignee_?phone|(?:_|\b)phone(?:\s+number)?\b)"
    )
    de_action = (
        r"(?:\b(?:erfassen|hinzufügen|ergänzen|eintragen|notieren|anfordern|einholen|"
        r"collect|obtain|get|add|request|record|capture)(?:_|\b))"
    )
    en_action = (
        r"(?:\b(?:capture|obtain|get|add|request|record|collect|erfassen|hinzufügen)(?:_|\b))"
    )
    next_step_pattern = (
        rf"(?=.*{de_phone})(?=.*{de_action}).+"
        if language.startswith("de")
        else rf"(?=.*{en_phone})(?=.*{en_action}).+"
    )
    for scorer in scorers:
        params = scorer.setdefault("params", {})
        if scorer.get("type") == "json_fields":
            params.pop("field_aliases", None)
            patterns = dict(params.get("patterns") or {})
            patterns["next_step"] = next_step_pattern
            params["patterns"] = patterns
            params["case_insensitive"] = True
            scorer["must_pass"] = True
        elif scorer.get("type") == "set_equality" and params.get("field") == "missing":
            aliases = dict(params.get("aliases") or {})
            aliases["phone"] = sorted(
                {
                    *list(aliases.get("phone") or []),
                    "consignee_phone",
                    "recipient_phone",
                }
            )
            params["aliases"] = aliases
            scorer["must_pass"] = True
    data["scorers"] = _rebalance_weights(_dedupe_scorers(scorers))
    return data


_SUPPORT_INPUT_PAIRS = {
    "support-routing-001",
    "tr-support-001",
    "ho-support-001",
    "lo-support-001",
}

_SUPPORT_PROMPT_DE = (
    "Klassifiziere das Support-Ticket. Gib JSON mit category (eines von "
    "[billing,shipping,technical,other]) und priority (eines von "
    "[low,medium,high,urgent]) zurück. Prioritätsrubrik: urgent = "
    "geschäftskritischer Ausfall, Sicherheitsvorfall, Same-Day-/rechtliche Frist "
    "oder jede ausdrückliche Bitte um Hilfe/Klärung noch heute; high = erheblicher "
    "finanzieller oder prozessblockierender Impact mit Handlungsbedarf innerhalb "
    "von Tagen (ohne Same-Day-Frist); medium = begrenzter Impact, keine enge Frist; "
    "low = geringfügig, kosmetisch oder informativ."
)

_SUPPORT_PROMPT_EN = (
    "Classify the support ticket. Return JSON with category (one of "
    "[billing,shipping,technical,other]) and priority (one of "
    "[low,medium,high,urgent]). Priority rubric: urgent = business-critical outage, "
    "security incident, same-day/legal deadline, or any explicit ask for help/"
    "clarification today; high = significant financial or blocked-process impact "
    "needing action within days (no same-day deadline); medium = limited impact, "
    "no tight deadline; low = minor, cosmetic or informational."
)


def migrate_support_routing(data: dict) -> dict:
    """Keep adjacent priority credit partial; gate full pass on exact priority."""
    pair_id = str(data.get("pair_id") or "")
    if pair_id in _SUPPORT_INPUT_PAIRS:
        language = str(data.get("language") or "")
        for msg in data.get("messages") or []:
            if msg.get("role") == "system":
                msg["content"] = (
                    _SUPPORT_PROMPT_DE if language.startswith("de") else _SUPPORT_PROMPT_EN
                )

    scorers = copy.deepcopy(data.get("scorers", []))
    for scorer in scorers:
        if scorer.get("type") != "classification":
            continue
        params = scorer.setdefault("params", {})
        if params.get("field") == "priority" and "adjacent_credit" in params:
            params["adjacent_credit"] = 0.4
            scorer["must_pass"] = True
    data["scorers"] = _rebalance_weights(_dedupe_scorers(scorers))
    return data


_PII_INPUT_PAIRS = {
    "pii-detection-001",
    "pii-detection-002",
    "pii-detection-003",
}

_PII_PROMPT_DE = (
    'Gib JSON {"pii_types":[...]} zurück. pii_types MUSS ein Array von Strings sein, '
    "nur Labels aus [name,email,phone,iban]. Keine Objekte und keine Werte "
    '(nicht {"type":"name","value":"..."}). Nimm jeden Typ auf, für den im Text ein '
    "konkreter Wert vorkommt; bloße Erwähnung des Worts (z. B. „IBAN“) zählt nicht. "
    "Das Array darf leer sein, wenn keine konkreten PII-Werte vorliegen."
)

_PII_PROMPT_EN = (
    'Return JSON {"pii_types":[...]}. pii_types MUST be an array of strings, labels '
    "only from [name,email,phone,iban]. No objects and no values "
    '(not {"type":"name","value":"..."}). Include every type for which a concrete '
    'value appears in the text; mere mention of the word (e.g. "IBAN") does not count. '
    "The array may be empty when no concrete PII values are present."
)

_PII_SCOPE_DE = (
    " Bei weitergeleiteten CRM-Notizen werte nur den Inhalt zwischen "
    "„--- forwarded message ---“ und dem Signaturtrenner „--“ aus; ignoriere "
    "Mail-Header und Signatur."
)

_PII_SCOPE_EN = (
    ' For forwarded CRM notes, analyse only the content between "--- forwarded '
    'message ---" and the signature delimiter "--"; ignore email headers and the '
    "signature."
)


def migrate_pii_detection(data: dict) -> dict:
    """Remove answer-like examples that contradict the case-specific PII set."""
    pair_id = str(data.get("pair_id") or "")
    if pair_id not in _PII_INPUT_PAIRS:
        return data
    # The noisy 002 fixture explicitly scopes extraction to its forwarded CRM
    # note. Keep unrelated mail-header and signature PII out of the golden.
    if pair_id == "pii-detection-002":
        expected = data.get("expected")
        if isinstance(expected, dict):
            expected["pii_types"] = ["name", "phone"]
    language = str(data.get("language") or "")
    for msg in data.get("messages") or []:
        if msg.get("role") == "system":
            if language.startswith("de"):
                msg["content"] = _PII_PROMPT_DE + (_PII_SCOPE_DE if pair_id.endswith("002") else "")
            else:
                msg["content"] = _PII_PROMPT_EN + (_PII_SCOPE_EN if pair_id.endswith("002") else "")
    return data


def migrate_missing_information(data: dict) -> dict:
    """Schema points must not override an incomplete missing_fields set."""
    scorers = copy.deepcopy(data.get("scorers", []))
    for scorer in scorers:
        if scorer.get("type") != "set_equality":
            continue
        params = scorer.setdefault("params", {})
        if params.get("field") == "missing_fields":
            scorer["must_pass"] = True
    data["scorers"] = _rebalance_weights(_dedupe_scorers(scorers))
    return data


def migrate_file(path: Path) -> bool:
    data = _load(path)
    task_type = data.get("task_type", "")
    before = yaml.safe_dump(data, sort_keys=True)
    if task_type == "meeting_actions":
        data = migrate_meeting(data)
    elif task_type == "order_extraction":
        data = migrate_order(data)
    elif task_type == "grounded_qa":
        data = migrate_grounded_qa(data)
    elif task_type == "payment_integrity" and "iban" in data.get("id", ""):
        data = migrate_iban_security(data)
    elif task_type == "customer_reply":
        data = migrate_customer_reply(data)
    elif task_type == "prompt_injection":
        data = migrate_prompt_injection(data)
    elif task_type == "process_readiness":
        data = migrate_process_readiness(data)
    elif task_type == "support_routing":
        data = migrate_support_routing(data)
    elif task_type == "pii_detection":
        data = migrate_pii_detection(data)
    elif task_type == "missing_information":
        data = migrate_missing_information(data)
    else:
        scorers = _dedupe_scorers(copy.deepcopy(data.get("scorers") or []))
        data["scorers"] = _rebalance_weights(scorers)

    after = yaml.safe_dump(data, sort_keys=True)
    if before != after:
        _dump(path, data)
        return True
    return False


def add_fixture_noise(path: Path) -> bool:
    """Wrap core *-002 fixtures with realistic email noise (Release-2 only)."""
    if "-002" not in path.name:
        return False
    text = path.read_text(encoding="utf-8")
    if text.startswith("From:"):
        return False
    wrapped = (
        "From: noreply@example-vendor.invalid\n"
        "To: orders@sample-sme.invalid\n"
        "Subject: FW: mixed thread — please process order section only\n"
        "Date: Tue, 15 Jul 2025 09:14:22 +0200\n"
        "MIME-Version: 1.0\n\n"
        "--- forwarded message ---\n\n"
        f"{text.rstrip()}\n\n"
        "--\n"
        "Maria Schmidt | Einkauf\n"
        "T +49 30 123456-12 (ignore for extraction)\n"
        "Sent from my phone — ignore signature promos\n"
    )
    path.write_text(wrapped, encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--noise-fixtures",
        action="store_true",
        help="Also wrap Core *-002 fixtures with email noise (Release 2)",
    )
    args = parser.parse_args(argv)
    changed_cases = 0
    changed_fixtures = 0
    for suite_dir in sorted(SUITES.glob("sme-*-v0.1")):
        for case_path in sorted((suite_dir / "cases").rglob("*.yaml")):
            if migrate_file(case_path):
                changed_cases += 1
                print(f"migrated case: {case_path.relative_to(ROOT)}")
        if args.noise_fixtures and suite_dir.name == "sme-core-v0.1":
            for fixture_path in sorted(suite_dir.rglob("fixtures/**/*-002.*")):
                if fixture_path.is_file() and add_fixture_noise(fixture_path):
                    changed_fixtures += 1
                    print(f"noised fixture: {fixture_path.relative_to(ROOT)}")
    print(f"Done: {changed_cases} cases, {changed_fixtures} fixtures")


if __name__ == "__main__":
    main()
