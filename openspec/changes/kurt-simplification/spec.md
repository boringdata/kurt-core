# Kurt Core Simplification - Migration Spec

## Overview

**Goal**: Remove DBOS completely. Consolidate all logic into `tools/`. CLI calls tools directly via TOML engine.

**Status**: In Progress

---

## Architecture Change

### Before (DBOS-based)
```
CLI commands (kurt map, kurt fetch)
    ↓
workflows/<name>/cli.py
    ↓
@DBOS.workflow() in workflow.py
    ↓
@DBOS.step() in steps.py
    ↓
Core logic (fetch engines, map discovery)
    ↓
DBOS tables (workflow_status, workflow_events, workflow_streams)
+ Domain tables (map_documents, fetch_documents)
```

### After (Tool-based)
```
CLI commands (kurt map, kurt fetch)
    ↓
tools/<name>/cli.py
    ↓
ToolClass.run() in tools/<name>/
    ↓
Core logic (same fetch engines, map discovery)
    ↓
Dolt tables only (map_documents, fetch_documents, workflow_runs, step_events)
```

---

## Module Structure

### Current State
```
src/kurt/
├── core/                      # DBOS wrappers (TO DELETE)
│   ├── dbos.py               # DBOS init
│   ├── runner.py             # DBOS runner
│   ├── llm_step.py           # @LLMStep wrapper
│   ├── embedding_step.py     # @EmbeddingStep wrapper
│   └── ...
│
├── workflows/                 # DBOS workflows (TO MIGRATE)
│   ├── fetch/
│   │   ├── cli.py            # CLI → move to tools/
│   │   ├── workflow.py       # @DBOS.workflow → DELETE
│   │   ├── steps.py          # @DBOS.step → DELETE
│   │   ├── models.py         # SQLModel → move to tools/
│   │   ├── config.py         # Config → move to tools/
│   │   ├── utils.py          # Logic → move to tools/
│   │   └── fetch_*.py        # Engines → move to tools/
│   ├── map/                   # Same pattern
│   ├── research/
│   ├── signals/
│   ├── domain_analytics/
│   └── agents/                # KEEP (special case)
│
├── tools/                     # Tool implementations (TARGET)
│   ├── fetch_tool.py         # FetchTool class
│   ├── map_tool.py           # MapTool class
│   └── ...
```

### Target State
```
src/kurt/
├── core/                      # Minimal utilities only
│   ├── display.py            # Rich progress
│   ├── hooks.py              # Hook system
│   ├── mocking.py            # Test mocking
│   └── model_utils.py        # SQLModel helpers
│
├── tools/                     # ALL tool logic here
│   ├── fetch/
│   │   ├── __init__.py       # Exports FetchTool, models
│   │   ├── cli.py            # CLI commands
│   │   ├── tool.py           # FetchTool class
│   │   ├── models.py         # FetchDocument, FetchStatus
│   │   ├── config.py         # FetchConfig
│   │   ├── utils.py          # Shared utilities
│   │   ├── trafilatura.py    # Engine
│   │   ├── httpx.py          # Engine
│   │   ├── tavily.py         # Engine
│   │   ├── firecrawl.py      # Engine
│   │   ├── file.py           # Local file fetcher
│   │   ├── web.py            # Web fetcher
│   │   └── tests/
│   │
│   ├── map/
│   │   ├── __init__.py       # Exports MapTool, models
│   │   ├── cli.py            # CLI commands
│   │   ├── tool.py           # MapTool class
│   │   ├── models.py         # MapDocument, MapStatus
│   │   ├── config.py         # MapConfig
│   │   ├── utils.py          # Shared utilities
│   │   ├── url.py            # URL discovery
│   │   ├── folder.py         # Folder discovery
│   │   ├── cms.py            # CMS discovery
│   │   └── tests/
│   │
│   ├── research/
│   │   ├── __init__.py       # ResearchTool
│   │   ├── cli.py
│   │   └── models.py
│   │
│   ├── signals/
│   │   ├── __init__.py       # SignalsTool
│   │   ├── cli.py
│   │   └── models.py
│   │
│   ├── analytics/
│   │   ├── __init__.py       # AnalyticsTool
│   │   ├── cli.py
│   │   └── models.py
│   │
│   ├── llm/                   # Existing
│   ├── embed/                 # Existing
│   ├── write/                 # Existing
│   ├── sql/                   # Existing
│   ├── agent/                 # Existing
│   │
│   ├── base.py               # Tool base class
│   ├── context.py            # ToolContext
│   ├── registry.py           # Tool registration
│   └── errors.py
│
├── workflows/                 # Only agents (special case)
│   └── agents/
│       ├── parser.py         # Markdown workflow parser
│       ├── registry.py       # Workflow discovery
│       ├── executor.py       # Claude subprocess (no DBOS)
│       ├── scheduler.py      # Cron (no DBOS)
│       └── cli.py
│
├── observability/             # Tracking (replaces DBOS events)
│   ├── lifecycle.py          # WorkflowLifecycle
│   ├── streaming.py          # Event streaming
│   └── traces.py             # LLM tracing
│
├── documents/                 # Document registry (unchanged)
├── status/                    # Status queries (update imports)
├── integrations/              # External adapters (unchanged)
├── db/                        # Database layer (unchanged)
├── engine/                    # TOML workflow engine (unchanged)
└── cli/                       # CLI entry points (update imports)
```

---

## Database Tables

### Tables to KEEP (in Dolt)
| Table | Description |
|-------|-------------|
| `map_documents` | Discovered sources (URLs, files) |
| `fetch_documents` | Fetched content results |
| `research_documents` | Research query results |
| `monitoring_signals` | Signal monitoring results |
| `analytics_domains` | Domain analytics |
| `page_analytics` | Page-level analytics |
| `llm_traces` | LLM call traces |
| `workflow_runs` | Workflow execution metadata |
| `step_logs` | Step-level logs |
| `step_events` | Progress events |

### Tables to DELETE (DBOS internal)
| Table | Replacement |
|-------|-------------|
| `workflow_status` | `workflow_runs` |
| `workflow_events` | `step_events` |
| `workflow_streams` | `step_events` |
| `operation_outputs` | Not needed |
| `notifications` | Not needed |
| `scheduler_state` | Custom if needed |

---

## Files to DELETE

### core/ (DBOS wrappers)
```
src/kurt/core/
├── dbos.py                    # DBOS init
├── runner.py                  # DBOS runner
├── _worker.py                 # DBOS worker
├── llm_step.py                # @LLMStep
├── embedding_step.py          # @EmbeddingStep
├── save_step.py               # @SaveStep
├── workflow_utils.py          # run_workflow()
├── tracing.py                 # DBOS tracing
└── tests/
    ├── test_background_integration.py
    ├── test_save_step.py
    ├── test_embedding_step.py
    ├── test_llm_step.py
    ├── test_tracing.py
    └── test_worker.py
```

### workflows/ (DBOS workflows)
```
src/kurt/workflows/
├── fetch/
│   ├── steps.py               # @DBOS.step wrappers
│   ├── workflow.py            # @DBOS.workflow
│   └── __init__.py            # Update to re-export from tools/
├── map/
│   ├── steps.py
│   ├── workflow.py
│   └── __init__.py
├── research/
│   ├── steps.py
│   ├── workflow.py
│   └── (move rest to tools/research/)
├── signals/
│   ├── steps.py
│   ├── workflow.py
│   └── (move rest to tools/signals/)
├── domain_analytics/
│   ├── steps.py
│   ├── workflow.py
│   └── (move rest to tools/analytics/)
└── queries.py                 # DBOS queries
```

### cli/ (legacy)
```
src/kurt/cli/
├── workflows.py               # DBOS workflow commands
└── tests/test_workflows.py
```

---

## Files to MOVE

### workflows/fetch/ → tools/fetch/
| From | To |
|------|-----|
| `workflows/fetch/fetch_trafilatura.py` | `tools/fetch/trafilatura.py` |
| `workflows/fetch/fetch_httpx.py` | `tools/fetch/httpx.py` |
| `workflows/fetch/fetch_tavily.py` | `tools/fetch/tavily.py` |
| `workflows/fetch/fetch_firecrawl.py` | `tools/fetch/firecrawl.py` |
| `workflows/fetch/fetch_file.py` | `tools/fetch/file.py` |
| `workflows/fetch/fetch_web.py` | `tools/fetch/web.py` |
| `workflows/fetch/utils.py` | `tools/fetch/utils.py` |
| `workflows/fetch/config.py` | `tools/fetch/config.py` |
| `workflows/fetch/models.py` | `tools/fetch/models.py` |
| `workflows/fetch/cli.py` | `tools/fetch/cli.py` |
| `workflows/fetch/tests/*` | `tools/fetch/tests/` |

### workflows/map/ → tools/map/
| From | To |
|------|-----|
| `workflows/map/map_url.py` | `tools/map/url.py` |
| `workflows/map/map_folder.py` | `tools/map/folder.py` |
| `workflows/map/map_cms.py` | `tools/map/cms.py` |
| `workflows/map/utils.py` | `tools/map/utils.py` |
| `workflows/map/config.py` | `tools/map/config.py` |
| `workflows/map/models.py` | `tools/map/models.py` |
| `workflows/map/cli.py` | `tools/map/cli.py` |
| `workflows/map/tests/*` | `tools/map/tests/` |

### Other workflows → tools/
| Workflow | Target | Notes |
|----------|--------|-------|
| `workflows/research/` | `tools/research/` | Wraps integrations/research/ |
| `workflows/signals/` | `tools/signals/` | Wraps integrations/research/monitoring/ |
| `workflows/domain_analytics/` | `tools/analytics/` | Wraps integrations/domains_analytics/ |

---

## Import Updates

### Files importing from workflows/fetch/models
```python
# BEFORE
from kurt.workflows.fetch.models import FetchDocument, FetchStatus

# AFTER
from kurt.tools.fetch.models import FetchDocument, FetchStatus
# OR
from kurt.tools.fetch import FetchDocument, FetchStatus
```

**Files to update:**
- `src/kurt/db/models.py`
- `src/kurt/status/queries.py`
- `src/kurt/documents/models.py`
- `src/kurt/documents/registry.py`
- `src/kurt/documents/filtering.py`
- `src/kurt/documents/cli.py`
- `src/kurt/documents/__init__.py`
- `src/kurt/documents/tests/*`
- `src/kurt/tools/fetch_tool.py`
- `src/kurt/cli/tests/test_admin.py`

### Files importing from workflows/map/models
```python
# BEFORE
from kurt.workflows.map.models import MapDocument, MapStatus

# AFTER
from kurt.tools.map.models import MapDocument, MapStatus
# OR
from kurt.tools.map import MapDocument, MapStatus
```

**Files to update:**
- `src/kurt/db/models.py`
- `src/kurt/status/queries.py`
- `src/kurt/documents/models.py`
- `src/kurt/documents/registry.py`
- `src/kurt/documents/filtering.py`
- `src/kurt/documents/cli.py`
- `src/kurt/documents/__init__.py`
- `src/kurt/documents/tests/*`
- `src/kurt/tools/map_tool.py`

### Files importing from workflows/fetch/utils
```python
# BEFORE
from kurt.workflows.fetch.utils import extract_with_trafilatura

# AFTER
from kurt.tools.fetch.utils import extract_with_trafilatura
```

**Files to update:**
- `src/kurt/tools/fetch_tool.py`
- `src/kurt/documents/__init__.py`

---

## CLI Changes

### Before
```
kurt
├── content
│   ├── map          # → workflows/map/cli.py
│   ├── fetch        # → workflows/fetch/cli.py
│   └── show         # → documents/cli.py
├── map              # Alias → workflows/map/cli.py
├── fetch            # Alias → workflows/fetch/cli.py
├── workflows        # → cli/workflows.py (DBOS commands)
├── workflow         # → cli/workflow.py (TOML engine)
└── ...
```

### After
```
kurt
├── content
│   ├── map          # → tools/map/cli.py
│   ├── fetch        # → tools/fetch/cli.py
│   └── show         # → documents/cli.py
├── map              # Alias → tools/map/cli.py
├── fetch            # Alias → tools/fetch/cli.py
├── run              # → cli/workflow.py (TOML engine)
├── workflow status  # → cli/workflow.py (query workflow_runs)
├── workflow logs    # → cli/workflow.py (query step_events)
├── status           # → status/cli.py (project status - unchanged)
└── ...
```

### CLI main.py updates
```python
# BEFORE
from kurt.workflows.fetch.cli import fetch_cmd
from kurt.workflows.map.cli import map_cmd

# AFTER
from kurt.tools.fetch.cli import fetch_cmd
from kurt.tools.map.cli import map_cmd
```

---

## agents/ Workflow (Special Case)

The `workflows/agents/` module is **different** - it runs Claude CLI as a subprocess, not DBOS workflows. However, it still uses DBOS decorators for tracking.

### Changes needed:
1. Remove `@DBOS.workflow()` from `executor.py`
2. Remove `@DBOS.step()` decorators
3. Use `observability/lifecycle.py` for tracking instead
4. Store results in `workflow_runs` and `step_events` tables

### Keep as-is:
- `parser.py` - Markdown frontmatter parsing
- `registry.py` - File-based workflow discovery
- `cli.py` - CLI commands
- `tool_cli.py` - Tool tracking hooks

---

## Migration Steps

### Phase 1: Move fetch/map files ✅
```bash
# Already done
git mv src/kurt/workflows/fetch/fetch_*.py src/kurt/tools/fetch/
git mv src/kurt/workflows/fetch/{utils,config,models}.py src/kurt/tools/fetch/
git mv src/kurt/workflows/fetch/tests/* src/kurt/tools/fetch/tests/
git mv src/kurt/workflows/map/map_*.py src/kurt/tools/map/
git mv src/kurt/workflows/map/{utils,config,models}.py src/kurt/tools/map/
git mv src/kurt/workflows/map/tests/* src/kurt/tools/map/tests/
```

### Phase 2: Create __init__.py exports ✅
```bash
# Already done
# tools/fetch/__init__.py - exports FetchDocument, FetchStatus
# tools/map/__init__.py - exports MapDocument, MapStatus
```

### Phase 3: Update imports (IN PROGRESS)
```bash
# Update all files importing from workflows/fetch/models
# Update all files importing from workflows/map/models
# Update fetch_tool.py and map_tool.py
```

### Phase 4: Move CLI files
```bash
git mv src/kurt/workflows/fetch/cli.py src/kurt/tools/fetch/cli.py
git mv src/kurt/workflows/map/cli.py src/kurt/tools/map/cli.py
# Update cli/main.py imports
```

### Phase 5: Create research/signals/analytics tools
```bash
mkdir -p src/kurt/tools/{research,signals,analytics}
# Create tool wrappers over integrations/
```

### Phase 6: Delete DBOS files
```bash
rm src/kurt/workflows/fetch/{steps,workflow}.py
rm src/kurt/workflows/map/{steps,workflow}.py
rm src/kurt/workflows/{research,signals,domain_analytics}/{steps,workflow}.py
rm src/kurt/workflows/queries.py
rm src/kurt/core/{dbos,runner,_worker,llm_step,embedding_step,save_step,workflow_utils,tracing}.py
rm src/kurt/cli/workflows.py
```

### Phase 7: Update agents/ (remove DBOS)
```bash
# Edit executor.py - remove DBOS decorators
# Edit scheduler.py - remove DBOS cron
# Use observability/ for tracking
```

### Phase 8: Clean up empty directories
```bash
rmdir src/kurt/workflows/{fetch,map,research,signals,domain_analytics}
# Keep workflows/agents/
```

### Phase 9: Verification
```bash
# No DBOS imports
grep -r "from dbos" src/kurt/ --include="*.py"
# Should return nothing

# Tests pass
uv run pytest src/kurt/tools/ -v
uv run pytest src/kurt/engine/tests/ -v

# CLI works
kurt map --help
kurt fetch --help
kurt run examples/simple.toml --dry-run
```

---

## Background Execution (Tool Runner)

Background runs are handled by per-run subprocesses (no daemon). The CLI:
1. Creates a `workflow_runs` record with status `pending` and metadata (including priority)
2. Spawns a detached subprocess to execute the tool
3. The subprocess updates `workflow_runs`, `step_logs`, and `step_events` via `WorkflowLifecycle`

Priority is stored in `workflow_runs.metadata` for future scheduling (no queue yet).

---

## Rollback Plan

If issues arise, the migration can be rolled back by:

1. Reverting git commits (files were moved with `git mv`)
2. Restoring deleted files from git history
3. Re-adding DBOS to pyproject.toml dependencies

---

## Dependencies

### Remove from pyproject.toml
```toml
# Remove
dbos = "..."
```

### Keep
```toml
# Already present
sqlmodel = "..."
dolt-integrations = "..."  # If using Dolt
httpx = "..."
trafilatura = "..."
```

---

## Timeline

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Done | Move fetch/map files to tools/ |
| 2 | ✅ Done | Create __init__.py exports |
| 3 | 🔄 In Progress | Update all imports |
| 4 | ⏳ Pending | Move CLI files |
| 5 | ⏳ Pending | Create research/signals/analytics tools |
| 6 | ⏳ Pending | Delete DBOS files |
| 7 | ⏳ Pending | Update agents/ workflow |
| 8 | ⏳ Pending | Clean up empty directories |
| 9 | ⏳ Pending | Verification |
