# Beads Reference

Beads are the unit of work. The lifecycle is driven by bead state, plus evidence and a single
explicit `NEXT` transition written into the bead comment.

## Canonical STATE values

- `impl:queued`
- `impl:done`
- `proof:failed`
- `proof:passed`
- `review:failed`
- `review:passed`

## Canonical NEXT values

- `impl`
- `proof`
- `review`
- `none`

## Transitions

- `impl:queued` -> `impl:done`
- `impl:done` -> `proof:passed` -> `review:passed` (ready to close)
- `impl:done` -> `proof:failed` -> back to `impl:done`
- `proof:passed` -> `review:failed` -> back to `impl:queued`

## Who closes a bead?

Default closure rule:
- Reviewer writes `STATE: review:passed` / `NEXT: none`.
- Bead is closed later by whoever lands the change, once commits/PR exist.

If landing pointers exist at review time (`COMMITS:` and/or `PR:` in bead comments), the Reviewer may close immediately:
`br close <bead-id> --reason "implemented + verified"`

## Definition of Done (DoD)

A bead can be closed ONLY when all are true:

- Acceptance criteria met (explicitly verified).
- Verification executed (tests/lints/manual checks).
- Changes are committed with bead ID in commit message.
- Evidence is recorded in the bead comment (see `docs/workflow/EVIDENCE.md`).

## Review gate

Default rule: implementers do NOT close their own beads.

1. Implementer adds evidence comment with `NEXT: review`.
2. Reviewer re-verifies quickly (run tests / inspect diff).
3. Reviewer closes: `br close <bead-id> --reason "implemented + verified"`

Self-close is allowed ONLY if: you ran verification, ran an independent review (different model/agent), and write `SELF-CLOSED` in the evidence comment.

## Stale bead recovery

A bead is considered stale if its latest comment is >2 hours old and `NEXT` points to a role
that hasn't acted.

Recovery protocol:

1. Any agent may reclaim a stale bead by appending a comment:
   `STATE: <current state>`, `NEXT: <current next>`, `SUMMARY: reclaimed - previous worker inactive`.
2. If `impl:done, NEXT: proof` - re-run proof from scratch (evidence is append-only, no conflict).
3. If `impl:queued, NEXT: impl` with partial work on disk - inspect latest `continuation.md` and continue.
4. If in doubt, bounce to `impl:queued` with `NEXT: impl` (safe restart).

## Bead format requirements

Every bead created during decomposition SHOULD include:

1. Goal (1-3 lines)
2. Scope / non-goals (bullets)
3. Acceptance checklist:
   - [ ] Implementation complete (files/paths + what changed)
   - [ ] Gates passed (exact commands) OR explicit skip reason
   - [ ] Evidence captured under `.agent-evidence/` with pointers
   - [ ] Docs updated if needed (`docs/ARCHITECTURE.md` / ADR / runbook / `docs/QUALITY.md`) OR N/A
4. Gate commands section with exact commands + pass criteria
5. Evidence section describing what files/logs to write in `.agent-evidence/`

Notes:

- Do NOT include review in the bead checklist (review happens in the review stage).
- Keep beads small: <= ~2 hours of agent work.
- Minimize file overlap between parallel beads.

