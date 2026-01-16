---
description: kurt_new core framework for DBOS workflow creation
---

# kurt_new Core Framework Guide

This guide explains how to build DBOS workflows using the kurt_new core abstractions.
Keep workflows minimal, durable, and observable. Use DBOS for orchestration and
use kurt_new core for LLM batch steps and tracing.

## Database Modes

Kurt supports three database modes via `DATABASE_URL` in `kurt.config`:

1. **SQLite (Local Development)**
   ```
   DATABASE_URL="sqlite:///.kurt/kurt.sqlite"
   ```
   - File-based database for local development
   - No server required
   - Single-user, local files only
   - Views and JOINs work natively

2. **PostgreSQL (Direct Connection)**
   ```
   DATABASE_URL="postgresql://user:pass@host:5432/dbname"
   ```
   - Direct PostgreSQL connection
   - Full SQL support including views and JOINs
   - Use for self-hosted PostgreSQL or local Postgres

3. **Kurt Cloud (PostgREST via Supabase)**
   ```
   DATABASE_URL="kurt"
   ```
   - Uses PostgREST API (not direct SQL)
   - Automatic multi-tenancy via RLS
   - Requires `kurt cloud login` for authentication
   - JOINs use database VIEWs (e.g., `document_lifecycle`)
   - PostgREST quirks: returns string 'null' for NULL values

### Database Views for Cloud Mode

When using Kurt Cloud (PostgREST), complex JOINs must be pre-defined as database VIEWs:
- **document_lifecycle**: Joins `map_documents` ⟕ `fetch_documents`
- Views are detected in `SupabaseSession._exec_join_query()` and used automatically
- RLS policies apply to views automatically

### Cloud Mode Architecture: CLI → Web API → Queries

**Problem**: PostgREST API cannot execute arbitrary SQLAlchemy queries (COUNT, aggregations, complex JOINs fail).

**Solution**: CLI routes to web API in cloud mode, which runs SQLAlchemy queries server-side.

**Architecture**:
```
Local Mode:
  kurt status → queries.py → SQLite/PostgreSQL
  kurt serve → web/api/server.py (web UI)

Cloud Mode:
  kurt status → HTTP → web/api/server.py → queries.py → PostgreSQL
  Web UI → HTTP → web/api/server.py → queries.py → PostgreSQL
```

**Module Structure** (example: `src/kurt/status/`):
```
status/
├── __init__.py     # Public exports
├── cli.py          # Click commands - routes based on is_cloud_mode()
└── queries.py      # SQLAlchemy queries (used by web API)

documents/
├── __init__.py     # Public exports
├── cli.py          # Click commands - routes based on is_cloud_mode()
├── registry.py     # DocumentRegistry class with list(), get(), count()
├── filtering.py    # DocumentFilters
└── models.py       # DocumentView dataclass

web/api/
└── server.py       # FastAPI app with ALL endpoints (CLI + web UI)
```

**Key points**:
- `queries.py` contains pure SQLAlchemy - works in all modes
  - For simple modules (status), create dedicated `queries.py`
  - For complex modules (documents), use existing registry/service classes directly
- `cli.py` checks `is_cloud_mode()` and routes to queries/registry or web API
- `web/api/server.py` defines ALL endpoints (used by CLI and web UI)
- Kurt-cloud hosts `web/api/server.py` (single FastAPI app)
- **No PostgREST emulation** - direct PostgreSQL on backend
- **Single API** - CLI and web UI use same endpoints

**Benefits**:
- ✅ Single source of truth for SQL queries
- ✅ Single API definition (`web/api/server.py`)
- ✅ No duplication between CLI API and web UI API
- ✅ `kurt serve` uses same API that kurt-cloud hosts
- ✅ Better performance (one HTTP call vs multiple PostgREST queries)

**When adding new features**:
1. Use existing registry/service classes OR create `module/queries.py` with SQLAlchemy queries
2. Add `/api/module` endpoint to `web/api/server.py` that calls queries/registry directly
3. Create `module/cli.py` that routes to queries/registry (local) or API (cloud)

### Multi-Tenancy with RLS (Row Level Security)

**Overview**: Kurt uses PostgreSQL RLS for multi-tenant data isolation in cloud mode.

**Architecture**:
```
1. JWT Token → 2. Middleware → 3. Context → 4. Session → 5. PostgreSQL RLS
   (user_id,       set_workspace_   (contextvars)  SET LOCAL    (auto-filter)
    workspace_id)  context()                       variables
```

**Implementation**:

```python
# 1. Middleware (web/api/auth.py) extracts JWT claims
async def auth_middleware_setup(request, call_next):
    user_data = verify_token_with_supabase(token)
    user_id = user_data.get("id")
    workspace_id = user_data.get("user_metadata", {}).get("workspace_id")

    # 2. Set workspace context (thread-local via contextvars)
    set_workspace_context(workspace_id=workspace_id, user_id=user_id)

    try:
        response = await call_next(request)
        return response
    finally:
        clear_workspace_context()

# 3. managed_session() reads context and sets PostgreSQL variables
@contextmanager
def managed_session():
    session = get_session()
    try:
        # Calls set_rls_context(session) which does:
        # session.execute(text("SET LOCAL app.user_id = :user_id"), {"user_id": ...})
        # session.execute(text("SET LOCAL app.workspace_id = :workspace_id"), {"workspace_id": ...})
        set_rls_context(session)
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# 4. RLS policies in PostgreSQL automatically filter data:
# CREATE POLICY tenant_isolation ON map_documents
#   USING (workspace_id = current_setting('app.workspace_id', true)::uuid);
```

**Key Points**:
- ✅ Context variables (`set_workspace_context`) propagate across async boundaries
- ✅ Parameterized queries prevent SQL injection (`SET LOCAL app.user_id = :user_id`)
- ✅ Local mode (SQLite) skips RLS - no overhead
- ✅ SupabaseSession skips RLS - handled by PostgREST
- ✅ Tests verify SQL injection protection and context propagation

**Files**:
- `src/kurt/db/tenant.py` - Context management and `set_rls_context()`
- `src/kurt/db/database.py` - `managed_session()` calls `set_rls_context()`
- `src/kurt/web/api/auth.py` - Middleware sets context from JWT
- `src/kurt/web/api/tests/test_rls_integration.py` - RLS tests (5 tests passing)

**Security**:
- SQL injection prevented via parameterized queries
- Workspace isolation enforced at database level
- JWT validation via Supabase auth API

## Principles

- Keep core logic small; put domain persistence in workflow modules.
- Use DBOS for durability and workflow state.
- Emit progress and logs via DBOS events and streams.
- Trace LLM costs/tokens in `llm_traces` only (DBOS does not track these).

## Core Components

- `LLMStep` / `@llm_step`: durable, parallel LLM batch steps
- `StepHooks`: lifecycle hooks for tracking and tracing
- `TrackingHooks`: DBOS events + streams (progress and logs)
- `TracingHooks`: writes `llm_traces` with tokens/costs
- `status` utils: `get_live_status`, `get_step_logs_page`, `get_progress_page`

## Recommended Usage

### 1) Create hooks

```python
from kurt_new.core import CompositeStepHooks, TrackingHooks, TracingHooks

hooks = CompositeStepHooks([
    TrackingHooks(),
    TracingHooks(model_name="gpt-4", provider="openai"),
])
```

### 2) Define an LLM step

```python
from pydantic import BaseModel
from kurt_new.core import LLMStep

class ExtractOut(BaseModel):
    entities: list[dict] = []
    sentiment: str = "neutral"

def llm_call(prompt: str):
    result = ExtractOut(entities=[{"name": "Example"}], sentiment="neutral")
    metrics = {"tokens_in": 120, "tokens_out": 34, "cost": 0.0023}
    return result, metrics  # metrics are optional

extract_step = LLMStep(
    name="extract",
    input_columns=["content"],
    prompt_template="Extract entities:\n{content}",
    output_schema=ExtractOut,
    llm_fn=llm_call,
    concurrency=3,
    hooks=hooks,
)
```

### 3) Use inside a DBOS workflow

```python
from dbos import DBOS
import pandas as pd

@DBOS.workflow()
def my_pipeline(docs_json: str):
    df = pd.read_json(docs_json, orient="records")
    df = extract_step.run(df)
    return {"rows": len(df)}
```

## Tracking and Live Status

`TrackingHooks` emits:
- Events: `current_step`, `stage`, `stage_total`, `stage_current`, `stage_status`
- Streams: `progress`, `logs`

To read status/logs:

```python
from kurt_new.core import get_live_status, get_step_logs_page

status = get_live_status(workflow_id)
page = get_step_logs_page(workflow_id, since_offset=last_offset)
last_offset = page["next_offset"]
```

## Tracing Tokens and Cost

`TracingHooks` records `llm_traces`. Provide metrics by returning
`(result, metrics)` from `llm_fn`. Supported keys:

- `tokens_in` or `input_tokens`
- `tokens_out` or `output_tokens`
- `cost` or `total_cost`

## Multi-Tenancy

`llm_traces` includes `user_id` and `workspace_id`. Use these when:

- writing traces in `TracingHooks` (pass `user_id` / `workspace_id`)
- querying traces (filter by tenant in your workflow code)

Keep tenant-specific business tables outside core. Put them in workflow modules
and add `user_id` / `workspace_id` there as needed.

## Table Schema Management

### Database Schema Separation

Kurt uses **two separate Alembic migration trees** to separate concerns:

1. **Kurt-core migrations** (`src/kurt/db/migrations/`)
   - Schema: `public` (default PostgreSQL schema)
   - Tables: Workflow data (map_documents, fetch_documents, content_items, etc.)
   - Owned by: kurt-core repository
   - Applied by: `scripts/run_core_migrations.py` in kurt-cloud

2. **Kurt-cloud migrations** (`src/kurt_cloud/db/migrations/` in kurt-cloud repo)
   - Schema: `cloud` (separate schema)
   - Tables: Multi-tenancy (workspaces, workspace_members, user_connections, usage_events)
   - Owned by: kurt-cloud repository
   - Applied by: `alembic upgrade head` in kurt-cloud

**IMPORTANT**: Workspace/auth tables belong in kurt-cloud (not kurt-core).

### DBOS Tables

- DBOS tables (events/streams/workflow_status) are managed by DBOS
- Do not create or migrate DBOS tables manually
- Use raw SQL for DBOS queries (no SQLModel models)

### Creating Kurt-Core Migrations

When you add workflow tables (map, fetch, content, etc.):

```bash
cd src/kurt/db/migrations
alembic revision -m "add_my_workflow_tables"
```

Edit the generated file in `versions/`:
```python
def upgrade() -> None:
    op.create_table(
        "my_workflow_documents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=True),  # For multi-tenancy
        # ... other columns
    )
```

Apply locally:
```bash
export DATABASE_URL="sqlite:///.kurt/kurt.sqlite"
cd src/kurt/db/migrations
alembic upgrade head
```

Apply to Supabase (from kurt-cloud):
```bash
cd /path/to/kurt-cloud
export SUPABASE_DB_URL="postgresql://postgres:PASSWORD@db.xxx.supabase.co:5432/postgres"
python scripts/run_core_migrations.py
```

### SQL Migrations (Deprecated)

**Do NOT use manual SQL migrations** (e.g., `supabase/migrations/*.sql`). Use Alembic exclusively for consistency and version control.

## Testing

Use `mock_llm` and response factories to avoid real LLM calls:

```python
from kurt_new.core import mock_llm, create_response_factory

factory = create_response_factory(ExtractOut, {"sentiment": "positive"})
with mock_llm([extract_step], factory):
    df = extract_step.run(df)
```

## Do / Don't

- Do: keep workflow state in DBOS, not custom tables
- Do: use hooks for tracking/tracing
- Don't: add domain persistence in core
- Don't: bypass DBOS events/streams for progress

---

## Adding a New Workflow

Each workflow is a **self-contained feature module** with its own configuration, steps, models, and migrations. Workflows live in `src/kurt_new/workflows/<name>/`.

### Workflow Structure

```
src/kurt_new/workflows/<workflow_name>/
├── __init__.py          # Public exports
├── config.py            # Configuration schema (Pydantic)
├── steps.py             # Step implementations (DBOS steps, LLM steps)
├── workflow.py          # Main workflow definition
├── models.py            # Database models (SQLModel) - workflow-specific tables
├── utils.py             # Shared helpers (pure functions)
├── migrations/          # Alembic migrations for this workflow's tables
│   └── versions/
└── tests/
    └── test_<name>.py
```

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Workflow folder | `snake_case`, short noun | `map/`, `extract/`, `entity_resolution/` |
| Config class | `<Name>Config` | `MapConfig`, `ExtractConfig` |
| Workflow function | `<name>_workflow` | `map_workflow`, `extract_workflow` |
| Step functions | `<verb>_step` or `<name>_step` | `map_step`, `extract_entities_step` |
| DB models | `PascalCase`, singular | `ExtractedEntity`, `ResolvedClaim` |
| Table names | `snake_case`, prefixed by workflow | `extract_entities`, `map_sources` |

### Step 1: Create the Workflow Folder

```bash
mkdir -p src/kurt_new/workflows/my_feature
touch src/kurt_new/workflows/my_feature/__init__.py
```

### Step 2: Define Configuration (`config.py`)

Configuration is the **input contract** for your workflow:

```python
from typing import Optional
from pydantic import BaseModel, Field

class MyFeatureConfig(BaseModel):
    """Configuration for my_feature workflow."""

    # Required inputs
    source_url: str = Field(..., description="URL to process")

    # Optional parameters with defaults
    max_items: int = Field(default=100, ge=1, le=1000)
    include_metadata: bool = Field(default=True)
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)

    # Patterns (comma-separated strings for API compatibility)
    include_patterns: Optional[str] = Field(default=None)
    exclude_patterns: Optional[str] = Field(default=None)
```

### Step 3: Define Database Models (`models.py`)

Each workflow owns its **output tables**. Use mixins from `kurt_new.db.models`:

```python
from typing import Optional
from sqlmodel import Field, SQLModel
from kurt_new.db.models import TimestampMixin, TenantMixin, ConfidenceMixin

class ExtractedItem(TimestampMixin, TenantMixin, ConfidenceMixin, SQLModel, table=True):
    """Items extracted by my_feature workflow."""

    __tablename__ = "my_feature_items"  # Prefix with workflow name

    id: Optional[int] = Field(default=None, primary_key=True)
    workflow_id: str = Field(index=True)

    # Workflow-specific fields
    source_url: str
    item_name: str
    item_type: str
    metadata_json: Optional[str] = Field(default=None)

    # Foreign key to shared tables (optional)
    document_id: Optional[str] = Field(default=None, index=True)
```

**Status fields should use enums.** Define a local Enum in `models.py` for status columns.

**Available Mixins:**
- `TimestampMixin`: adds `created_at`, `updated_at`
- `TenantMixin`: adds `user_id`, `workspace_id` (for multi-tenancy)
- `ConfidenceMixin`: adds `confidence` float field
- `EmbeddingMixin`: adds `embedding` bytes field for vectors

### Step 4: Create Steps (`steps.py`)

Steps contain the business logic. Keep them focused and testable:

```python
from __future__ import annotations
import time
from typing import Any
from pydantic import BaseModel, Field
from dbos import DBOS

from .config import MyFeatureConfig

@DBOS.step(name="my_feature_process")
def process_step(config_dict: dict[str, Any]) -> dict[str, Any]:
    """Process items from source."""
    config = MyFeatureConfig.model_validate(config_dict)
    results = []
    total = config.max_items

    DBOS.set_event("stage_total", total)

    for idx in range(total):
        result = {"item": f"item_{idx}", "status": "success"}
        results.append(result)
        DBOS.set_event("stage_current", idx + 1)

    return {"total": len(results), "results": results}

@DBOS.transaction()
def persist_items(items_json: str, workflow_id: str) -> int:
    """Persist extracted items to database."""
    # Your persistence logic using SQLModel
    return inserted_count
```

### Step 5: Create the Workflow (`workflow.py`)

The workflow orchestrates steps:

```python
from __future__ import annotations
import time
from typing import Any
from dbos import DBOS

from .config import MyFeatureConfig
from .steps import process_step, persist_items

@DBOS.workflow()
def my_feature_workflow(config_dict: dict[str, Any]) -> dict[str, Any]:
    config = MyFeatureConfig.model_validate(config_dict)
    workflow_id = DBOS.workflow_id

    DBOS.set_event("status", "running")

    # Step 1: Process
    result = process_step(config.model_dump())

    # Step 2: Persist (transaction called from workflow, not step)
    if not config.dry_run:
        count = persist_items(result["results"], workflow_id)
        result["persisted"] = count

    DBOS.set_event("status", "completed")
    return result

def run_my_feature(config: MyFeatureConfig | dict[str, Any]) -> dict[str, Any]:
    """Run the workflow and return result."""
    payload = config.model_dump() if isinstance(config, MyFeatureConfig) else config
    handle = DBOS.start_workflow(my_feature_workflow, payload)
    return handle.get_result()
```

### Step 6: Export Public API (`__init__.py`)

```python
"""My feature workflow - processes items from sources."""

from .config import MyFeatureConfig
from .workflow import my_feature_workflow, run_my_feature
from .steps import process_step

__all__ = [
    "MyFeatureConfig",
    "my_feature_workflow",
    "run_my_feature",
    "process_step",
]
```

### Step 7: Add Migration

```bash
cd src/kurt_new/db/migrations
alembic revision -m "add_my_feature_tables"
```

---

## Workflow Checklist

When creating a new workflow, ensure:

- [ ] Folder created: `src/kurt_new/workflows/<name>/`
- [ ] `config.py` with Pydantic config class
- [ ] `steps.py` with DBOS steps
- [ ] `workflow.py` with `@DBOS.workflow()` function
- [ ] `models.py` with SQLModel tables (if persisting data)
- [ ] `__init__.py` with public exports
- [ ] Migration created for new tables
- [ ] Tests in `tests/test_<name>.py`
- [ ] **E2E test** that calls `run_<workflow>()` with real DBOS
- [ ] Table names prefixed with workflow name
- [ ] Multi-tenancy fields (`user_id`, `workspace_id`) if needed

---

## DBOS Architecture Constraints

### Transactions Must Be Called From Workflow

DBOS enforces strict separation:
- **`@DBOS.step()`**: Computation, can call other steps
- **`@DBOS.transaction()`**: Database operations, must be called **directly from a workflow**

```python
# WRONG - transaction called from step
@DBOS.step()
def my_step(data):
    persist_data(data)  # ERROR!

# CORRECT - transaction called from workflow
@DBOS.workflow()
def my_workflow(config):
    result = my_step(config)
    persist_data(result)  # OK
```

### Cannot Start Workflows From Within Steps

DBOS steps cannot start workflows or use queues:
- `DBOS.start_workflow()` - forbidden in steps
- `Queue.enqueue()` - forbidden in steps
- `EmbeddingStep.run()` or `LLMStep.run()` - use queues internally, forbidden in steps

For batch operations inside a step, use direct API calls (e.g., `generate_embeddings()`) instead of step classes.

### Pattern: Step Returns Data, Workflow Persists

1. **Step** does processing and returns serializable data
2. **Workflow** receives data and calls transaction to persist
3. **Transaction** handles database operations

This enables dry-run mode and proper DBOS recovery.

---

## Testing with DBOS

### Key Fixtures

| Fixture | Use Case |
|---------|----------|
| `tmp_database` | Simple DB tests without DBOS |
| `tmp_project` | Project with config and database |
| `tmp_project_with_docs` | Project pre-populated with sample data |
| `dbos_launched` | Real DBOS for workflow/background tests |
| `tmp_kurt_project` | Full e2e (includes everything) |

### Reset DBOS State Between Tests

DBOS maintains global state. Always reset between tests:

```python
@pytest.fixture
def reset_dbos_state():
    def _reset():
        try:
            import dbos._dbos as dbos_module
            if hasattr(dbos_module, "_dbos_global_instance"):
                instance = dbos_module._dbos_global_instance
                if instance and hasattr(instance, "_destroy"):
                    instance._destroy(workflow_completion_timeout_sec=0)
                dbos_module._dbos_global_instance = None
        except Exception:
            pass
    _reset()
    yield
    _reset()
```

### E2E Tests Are Mandatory

Unit tests do NOT catch DBOS architecture violations. Every workflow needs an e2e test:

```python
class TestMyWorkflowE2E:
    def test_full_workflow(self, tmp_kurt_project):
        result = run_my_workflow({"source": "...", "dry_run": False})
        assert result["status"] == "success"
```

### Factory Fixture Pattern

Create reusable, composable fixtures:

```python
@pytest.fixture
def insert_workflow(dbos_launched):
    def _insert(workflow_uuid, name, status):
        with managed_session() as session:
            session.execute(...)
    return _insert

@pytest.fixture
def sample_workflow(insert_workflow):
    insert_workflow("sample-001", "sample", "SUCCESS")
    return "sample-001"
```

### Mock LLM for Tests

```python
from kurt_new.core import mock_llm, create_response_factory

factory = create_response_factory(OutputSchema, {"field": "value"})
with mock_llm([my_step], factory):
    result = my_step.run(df)
```

---

## Architecture Patterns

### Thread-Local Storage for Context

For managing state that varies by execution context (e.g., display enabled):

```python
import threading

_context = threading.local()

def is_enabled() -> bool:
    return getattr(_context, "enabled", False)

def set_enabled(enabled: bool) -> None:
    _context.enabled = enabled
```

### Background Workflow as Subprocess

Background workflows use process isolation:

```python
subprocess.Popen(
    cmd,
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    start_new_session=True,  # Detach from parent
)
```

Benefits: Process isolation, CLI returns immediately, survives parent termination.

### Safe Event Emission

Wrap DBOS calls to avoid crashes when not initialized:

```python
def _safe_set_event(key: str, value: Any) -> None:
    try:
        DBOS.set_event(key, value)
    except Exception:
        pass
```

### Singleton with Thread Safety

For shared resources across threads:

```python
class Manager:
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance
```

Use `RLock` (reentrant) for nested calls within same thread.

---

## CLI Patterns

### Singular/Plural Option Merging

When CLI accepts both `--url` and `--urls`:

```python
@click.option("--url", "single_url", help="Single URL")
@click.option("--urls", help="Comma-separated URLs")
def cmd(single_url, urls, ...):
    if single_url:
        urls = f"{urls},{single_url}" if urls else single_url
```

### Background Mode Return Types

Background returns `str` (workflow_id), foreground returns `dict`:

```python
if isinstance(result, str):
    output = {"workflow_id": result, "background": True}
else:
    output = result
```

### Telemetry Decorator

Apply `@track_command` on CLI commands, immediately after `@click.command()`:

```python
@click.command()
@track_command
@add_filter_options()
def my_command():
    ...
```

---

## Common Bugs and Fixes

### SQLModel JSON Field

SQLModel needs explicit type for JSON columns:

```python
# Wrong - generates NullType
keywords: list[str] = Field(default_factory=list)

# Correct
from sqlalchemy import JSON
keywords: list[str] = Field(default_factory=list, sa_type=JSON)
```

### SQLModel Query Syntax

Use SQLModel's `select()`, not SQLAlchemy's `.query()`:

```python
# Wrong
docs = session.query(Model).all()

# Correct
from sqlmodel import select
docs = session.exec(select(Model)).all()
```

### DBOS Internal Tables

Use raw SQL for DBOS tables, don't create SQLModel models for them:

```python
from sqlalchemy import text
session.execute(text("SELECT * FROM workflow_status WHERE ..."))
```

### SQLModel Model Registration

SQLModel doesn't auto-discover models. Call `register_all_models()` before `create_all()`.

### ConfigParam vs Runtime Flags

In workflow configs (`StepConfig`), distinguish between:

**Persistent config** (use `ConfigParam`) - settings that make sense in `kurt.config`:
- `fetch_engine`, `batch_size` - project-wide preferences
- `max_pages`, `max_depth` - workflow tuning parameters
- `model`, `recency` - API configuration

**Runtime flags** (use simple Pydantic field) - CLI pass-through options:
- `dry_run` - only relevant for a single command execution
- `save` - runtime behavior toggle

```python
# WRONG - dry_run as ConfigParam (would be stored in kurt.config)
dry_run: bool = ConfigParam(default=False, description="Dry run mode")

# CORRECT - dry_run as simple field (CLI pass-through only)
dry_run: bool = False  # Preview mode - don't persist changes
```

Rule of thumb: If storing `WORKFLOW.PARAM=value` in `kurt.config` file doesn't make sense, use a simple field instead of `ConfigParam`.

---

## Important Gotchas

1. **DBOS State Pollution**: Use `reset_dbos_state` fixture between tests.

2. **No Workflows From Steps**: Cannot use `Queue.enqueue()`, `LLMStep.run()`, or `DBOS.start_workflow()` inside steps.

3. **Background Output**: Worker subprocess must redirect stdout/stderr.

4. **Rich Thread Safety**: Use locks when coordinating Rich `Live` displays.

5. **Click Decorator Order**: Composed decorators apply in reverse order.

6. **CLI Argument Passing**: Use keyword arguments when calling internal functions from CLI handlers to avoid silent failures.

---

## Agent Workflows (Claude Code)

Agent workflows execute Claude Code CLI as a subprocess inside DBOS workflows. They're defined as Markdown files with YAML frontmatter in `workflows/` (configurable via `PATH_WORKFLOWS` in `kurt.config`).

### Directory Structure

Three distinct directories for agent-related files:

1. **`src/kurt/agents/templates/`** - Agent prompt templates
   - Static prompt files for agent operations
   - Example: `setup-github-workspace.md`, `plan-template.md`
   - Shipped with the product
   - Used by agent CLI for specific tasks

2. **`src/kurt/workflows/agents/`** - Agent workflow system implementation
   - Parser, executor, registry, scheduler
   - CLI commands (`kurt agents list`, `kurt agents run`)
   - Tests for the workflow system
   - This is the **code** that runs user workflows

3. **`/workflows/`** (project root) - User-defined workflows (development testing only)
   - Gitignored via `/workflows/`
   - Used for testing during development
   - In production, users create workflows in their own project directories
   - Configured via `PATH_WORKFLOWS` in `kurt.config`

### Workflow Definition Format

```markdown
---
name: my-workflow
title: My Agent Workflow
description: |
  What this workflow does.

agent:
  model: claude-sonnet-4-20250514
  max_turns: 10
  allowed_tools:
    - Bash
    - Read
    - Write
    - Glob
  permission_mode: bypassPermissions

guardrails:
  max_tokens: 100000
  max_tool_calls: 50
  max_time: 300

schedule:
  cron: "0 9 * * 1-5"
  timezone: "UTC"
  enabled: true

inputs:
  task: "default value"

tags: [automation, daily]
---

# Workflow Body

Your prompt goes here. Use template variables:
- {{task}} - from inputs
- {{date}} - current date (YYYY-MM-DD)
- {{datetime}} - ISO timestamp
- {{project_root}} - project directory
```

### CLI Commands

```bash
# List all workflow definitions
kurt agents list
kurt agents list --tag automation
kurt agents list --scheduled

# Show workflow details
kurt agents show my-workflow

# Validate workflow files
kurt agents validate                    # Validate all
kurt agents validate workflows/my.md    # Validate specific file

# Run a workflow
kurt agents run my-workflow             # Background (default)
kurt agents run my-workflow --foreground
kurt agents run my-workflow --input task="Custom task"

# View run history
kurt agents history my-workflow --limit 20

# Initialize with example
kurt agents init
```

### Execution Model

1. **Parser** (`parser.py`): Parses Markdown frontmatter into Pydantic models
2. **Registry** (`registry.py`): File-based discovery from `workflows/` directory
3. **Executor** (`executor.py`): DBOS workflow that runs Claude CLI via subprocess
4. **Scheduler** (`scheduler.py`): DBOS native cron scheduling

### Key Metrics

The executor tracks these metrics via DBOS events:
- `agent_turns`: Number of conversation turns
- `tokens_in`: Input tokens (includes cache reads)
- `tokens_out`: Output tokens
- `cost_usd`: Total API cost
- `tool_calls`: All tool invocations (Bash, Read, Write, Glob, etc.)

#### Tool Call Tracking

Tool calls are tracked using Claude Code's `PostToolUse` hook system:

1. A temporary settings file is created with a hook that calls `kurt agents track-tool`
2. Each tool invocation is logged to a temporary JSONL file
3. After execution, the log file is read to count total tool calls
4. Temp files are cleaned up automatically

This allows accurate tracking of ALL tool calls, not just web_search/web_fetch.

### Nested Workflow Display

When an agent workflow runs `kurt` CLI commands (e.g., `kurt content map`, `kurt agents run`), child workflows are automatically linked to their parent. This enables hierarchical display in the web UI.

#### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  execute_agent_workflow (parent)                            │
│  workflow_id: abc-123                                       │
│                                                             │
│  1. Set env: KURT_PARENT_WORKFLOW_ID=abc-123                │
│  2. Run Claude CLI subprocess                               │
│     │                                                       │
│     │  ┌───────────────────────────────────────────┐        │
│     └─▶│ Claude runs: kurt content map ...         │        │
│        │                                           │        │
│        │  ┌─────────────────────────────────────┐  │        │
│        │  │ map_workflow (child)                │  │        │
│        │  │ workflow_id: def-456                │  │        │
│        │  │                                     │  │        │
│        │  │ Reads KURT_PARENT_WORKFLOW_ID       │  │        │
│        │  │ Stores: parent_workflow_id=abc-123  │  │        │
│        │  └─────────────────────────────────────┘  │        │
│        └───────────────────────────────────────────┘        │
│                                                             │
│  Result: def-456.parent_workflow_id → abc-123               │
└─────────────────────────────────────────────────────────────┘
```

1. **Parent ID Propagation**: The executor sets `KURT_PARENT_WORKFLOW_ID` env var before running Claude
2. **Child Workflow Storage**: Each workflow function reads the env var and stores it as a DBOS event
3. **API Response**: The web API includes `parent_workflow_id` in workflow listings
4. **Frontend Display**: Child workflows can be grouped/nested under their parent

#### Supported Child Workflows

All workflows in `src/kurt/workflows/` support parent linking via the `@with_parent_workflow_id` decorator:
- `execute_agent_workflow` - Agent workflows running other agents
- `map_workflow` - Content mapping via `kurt content map`
- `fetch_workflow` - Content fetching via `kurt content fetch`
- `research_workflow` - Research queries via `kurt research`
- `signals_workflow` - Signal monitoring via `kurt signals`
- `domain_analytics_workflow` - Analytics sync via `kurt analytics`

#### Environment Variable

```
KURT_PARENT_WORKFLOW_ID=<parent-workflow-uuid>
```

This is automatically set by `agent_execution_step()` and inherited by all subprocess commands.

#### Adding Nested Support to New Workflows

Use the `@with_parent_workflow_id` decorator from `kurt.core`:

```python
from dbos import DBOS
from kurt.core import with_parent_workflow_id

@DBOS.workflow()
@with_parent_workflow_id
def my_workflow(config_dict: dict) -> dict:
    workflow_id = DBOS.workflow_id
    DBOS.set_event("status", "running")
    # ... rest of workflow
```

The decorator automatically reads `KURT_PARENT_WORKFLOW_ID` from the environment and stores it as a DBOS event. It must be placed AFTER `@DBOS.workflow()` (decorators apply bottom-up).

Alternatively, call `store_parent_workflow_id()` manually inside the workflow:

```python
from kurt.core import store_parent_workflow_id

@DBOS.workflow()
def my_workflow(config_dict: dict) -> dict:
    store_parent_workflow_id()  # Must be inside @DBOS.workflow function
    # ... rest of workflow
```

#### Querying Parent-Child Relationships

```python
import sqlite3
import base64
import pickle

# Find child workflows for a parent
cursor.execute('''
    SELECT ws.workflow_uuid, ws.name, we.value as parent_id
    FROM workflow_status ws
    JOIN workflow_events we ON ws.workflow_uuid = we.workflow_uuid
    WHERE we.key = 'parent_workflow_id'
''')

for row in cursor.fetchall():
    parent_id = pickle.loads(base64.b64decode(row[2]))
    print(f"Child: {row[0]} → Parent: {parent_id}")
```

#### Testing Nested Workflows

Create a test workflow that runs a kurt command:

```markdown
---
name: nested-test
title: Nested Workflow Test
agent:
  model: claude-sonnet-4-20250514
  max_turns: 3
  allowed_tools:
    - Bash
guardrails:
  max_tokens: 50000
  max_time: 120
---

# Task

Run this command to create a child workflow:

```bash
kurt content map https://example.com --background
```

Report the workflow ID from the output.
```

Then verify in the database:
```bash
# Run the workflow
kurt agents run nested-test --foreground

# Check parent_workflow_id was stored
kurt workflows list  # Shows both parent and child
```

### Guardrails

Three guardrails are enforced:
- `max_tokens`: Maximum token budget (default: 500,000)
- `max_tool_calls`: Maximum tool invocations (default: 200) - **not enforced by CLI**
- `max_time`: Maximum execution time in seconds (default: 3600)

### Module Structure

```
src/kurt/workflows/agents/
├── __init__.py      # Public exports
├── parser.py        # Frontmatter parsing (Pydantic models)
├── registry.py      # File-based workflow registry
├── executor.py      # DBOS workflow + Claude subprocess + tool tracking
├── scheduler.py     # DBOS cron scheduling
├── cli.py           # CLI commands (kurt agents ...)
└── tests/
    ├── __init__.py
    ├── test_cli.py           # CLI command tests
    ├── test_executor.py      # Executor and tool tracking tests
    ├── test_nested_workflows.py  # Parent workflow ID tests
    ├── test_parser.py        # Parser and config model tests
    └── test_registry.py      # Registry function tests
```

### Configuration

In `kurt.config`:
```
PATH_WORKFLOWS=workflows
```

### Running Workflows Programmatically

```python
from kurt.workflows.agents import run_definition

# Background execution
result = run_definition("my-workflow", inputs={"task": "..."})
print(result["workflow_id"])

# Foreground execution
result = run_definition("my-workflow", background=False)
print(result["status"], result["turns"], result["tokens_in"])
```

---

## Building Workflow Definitions

### Quick Start

1. Create `workflows/my-workflow.md`
2. Add frontmatter (YAML) + prompt body (Markdown)
3. Validate: `kurt agents validate workflows/my-workflow.md`
4. Run: `kurt agents run my-workflow --foreground`

### Frontmatter Reference

```yaml
---
name: my-workflow                    # Required: unique ID (kebab-case)
title: My Workflow Title             # Required: display name

agent:
  model: claude-sonnet-4-20250514    # Model to use
  max_turns: 15                      # Conversation turns limit
  allowed_tools: [Bash, Read, Write, Glob, Grep]

guardrails:
  max_tokens: 150000                 # Token budget
  max_time: 600                      # Timeout (seconds)

inputs:
  topic: "default value"             # Runtime parameters

schedule:                            # Optional: cron scheduling
  cron: "0 9 * * 1-5"
  enabled: true

tags: [research, daily]              # For filtering
---
```

### Template Variables

| Variable | Example |
|----------|---------|
| `{{topic}}` | From inputs |
| `{{date}}` | `2024-01-15` |
| `{{datetime}}` | `2024-01-15T09:30:00` |
| `{{project_root}}` | `/path/to/project` |

### Prompt Structure

```markdown
# Workflow Title

Context about the task.

## Steps

1. **Step One**: Use `command` to do X
2. **Step Two**: Save to `reports/output-{{date}}.md`

## Success Criteria

- Output file created
- No errors
```

### Guardrail Guidelines

| Workflow Type | `max_turns` | `max_tokens` | `max_time` |
|---------------|-------------|--------------|------------|
| Quick task | 5-10 | 50,000 | 120 |
| Standard | 15-25 | 150,000 | 600 |
| Complex | 30-50 | 300,000 | 1800 |
