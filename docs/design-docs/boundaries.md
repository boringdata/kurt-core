# BOUNDARIES (Fixed Constraints)

Use normative language: MUST / MUST NOT (hard), SHOULD / SHOULD NOT (strong defaults).

## Safety & Destructive Ops

- Agents MUST NOT run destructive ops without explicit instruction:
  `rm -rf`, `git reset --hard`, `git clean -fd`, force-push, history rewrites.
- Agents MUST NOT commit secrets into git.
- Agents MUST redact secrets from logs and evidence.
- Agents MUST NOT run broad rewrite scripts (codemods, "fix everything") without approval.

## Repo Boundaries

- Agents MUST keep changes small and incremental.
- Agents MUST NOT introduce new tooling/frameworks without an explicit plan update.
- Agents MUST follow the repo structure in `docs/ARCHITECTURE.md`.
- Agents MUST prefer editing existing files over creating new variants (`*_v2.*`).
- Agents MUST NOT delete files unless they have explicit written permission.

## Evidence

- Agents MUST write full run evidence under `.agent-evidence/` (not committed to git).
- Agents MUST link evidence paths in the issue comment or PR description.

## Plans

- Active work SHOULD have a plan in `docs/exec-plans/active/`.
- Completed work SHOULD move the plan to `docs/exec-plans/completed/`.

## Gates

- Every phase/task SHOULD have a gate: verification commands + pass criteria.
- If a gate is skipped, it MUST be explicit with reason and risk.

