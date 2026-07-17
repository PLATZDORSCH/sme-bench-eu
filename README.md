# SME-Bench

SME-Bench bewertet Sprachmodelle an **realistischen Aufgaben kleiner und mittlerer Unternehmen (KMU)** auf Deutsch und Englisch — nicht an Allgemeinwissen oder Multiple-Choice-Tests.

Gemessen werden getrennt:

- fachliche Qualität
- Zuverlässigkeit über Wiederholungen
- kritische Fehler (Halluzinationen, Datenlecks, unerlaubte Aktionen)
- Sprachparität DE/EN
- Format- und Prozesskonformität
- Performance (TTFR, TTFT, Latenz, Tokens/s)
- optional Wirtschaftlichkeit (Tokenkosten)

Es gibt **keinen undurchsichtigen Gesamtscore allein**. Der transparente Score erscheint immer zusammen mit Erfolgsrate, kritischer Fehlerrate, Sprachvergleich und Performancewerten.

## Installation

Voraussetzung: Python ≥ 3.11 und [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras --dev
```

## Schnellstart

**Standard ist der Full-Run** (Core + alle Domänenpacks, ~156 Fälle):

```bash
# Endpoint prüfen
uv run sme-bench doctor \
  --base-url http://localhost:11434/v1 \
  --model qwen2.5:14b

# Full-Benchmark starten (Standard — kein --suite nötig)
uv run sme-bench run \
  --base-url http://localhost:11434/v1 \
  --model qwen2.5:14b \
  --languages de-DE,en-GB \
  --repeats 3 \
  --concurrency 1 \
  --seed 42 \
  --output runs/qwen2.5-full
```

Nur den Kernbenchmark (72 Fälle) ausführen:

```bash
uv run sme-bench run \
  --base-url http://localhost:11434/v1 \
  --model qwen2.5:14b \
  --suite suites/sme-core-v0.1 \
  --output runs/qwen2.5-core
```

API-Keys werden aus der Umgebungsvariable `OPENAI_API_KEY` gelesen (Standard für lokale Endpoints: `EMPTY`).

## CLI-Befehle

| Befehl | Zweck |
| --- | --- |
| `sme-bench doctor` | Erreichbarkeit, Streaming, Usage prüfen |
| `sme-bench list --suite …` | Fälle, Sprachen, Paare auflisten |
| `sme-bench validate …` | Suite, Fixtures, Scorer, Pairing prüfen |
| `sme-bench run …` | Benchmark ausführen (**Default: Full**) |
| `sme-bench catalog …` | `CASES.md` — Dokumentation aller Fälle erzeugen |
| `sme-bench report …` | Berichte aus Rohdaten neu erzeugen (`summary|failures|success`.`de|en`.md) |
| `sme-bench compare …` | Mehrere Läufe vergleichen |

## Kennzahlen

- **Attempt Pass Rate:** bestandene Versuche / alle Versuche (≥85 %, vollständig korrekt)
- **Attempt Partial Rate:** teilweise bestandene Versuche (65–84 %, überwiegend korrekt)
- **Reliable Pass Rate:** Fälle, die in *allen* Wiederholungen bestanden / alle Fälle
- **Critical Failure:** kritischer Scorer fehlgeschlagen → effektiver Score `0` für Ranglisten
- **SME Core Score:** Mittelwert der kategoriegewichteten effektiven Scores × 100
- **Language gap:** Pass-/Score-Differenz `en-GB − de-DE` sowie Pair-Konsistenz

## Aufgabenpakete

Alle Packs sind **released** (`review_status: approved`) und versioniert als **v0.1**.

| Name | Pfad | Inhalt | Fälle |
| --- | --- | --- | --- |
| **SME Full** | *(virtuell)* | Standard-Ranking: Core + alle Domänen | ~156 |
| **SME Core v0.1** | `suites/sme-core-v0.1` | Kern: 12 Task-Typen × 3 Varianten (DE/EN) | 72 |
| **SME Trades v0.1** | `suites/sme-trades-v0.1` | Handwerk/Bau | 14 |
| **SME E-Commerce v0.1** | `suites/sme-ecommerce-v0.1` | Shop/Retail | 14 |
| **SME Financial v0.1** | `suites/sme-financial-v0.1` | Buchhaltung/Finance | 14 |
| **SME Hospitality v0.1** | `suites/sme-hospitality-v0.1` | Gastro/Hotel | 14 |
| **SME Logistics v0.1** | `suites/sme-logistics-v0.1` | Logistik/Lager | 14 |
| **SME Chains v0.1** | `suites/sme-chains-v0.1` | Prozessketten + Security/PII | 14 |

Details zu jedem Pack stehen in `suites/<pack>/README.md` (Grundlage für die spätere Website).

### Full vs. einzelnes Pack

```bash
export BASE_URL=http://localhost:11434/v1
export MODEL=qwen2.5:14b
export OPENAI_API_KEY=EMPTY

# Standard: Full
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" --output runs/full

# Optional: nur Core
uv run sme-bench validate suites/sme-core-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-core-v0.1 --output runs/core

# Optional: nur ein Domänenpack
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-financial-v0.1 --output runs/financial
```

Enthalten im Full-Run: `sme-core-v0.1`, `sme-trades-v0.1`, `sme-ecommerce-v0.1`, `sme-financial-v0.1`, `sme-hospitality-v0.1`, `sme-logistics-v0.1`, `sme-chains-v0.1`.

## Eigene Aufgaben

Schritt-für-Schritt für Menschen und Coding-Agenten: **[docs/AUTHORING_SUITES.md](docs/AUTHORING_SUITES.md)** (Layout, Case-Schema, Scorer, Fairness, Validate/Run).

Kurz:

1. YAML unter `suites/<suite>/cases/<lang>/` anlegen.
2. Fixtures relativ zur Suite referenzieren; Pfade dürfen das Suite-Verzeichnis nicht verlassen.
3. DE/EN-Paare über dieselbe `pair_id` koppeln.
4. Mit `sme-bench validate` prüfen.

## Datenschutz und Grenzen

- Local-first, keine Telemetrie.
- Keine API-Keys in Logs oder Ergebnisdateien.
- Kein LLM-as-a-Judge; Freitext über Pflichtinhalte, verbotene Aussagen und Struktur.

## Entwicklung

```bash
uv run ruff check .
uv run mypy src
uv run pytest
```
