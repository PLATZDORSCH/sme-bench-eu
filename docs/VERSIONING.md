# Versioning and releases

SME-Bench uses [Semantic Versioning](https://semver.org/) and publishes
[GitHub Releases](https://github.com/PLATZDORSCH/sme-bench-eu/releases).

There are **two version lines**. Both appear in run `metadata.json`
(`sme_bench_version`, `suite_version` / member suite versions).

## 1. Tool (harness) — `pyproject.toml` → `sme_bench_version`

The CLI, client, scorers, and reporters.

| Bump | When |
| --- | --- |
| **Patch** (`0.1.1`) | Bugfixes that do **not** change case content or scores for unchanged inputs (e.g. crash fix, clearer error, docs-only in the package) |
| **Minor** (`0.2.0`) | Backward-compatible features (new CLI flags, report formats, optional scorers) |
| **Major** (`1.0.0`) | Breaking CLI/API changes once the public surface is stable |

## 2. Benchmark content — suite folders (`…-v0.1`) and suite `version`

Cases, prompts, fixtures, expected answers, weights, and pack membership.

| Change | Action |
| --- | --- |
| Typo in docs / README only | No suite bump |
| Prompt, fixture, expected, weights, or suite composition | **New suite / overall content version** (e.g. `v0.2`, package minor or patch as appropriate) |
| Scorer fix that changes grades for the same model output | **New release**; document that old runs need `--rescore` and are not silently comparable |

**Same content version = comparable runs.** Do not mix leaderboard rows from different content versions without labelling them.

## GitHub Releases

1. Update [`CHANGELOG.md`](../CHANGELOG.md): move items from **Unreleased** into the new version section.
2. Bump `version` in `pyproject.toml` when the tool or published benchmark line changes.
3. Commit on `main`, then tag `vX.Y.Z` (annotated) and create a GitHub Release from that tag.
4. Release notes should state whether **tool**, **benchmark content**, or **both** changed.

### Rule of thumb (0.x)

- Stay on the current release for harness-only bugfixes (patch).
- Ship a **new version** for prompt/case/scorer behaviour that affects scores (including the next minor after `0.1.0`).
