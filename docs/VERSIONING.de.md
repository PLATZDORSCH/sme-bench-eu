# Versionierung und Releases

SME-Bench folgt [Semantic Versioning](https://semver.org/lang/de/) und veröffentlicht
[GitHub Releases](https://github.com/PLATZDORSCH/sme-bench-eu/releases).

Es gibt **drei Versionslinien**. Alle stehen in der Run-`metadata.json`
(`sme_bench_version`, `suite_version` / Member-Suite-Versionen, `scoring_spec_version`).

## 1. Tool (Harness) — `pyproject.toml` → `sme_bench_version`

CLI, Client, Scorer und Reporter.

| Sprung | Wann |
| --- | --- |
| **Patch** (`0.1.1`) | Bugfixes, die **keine** Case-Inhalte und bei gleichen Inputs **keine** Scores ändern (z. B. Crash-Fix, klarere Fehler, reine Package-Docs) |
| **Minor** (`0.2.0`) | Rückwärtskompatible Features (neue CLI-Flags, Report-Formate, optionale Scorer) |
| **Major** (`1.0.0`) | Breaking CLI/API-Änderungen, sobald die öffentliche Oberfläche stabil ist |

## 2. Benchmark-Inhalt — Suite-Ordner (`…-v0.1`) und Suite-`version`

Cases, Prompts, Fixtures, Expected Answers, Gewichte und Test-Suite-Zusammensetzung.

Test-Suite-**Ordner-IDs** (z. B. `sme-core-v0.1`) bleiben bei kleinen Inhalts-Bumps stabil.
Die genaue Inhaltslinie ist das Suite-YAML-Feld `version` und das Package-Release
(z. B. Ordner weiter `*-v0.1`, Suite `version: 0.2.0` → veröffentlicht als **v0.2.0**).
Ordner nur bei größerem Test-Suite-Redesign umbenennen.

| Änderung | Aktion |
| --- | --- |
| Nur Tippfehler in Docs / README | Kein Suite-Bump |
| Prompt, Fixture, Expected, Gewichte, Suite-Zusammensetzung oder score-relevantes Scorer-Verhalten | Suite-`version` + Package-Release anheben (z. B. **0.10.0** / Harness **0.7.6**); bei unveränderten Inputs `sme-bench regrade`; für partielle Neuausführung `merge-run` |
| Scorer-Fix, der Noten bei gleicher Modell-Ausgabe ändert | Wie oben; **`regrade`** gegenüber In-Place-`--rescore` bevorzugen; Leaderboard nach `suite_version` filtern |

**Gleiche Inhaltsversion = vergleichbare Runs.** Leaderboard-Zeilen unterschiedlicher Inhaltsversionen nicht ohne Kennzeichnung mischen. Regraded Runs kopieren die Inference eines früheren Runs und wenden nur das Scoring neu an; sie tragen `regraded_from` in der Metadata und bleiben an den Quell-Inference-Run gebunden.

## 3. Scoring-Spezifikation — `scoring_spec_version`

Fingerprint, wie Scores für eine Inhaltslinie berechnet werden (Gewichte, Must-Pass-Gates, Matcher-Semantik, Input-Normalisierung). Steht in der Run-Metadata als `scoring_spec_version` (aktuell: **0.6.3**).

| Änderung | Aktion |
| --- | --- |
| Nur Docs / Harness-Packaging | Kein Scoring-Spec-Bump |
| Score-relevante Scorer- oder Aggregationsänderung bei unveränderten Modell-Inputs | `scoring_spec_version` mit Content-/Harness-Release anheben; bestehende Runs bleiben **regrade-fähig**, solange die Inputs unverändert sind |

Ein **Scorer-Defekt** — eine korrekte Antwort wird als falsch bewertet — wird auf der Scoring-Spec-Linie behoben und per Regrade rückwirkend angewendet, weil die Antwort unter der beabsichtigten Semantik immer richtig war. Eine **Lücke in der Aufgabenspezifikation** — bewertet wird gegen eine Anforderung, die im Prompt nie stand — wird nach vorne auf der Content-Linie mit einem Rerun behoben; ein Modell lässt sich nicht rückwirkend an einem Prompt messen, den es nie gesehen hat.

Kompatibilitäts-Manifeste unter [`suites/compatibility/`](../suites/compatibility/) halten fest, welche Tasks regrade-sicher sind und welche ein frisches Inference-Delta brauchen, z. B. [`regrade-0.10.3-baseline.json`](../suites/compatibility/regrade-0.10.3-baseline.json).

### Regrade versus Rerun

| Situation | Befehl |
| --- | --- |
| Gleiche Modell-Inputs; nur Scoring/Spec geändert | `sme-bench regrade SOURCE --output TARGET` |
| Teilmenge der Task-Inputs geändert | `sme-bench run … --task-ids …`, danach `sme-bench merge-run --base … --delta … -o …` |
| Prüfen, welcher Pfad für welche Tasks gilt | `sme-bench compat-report SOURCE` |
| Input-Fingerprints für Manifeste exportieren | `sme-bench fingerprints --suite …` |

Für veröffentlichte Vergleiche **`regrade`** gegenüber In-Place-`report --rescore` bevorzugen: Regrade schreibt ein neues Run-Verzeichnis und erhält den Quell-Inference-Run.

## GitHub Releases

1. [`CHANGELOG.md`](../CHANGELOG.md) aktualisieren: Einträge von **Unreleased** in die neue Versionssektion verschieben.
2. `version` in `pyproject.toml` anheben, wenn sich Tool oder veröffentlichte Benchmark-Linie ändert.
3. Auf `main` committen, dann Tag `vX.Y.Z` (annotated) und GitHub Release von diesem Tag anlegen.
4. In den Release Notes angeben, ob sich **Tool**, **Benchmark-Inhalt**, **Scoring-Spec** oder eine Kombination geändert hat.

### Faustregel (0.x)

- Bei reinen Harness-Bugfixes im aktuellen Release bleiben (Patch).
- Bei Prompt-/Case-/Scorer-Verhalten mit Score-Impact eine **neue Version** veröffentlichen (nach `0.1.0` also der nächste Minor).
