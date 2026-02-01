# Proposal: Kurt Simplification

**Change ID:** `kurt-simplification`
**Status:** Draft
**Breaking Changes:** Yes

## Summary

Transform Kurt from DBOS-based workflow system to simple tool-based CLI:
- Replace DBOS orchestration with stateless tool primitives + TOML workflows
- Replace PostgreSQL multi-tenancy with Git+Dolt branch isolation
- Enable Claude Code to compose tools via TOML instead of Python code

## Motivation

**Current pain points:**
1. DBOS complexity makes debugging difficult (opaque queue system, resumability edge cases)
2. Python-defined workflows require code changes for new pipelines
3. Database-level multi-tenancy (RLS) complicates local development
4. Agents can't easily compose or modify workflows (requires Python)

**Target state:**
- Agents define workflows in TOML (human-readable, versionable)
- Tools are stateless functions with clear input/output contracts
- Git+Dolt branches provide isolation without database complexity
- Progress/status tracked in Dolt tables (query-able, mergeable)

## Scope

### In Scope

1. **Tool System (Layer 1)** - 7 stateless tool primitives:
   - `map` - Discover URLs/files from sources
   - `fetch` - Fetch content from URLs
   - `llm` - Batch LLM calls with structured output
   - `embed` - Generate vector embeddings
   - `write` - Persist data to Dolt tables
   - `sql` - Query Dolt database
   - `agent` - Run sub-agent (Claude Code subprocess)

2. **Workflow Engine (Layer 2)** - TOML-based orchestration:
   - Parse TOML workflow definitions
   - Build DAG from step dependencies
   - Execute steps with data flow (concat for fan-in)
   - Template interpolation for inputs

3. **Observability** - Replace DBOS tracking:
   - `workflow_runs` table for run status
   - `step_logs` table for step summaries
   - `step_events` table for substep progress (append-only)
   - `llm_traces` table (keep existing, migrate to Dolt)

4. **Git+Dolt Isolation (Layer 3)** - Branch-based multi-tenancy:
   - Synchronized Git + Dolt branching
   - Git hooks for automatic sync
   - `kurt merge` / `kurt pull` for cross-branch operations
   - `kurt doctor` / `kurt repair` for sync validation

### Out of Scope (v1)

- Workflow resumability (checkpoint to Dolt)
- Real-time collaboration (Yjs layer)
- Dolt remote hosting (bucket sync)
- Streaming transport (WebSocket/SSE)

## Migration Impact

| Component | Before | After |
|-----------|--------|-------|
| Workflows | `@DBOS.workflow()` Python | TOML files in `workflows/` |
| Steps | `@DBOS.step()` Python | `Tool.run()` async function |
| Queues | `DBOS.Queue` | `asyncio.Semaphore` |
| Progress | `DBOS.set_event()` | `INSERT INTO step_events` |
| Multi-tenancy | Per-workspace schema | Git+Dolt branches |
| Status | DBOS `workflow_status` | Dolt `workflow_runs` |

**Breaking changes:**
- All existing Python workflows become obsolete
- DBOS tables (`workflow_status`, etc.) no longer used
- Workspace-based isolation replaced with branch-based
- API endpoints for workflow status change

## Dependencies

- **Dolt** - Embedded database with Git-like versioning
- **TOML** - Workflow definition format (Python tomllib)
- **asyncio** - Concurrent tool execution
- **Git hooks** - Auto-sync mechanism

## Risks

| Risk | Mitigation |
|------|------------|
| Git hook bypass (`--no-verify`, fast-forward) | `kurt doctor` detects desync, `kurt repair` fixes |
| Dolt learning curve | Provide `kurt branch`, `kurt merge` wrappers |
| Loss of DBOS resumability | Explicit design decision; add in v2 if needed |
| Agent recursion (agent calling agent) | Block in tool validation |

## Success Criteria

1. Existing map/fetch/research workflows recreated in TOML
2. `kurt run workflow.toml` executes full pipeline
3. `kurt status --follow` streams progress from Dolt
4. `kurt branch create/switch/merge` syncs Git+Dolt
5. Tests pass without DBOS dependency

## Related Specs

- `tool-system` - Tool interface, registry, implementations
- `workflow-engine` - TOML parser, DAG builder, executor
- `observability` - Event tracking, status display
- `git-dolt-isolation` - Branch sync, hooks, conflict detection
