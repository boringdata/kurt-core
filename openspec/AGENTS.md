# Agents

## Repository Map

| Repo | Location | Branch | Workflow |
|------|----------|--------|----------|
| **kurt-cloud** | `.` | `main` | Direct commits to main |
| **kurt-core** | `../kurt-core-neon-migration` | `neon-migration` | PR for review |

### Git Workflow

**Kurt-Cloud:** Work directly on `main`
```bash
cd /Users/julien/Documents/wik/wikumeo/projects/kurt-cloud
# Make changes, commit, push
```

**Kurt-Core:** Work on branch, create PR
```bash
cd ../kurt-core-neon-migration
git branch  # Should show: * neon-migration

# After all changes complete:
git push origin neon-migration
gh pr create --title "feat: Neon migration support" --base main
```

## Active Changes

### migrate-to-neon
**Status**: In Progress
**Scope**: kurt-cloud (Phase 2) + kurt-core (Phase 3)

Migrate from Supabase (Auth + Postgres) to Neon (Auth + Postgres) for:
- Scale-to-zero compute
- Direct SQL access with JWT
- Remove REST API endpoints (use direct SQL + RLS)
- Database-level rate limiting
