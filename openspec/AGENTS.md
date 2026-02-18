# OpenSpec (kurt-core)

This folder is the source of truth for change proposals, specs, and task breakdowns.

Open this file when a request involves a plan/proposal/spec, breaking changes, architecture shifts, or ambiguous requirements.

## Where Things Live

- Project overview: `openspec/project.md`
- Change proposals/specs/tasks: `openspec/changes/<change-slug>/`

Examples (existing change directories):

- `openspec/changes/provider-system/`
- `openspec/changes/kurt-simplification/`

## Change Directory Structure

Create a new change under `openspec/changes/<change-slug>/` using the existing pattern:

- `proposal.md`: why we are changing, scope/non-scope, constraints, open questions
- `spec.md` or `SPEC.md`: the technical design/contract (interfaces, rules, invariants)
- `tasks.md`: executable task list (or beads decomposition)
- Optional: `design.md`, `ARCHITECTURE.md`, `TESTING.md`, `CONFIGURATION.md` (when useful)

Conventions:

- Use a stable slug (kebab-case).
- Put dates in ISO format (`YYYY-MM-DD`).
- If the spec defines behavior contracts, include at least one test plan section and link to the test location in the repo.

## Applying a Change

When implementing an OpenSpec change:

1. Identify the authoritative spec file(s) under `openspec/changes/<slug>/`.
2. Implement only what the spec requires; avoid opportunistic refactors.
3. Add/adjust tests to enforce the spec contract.
4. Update docs under `docs/` if the change affects developer workflows or user-visible behavior.

