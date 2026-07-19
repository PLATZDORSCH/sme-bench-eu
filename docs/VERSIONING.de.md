# Versionierung und Releases

SME-Bench folgt [Semantic Versioning](https://semver.org/lang/de/) und veröffentlicht
[GitHub Releases](https://github.com/PLATZDORSCH/sme-bench-eu/releases).

Es gibt **zwei Versionslinien**. Beide stehen in der Run-`metadata.json`
(`sme_bench_version`, `suite_version` / Member-Suite-Versionen).

## 1. Tool (Harness) — `pyproject.toml` → `sme_bench_version`

CLI, Client, Scorer und Reporter.

| Sprung | Wann |
| --- | --- |
| **Patch** (`0.1.1`) | Bugfixes, die **keine** Case-Inhalte und bei gleichen Inputs **keine** Scores ändern (z. B. Crash-Fix, klarere Fehler, reine Package-Docs) |
| **Minor** (`0.2.0`) | Rückwärtskompatible Features (neue CLI-Flags, Report-Formate, optionale Scorer) |
| **Major** (`1.0.0`) | Breaking CLI/API-Änderungen, sobald die öffentliche Oberfläche stabil ist |

## 2. Benchmark-Inhalt — Suite-Ordner (`…-v0.1`) und Suite-`version`

Cases, Prompts, Fixtures, Expected Answers, Gewichte und Pack-Zusammensetzung.

Pack-**Ordner-IDs** (z. B. `sme-core-v0.1`) bleiben bei kleinen Inhalts-Bumps stabil.
Die genaue Inhaltslinie ist das Suite-YAML-Feld `version` und das Package-Release
(z. B. Ordner weiter `*-v0.1`, Suite `version: 0.2.0` → veröffentlicht als **v0.2.0**).
Ordner nur bei größerem Pack-Redesign umbenennen.

| Änderung | Aktion |
| --- | --- |
| Nur Tippfehler in Docs / README | Kein Suite-Bump |
| Prompt, Fixture, Expected, Gewichte, Suite-Zusammensetzung oder score-relevantes Scorer-Verhalten | Suite-`version` + Package-Release anheben (z. B. **0.2.0**); bei Wiederverwendung alter Attempts `--rescore` dokumentieren |
| Scorer-Fix, der Noten bei gleicher Modell-Ausgabe ändert | Wie oben; Runs unterschiedlicher Inhaltsversionen nicht stillschweigend vergleichen |

**Gleiche Inhaltsversion = vergleichbare Runs.** Leaderboard-Zeilen unterschiedlicher Inhaltsversionen nicht ohne Kennzeichnung mischen.

## GitHub Releases

1. [`CHANGELOG.md`](../CHANGELOG.md) aktualisieren: Einträge von **Unreleased** in die neue Versionssektion verschieben.
2. `version` in `pyproject.toml` anheben, wenn sich Tool oder veröffentlichte Benchmark-Linie ändert.
3. Auf `main` committen, dann Tag `vX.Y.Z` (annotated) und GitHub Release von diesem Tag anlegen.
4. In den Release Notes angeben, ob sich **Tool**, **Benchmark-Inhalt** oder **beides** geändert hat.

### Faustregel (0.x)

- Bei reinen Harness-Bugfixes im aktuellen Release bleiben (Patch).
- Bei Prompt-/Case-/Scorer-Verhalten mit Score-Impact eine **neue Version** veröffentlichen (nach `0.1.0` also der nächste Minor).
