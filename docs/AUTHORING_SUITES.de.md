# Suite-Authoring (Menschen & Coding-Agents)

Anleitung für **eigene SME-Bench-Suites**: Verzeichnisstruktur, `suite.yaml`, Case-YAML, Scorer, Validierung, Fairness-Regeln.

Vorlage: [`sme-trades-v0.1`](/suites/sme-trades-v01) (`suites/sme-trades-v0.1/`).

---

## Ziele

- Nur deterministische Bewertung (kein LLM-as-a-Judge).
- DE/EN-Paare über gemeinsame `pair_id`.
- Nur synthetische oder anonymisierte Fixtures; keine echten Secrets oder PII im Repo.
- Eigene Suites werden **nicht** automatisch in SME Full übernommen — Ausführung mit `--suite PATH`.

---

## Checkliste (Agent-Workflow)

1. `suites/<id>/` anlegen mit `suite.yaml`, `cases/de-DE/`, `cases/en-GB/`, ggf. `fixtures/`, `schemas/`.
2. Cases als YAML; jede Message nutzt entweder `content` **oder** `fixture` (nicht beides, nicht keins).
3. **Jeden Case in beiden Sprachen** — je eine Datei unter `cases/de-DE/` und `cases/en-GB/`.
4. Fixture- und Schema-Pfade sind **relativ zum Suite-Root** und müssen im Suite-Verzeichnis bleiben.
5. DE/EN paaren: gleiche `pair_id`, gleicher `task_type`, gleiche `difficulty`, vergleichbare Summe positiver Scorer-Gewichte (Δ ≤ 0.05).
6. Mindestens ein Scorer mit `weight > 0`. `critical: true` nur für harte Fail-Bedingungen (effektiver Score → 0).
7. Validieren: `uv run sme-bench validate suites/<id>`
8. Smoke-Run: `uv run sme-bench run --base-url … --model … --suite suites/<id> --repeats 1 --output runs/<id>-smoke`
9. Optional Katalog: `uv run sme-bench catalog --suite suites/<id> --output suites/<id>/CASES.md`
10. `review_status: draft` bis zur manuellen Prüfung; `approved` erst bei Release-Reife.

---

## Verzeichnisstruktur

```text
suites/my-domain-v0.1/
├── suite.yaml                 # Pflicht-Manifest
├── README.md                  # optionale Pack-Beschreibung
├── cases/
│   ├── de-DE/
│   │   └── de-xx-task-001.yaml
│   └── en-GB/
│       └── en-xx-task-001.yaml
├── fixtures/                  # Eingabetexte, CSVs, …
│   ├── de-….txt
│   └── en-….txt
└── schemas/                   # JSON-Schema für json_schema-Scorer
    └── ….schema.json
```

Namenskonventionen (released Packs):

| Element | Muster | Beispiel |
| --- | --- | --- |
| Suite-Ordner / `id` | `sme-<domain>-v0.1` | `sme-trades-v0.1` |
| Case-`id` | `<lang>-<abbr>-<type>-<nnn>` | `de-tr-invoice-001` |
| `pair_id` | sprachübergreifend | `tr-invoice-001` |
| Case-Datei | entspricht `id` | `de-tr-invoice-001.yaml` |

---

## `suite.yaml`

```yaml
schema_version: "1.0"
id: my-domain-v0.1
name: My Domain Pack
version: 0.1.0
description: Kurzbeschreibung Domain und Task-Mix
languages:
  - de-DE
  - en-GB
default_repeats: 3
default_pass_threshold: 0.85
default_partial_threshold: 0.65
case_globs:
  - cases/**/*.yaml
category_weights:
  document_extraction: 1.0
  customer_service: 1.0
  # … nur genutzte Kategorien
provenance:
  type: synthetic
  notes: "Custom pack. Synthetic fixtures."
```

Hinweise:

- Case-Sprache muss in `languages` stehen.
- Fehlen Schwellwerte am Case, gelten Suite-Defaults (`pass` 0.85, `partial` 0.65).
- `partial_threshold` muss **strikt kleiner** als `pass_threshold` sein.

---

## Case-YAML

### Pflicht / häufige Felder

| Feld | Werte / Hinweise |
| --- | --- |
| `schema_version` | `"1.0"` |
| `id` | eindeutig in der Suite (und bei Full-Merge repo-weit) |
| `pair_id` | gemeinsame DE/EN-ID (empfohlen) |
| `title` | kurzer Titel |
| `language` | `de-DE` oder `en-GB` |
| `category` | z. B. `document_extraction`, `customer_service`, `grounded_qa`, … |
| `task_type` | freier String; innerhalb eines Paars konsistent |
| `difficulty` | `easy` \| `normal` \| `hard` |
| `risk` | `low` \| `medium` \| `high` \| `critical` |
| `review_status` | `draft` \| `reviewed` \| `approved` |
| `data_classification` | `synthetic` \| `anonymized` \| `confidential` |
| `tags` | String-Liste |
| `messages` | Liste aus `{role, content}` oder `{role, fixture}` |
| `generation` | `max_tokens`, `temperature` (meist `0`), `response_format` |
| `expected` | Ground Truth für Scorer (Objekt, String oder Liste) |
| `scorers` | Scorer-Spezifikationen |
| `pass_threshold` / `partial_threshold` | optionale Overrides |

`response_format`: `text` \| `json` \| `classification`.

### DE + EN als Paar

Jeder Custom-Case existiert in **Deutsch und Englisch**, gekoppelt über `pair_id`. Der Validator warnt bei `pair_id` mit weniger als zwei Sprachvarianten und meldet Fehler bei inkonsistentem `task_type` / `difficulty` / nicht vergleichbaren Scorer-Gewichten.

Regeln pro Paar:

- **Gleich:** `pair_id`, `task_type`, `difficulty`, vergleichbare Summe positiver Scorer-Gewichte (Δ ≤ 0.05).
- **Unterschiedlich:** `id` (Sprachpräfix), `language`, `title`, meist `fixture` (lokalisierte Eingabe).
- Strukturierte `expected`-Werte (Kategorien, Zahlen, SKUs) typischerweise identisch; nur Freitext lokalisieren.
- Sprachordner: `cases/de-DE/` und `cases/en-GB/`.

Ausführliche Beispiele (Classification, JSON Schema, `set_equality`, `citations`, `forbidden_terms`) in den released Cases — jeweils als DE/EN-Paar.

---

## Scorer

```yaml
- type: <name>
  weight: 0.5          # Anteil am gewichteten Score; 0 = reine Prüfung / oft mit critical
  critical: false      # bei Fail → critical_failure, effektiver Score 0
  params: { … }
```

| Typ | Typischer Einsatz | Wichtige `params` |
| --- | --- | --- |
| `json_schema` | Ausgabe entspricht JSON Schema | `schema: schemas/….json` |
| `json_fields` | Feldabgleich vs. `expected` | `fields`, optional `match`, `case_insensitive` |
| `numeric` | Float-Felder mit Toleranz | `fields`, `absolute_tolerance`, `relative_tolerance` |
| `classification` | Label in einem Feld | `field`, `expected`, `allowed`, optional `scale` + `adjacent_credit` |
| `contains` | Pflicht-Substrings | `terms`: String oder Liste von Alternativen pro Slot; `mode: all\|any`, `case_insensitive` |
| `forbidden_terms` | Darf nicht vorkommen (oft `critical: true`) | `terms`, optional `fields` / `exclude_fields`, `ignore_negated` |
| `set_equality` | Ungeordnete Listen | `field`, `ignore_order`, optional `keys`, `aliases` |
| `citations` | Zitations-IDs in Allow-List | `field`, `allowed`, `require_nonempty` |
| `exact_match` | Vollstring-Vergleich | optional `expected`, `case_insensitive`, `normalize_whitespace` |
| `regex` | Musterprüfung | `patterns`, optional `case_insensitive` |

### Fairness (weniger flaky Fails)

- **System-Prompt:** exakte JSON-Keys und Formate benennen (`vat_rate` als Dezimal `0.19`, Datum `YYYY-MM-DD`).
- **`forbidden_terms`:** `fields` zum Scannen strukturierter Werte oder `exclude_fields` (z. B. `reason`), damit Freitext nicht false-positive auslöst.
- **Listen:** `set_equality` + `keys: [sku, qty]` statt Vollobjekt-Gleichheit, wenn Extra-Keys erlaubt sind.
- **Citations:** IDs als `SEC-A` oder `[SEC-A]`; Scorer normalisiert gängige Formen.
- Positive Scorer-Gewichte sinnvoll summieren (oft ≈ 1.0); Paare vergleichbar halten.

---

## Bewertungsschwellen

| Note | Default | Bedeutung |
| --- | --- | --- |
| Pass | ≥ 0.85 | vollständig korrekt |
| Partial | 0.65–0.84 | überwiegend korrekt |
| Fail | < 0.65 | hartes Fail |
| Critical | Critical-Scorer failed | effektiver Score 0 |

**Reliable pass** (Reports): Case in jedem Repeat bestanden. Siehe Root-README Kennzahlen.

---

## Validierung & Ausführung

```bash
# Struktur, Fixtures, Scorer, Paarung
uv run sme-bench validate suites/my-domain-v0.1

# Cases auflisten
uv run sme-bench list --suite suites/my-domain-v0.1

# Nur diese Suite (nicht Full)
uv run sme-bench run \
  --base-url "$BASE_URL" \
  --model "$MODEL" \
  --suite suites/my-domain-v0.1 \
  --languages de-DE,en-GB \
  --repeats 3 \
  --output runs/my-domain-v0.1

# Zweisprachige Reports aus bestehendem Run
uv run sme-bench report runs/my-domain-v0.1 --format all
```

Validate schlägt fehl bei unbekannten Scorer-Typen, fehlenden Fixtures, Path-Escapes, ungültigem YAML/Pydantic, doppelten IDs, Sprache nicht im Manifest, nicht vergleichbaren Paaren. Ungepaarte `pair_id` → **Warnung**.

---

## Do / Don't

**Do**

- Bestehendes Pack als Vorlage für Scorer- und Prompt-Stil.
- Reviewbare Fixture-Länge; lange Inputs in `fixtures/`.
- Pack in `suites/<id>/README.md` dokumentieren (Task-Tabelle + Run-Befehle).
- `data_classification: synthetic` für erfundene Inhalte.

**Don't**

- Dateien außerhalb des Suite-Verzeichnisses referenzieren.
- Modell-„Urteil“ in Scorern.
- API-Keys, echte Kundendaten oder Live-Credentials in Fixtures.
- Erwarten, dass Custom-Suites in Default-Full erscheinen, ohne Eintrag in `FULL_SUITE_IDS` (`src/sme_bench/task_loader.py`, Maintainer).

---

## SME Full (Maintainer)

Released Packs unter `suites/`, gelistet in `FULL_SUITE_IDS`. Community-Suites bleiben getrennt (`--suite`). Full-Erweiterung nur nach Review (`review_status: approved`, eindeutige Task-IDs, Doku, Changelog).

Änderungen an Prompts, Fixtures, Expected Answers oder Gewichten erfordern eine **neue Inhaltsversion** — siehe [VERSIONING.de.md](VERSIONING.de.md).

---

## Referenz-Implementierungen

| Pack | Eignung als Vorlage |
| --- | --- |
| [`sme-trades-v0.1`](/suites/sme-trades-v01) | Kompaktes Domain-Pack (14 Cases) |
| [`sme-core-v0.1`](/suites/sme-core-v01) | Vollständige Task-Typ-Abdeckung |
| [`sme-chains-v0.1`](/suites/sme-chains-v01) | Prozessketten + Security / PII / Injection |

Modelle: `src/sme_bench/models.py` (`BenchmarkTask`, `SuiteManifest`, `ScorerSpec`).  
Loader / Checks: `src/sme_bench/task_loader.py`.  
Scorer-Registry: `src/sme_bench/scorers/`.
