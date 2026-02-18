<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# kurt-core: Agent Index

Read this first. Re-read after compaction.

## Safety (Non-Negotiable)

- No destructive ops without explicit instruction (no `rm -rf`, `git reset --hard`, `git clean -fd`, force-push).
- No secrets in git. Do not paste tokens into commits, logs, or issues.
- No broad rewrite scripts (codemods, "fix everything") without approval.
- No file variants (`*_v2.*`) or "backup copies" checked into git; edit in place.
- Never delete files unless you have explicit written permission. Prefer `git mv` into `archive/`.

## Core Entrypoints

- Repo overview: `README.md`
- Docs index: `docs/README.md`
- Project context (agents): `docs/PROJECT_CONTEXT.md`
- Architecture map: `docs/ARCHITECTURE.md`
- OpenSpec (proposals/specs/tasks): `openspec/AGENTS.md`, `openspec/changes/`
- Workflow + evidence conventions: `docs/workflow/`

## Beads (br)

**Note:** `br` is non-invasive and never executes git commands. After `br sync --flush-only`, you must manually run `git add` and `git commit`.

Common commands:
```bash
br ready
br list --status=open
br show <id>
br create --title="..." --description="..." --type=task --priority=2
br update <id> --status=in_progress
br close <id> --reason="..."
```

If this repo's `.beads/` is not currently tracked in git, see `docs/runbooks/beads.md` before relying on `br sync`.

## Session Startup

1. Read `AGENTS.md` end-to-end.
2. Read `docs/PROJECT_CONTEXT.md`.
3. Find how to run: tests, lint/format, dev server (see Project Commands below).
4. If doing a spec/proposal: open `openspec/AGENTS.md` and follow the conventions there.

For full session lifecycle (blocked protocol, compaction/restart, end-of-session), see `docs/workflow/OPERATIONS.md`.

## Project Commands

```bash
# Install (uses uv.lock)
uv sync --all-extras

# Tests
uv run pytest -q

# Lint
uv run ruff check .
```

Smoke gate: `scripts/gates/smoke.sh`

## Landing The Plane (Session Completion)

Work is not complete until `git push` succeeds.

1. File issues for any follow-up work (or document TODOs with a clear owner and next step).
2. Run quality gates (tests/lints) if code changed.
3. Sync beads export (if used):
   ```bash
   br sync --flush-only
   ```
4. Commit and push:
   ```bash
   git pull --rebase
   git add .
   git commit -m "..."   # keep commits scoped; include bead-id when applicable
   git push
   git status            # must show "up to date with origin"
   ```
5. Hand off: write a short status note (what changed, what remains, next command to run).
