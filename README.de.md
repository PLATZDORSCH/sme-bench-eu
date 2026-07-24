# SME-Bench

SME-Bench bewertet Sprachmodelle an **realistischen Aufgaben kleiner und mittlerer Unternehmen (KMU)** auf Deutsch und Englisch — nicht an Allgemeinwissen oder Multiple-Choice-Fragen.

Gemessen wird getrennt:

- Domänenqualität
- Zuverlässigkeit über Wiederholungen
- kritische Fehler (Halluzinationen, Datenlecks, unzulässige Aktionen)
- DE/EN-Sprachparität
- Format- und Prozesskonformität
- Performance (TTFR, TTFT, Latenz, Tokens/s)
- optional Kosteneffizienz (Tokenkosten)

Es gibt **keinen undurchsichtigen Gesamtscore**. Der transparente Score erscheint immer zusammen mit Pass Rate, Critical-Failure-Rate, Sprachvergleich und Performance-Kennzahlen.

## Installation

Voraussetzung: Python ≥ 3.11 und [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras --dev
```

## Schnellstart

`.env.example` nach `.env` kopieren und die benötigten Keys eintragen. Die CLI lädt `.env` automatisch. Mit `--api-key-env` wählst du die Variable (Standard: `OPENAI_API_KEY`). Lokale Server akzeptieren oft jeden Wert oder `EMPTY`.

```bash
cp .env.example .env
```

**Standardziel ist SME Full** (Core + alle Domänen-Test-Suites, 196 Cases × Repeats).

### Ollama

```bash
uv run sme-bench doctor \
  --base-url http://localhost:11434/v1 \
  --model qwen3.6:27b \
  --api-key-env OPENAI_API_KEY

uv run sme-bench run \
  --base-url http://localhost:11434/v1 \
  --model qwen3.6:27b \
  --api-key-env OPENAI_API_KEY \
  --output runs/ollama-qwen3.6-27b
```

### LM Studio

Der lokale Server von LM Studio ist OpenAI-kompatibel (Standardport `1234`):

```bash
uv run sme-bench doctor \
  --base-url http://localhost:1234/v1 \
  --model local-model \
  --api-key-env OPENAI_API_KEY

uv run sme-bench run \
  --base-url http://localhost:1234/v1 \
  --model local-model \
  --api-key-env OPENAI_API_KEY \
  --output runs/lmstudio
```

Als Modell-ID den Namen aus LM Studio verwenden (geladenes Modell / API-Name).

### OpenAI

```bash
uv run sme-bench doctor \
  --base-url https://api.openai.com/v1 \
  --model gpt-4o-mini \
  --api-key-env OPENAI_API_KEY

uv run sme-bench run \
  --base-url https://api.openai.com/v1 \
  --model gpt-4o-mini \
  --api-key-env OPENAI_API_KEY \
  --output runs/gpt-4o-mini
```

### Nebius

```bash
uv run sme-bench doctor \
  --base-url https://api.tokenfactory.nebius.com/v1 \
  --model zai-org/GLM-5.2 \
  --api-key-env NEBIUS_API_KEY

uv run sme-bench run \
  --base-url https://api.tokenfactory.nebius.com/v1 \
  --model zai-org/GLM-5.2 \
  --api-key-env NEBIUS_API_KEY \
  --extra-body-file examples/extra-body-glm-no-thinking.json \
  --output runs/glm-5.2
```

Standardmäßig gilt `--max-tokens-min 8192` und `--timeout 300`. Suite-Tasks
erlauben oft nur ~150–400 Completion-Tokens; Reasoning bricht dann mitten im
CoT ab (gpt-oss, Qwen Thinking, Nemotron, …). Abgerechnet wird meist nach
erzeugten Tokens — der Floor ist nur eine Obergrenze. Mit `--max-tokens-min 0`
wieder die rohen Suite-Budgets.

Wenn ein Thinking-Modell sein Token-Budget erschöpft, bevor eine finale Antwort
kommt, bleibt die Chain-of-Thought in `reasoning_text` (Diagnose) und wird
**nicht** als `output_text` gewertet oder angezeigt. Der Provider-`finish_reason`
wird pro Attempt (und in `attempts.csv`) gespeichert, sofern die API ihn liefert.

Reasoning über `reasoning_effort` (gpt-oss / GPT-5.x):

```bash
uv run sme-bench run \
  --base-url https://api.tokenfactory.nebius.com/v1 \
  --model openai/gpt-oss-120b \
  --api-key-env NEBIUS_API_KEY \
  --extra-body-file examples/extra-body-gpt54-reasoning.json \
  --save-reasoning \
  --output runs/gpt-oss-120b-thinking
```

### LiteLLM / vLLM

Jeder OpenAI-kompatible Proxy (LiteLLM, vLLM, …):

```bash
uv run sme-bench doctor \
  --base-url http://localhost:4000/v1 \
  --model qwen3.6-35b \
  --api-key-env LITELLM_API_KEY

uv run sme-bench run \
  --base-url http://localhost:4000/v1 \
  --model qwen3.6-35b \
  --api-key-env LITELLM_API_KEY \
  --output runs/litellm-qwen
```

Optional: Qwen-Style-Thinking (`chat_template_kwargs`). Token-Floor und Timeout
gelten bereits wie oben. `--save-reasoning` empfohlen:

```bash
uv run sme-bench run \
  --base-url http://localhost:4000/v1 \
  --model qwen3.6-35b \
  --api-key-env LITELLM_API_KEY \
  --enable-thinking \
  --save-reasoning \
  --output runs/litellm-qwen-thinking
```

Nur bei Bedarf überschreiben (z. B. `--max-tokens-min 4096` oder `--timeout 180`).
Allein `--max-tokens-mult 8` reicht nicht — ohne Floor wurden kurze Tasks bei
1200–2800 Completion-Tokens abgeschnitten.

### Nur Core

```bash
uv run sme-bench run \
  --base-url http://localhost:11434/v1 \
  --model qwen3.6:27b \
  --api-key-env OPENAI_API_KEY \
  --suite suites/sme-core-v0.1 \
  --output runs/core
```

## CLI-Befehle

| Befehl | Zweck |
| --- | --- |
| `sme-bench doctor` | Erreichbarkeit, Streaming, Usage prüfen |
| `sme-bench list --suite …` | Cases, Sprachen, Paare auflisten |
| `sme-bench validate …` | Suite, Fixtures, Scorer, Paarung prüfen |
| `sme-bench run …` | Benchmark starten (**Standard: Full**) |
| `sme-bench catalog …` | `CASES.md` erzeugen — Doku aller Cases |
| `sme-bench report …` | Reports neu bauen (`summary\|failures\|success`.`de\|en`.md); `--rescore` nur im Speicher |
| `sme-bench regrade SOURCE --output TARGET` | Nicht-destruktiv neu bewerten in ein neues Run-Verzeichnis |
| `sme-bench merge-run --base … --delta … -o …` | Vollen Base-Run mit selektiven `--task-ids`-Deltas mergen und rescoren |
| `sme-bench compat-report SOURCE` | Regrade-fähig vs. Neu-Run nötig anzeigen |
| `sme-bench fingerprints --suite …` | Legacy-Input-Fingerprint-Manifest exportieren |
| `sme-bench compare …` | Mehrere Runs vergleichen |

Mit `--task-ids id1,id2` auf `run` lassen sich selektive Deltas erzeugen, wenn nur einzelne Inputs geändert wurden.

## Kennzahlen

- **Attempt Pass Rate:** bestandene Attempts / alle Attempts (≥85 %, vollständig korrekt)
- **Attempt Partial Rate:** teilweise bestandene Attempts (65–84 %, größtenteils korrekt)
- **Reliable Pass Rate:** Cases, die in *jeder* Wiederholung bestanden (3/3) / alle Cases
- **Mostly Pass Rate:** Cases mit 2 von 3 bestandenen Wiederholungen / alle Cases
- **Unreliable Pass Rate:** Cases mit 1 von 3 bestandenen Wiederholungen / alle Cases
- **Failed Task Rate:** Cases mit 0 von 3 vollen Passes / alle Cases
- **Critical Failure:** kritischer Scorer fehlgeschlagen → effektiver Score `0` für den Attempt
- **SME Core Score:** Mittel der kategoriegewichteten effektiven Scores × 100 (Domänenqualität, ohne Raten-Penalty)
- **SME Rank Score:** `SME Core × Attempt Pass × max(0, 1 − 5 × critical_rate) × max(0, 1 − 0.5 × partial_rate)` — primäre Leaderboard-Metrik; erfolgreiche Wiederholungen werden anteilig berücksichtigt
- **Language gap:** Pass-/Score-Differenz `en-GB − de-DE` plus Paarkonsistenz

## Releases und Versionierung

Aktuelles Release: **v0.7.3** (Harness) mit SME-Full-Content **0.8.0** (196 DE/EN-Fälle) und Scoring-Spec **0.5.0**. Die 40 neuen Domänenvarianten bestanden Pair-Review, deterministische Golden-Checks und die Kalibrierung mit GPT-5.6 Luna sowie GLM-5.2 Thinking.

Harness-Bugfixes bleiben auf derselben Inhaltslinie (Patch). Prompt-, Case- oder score-relevante Änderungen bekommen eine **neue Version**, damit Leaderboard-Runs vergleichbar bleiben. Details: **[docs/VERSIONING.de.md](docs/VERSIONING.de.md)**.

## Test-Suites

Alle Cases einer freigegebenen Content-Linie haben `review_status: approved`. Ordner-IDs bleiben `*-v0.1`; die aktuelle Suite-Version ist **0.8.0**.

| Name | Pfad | Inhalt | Cases |
| --- | --- | --- | --- |
| **SME Full** | *(virtuell)* | Standard-Ranking: Core + kuratierte Domänen-Varianten | 196 |
| **SME Core v0.1** | `suites/sme-core-v0.1` | Core: 12 Task-Typen × 3 Varianten (DE/EN) | 72 |
| **SME Trades v0.1** | `suites/sme-trades-v0.1` | Handwerk/Bau | 22 |
| **SME E-Commerce v0.1** | `suites/sme-ecommerce-v0.1` | Shop/Retail | 22 |
| **SME Financial v0.1** | `suites/sme-financial-v0.1` | Buchhaltung/Finance | 22 |
| **SME Hospitality v0.1** | `suites/sme-hospitality-v0.1` | Gastronomie/Hotel | 24 |
| **SME Logistics v0.1** | `suites/sme-logistics-v0.1` | Logistik/Lager | 20 |
| **SME Chains v0.1** | `suites/sme-chains-v0.1` | Prozessketten + Security/PII | 14 |

Details zu jeder Test-Suite stehen in `suites/<id>/README.md`.

### Full vs. einzelne Test-Suite

```bash
export BASE_URL=http://localhost:11434/v1
export MODEL=qwen3.6:27b
export OPENAI_API_KEY=EMPTY

# Standard: Full
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" --output runs/full

# Optional: nur Core
uv run sme-bench validate suites/sme-core-v0.1
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-core-v0.1 --output runs/core

# Optional: eine Domänen-Test-Suite
uv run sme-bench run --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/sme-financial-v0.1 --output runs/financial
```

Im Full-Lauf enthalten: `sme-core-v0.1`, `sme-trades-v0.1`, `sme-ecommerce-v0.1`, `sme-financial-v0.1`, `sme-hospitality-v0.1`, `sme-logistics-v0.1`, `sme-chains-v0.1`.

Custom-Beispiel (nicht in Full): [`suites/demo-v0.1`](suites/demo-v0.1) — mit `--suite suites/demo-v0.1` starten.

## Eigene Test-Suite schreiben

Schritt für Schritt für Menschen und Coding-Agents: **[docs/AUTHORING_SUITES.de.md](docs/AUTHORING_SUITES.de.md)** (Layout, Case-Schema, Scorer, Fairness, validate/run).

Kurz:

1. YAML unter `suites/<suite>/cases/<lang>/` anlegen.
2. Fixtures relativ zur Suite referenzieren; Pfade dürfen die Suite nicht verlassen.
3. DE/EN über gemeinsame `pair_id` koppeln.
4. Mit `sme-bench validate` prüfen.

## Privatsphäre und Grenzen

- Local-first, keine Telemetrie.
- Keine API-Keys in Logs oder Ergebnisdateien.
- Kein LLM-as-a-Judge; Freitext wird über Pflichtinhalte, verbotene Aussagen und Struktur bewertet.

## Entwicklung

```bash
uv run ruff check .
uv run mypy src
uv run pytest --cov=sme_bench --cov-report=term-missing
```

CI läuft mit ruff, mypy, Suite-Validierung, README-Example-Pfadchecks und pytest inkl.
Coverage (Gate ≥76 %) auf Python 3.11 und 3.12.

### Test-Layout

| Pfad | Umfang |
| --- | --- |
| `tests/unit/test_models.py` | Pydantic-Modelle |
| `tests/unit/test_utils.py` | Pfadsicherheit, JSON-Extraktion, Redaction |
| `tests/unit/test_scorers.py` | Alle deterministischen Scorer (parametrisiert) |
| `tests/unit/test_scoring.py` | Schwellen, kritische Fehler |
| `tests/unit/test_statistics.py` | Aggregation, Sprachparität, TPS |
| `tests/unit/test_reporters.py` | Markdown/JSON-Reports, Dashboard |
| `tests/unit/test_task_loader.py` | Full-Benchmark-Load, Resume-Keys |
| `tests/unit/test_pricing.py` | Token-Kostenschätzung |
| `tests/unit/test_client.py` | HTTP-Client, Streaming, Retries |
| `tests/integration/test_e2e.py` | CLI End-to-End (run, compare, list, validate, Determinismus) |
