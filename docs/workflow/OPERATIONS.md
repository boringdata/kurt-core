# OPERATIONS

Session lifecycle: startup, compaction, blocked, and end-of-session protocols.

## Session Startup / Reconnect

Do this once per session (and again after compaction):

1. Read `AGENTS.md` end-to-end.
2. Read `docs/PROJECT_CONTEXT.md`.
3. Find how to run: tests, lint/format, dev server.
4. If using beads, pick the next issue via `br ready` or your triage process.

## Bead Startup (Per Bead)

When starting work on a specific bead:

1. `br show <bead-id>` - read goal, scope, gates, checklist, and latest comments.
2. Find the latest `EVIDENCE:` path in bead comments.
3. Inspect `.agent-evidence/beads/<bead-id>/...` for prior work.
4. Confirm the bead's `STATE` and `NEXT` match your role before proceeding.

## Compaction / Restart Protocol

If context compaction happens or the session restarts:

1. Re-read `AGENTS.md`.
2. If working on a bead, `br show <current-bead>` and restate:
   - goal
   - what is done
   - what remains
3. Continue the bead or mark blocked with clear notes.

## Blocked Protocol

If blocked for >10 minutes or repeating the same failure 3 times:

1. Write a precise bead comment with:
   - blocker
   - what you tried
   - what decision/info you need
2. If needed, create a blocker bead and add a dependency:
   - `br create "BLOCKER: <title>" -d "<details>"` -> returns `<blocker-id>`
   - `br dep add <bead-id> <blocker-id>`
3. Move to the next ready bead: `br ready`

## Landing The Plane (End Of Session)

Before ending a session, do not leave work stranded locally:

1. Run verification (tests/lints) if code changed.
2. If using beads, export changes:
   - `br sync --flush-only`
3. Commit and push:
   - `git pull --rebase`
   - `git add .`
   - `git commit -m "..."`
   - `git push`
4. Send a short handoff (issue comment, Agent Mail, or PR comment) with current state and next step.

