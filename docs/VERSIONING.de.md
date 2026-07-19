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

| Änderung | Aktion |
| --- | --- |
| Nur Tippfehler in Docs / README | Kein Suite-Bump |
| Prompt, Fixture, Expected, Gewichte oder Suite-Zusammensetzung | **Neue Suite- / Inhaltsversion** (z. B. `v0.2`, Package entsprechend minor/patch) |
| Scorer-Fix, der Noten bei gleicher Modell-Ausgabe ändert | **Neues Release**; dokumentieren, dass alte Runs `--rescore` brauchen und nicht stillschweigend vergleichbar sind |

**Gleiche Inhaltsversion = vergleichbare Runs.** Leaderboard-Zeilen unterschiedlicher Inhaltsversionen nicht ohne Kennzeichnung mischen.

## GitHub Releases

1. [`CHANGELOG.md`](../CHANGELOG.md) aktualisieren: Einträge von **Unreleased** in die neue Versionssektion verschieben.
2. `version` in `pyproject.toml` anheben, wenn sich Tool oder veröffentlichte Benchmark-Linie ändert.
3. Auf `main` committen, dann Tag `vX.Y.Z` (annotated) und GitHub Release von diesem Tag anlegen.
4. In den Release Notes angeben, ob sich **Tool**, **Benchmark-Inhalt** oder **beides** geändert hat.

### Faustregel (0.x)

- Bei reinen Harness-Bugfixes im aktuellen Release bleiben (Patch).
- Bei Prompt-/Case-/Scorer-Verhalten mit Score-Impact eine **neue Version** veröffentlichen (nach `0.1.0` also der nächste Minor).
