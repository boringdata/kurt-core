# QUALITY

Track domain grades + known gaps.

- domain: `cli` — grade: B — gaps: end-to-end CLI smoke coverage, docs consistency for modes/output
- domain: `tools/core` — grade: B — gaps: explicit contracts for provider matching and config mapping (keep OpenSpec in sync)
- domain: `workflows` — grade: C — gaps: integration test coverage for TOML runtime wiring and failure modes
- domain: `db` — grade: C — gaps: clear single-source-of-truth docs for local DB mode(s), isolation edge cases, fast local setup
- domain: `web` — grade: D — gaps: build/test gates for client assets, API contract tests (if shipped)

