# Versioning and releases

SME-Bench uses [Semantic Versioning](https://semver.org/) and publishes
[GitHub Releases](https://github.com/PLATZDORSCH/sme-bench-eu/releases).

There are **three version lines**. All appear in run `metadata.json`
(`sme_bench_version`, `suite_version` / member suite versions, `scoring_spec_version`).

## 1. Tool (harness) — `pyproject.toml` → `sme_bench_version`

The CLI, client, scorers, and reporters.

| Bump | When |
| --- | --- |
| **Patch** (`0.1.1`) | Bugfixes that do **not** change case content or scores for unchanged inputs (e.g. crash fix, clearer error, docs-only in the package) |
| **Minor** (`0.2.0`) | Backward-compatible features (new CLI flags, report formats, optional scorers) |
| **Major** (`1.0.0`) | Breaking CLI/API changes once the public surface is stable |

## 2. Benchmark content — suite folders (`…-v0.1`) and suite `version`

Cases, prompts, fixtures, expected answers, weights, and test-suite membership.

Test-suite **folder ids** (e.g. `sme-core-v0.1`) stay stable across small content line bumps.
The precise content line is the suite YAML `version` field and the package release
(e.g. folders still named `*-v0.1`, suite `version: 0.2.0` → published as **v0.2.0**).
Rename folders only for a larger test-suite redesign.

| Change | Action |
| --- | --- |
| Typo in docs / README only | No suite bump |
| Prompt, fixture, expected, weights, suite composition, or score-changing scorer behaviour | Bump suite `version` + package release (e.g. **0.8.0** / harness **0.7.3**); use `sme-bench regrade` when inputs are unchanged; `merge-run` for partial new-task execution |
| Scorer fix that changes grades for the same model output | Same as above; prefer **`regrade`** over in-place `--rescore`; filter leaderboard by `suite_version` |

**Same content version = comparable runs.** Do not mix leaderboard rows from different content versions without labelling them. Regraded runs copy inference from a prior run and only re-apply scoring; they carry `regraded_from` in metadata and remain tied to the source inference run.

## 3. Scoring specification — `scoring_spec_version`

Fingerprint of how scores are computed for a given content line (weights, must-pass gates, matcher semantics). Stored in run metadata as `scoring_spec_version` (current: **0.5.0**).

| Change | Action |
| --- | --- |
| Docs-only / harness packaging | No scoring-spec bump |
| Score-changing scorer or aggregation change with unchanged model inputs | Bump `scoring_spec_version` with the content/harness release; existing runs stay **regradable** when inputs are unchanged |

Compatibility manifests under [`suites/compatibility/`](../suites/compatibility/) record which tasks are regrade-safe versus require a fresh inference delta, for example [`regrade-0.8.0-baseline.json`](../suites/compatibility/regrade-0.8.0-baseline.json).

### Regrade versus rerun

| Situation | Command |
| --- | --- |
| Same model inputs; only scoring/spec changed | `sme-bench regrade SOURCE --output TARGET` |
| A subset of task inputs changed | `sme-bench run … --task-ids …` then `sme-bench merge-run --base … --delta … -o …` |
| Inspect which tasks need which path | `sme-bench compat-report SOURCE` |
| Export input fingerprints for manifests | `sme-bench fingerprints --suite …` |

Prefer **`regrade`** over in-place `report --rescore` for published comparisons: regrade writes a new run directory and preserves the source inference run.

## GitHub Releases

1. Update [`CHANGELOG.md`](../CHANGELOG.md): move items from **Unreleased** into the new version section.
2. Bump `version` in `pyproject.toml` when the tool or published benchmark line changes.
3. Commit on `main`, then tag `vX.Y.Z` (annotated) and create a GitHub Release from that tag.
4. Release notes should state whether **tool**, **benchmark content**, **scoring spec**, or a combination changed.

### Rule of thumb (0.x)

- Stay on the current release for harness-only bugfixes (patch).
- Ship a **new version** for prompt/case/scorer behaviour that affects scores (including the next minor after `0.1.0`).
