# ARCHITECTURE

Goal: a navigable domain map for `kurt-core`.

## Domains

- `src/kurt/cli/`: CLI wiring and UX (Click commands, output modes, shared options).
- `src/kurt/config/`: configuration loading/validation and defaults.
- `src/kurt/tools/`: tool SDK and tool implementations (fetch/map/research/etc.).
- `src/kurt/workflows/`: workflow runtime, orchestration helpers, TOML-driven execution.
- `src/kurt/db/`: database client(s), schema, sessions, and isolation helpers.
- `src/kurt/integrations/`: optional third-party integrations (research, CMS, etc.).
- `src/kurt/agents/`: agent-facing templates and scaffolding content.
- `src/kurt/web/`: web UI / API surfaces (if enabled for the build target).
- `src/kurt/cloud/`: cloud mode scaffolding (auth/tenant), may be partially implemented or gated.
- `eval/`: evaluation harness and fixtures.

## Dependency Direction Rules

- `cli` depends on `config`, `tools`, and `workflows`.
- `tools/*` depend on `tools/core` and may depend on `config`, `db`, and `integrations`.
- `workflows` depend on `tools` and `db` (not vice versa).
- `db` should not depend on higher-level domains (`cli`, `tools`, `workflows`).
- `eval` can depend on anything; production code must not depend on `eval`.

## Deeper Docs

- Project context: `docs/PROJECT_CONTEXT.md`
- OpenSpec changes/specs: `openspec/changes/`
- Requirements docs (if applicable): `docs/requirements/`

