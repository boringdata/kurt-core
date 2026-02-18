# Project Context: kurt-core

## Purpose

`kurt-core` is the Kurt CLI + core libraries for content ingestion, indexing, retrieval, and research workflows, with an emphasis on an extensible tool/provider system.

## Tech Stack

- Language: Python 3.10+
- Package manager: `uv` (`uv.lock` is committed)
- CLI: Click
- Data modeling: Pydantic v2, SQLModel/SQLAlchemy
- Local DB (current direction): Dolt via MySQL protocol (see `src/kurt/db/`)

## Architecture (High Level)

- `src/kurt/cli/`: CLI commands and UX
- `src/kurt/tools/`: tool SDK + tool implementations
- `src/kurt/workflows/`: workflow runtime and TOML-driven execution
- `src/kurt/db/`: database client, schema, and isolation helpers
- `openspec/changes/`: change specs/contracts that should be enforced by code + tests

## Notes

If code and docs disagree, prefer:

1. An OpenSpec contract under `openspec/changes/` (when it exists)
2. Tests that encode the contract
3. Runtime behavior in `src/`

