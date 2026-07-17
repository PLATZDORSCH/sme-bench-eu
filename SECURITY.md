# Security Policy

## Reporting a vulnerability

If you discover a security issue, please **do not open a public issue**. Instead,
email the maintainer at **dau@pd-we.de** with:

- a description of the issue and its impact,
- steps to reproduce,
- any relevant logs or proof-of-concept (without real secrets).

You can expect an initial response within a reasonable time frame. Please allow
time for a fix before public disclosure.

## Scope and data handling

SME-Bench is **local-first** and has no telemetry. Keep the following in mind:

- API keys are read from environment variables and must never be committed.
- Result files and logs must not contain API keys or credentials.
- All benchmark fixtures are **synthetic or anonymized**. The security/PII/prompt-injection
  cases contain deliberately fake data (e.g. `sk-DEMOSECRET999`, `*.test` emails)
  used only to test model behaviour. Do not replace them with real data.

If you find real secrets or personal data accidentally committed to the
repository, please report it privately using the contact above.
