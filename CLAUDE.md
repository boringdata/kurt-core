<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

---
description: Kurt core framework for workflow creation
---

# Kurt Core Framework Guide

This guide explains how to build workflows using the Kurt core abstractions.
Keep workflows minimal and observable.

## Database: Dolt

Kurt uses **Dolt** as its only database backend. Dolt is a SQL database with Git-like version control features, accessed via MySQL protocol.

### Connection Modes

Dolt supports two connection modes (configured automatically):

| Mode | Use Case | How It Works |
|------|----------|--------------|
| **Embedded** | Local CLI operations | Uses `dolt sql` CLI directly |
| **Server** | Concurrent access, web UI | Connects to `dolt sql-server` via MySQL protocol |

The `DoltDB` class auto-starts a server when needed for SQLModel/SQLAlchemy sessions.

### Configuration

In `kurt.toml`:
```toml
# No DATABASE_URL needed for local Dolt (default)
# Optional: connect to remote Dolt server
DATABASE_URL="mysql+pymysql://root@localhost:3306/kurt"
```

### Key Features

- **Git-like versioning**: Branch, commit, merge, diff on your data
- **MySQL protocol**: Standard SQL via SQLModel/SQLAlchemy
- **No migrations needed**: Schema changes via Dolt commits
- **Local-first**: Works offline, sync later

### Usage

```python
from kurt.db import get_database_client, managed_session

# Get Dolt client
db = get_database_client()

# Raw SQL queries
result = db.query("SELECT * FROM documents WHERE status = ?", ["completed"])

# SQLModel sessions (auto-starts server if needed)
with managed_session() as session:
    docs = session.exec(select(Document)).all()

# Git-like operations
db.branch_create("feature/experiment")
db.branch_switch("feature/experiment")
db.commit("Add new documents", author="Agent <agent@kurt.dev>")
```

### Files

- `src/kurt/db/dolt.py` - Main DoltDB class (composed from connection + queries)
- `src/kurt/db/connection.py` - Connection pool, server lifecycle, sessions
- `src/kurt/db/queries.py` - Query execution, parameter interpolation
- `src/kurt/db/schema.py` - Schema initialization helpers

### Workspace Context (Multi-Tenancy Prep)

Even in local mode, Kurt tracks `workspace_id` and `user_id` for future cloud sync:

```python
from kurt.db import set_workspace_context, get_workspace_id

# Set at CLI startup (from kurt.toml WORKSPACE_ID)
set_workspace_context(workspace_id="ws-123", user_id="local")

# Auto-populated on new records via SQLAlchemy listener
# Models with TenantMixin get workspace_id/user_id automatically
```

### Cloud Authentication (Future)

Kurt has infrastructure for future cloud sync:

```bash
kurt cloud login    # OAuth via browser
kurt cloud status   # Show auth status
kurt cloud logout   # Clear credentials
```

The `is_cloud_mode()` function checks for `DATABASE_URL="kurt"` but cloud routing is not yet implemented. Currently all operations use local Dolt.

## Principles

- Keep core logic small; put domain persistence in workflow modules.
- Track workflow state via observability tables.
- Trace LLM costs/tokens in `llm_traces`.

## Core Components

- `LLMStep` / `@llm_step`: parallel LLM batch steps
- `StepHooks`: lifecycle hooks for tracking and tracing
- `TracingHooks`: writes `llm_traces` with tokens/costs
- `status` utils: `get_live_status`, `get_step_logs_page`

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

### 3) Use in a workflow

```python
import pandas as pd

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

### Schema with Dolt

Kurt uses Dolt for all data storage. Schema management is simpler than traditional SQL databases:

1. **Define SQLModel models** in your workflow's `models.py`
2. **Call `ensure_tables()`** at startup to create tables
3. **Dolt commits** track schema changes like code changes

### Creating Tables

```python
from sqlmodel import Field, SQLModel
from kurt.db.models import TimestampMixin, TenantMixin

class MyDocument(TimestampMixin, TenantMixin, SQLModel, table=True):
    """Documents for my workflow."""
    __tablename__ = "my_workflow_documents"

    id: str = Field(primary_key=True)
    title: str
    content: str | None = None
```

### Initializing Schema

```python
from kurt.db import get_database_client, init_observability_schema

db = get_database_client()

# Initialize observability tables (workflow_runs, step_logs, step_events)
init_observability_schema(db)

# SQLModel tables are created via ensure_tables() or db.init_database()
```

### Schema Versioning

Dolt tracks schema changes as commits:

```bash
# After adding/modifying tables
dolt add -A
dolt commit -m "Add my_workflow_documents table"

# View schema history
dolt log --oneline
dolt diff HEAD~1 HEAD --schema
```

## Testing

Use `mock_llm` and response factories to avoid real LLM calls:

```python
from kurt_new.core import mock_llm, create_response_factory

factory = create_response_factory(ExtractOut, {"sentiment": "positive"})
with mock_llm([extract_step], factory):
    df = extract_step.run(df)
```

## Do / Don't

- Do: use hooks for tracking/tracing
- Do: track state via observability tables
- Don't: add domain persistence in core

---

## Tool & Provider System

Kurt uses a pluggable provider system for tools like `fetch` and `map`.

### Concepts

| Concept | Description | Example |
|---------|-------------|---------|
| **Tool** | Category with standard interface | fetch, map, publish, llm |
| **Provider** | Implementation of a tool | trafilatura, notion, httpx, sitemap |
| **ProviderRegistry** | Singleton for discovery and URL-based routing | `get_provider_registry()` |

### Provider Discovery

Providers are discovered in priority order (first occurrence wins):

1. **Project**: `<project>/kurt/tools/<tool>/providers/<name>/provider.py`
2. **User**: `~/.kurt/tools/<tool>/providers/<name>/provider.py`
3. **Built-in**: `src/kurt/tools/<tool>/providers/<name>/provider.py`

Project providers can extend builtin tools without needing a `tool.py` — just add a `providers/` subdirectory.

### URL Auto-Selection

Providers declare `url_patterns` for automatic selection:

| URL Pattern | Provider | Tool |
|-------------|----------|------|
| `*.notion.so/*` | notion | fetch |
| `*/sitemap.xml` | sitemap | map |
| `*/feed*`, `*/rss*` | rss | map |
| `*twitter.com/*` | twitterapi | fetch |
| `*` (fallback) | trafilatura | fetch |

### Built-in Providers

**Fetch** (6): trafilatura, httpx, tavily, firecrawl, apify, twitterapi
**Map** (6): sitemap, rss, crawl, cms, folder, apify

### CLI Commands

```bash
kurt tool list              # List all tools and providers
kurt tool info fetch        # Show tool details
kurt tool providers fetch   # List providers for a tool
kurt tool check fetch       # Validate env requirements
kurt tool new my-tool       # Scaffold a new tool
kurt tool new-provider fetch notion  # Add provider to existing tool
```

### Workflow Configuration

```toml
# Explicit provider selection:
[[steps]]
type = "fetch"
config.provider = "notion"
config.url = "https://notion.so/page"

# Auto-selection via URL pattern (no provider needed):
[[steps]]
type = "fetch"
config.url = "https://notion.so/page"  # Auto-selects notion provider
```

### Provider Config (kurt.toml)

Providers can have per-project configuration in `kurt.toml`:

```toml
[providers.fetch.firecrawl]
formats = ["markdown"]
timeout = 60

[providers.map.crawl]
max_depth = 3
```

Config hierarchy: CLI flags > project `kurt.toml` > user `~/.kurt/config.toml` > provider defaults.

### Creating Custom Providers

Use `kurt tool new <name>` for a new tool or `kurt tool new-provider <tool> <name>` for a provider.

Provider classes must be self-contained (no relative imports) since they're loaded via `importlib.util.spec_from_file_location`. Required attributes: `name`, and optionally `version`, `url_patterns`, `requires_env`.

### Files

- `src/kurt/tools/core/provider.py` - ProviderRegistry singleton
- `src/kurt/tools/core/registry.py` - Tool registry and execution
- `src/kurt/tools/core/config_resolver.py` - Provider config from TOML
- `src/kurt/tools/<tool>/providers/<name>/provider.py` - Built-in providers
- `src/kurt/tools/templates/scaffolds.py` - Tool/provider scaffolding

---

## Adding a New Workflow

Workflows are self-contained modules in `src/kurt/workflows/<name>/`.

### Structure

```
src/kurt/workflows/<name>/
├── __init__.py    # Public exports
├── config.py      # Pydantic config
├── steps.py       # Step functions
├── workflow.py    # Main workflow function
├── models.py      # SQLModel tables (optional)
└── tests/
```

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Folder | `snake_case` | `map/`, `fetch/` |
| Config | `<Name>Config` | `MapConfig` |
| Workflow | `<name>_workflow` | `map_workflow` |
| Tables | prefix with workflow | `map_documents` |

### Minimal Example

```python
# config.py
from pydantic import BaseModel

class MyConfig(BaseModel):
    url: str
    max_items: int = 100

# workflow.py
def my_workflow(config_dict: dict) -> dict:
    config = MyConfig.model_validate(config_dict)
    # ... do work
    return {"status": "completed"}
```

### Mixins for Models

- `TimestampMixin`: `created_at`, `updated_at`
- `TenantMixin`: `user_id`, `workspace_id`
- `ConfidenceMixin`: `confidence` float
- `EmbeddingMixin`: `embedding` bytes

---

## Workflow Checklist

- [ ] `config.py` with Pydantic config
- [ ] `workflow.py` with main workflow function
- [ ] `models.py` if persisting data
- [ ] Tests in `tests/`
- [ ] Table names prefixed with workflow name
- [ ] Multi-tenancy fields (`user_id`, `workspace_id`) if needed

---

## Testing

### Key Fixtures

| Fixture | Use Case |
|---------|----------|
| `tmp_database` | Simple DB tests |
| `tmp_project` | Project with config and database |
| `tmp_kurt_project` | Full e2e (includes everything) |

### Mock LLM for Tests

```python
from kurt.core import mock_llm, create_response_factory

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

### SQLModel Model Registration

SQLModel doesn't auto-discover models. Call `register_all_models()` before `create_all()`.

### ConfigParam vs Runtime Flags

In workflow configs (`StepConfig`), distinguish between:

**Persistent config** (use `ConfigParam`) - settings that make sense in `kurt.config`:
- `provider`, `batch_size` - project-wide preferences
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

1. **Background Output**: Worker subprocess must redirect stdout/stderr.

2. **Rich Thread Safety**: Use locks when coordinating Rich `Live` displays.

3. **Click Decorator Order**: Composed decorators apply in reverse order.

4. **CLI Argument Passing**: Use keyword arguments when calling internal functions from CLI handlers to avoid silent failures.

---

## Agent Workflows (Claude Code)

Agent workflows execute Claude Code CLI as a subprocess. Defined as Markdown files with YAML frontmatter.

### Workflow Definition

```markdown
---
name: my-workflow
title: My Workflow
agent:
  model: claude-sonnet-4-20250514
  max_turns: 10
  allowed_tools: [Bash, Read, Write, Glob]
guardrails:
  max_tokens: 100000
  max_time: 300
inputs:
  task: "default value"
tags: [automation]
---

# Task

Your prompt here. Variables: {{task}}, {{date}}, {{project_root}}
```

### CLI Commands

```bash
kurt workflow list                    # List definitions
kurt workflow run my-workflow.md      # Run (background)
kurt workflow run my-workflow.md --foreground
kurt workflow validate                # Validate all
```

### Key Metrics Tracked

`agent_turns`, `tokens_in`, `tokens_out`, `cost_usd`, `tool_calls`

### Nested Workflows

Child workflows automatically link to parents via `KURT_PARENT_WORKFLOW_ID` env var.

```python
from kurt.core import with_parent_workflow_id

@with_parent_workflow_id
def my_workflow(config_dict: dict) -> dict:
    # Parent ID auto-stored as workflow event
    ...
```

### Guardrail Guidelines

| Type | max_turns | max_tokens | max_time |
|------|-----------|------------|----------|
| Quick | 5-10 | 50,000 | 120 |
| Standard | 15-25 | 150,000 | 600 |
| Complex | 30-50 | 300,000 | 1800 |

### Files

- `src/kurt/workflows/agents/` - Parser, executor, registry, scheduler, CLI
- `src/kurt/agents/templates/` - Built-in prompt templates

---

## Workflow Observability API

### Tables

| Table | Purpose |
|-------|---------|
| `workflow_runs` | One row per workflow execution (status, inputs, metadata) |
| `step_logs` | Summary per step (input/output counts, errors) |
| `step_events` | Append-only progress stream (current/total, messages) |

### Status Values

- **Workflow**: `pending` → `running` → `completed` / `failed` / `canceled`
- **Step**: `pending` → `running` → `completed` / `failed` / `skipped`

### Key API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/workflows` | List workflows (filter by status, type, parent) |
| `GET /api/workflows/{id}` | Get workflow details |
| `GET /api/workflows/{id}/status` | Live status with step progress |
| `GET /api/workflows/{id}/status/stream` | SSE stream for real-time updates |
| `POST /api/workflows/{id}/cancel` | Cancel running workflow |
| `POST /api/workflows/{id}/retry` | Retry failed workflow |

### Python API

```python
from kurt.observability.status import get_live_status
from kurt.db import get_database_client

db = get_database_client()
status = get_live_status(db, "workflow-id")
# Returns: {status, progress: {current, total}, steps: [...]}
```

### Metadata Keys

Common keys in `workflow_runs.metadata_json`:
- `workflow_type`: "agent", "tool", "map", "fetch"
- `cli_command`: Original CLI command
- `parent_workflow_id`: Parent workflow UUID (for nested workflows)
- `tokens_in`, `tokens_out`, `cost_usd`: LLM usage metrics

### Files

- `src/kurt/observability/` - Models, lifecycle, tracking, status queries
- `src/kurt/web/api/server.py` - API endpoints
