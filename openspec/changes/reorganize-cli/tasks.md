# Tasks: CLI Reorganization

## Phase 1: Create New Command Groups

- [ ] 1.1 Create unified `workflow` group (merge agents + workflow)
  - `workflow run` - Run TOML or MD workflow
  - `workflow test` - Test workflow
  - `workflow logs` - View logs
  - `workflow cancel` - Cancel workflow
  - `workflow list` - List all workflows (.toml + .md)
  - `workflow show` - Show workflow details
  - `workflow validate` - Validate workflow file
  - `workflow create` - Create new workflow
  - `workflow history` - Run history

- [ ] 1.2 Create unified `tool` group
  - `tool map` - Discover URLs
  - `tool fetch` - Fetch content
  - `tool llm` - LLM processing
  - `tool embed` - Generate embeddings
  - `tool sql` - Query database
  - `tool save` - Save to DB table (rename from write)
  - `tool research` - Research queries
  - `tool signals` - Signal monitoring

- [ ] 1.3 Create `docs` group (rename from `content`)
  - `docs list`, `docs get`, `docs delete`

- [ ] 1.4 Create `sync` group for Git+Dolt
  - `sync pull`, `sync push`, `sync branch`, `sync merge`

- [ ] 1.5 Simplify `connect` group (CMS/analytics only)
  - `connect cms`, `connect analytics`
  - Remove research/signals (now in tool)

- [ ] 1.6 Reorganize `admin` group
  - `admin db`, `admin migrate`, `admin telemetry`, `admin update`

- [ ] 1.7 Rename `show` to `help`

## Phase 2: Add Backwards Compatibility Aliases

- [ ] 2.1 Create alias mechanism in LazyGroup
- [ ] 2.2 Add aliases for old command names:
  - `content` → `docs`
  - `integrations` → `connect`
  - `agents` → `workflow` (with subcommand mapping)
  - `branch` → `sync branch`
  - `pull` → `sync pull`
  - `push` → `sync push`
  - `merge` → `sync merge`
  - `show` → `help`
  - `map` → `tool map`
  - `fetch` → `tool fetch`
  - `run` → `workflow run`
  - `write` → `tool save`

- [ ] 2.3 Add deprecation warnings when aliases used

## Phase 3: Update Documentation

- [ ] 3.1 Update AGENTS.md with new command names
- [ ] 3.2 Update CLAUDE.md
- [ ] 3.3 Update `help` subcommands to reference new structure

## Phase 4: Clean Up (Future Major Version)

- [ ] 4.1 Remove old aliases
- [ ] 4.2 Update all references

## Validation

- [ ] `kurt --help` shows ~12 commands
- [ ] All old command paths still work (with warnings)
- [ ] Tests pass
- [ ] Demo project works with new commands
