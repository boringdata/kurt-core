---
description: kurt_new core framework for DBOS workflow creation
---

# kurt_new Core Framework Guide

This guide explains how to build DBOS workflows using the kurt_new core abstractions.
Keep workflows minimal, durable, and observable. Use DBOS for orchestration and
use kurt_new core for LLM batch steps and tracing.

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

- DBOS tables (events/streams/workflow state) are managed by DBOS. Do not
  create or migrate them manually.
- kurt_new schema tables live in `src/kurt_new/db/models.py`.
- Use Alembic migrations in `src/kurt_new/db/migrations` for kurt_new tables.

When you add or change a kurt_new table:
1) Update `src/kurt_new/db/models.py`
2) Create a migration
3) Apply migrations in your environment

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
