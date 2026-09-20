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

**Standardziel ist SME Full** (Core + Domänen-Packs + Advanced + Expert + Tools + Dialog + Long-Context + Agentic, 284 Cases × 2 Repeats).

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

## Was der Score bedeutet

SME-Bench ist ein **Eignungstest**, kein Ranking. Die Cases bilden Arbeit ab, die ein Modell im KMU-Alltag beherrschen muss. Hohe Scores heißen: das Modell ist für diese Arbeit einsetzbar. 100 % auf einem Aufgabentyp bleiben bewusst als Regressionsschutz. Härtere Differenzierung gehört in ein separates Expert-Pack, nicht ins Standardpaket.

| Eignungsstufe | Wann |
| --- | --- |
| **einsatzbereit** | SME Readiness Score ≥ 95, keine kritischen Fehler, Sprachtreue 100 % (wenn gemessen) |
| **mit Aufsicht** | Score 85–95, oder ein Sprachbruch (dann höchstens diese Stufe, auch bei höherem Score) |
| **nicht empfohlen** | Score unter 85, oder mindestens ein kritischer Fehler |
| **nicht aussagekräftig** | Completion Rate unter 95 % — der Lauf ist nicht voll vergleichbar |

Der JSON-Key bleibt `sme_rank_score`, damit bestehende Runs lesbar bleiben.

## Kennzahlen

- **Attempt Pass Rate:** bestandene Attempts / alle Attempts (≥85 %, vollständig korrekt)
- **Attempt Partial Rate:** teilweise bestandene Attempts (65–84 %, größtenteils korrekt)
- **Reliable Pass Rate:** Cases, die in *jeder* Wiederholung bestanden / alle Cases
- **Mostly Pass Rate:** Cases, die die meisten Repeats bestanden, aber nicht alle / alle Cases
- **Unreliable Pass Rate:** Cases, die einige, aber nicht alle Repeats bestanden / alle Cases
- **Failed Task Rate:** Cases ohne vollen Pass / alle Cases
- **Critical Failure:** kritischer Scorer fehlgeschlagen → effektiver Score `0` für den Attempt
- **SME Core Score:** Mittel der kategoriegewichteten effektiven Scores × 100 (Domänenqualität, ohne Raten-Penalty)
- **SME Readiness Score** (JSON-Key `sme_rank_score`): `SME Core × Attempt Pass × max(0, 1 − 5 × critical_rate) × max(0, 1 − 0.5 × partial_rate)` — primäre Eignungskennzahl; erfolgreiche Wiederholungen werden anteilig berücksichtigt
- **Eignungsstufe:** betriebliche Interpretation des Scores (`einsatzbereit` / `mit Aufsicht` / `nicht empfohlen` / `nicht aussagekräftig`)
- **Language gap:** Pass-/Score-Differenz `en-GB − de-DE` plus Paarkonsistenz
- **Sprachtreue:** Anteil der Attempts, die in der Fallsprache geantwortet haben (`—` bei Runs vor Content 0.9.0)
- **Nur-Format-Fehler:** Inhaltsscorer bestanden, Format-/Sprachscorer nicht
- **TTFT kalt / TTFA:** First-Token-Zeit nur bei `repeat_index == 0`, und Zeit bis zum ersten *Antwort*-Token (nicht Reasoning)
- Performance-Zahlen entstehen **unter Benchmark-Last** (Default-Concurrency 1). Für pp/tg-Sweeps, Prefix-Cache und Concurrency siehe [llama-benchy](https://github.com/eugr/llama-benchy).

### Scoring-Normalisierung

Das Scoring ist deterministisch und nutzt keinen LLM-Judge. Vor dem Vergleich faltet jeder Scorer typografische Unicode-Varianten auf **beiden** Seiten auf ihre ASCII-Entsprechung: geschütztes Trennzeichen (U+2011), Gedankenstriche, Minuszeichen, schmales geschütztes Leerzeichen (U+202F), weiches Trennzeichen, Zero-Width-Zeichen und typografische Anführungszeichen. Ein Modell, das eine Bestellnummer als `#W‑55021` schreibt, wird damit genauso bewertet wie eines, das `#W-55021` schreibt. Regex-*Patterns* sind ausgenommen, damit Zeichenklassen wie `[\u2010-\u2015]` weiter funktionieren; gefaltet wird nur der geprüfte Text.

### Sprachtreue

Ein deutscher Fall, der auf Englisch beantwortet wird, ist in der Praxis unbrauchbar. Deshalb nennt jeder Case seine Antwortsprache im Prompt und trägt einen `language`-Scorer mit `weight: 0` und `must_pass: true`. Ein Sprachbruch lässt den SME Core Score damit unberührt, verhindert aber das Bestehen des Attempts und senkt so Attempt Pass Rate und SME Readiness Score.

Die Prüfung zählt Funktionswörter, die für genau eine Sprache eindeutig sind, und schlägt erst an, wenn die falsche Sprache um zwei Marker führt. Sie hält sich bei dünner Evidenz absichtlich zurück, weil deutsche Geschäftsantworten legitim englische Lehnwörter und strukturierte Werte enthalten. Bekannte Konsequenz: eine kurze englische Phrase ohne Funktionswörter (`update inventory`) wird nicht erkannt. Dieser Schwellwert ist gegen die Musterantwort jedes einzelnen Cases validiert — eine strengere Einstellung würde Cases an ihrer eigenen Referenz scheitern lassen. JSON-Schlüssel werden nie geprüft, und Cases, deren `reason`-Feld einen abgewiesenen englischen Payload zitiert, schließen dieses Feld aus, genau wie `forbidden_terms` es bereits tut.

## Releases und Versionierung

Aktuelles Release: **v0.11.2** (Harness) mit SME-Full-Content **0.14.2** (284 DE/EN-Fälle) und Scoring-Spec **0.8.1**. Harness 0.11 ergänzt den Live-Mock-Tool-Loop, Completion Rate, eine `tool_choice=required`-Probe und Crowded-Namespace-Deltas. Harness 0.11.2 zeigt den Score als SME Readiness Score und ergänzt eine Eignungsstufe. Content 0.14.x fügt `sme-agentic-v0.1` und Crowded-Varianten in Tools hinzu; 0.14.1 schließt Spezifikationslücken in den Agentic-, Dialog-, Long-Context- und Tools-Prompts (geschlossene Literale, IDs und Zahlenformate stehen jetzt im Prompt); 0.14.2 macht `dialog-clarify-001` eindeutig.

Harness-Bugfixes bleiben auf derselben Inhaltslinie (Patch). Prompt-, Case- oder score-relevante Änderungen bekommen eine **neue Version**, damit veröffentlichte Vergleichs-Runs vergleichbar bleiben. Details: **[docs/VERSIONING.de.md](docs/VERSIONING.de.md)**.

## Test-Suites

Alle Cases einer freigegebenen Content-Linie haben `review_status: approved`. Ordner-IDs bleiben `*-v0.1`; die aktuelle Suite-Version ist **0.14.2**.

| Name | Pfad | Inhalt | Cases |
| --- | --- | --- | --- |
| **SME Full** | *(virtuell)* | Standard-Eignungsprüfung: Core + Domänen + Advanced + Expert + Tools + Dialog + Long-Context + Agentic | 284 |
| **SME Core v0.1** | `suites/sme-core-v0.1` | Trennscharfe Core-Aufgaben (DE/EN) | 42 |
| **SME Trades v0.1** | `suites/sme-trades-v0.1` | Handwerk/Bau | 14 |
| **SME E-Commerce v0.1** | `suites/sme-ecommerce-v0.1` | Shop/Retail | 22 |
| **SME Financial v0.1** | `suites/sme-financial-v0.1` | Buchhaltung/Finance | 16 |
| **SME Hospitality v0.1** | `suites/sme-hospitality-v0.1` | Gastronomie/Hotel | 16 |
| **SME Logistics v0.1** | `suites/sme-logistics-v0.1` | Logistik/Lager | 18 |
| **SME Chains v0.1** | `suites/sme-chains-v0.1` | Prozessketten + Security/PII | 4 |
| **SME Advanced v0.1** | `suites/sme-advanced-v0.1` | Harte Mehrschritt-Fälle | 36 |
| **SME Expert v0.1** | `suites/sme-expert-v0.1` | Sehr harte Mehrschritt-Fälle | 20 |
| **SME Tools v0.1** | `suites/sme-tools-v0.1` | Tool Use, Negativ- und Halluzinationsfälle, Crowded-Namespace | 32 |
| **SME Dialog v0.1** | `suites/sme-dialog-v0.1` | Multi-Turn-Kundenthreads | 16 |
| **SME Long Context v0.1** | `suites/sme-longctx-v0.1` | 8k–24k-Token-Nadeln | 16 |
| **SME Agentic v0.1** | `suites/sme-agentic-v0.1` | Live-Tool-Loops: Ketten, Recovery, Exactly-once, Auth | 32 |

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

Im Full-Lauf enthalten: `sme-core-v0.1`, `sme-trades-v0.1`, `sme-ecommerce-v0.1`, `sme-financial-v0.1`, `sme-hospitality-v0.1`, `sme-logistics-v0.1`, `sme-chains-v0.1`, `sme-advanced-v0.1`, `sme-expert-v0.1`, `sme-tools-v0.1`, `sme-dialog-v0.1`, `sme-longctx-v0.1`.

Custom-Beispiel (nicht in Full): [`suites/demo-v0.1`](suites/demo-v0.1) — mit `--suite suites/demo-v0.1` starten.

## Eigene Test-Suite schreiben

Mit einer eigenen Suite prüfst du Modelle an **deinen** Workflows — z. B. deine
Ticket-Kategorien, Rechnungsfelder oder Freigaberegeln — mit derselben
transparenten, deterministischen Bewertung wie SME Full. So siehst du, welches
Modell bei deinen Aufgaben zuverlässig ist, nicht nur im veröffentlichten Vergleich.

Ausführliche Anleitung (Layout, Case-Schema, Scorer, Fairness):
**[docs/AUTHORING_SUITES.de.md](docs/AUTHORING_SUITES.de.md)**.
Für Coding-Agents: kurzes Briefing in **[`suites/AGENTS.md`](suites/AGENTS.md)**
(verweist auf dieselbe Anleitung). Minimales Vorbild: [`suites/demo-v0.1`](suites/demo-v0.1).

### Warum eine eigene Suite?

- Du definierst die Ground Truth und Scorer selbst — kein LLM-as-a-Judge.
- DE/EN-Paare, Wiederholungen und Critical-Fails funktionieren wie im Full-Benchmark.
- Eigene Suites landen **nicht** automatisch im SME-Full-Vergleich; du startest
  sie gezielt mit `--suite`.

### So gehst du vor

1. **Ordner anlegen** unter `suites/<meine-suite-v0.1>/` mit `suite.yaml`,
   `cases/de-DE/`, `cases/en-GB/` und bei Bedarf `fixtures/` sowie `schemas/`.
2. **Cases schreiben** als YAML: System-/User-Prompt (direkt oder per Fixture),
   erwartetes Ergebnis und Scorer (z. B. `json_fields`, `contains`,
   `classification`, `forbidden_terms`).
3. **Sprachen koppeln**: denselben Task in DE und EN mit gemeinsamer `pair_id`,
   gleichem `task_type` und vergleichbaren Scorer-Gewichten.
4. **Prüfen**: `uv run sme-bench validate suites/<meine-suite-v0.1>`.
5. **Smoke-Run** mit einem Repeat, danach den vollen Lauf mit `--repeats 2`.

```bash
# Demo-Suite ausprobieren
uv run sme-bench validate suites/demo-v0.1
uv run sme-bench run \
  --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/demo-v0.1 --repeats 1 \
  --output runs/demo-smoke

# Eigene Suite
uv run sme-bench validate suites/meine-suite-v0.1
uv run sme-bench run \
  --base-url "$BASE_URL" --model "$MODEL" \
  --suite suites/meine-suite-v0.1 \
  --output runs/meine-suite
```

### Typische Struktur

```text
suites/meine-suite-v0.1/
├── suite.yaml
├── cases/de-DE/…yaml
├── cases/en-GB/…yaml
├── fixtures/          # optionale Eingabetexte
└── schemas/           # optional für json_schema-Scorer
```

Hinweise:

- Jede Message nutzt entweder `content` **oder** `fixture` (nicht beides).
- Fixture-Pfade sind relativ zum Suite-Root und dürfen die Suite nicht verlassen.
- Mindestens ein Scorer mit `weight > 0`; `critical: true` nur für harte
  Geschäftsregeln (z. B. verbotene Zusagen).
- `review_status: draft` bis zur Prüfung; für freigegebene Packs `approved`.

Optional Katalog erzeugen:
`uv run sme-bench catalog --suite suites/meine-suite-v0.1 --output suites/meine-suite-v0.1/CASES.md`.

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
