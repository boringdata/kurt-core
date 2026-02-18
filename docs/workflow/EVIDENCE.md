# EVIDENCE

Evidence is NOT committed to git. It lives under `.agent-evidence/` at the repo root.

## Directory layout

```text
.agent-evidence/beads/<bead-id>/
  <event-dir>/
    summary.md            (optional)
    continuation.md       (impl)
    diff.patch            (impl)
    proof.md              (proof, showboat transcript)
    failure.md            (proof fail only)
    review.txt            (review)
    artifacts/            (optional, for many files)
      logs/
      screenshots/
      showboat/
      diffs/
      notes/
```

## Naming

- `<event-dir>`: `YYYYMMDDTHHMMSSZ_<harness>_<session-id>`
  - example: `20260218T093012Z_codex-cli_abc123`
- `EVIDENCE-SESSION`: `<harness>_<session-id>` - stable identifier across events in the same session.

## Rules

- Append-only: never edit/delete old evidence; always create a new event directory.
- Canonical lifecycle log is the issue comment (via `br comments add`), not local state files.
- Every issue comment MUST include `EVIDENCE-SESSION`.

## Issue comment format

Each role appends an issue comment with:

```text
STATE: <impl:queued|impl:done|proof:failed|proof:passed|review:failed|review:passed>
NEXT: <impl|proof|review|none>
EVIDENCE-SESSION: <harness>_<session-id>
EVIDENCE: .agent-evidence/beads/<bead-id>/<event-dir>/
SUMMARY: <1-3 lines>
AGENT: <codex|claude|gemini|...>
HARNESS: <codex-cli|claude-code|gemini-cli|...>
SESSION-ID: <opaque string; required>
```

Optional fields (when applicable):
- `GATES: <exact commands + pass/fail>` (proof)
- `COMMITS: <sha1,sha2>` (if commits were made)
- `PR: <url>` (if a PR exists)

## Typical artifacts by phase

- Implementer: `diff.patch`, `continuation.md`
- Prover: `proof.md` (Showboat transcript), screenshots (if applicable), `failure.md` (on failure)
- Reviewer: `review.txt`

## Required pointer

Every issue comment MUST include:
- `EVIDENCE-SESSION: <harness>_<session-id>`
- `EVIDENCE: .agent-evidence/beads/<bead-id>/<event-dir>/`

