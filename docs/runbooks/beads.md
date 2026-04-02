# Runbook: Beads (`br`) Setup in This Repo

## Expected boring-coding setup (baseline)

- `.beads/issues.jsonl` is tracked in git (canonical export).
- `.beads/beads.db` is local-only and ignored via `.beads/.gitignore`.
- `br sync --flush-only` updates the JSONL export; you then commit it like any other change.

## Current kurt-core situation

This repo currently has a `.beads/` path, but it is not in the standard shape:

- The repo root `.gitignore` ignores `.beads/`.
- The on-disk `.beads/` directory is a git worktree (it contains a `.git` file pointing into `.git/worktrees/...`).

Result: you should NOT rely on `br sync` exports being committed/pushed as part of normal repo work unless you first migrate `.beads/` to the baseline layout above.

## Migration (Destructive, Requires Explicit Approval)

Only do this with explicit instruction, since it involves removing a git worktree directory:

1. Preserve any existing beads artifacts you care about (`issues.jsonl`, `metadata.json`, etc.).
2. Remove the `.beads/` worktree.
3. Create a new plain `.beads/` directory at the repo root.
4. Stop ignoring `.beads/` at the repo root; instead add `.beads/.gitignore` similar to:
   - ignore `*.db`, `*.db-wal`, `*.db-shm`
   - ignore `*.lock`, `last-touched`, `.br_history/`
5. Run `br sync --flush-only`.
6. `git add .beads/issues.jsonl .beads/metadata.json .beads/config.yaml` (as applicable) and commit.

