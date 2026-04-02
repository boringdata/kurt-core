# PROJECT CONTEXT

Goal: give agents the minimum context needed to do correct work without reading chat history.

## What Is This Project?

- One-liner: `kurt-core` is the Kurt CLI + core libraries for content ingestion, indexing, retrieval, and research workflows.
- Primary users: developers and content teams using the CLI (and IDE agents) to map/fetch/index sources and generate grounded outputs.
- Core value: a tool-based, extensible architecture where adding providers/skills is low-friction and behavior is testable.

## Repo Map (High Level)

- Entrypoints:
  - CLI: `src/kurt/cli/main.py` (installed as `kurt`)
  - Python package: `src/kurt/`
- Tools:
  - Tool SDK + registries: `src/kurt/tools/core/`
  - Tool implementations: `src/kurt/tools/` (fetch/map/research/etc.)
- Workflows:
  - Runtime wiring + execution: `src/kurt/workflows/`
  - TOML-driven execution: `src/kurt/workflows/toml/`
- Database:
  - Dolt client + schema/helpers: `src/kurt/db/`
  - Isolation helpers (branching/merge/remote): `src/kurt/db/isolation/`
- OpenSpec (change proposals/specs/tasks): `openspec/`

## Environments

- dev: local Python env (recommended via `uv`), local Dolt repo in the workspace via `.dolt/` and `dolt sql-server` (when used).
- staging/prod: varies by deployment target; this repo includes cloud-related modules under `src/kurt/cloud/` but shipping runtime may be CLI-only.

## Constraints / Invariants

- MUST: keep CLI behavior testable (unit/integration tests under `src/kurt/**/tests/`).
- MUST: keep tool/provider selection deterministic and documented when touching provider matching.
- MUST NOT: introduce breaking CLI surface changes without an OpenSpec change under `openspec/changes/`.

## How To Run

```bash
# Install
uv sync --all-extras

# Run CLI
uv run kurt --help

# Lint + tests
uv run ruff check .
uv run pytest -q
```

Smoke gate: `scripts/gates/smoke.sh`

## Links

- Top-level README: `README.md`
- Docs index: `docs/README.md`
- OpenSpec index: `openspec/AGENTS.md`

