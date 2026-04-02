# Kurt Core Simplification - Task Checklist

## Summary
Remove DBOS completely. Consolidate all logic into tools/. CLI calls tools directly via TOML engine.

## Architecture: Before → After

**BEFORE (DBOS-based):**
```
CLI → workflows/ (@DBOS.workflow) → steps.py (@DBOS.step) → core logic → DBOS tables
```

**AFTER (Tool-based):**
```
CLI → TOML engine (engine/) → tools/ → Dolt tables
```

---

## Phase 1: Fetch Tool Consolidation

### 1.1 Move fetch logic to tools/fetch/
- [x] `workflows/fetch/fetch_trafilatura.py` → `tools/fetch/trafilatura.py`
- [x] `workflows/fetch/fetch_httpx.py` → `tools/fetch/httpx.py`
- [x] `workflows/fetch/fetch_tavily.py` → `tools/fetch/tavily.py`
- [x] `workflows/fetch/fetch_firecrawl.py` → `tools/fetch/firecrawl.py`
- [x] `workflows/fetch/fetch_file.py` → `tools/fetch/file.py`
- [x] `workflows/fetch/fetch_web.py` → `tools/fetch/web.py`
- [x] `workflows/fetch/utils.py` → `tools/fetch/utils.py`
- [x] `workflows/fetch/config.py` → `tools/fetch/config.py`
- [x] `workflows/fetch/models.py` → `tools/fetch/models.py`
- [x] Move tests: `workflows/fetch/tests/*` → `tools/fetch/tests/`
- [x] Create `tools/fetch/__init__.py` with exports

### 1.2 Update fetch imports (IN PROGRESS)
- [ ] Update `fetch_tool.py` imports from `workflows/fetch/` to `tools/fetch/`
- [ ] Update all files importing `FetchDocument`, `FetchStatus`
- [ ] Merge `fetch_tool.py` into `tools/fetch/` or keep as thin wrapper

---

## Phase 2: Map Tool Consolidation

### 2.1 Move map logic to tools/map/
- [x] `workflows/map/map_url.py` → `tools/map/url.py`
- [x] `workflows/map/map_folder.py` → `tools/map/folder.py`
- [x] `workflows/map/map_cms.py` → `tools/map/cms.py`
- [x] `workflows/map/utils.py` → `tools/map/utils.py`
- [x] `workflows/map/config.py` → `tools/map/config.py`
- [x] `workflows/map/models.py` → `tools/map/models.py`
- [x] Move tests: `workflows/map/tests/*` → `tools/map/tests/`
- [x] Create `tools/map/__init__.py` with exports

### 2.2 Update map imports (IN PROGRESS)
- [ ] Update `map_tool.py` imports from `workflows/map/` to `tools/map/`
- [ ] Update all files importing `MapDocument`, `MapStatus`
- [ ] Merge `map_tool.py` into `tools/map/` or keep as thin wrapper

---

## Phase 3: Create New Tools (research, signals, analytics)

### 3.1 Research Tool
- [ ] Create `tools/research/__init__.py` - ResearchTool
- [ ] Wraps `integrations/research/`
- [ ] Move non-DBOS logic from `workflows/research/`

### 3.2 Signals Tool
- [ ] Create `tools/signals/__init__.py` - SignalsTool
- [ ] Wraps `integrations/research/monitoring/`
- [ ] Move non-DBOS logic from `workflows/signals/`

### 3.3 Analytics Tool
- [ ] Create `tools/analytics/__init__.py` - AnalyticsTool
- [ ] Wraps `integrations/domains_analytics/`
- [ ] Move non-DBOS logic from `workflows/domain_analytics/`

---

## Phase 4: Delete DBOS Workflow Wrappers

### 4.1 Delete workflow files
- [ ] `workflows/fetch/steps.py`
- [ ] `workflows/fetch/workflow.py`
- [ ] `workflows/map/steps.py`
- [ ] `workflows/map/workflow.py`
- [ ] `workflows/research/steps.py`
- [ ] `workflows/research/workflow.py`
- [ ] `workflows/signals/steps.py`
- [ ] `workflows/signals/workflow.py`
- [ ] `workflows/domain_analytics/steps.py`
- [ ] `workflows/domain_analytics/workflow.py`
- [ ] `workflows/queries.py`

### 4.2 Clean up empty workflow directories
- [ ] Remove `workflows/fetch/` (after moving all files)
- [ ] Remove `workflows/map/` (after moving all files)
- [ ] Remove `workflows/research/` (after creating tool)
- [ ] Remove `workflows/signals/` (after creating tool)
- [ ] Remove `workflows/domain_analytics/` (after creating tool)

---

## Phase 5: Delete Core DBOS Modules

### 5.1 Delete DBOS core files
- [ ] `core/dbos.py`
- [ ] `core/runner.py`
- [ ] `core/_worker.py`
- [ ] `core/llm_step.py`
- [ ] `core/embedding_step.py`
- [ ] `core/save_step.py`
- [ ] `core/workflow_utils.py`
- [ ] `core/tracing.py`

### 5.2 Delete DBOS tests
- [ ] `core/tests/test_background_integration.py`
- [ ] `core/tests/test_save_step.py`
- [ ] `core/tests/test_embedding_step.py`
- [ ] `core/tests/test_llm_step.py`
- [ ] `core/tests/test_tracing.py`
- [ ] `core/tests/test_worker.py`
- [ ] Clean up `core/tests/conftest.py` (remove DBOS fixtures)

### 5.3 Update core/__init__.py exports
- [ ] Remove DBOS-related exports
- [ ] Keep: display, hooks, mocking, model_utils

---

## Phase 6: CLI Updates

### 6.1 Move fetch CLI to tools/fetch/
- [ ] Move `workflows/fetch/cli.py` → `tools/fetch/cli.py`
- [ ] Update imports to use `tools/fetch/` modules
- [ ] Update `cli/main.py` to import from `tools/fetch/cli`
- [ ] Remove DBOS dependencies (no workflow launching)

### 6.2 Move map CLI to tools/map/
- [ ] Move `workflows/map/cli.py` → `tools/map/cli.py`
- [ ] Update imports to use `tools/map/` modules
- [ ] Update `cli/main.py` to import from `tools/map/cli`
- [ ] Remove DBOS dependencies (no workflow launching)

### 6.3 Update documents CLI
- [ ] Update `documents/cli.py` imports from `workflows/` to `tools/`
- [ ] Remove references to `workflows/fetch/cli` and `workflows/map/cli`

### 6.4 Delete legacy DBOS CLI
- [ ] `cli/workflows.py` (DBOS workflow commands)
- [ ] `cli/tests/test_workflows.py`

### 6.5 Update main.py
- [ ] Remove `workflows` lazy subcommand import
- [ ] Keep `workflow` (TOML-based)
- [ ] Update `content` subcommand routing
- [ ] Update direct tool commands (map, fetch) to use tools/ CLIs

---

## Phase 7: Update Agents Workflow

### 7.1 Remove DBOS from executor.py
- [ ] Remove `@DBOS.workflow()` decorator
- [ ] Remove `@DBOS.step()` decorators
- [ ] Use `observability/` for tracking
- [ ] Update tests

### 7.2 Remove DBOS from scheduler.py
- [ ] Remove DBOS cron scheduling
- [ ] Implement alternative (or remove if not needed)

---

## Phase 8: Update Imports

### 8.1 Update tools/registry.py
- [ ] Import from new tool locations

### 8.2 Update documents/
- [ ] Update imports from `workflows/fetch/models` → `tools/fetch/models`
- [ ] Update imports from `workflows/map/models` → `tools/map/models`

### 8.3 Update status/
- [ ] Update imports from `workflows/fetch/models` → `tools/fetch/models`
- [ ] Update imports from `workflows/map/models` → `tools/map/models`

### 8.4 Update cli/show/
- [ ] Remove DBOS-related show commands
- [ ] Update remaining imports

---

## Phase 9: Verification

### 9.1 Run tests
- [ ] `uv run pytest src/kurt/tools/ -v`
- [ ] `uv run pytest src/kurt/engine/tests/ -v`
- [ ] `uv run pytest src/kurt/observability/tests/ -v`

### 9.2 CLI smoke tests
- [ ] `kurt workflow run examples/simple.toml --dry-run`
- [ ] `kurt map --help`
- [ ] `kurt fetch --help`

### 9.3 Verify no DBOS imports remain
- [ ] `grep -r "from dbos" src/kurt/ --include="*.py"` should return nothing

---

## Notes

### Files to KEEP in core/
- `core/__init__.py` - Update exports
- `core/display.py` - Rich progress display
- `core/hooks.py` - Hook system
- `core/mocking.py` - Mock LLM for tests
- `core/model_utils.py` - SQLModel utilities
- `core/status.py` - UPDATE: query Dolt instead of DBOS
- `core/background.py` - UPDATE: use asyncio, not DBOS

### Files to KEEP in workflows/
Only `workflows/agents/` - runs Claude CLI subprocess:
- `parser.py` - Markdown workflow parser
- `registry.py` - Workflow discovery
- `executor.py` - UPDATE: remove DBOS
- `scheduler.py` - UPDATE: remove DBOS
- `cli.py` - CLI commands
- `tool_cli.py` - Tool tracking
