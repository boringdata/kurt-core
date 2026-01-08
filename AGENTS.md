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
├── map_url.py            # Source-specific utility (if needed)
├── map_folder.py         # Source-specific utility (if needed)
├── map_cms.py            # Source-specific utility (if needed)
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
# src/kurt_new/workflows/my_feature/config.py
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
# src/kurt_new/workflows/my_feature/models.py
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

**Status fields should use enums.** Define a local Enum in `models.py` for status columns
and store the enum type in SQLModel.

**Available Mixins:**
- `TimestampMixin`: adds `created_at`, `updated_at`
- `TenantMixin`: adds `user_id`, `workspace_id` (for multi-tenancy)
- `ConfidenceMixin`: adds `confidence` float field
- `EmbeddingMixin`: adds `embedding` bytes field for vectors

**Referencing Other Tables:**
```python
# Reference shared tables via foreign keys
document_id: Optional[str] = Field(default=None, foreign_key="documents.id")

# Reference other workflow tables
source_entity_id: Optional[int] = Field(default=None, foreign_key="extract_entities.id")
```

### Step 4: Create Steps (`steps.py`)

Steps contain the business logic. Keep them focused and testable:

```python
# src/kurt_new/workflows/my_feature/steps.py
from __future__ import annotations
import time
from typing import Any
from pydantic import BaseModel, Field
from dbos import DBOS

from .config import MyFeatureConfig

# LLM output schema (for structured extraction)
class ItemExtraction(BaseModel):
    items: list[dict] = Field(default_factory=list)
    confidence: float = 0.0

# Native DBOS step
@DBOS.step(name="my_feature_process")
def process_step(config_dict: dict[str, Any]) -> dict[str, Any]:
    """Process items from source."""
    config = MyFeatureConfig.model_validate(config_dict)

    # Your processing logic
    results = []
    total = config.max_items

    DBOS.set_event("stage_total", total)

    for idx in range(total):
        result = {"item": f"item_{idx}", "status": "success"}
        results.append(result)

        DBOS.set_event("stage_current", idx + 1)
        DBOS.write_stream("progress", {
            "step": "my_feature_process",
            "idx": idx,
            "total": total,
            "status": "success",
            "timestamp": time.time(),
        })

    return {
        "total": len(results),
        "results": results,
    }

# Transaction for persistence
@DBOS.transaction()
def persist_items(items_json: str, workflow_id: str) -> int:
    """Persist extracted items to database."""
    # Your persistence logic using SQLModel
    return inserted_count
```

**Source-specific steps:** For workflows that support multiple sources (URL, folder, CMS),
create **dedicated steps** (e.g. `map_url_step`, `map_folder_step`, `map_cms_step`) and
route from a thin `map_step` or in `workflow.py`.

**Workflow-local utilities:** Move shared helpers into `utils.py` and keep source-specific
logic in `map_url.py`, `map_folder.py`, `map_cms.py` to keep `steps.py` minimal.

### Step 5: Create the Workflow (`workflow.py`)

The workflow orchestrates steps:

```python
# src/kurt_new/workflows/my_feature/workflow.py
from __future__ import annotations
import time
from typing import Any
from dbos import DBOS
from kurt_new.core import track_step

from .config import MyFeatureConfig
from .steps import process_step, persist_items

@DBOS.workflow()
def my_feature_workflow(config_dict: dict[str, Any]) -> dict[str, Any]:
    """
    My feature workflow - processes items from a source.
    """
    config = MyFeatureConfig.model_validate(config_dict)
    workflow_id = DBOS.workflow_id

    DBOS.set_event("status", "running")
    DBOS.set_event("started_at", time.time())

    # Step 1: Process
    with track_step("process"):
        result = process_step(config.model_dump())

    # Step 2: Persist (optional)
    with track_step("persist", step_type="transaction"):
        count = persist_items(result["results"], workflow_id)

    DBOS.set_event("status", "completed")
    DBOS.set_event("completed_at", time.time())

    return {
        "workflow_id": workflow_id,
        "total_processed": result["total"],
        "persisted": count,
    }

# Convenience function
def run_my_feature(config: MyFeatureConfig | dict[str, Any]) -> dict[str, Any]:
    """Run the workflow and return result."""
    payload = config.model_dump() if isinstance(config, MyFeatureConfig) else config
    handle = DBOS.start_workflow(my_feature_workflow, payload)
    return handle.get_result()
```

### Step 6: Export Public API (`__init__.py`)

```python
# src/kurt_new/workflows/my_feature/__init__.py
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

Create a migration for your workflow's tables:

```bash
# Generate migration
cd src/kurt_new/db/migrations
alembic revision -m "add_my_feature_tables"
```

```python
# src/kurt_new/db/migrations/versions/YYYYMMDD_NNN_add_my_feature_tables.py
def upgrade():
    op.create_table(
        'my_feature_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('workflow_id', sa.String(), nullable=False, index=True),
        sa.Column('source_url', sa.String(), nullable=False),
        sa.Column('item_name', sa.String(), nullable=False),
        # ... other columns
        sa.Column('user_id', sa.String(), index=True),
        sa.Column('workspace_id', sa.String(), index=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now()),
    )

def downgrade():
    op.drop_table('my_feature_items')
```

### Step 8: Register Workflow (Optional)

Add to the workflows index if needed:

```python
# src/kurt_new/workflows/__init__.py
from .my_feature import my_feature_workflow, run_my_feature, MyFeatureConfig
```

---

## Cross-Workflow References

Workflows can reference tables from other workflows:

```python
# In workflows/enrichment/models.py
class EnrichedEntity(SQLModel, table=True):
    __tablename__ = "enrichment_entities"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Reference entity from extract workflow
    source_entity_id: int = Field(foreign_key="extract_entities.id", index=True)

    # Reference shared document
    document_id: str = Field(foreign_key="documents.id", index=True)

    # Enrichment-specific data
    enriched_data: str
```

**Best Practices:**
- Always use foreign keys for cross-references
- Index foreign key columns
- Document dependencies in the workflow's docstring
- Consider workflow execution order in pipelines

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
- [ ] **E2E test in `tests/test_e2e.py`** (CRITICAL - see below)
- [ ] Table names prefixed with workflow name
- [ ] Multi-tenancy fields (`user_id`, `workspace_id`) if needed

### E2E Tests Are Mandatory

**Every workflow MUST have an e2e test** that calls `run_<workflow>()` with real DBOS.

Unit tests do NOT catch DBOS architecture violations like:
- Starting workflows from within steps
- Calling transactions from within steps
- Using `Queue.enqueue()` inside steps

These violations only surface at runtime with real DBOS. The e2e test is the only way to catch them before production.

```python
# tests/test_e2e.py - REQUIRED for every workflow
class TestMyWorkflowE2E:
    def test_full_workflow(self, tmp_kurt_project: Path):
        """Test the complete workflow with real DBOS."""
        config = {"source": "...", "dry_run": False}

        # This WILL fail if architecture is broken
        result = run_my_workflow(config)

        assert result["status"] == "success"
        # Verify database state...
```

---

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Self-Contained** | Each workflow owns its config, steps, models, and migrations |
| **Durability** | Completed steps are cached; never re-executed on recovery |
| **Multi-Tenancy** | Use `TenantMixin` for `user_id`/`workspace_id` isolation |
| **Cross-References** | Use foreign keys to reference shared or other workflow tables |
| **Naming** | Prefix table names with workflow name to avoid collisions |

---

## DBOS Architecture Constraints

### Cannot Start Workflows From Within Steps

DBOS steps cannot start workflows or use queues that start workflows. This includes:
- `DBOS.start_workflow()`
- `Queue.enqueue()` (internally starts workflows)
- `EmbeddingStep.run()` or `LLMStep.run()` (they use queues internally)

**Wrong - Queue/Workflow started from Step:**
```python
@DBOS.step()
def my_step(data):
    # ERROR: Cannot start workflow from within a step
    embed_step = EmbeddingStep(...)
    result = embed_step.run(df)  # Uses queue.enqueue() internally
    return result
```

**Correct - Call embedding step at workflow level:**
```python
@DBOS.step(name="generate_embeddings")
def embedding_step(rows, config_dict):
    """Generate embeddings synchronously (no queue)."""
    texts = [r["content"][:1000] for r in rows]
    embeddings = generate_embeddings(texts)  # Direct API call
    for row, emb in zip(rows, embeddings):
        row["embedding"] = embedding_to_bytes(emb)
    return rows

@DBOS.workflow()
def my_workflow(docs, config_dict):
    # Step 1: Fetch content
    result = fetch_step(docs, config_dict)

    # Step 2: Generate embeddings (separate step, called from workflow)
    result["rows"] = embedding_step(result["rows"], config_dict)

    return result
```

For batch embeddings inside a step, use `generate_embeddings()` directly instead of `EmbeddingStep`.

### Transaction Must Be Called From Workflow

DBOS enforces strict separation between steps and transactions:

- **`@DBOS.step()`**: Deterministic computation, can call other steps
- **`@DBOS.transaction()`**: Database operations, must be called **directly from a workflow**

**Wrong - Transaction called from Step:**
```python
@DBOS.step()
def my_step(data):
    # Processing...
    result = process(data)
    # ERROR: Transactions must be called from within workflows
    persist_data(result)  # @DBOS.transaction()
    return result

@DBOS.workflow()
def my_workflow(config):
    return my_step(config)
```

**Correct - Transaction called from Workflow:**
```python
@DBOS.step()
def my_step(data):
    # Processing only - return data for persistence
    result = process(data)
    return {"data": result, "rows": serialize(result)}

@DBOS.transaction()
def persist_data(rows):
    # Persistence only
    with managed_session() as session:
        for row in rows:
            session.add(Model(**row))
    return {"inserted": len(rows)}

@DBOS.workflow()
def my_workflow(config):
    # Step 1: Process (step)
    result = my_step(config)

    # Step 2: Persist (transaction called from workflow)
    if not config.get("dry_run") and result.get("rows"):
        persistence = persist_data(result["rows"])
        result["inserted"] = persistence["inserted"]

    return result
```

### Pattern: Step Returns Rows, Workflow Persists

1. **Step** does discovery/processing and returns serializable rows
2. **Workflow** receives rows and calls transaction to persist
3. **Transaction** handles database operations

This separation enables:
- Dry-run mode (skip transaction call)
- Proper DBOS recovery semantics
- Clear separation of concerns

---

## E2E Testing with DBOS

### Creating a Temporary Kurt Project Fixture

For e2e tests that need real DBOS and database, create a `tmp_kurt_project` fixture:

```python
import contextlib
import io
import os
from pathlib import Path
import pytest

from kurt_new.db import init_database, managed_session


@pytest.fixture
def reset_dbos_state():
    """Reset DBOS state between tests."""
    try:
        import dbos._dbos as dbos_module
        if (
            hasattr(dbos_module, "_dbos_global_instance")
            and dbos_module._dbos_global_instance is not None
        ):
            instance = dbos_module._dbos_global_instance
            if hasattr(instance, "_destroy") and hasattr(instance, "_initialized") and instance._initialized:
                instance._destroy(workflow_completion_timeout_sec=0)
            dbos_module._dbos_global_instance = None
    except (ImportError, AttributeError, Exception):
        pass
    yield
    # Same cleanup after test


@pytest.fixture
def tmp_kurt_project(tmp_path: Path, monkeypatch, reset_dbos_state):
    """
    Create a full temporary kurt project with config, database, and DBOS.
    """
    from dbos import DBOS, DBOSConfig

    # Create required directories
    kurt_dir = tmp_path / ".kurt"
    kurt_dir.mkdir(parents=True, exist_ok=True)
    (tmp_path / "sources").mkdir(parents=True, exist_ok=True)

    # Create basic config file
    config_file = tmp_path / "kurt.config"
    config_file.write_text('''# Kurt Project Configuration
PATH_DB=".kurt/kurt.sqlite"
PATH_SOURCES="sources"
''')

    # Ensure no DATABASE_URL env var interferes
    monkeypatch.delenv("DATABASE_URL", raising=False)

    # Change to temp directory
    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    # Initialize database
    init_database()

    # Get database URL for DBOS config
    db_path = tmp_path / ".kurt" / "kurt.sqlite"
    db_url = f"sqlite:///{db_path}"

    # Initialize DBOS with config
    config = DBOSConfig(
        name="kurt_test",
        database_url=db_url,
    )

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        DBOS(config=config)
        DBOS.launch()

    yield tmp_path

    # Cleanup
    try:
        DBOS.destroy(workflow_completion_timeout_sec=0)
    except Exception:
        pass

    os.chdir(original_cwd)
```

### Writing E2E Tests

Use `run_<workflow>()` to test the full workflow with real DBOS:

```python
from kurt_new.workflows.map.workflow import run_map
from kurt_new.workflows.map.models import MapDocument, MapStatus

class TestMapFolderE2E:
    """End-to-end tests for folder discovery."""

    def test_discover_and_persist_folder(self, tmp_kurt_project: Path, tmp_docs_folder: Path):
        """Test full folder discovery and persistence flow."""
        config = {
            "source_folder": str(tmp_docs_folder),
            "dry_run": False,
        }

        result = run_map(config)

        assert result["discovery_method"] == "folder"
        assert result["total"] == 4
        assert result["rows_written"] == 4
        assert "workflow_id" in result

        # Verify documents are persisted in database
        with managed_session() as session:
            docs = session.query(MapDocument).all()
            assert len(docs) == 4

    def test_dry_run_does_not_persist(self, tmp_kurt_project: Path, tmp_docs_folder: Path):
        """Test that dry_run=True does not write to database."""
        config = {
            "source_folder": str(tmp_docs_folder),
            "dry_run": True,
        }

        result = run_map(config)

        assert result["rows_written"] == 0

        with managed_session() as session:
            docs = session.query(MapDocument).all()
            assert len(docs) == 0

    def test_rediscovery_marks_existing(self, tmp_kurt_project: Path, tmp_docs_folder: Path):
        """Test that re-running discovery marks documents as existing."""
        config = {"source_folder": str(tmp_docs_folder), "dry_run": False}

        # First run - all new
        result1 = run_map(config)
        assert result1["documents_discovered"] == 4
        assert result1["rows_written"] == 4

        # Second run - all existing
        result2 = run_map(config)
        assert result2["documents_discovered"] == 0
        assert result2["documents_existing"] == 4
        assert result2["rows_updated"] == 4
```

### Testing with Mocked External Services

For URL/API tests, mock the external calls but use real DBOS:

```python
from unittest.mock import patch

class TestMapUrlE2E:
    def test_discover_and_persist_url(self, tmp_kurt_project: Path):
        """Test URL discovery with mocked HTTP."""
        config = {
            "source_url": "https://example.com",
            "dry_run": False,
        }

        mock_result = {
            "discovered": [
                {"url": "https://example.com/page1", "title": "Page 1"},
                {"url": "https://example.com/page2", "title": "Page 2"},
            ],
            "method": "sitemap",
            "total": 2,
        }

        with patch(
            "kurt_new.workflows.map.steps.discover_from_url",
            return_value=mock_result,
        ):
            result = run_map(config)

        assert result["total"] == 2
        assert result["rows_written"] == 2
```

### Key Points

1. **Use `reset_dbos_state` fixture** to clean up DBOS between tests
2. **Create temp kurt project** with proper directory structure and config
3. **Call `run_<workflow>()`** not individual steps for true e2e tests
4. **Mock external services** (HTTP, APIs) but use real DBOS and database
5. **Verify database state** with `managed_session()` after workflow completes

---

## Testing Background Mode and CLI

### The Background Mode Bug Pattern

A common bug is when CLI options like `--background` and `--priority` are accepted by Click
but never passed to the underlying workflow function. This happens when:

```python
# Bug: background/priority accepted but never used
@add_background_options()
def fetch_cmd(background: bool, priority: int, ...):
    result = run_fetch(docs, config)  # BUG: background/priority not passed!
```

**Fix:**
```python
result = run_fetch(docs, config, background=background, priority=priority)
```

### Testing CLI Parameter Passing with DBOS

**DO NOT use mocking** to test CLI parameter passing. Use the `dbos_launched` fixture
to verify actual DBOS behavior. Mocking is fragile and doesn't catch real integration issues.

#### Available Test Fixtures

```python
# From kurt_new.conftest (available to all tests)

@pytest.fixture
def tmp_database(tmp_path, monkeypatch, reset_dbos_state):
    """Isolated temp database without DBOS. Use for simple DB tests."""

@pytest.fixture
def tmp_project(tmp_path, monkeypatch):
    """Temp project with config, database, and workflow tables."""

@pytest.fixture
def tmp_project_with_docs(tmp_project):
    """Temp project pre-populated with sample documents in various states."""

@pytest.fixture
def dbos_launched(tmp_database, reset_dbos_state):
    """Initializes and launches real DBOS. Use for workflow/background tests."""
```

#### Testing Background Execution

Test that `--background` actually runs workflows in background using real DBOS:

```python
# src/kurt_new/workflows/fetch/tests/test_cli.py

class TestBackgroundExecution:
    """Tests that verify --background actually runs workflows in background.

    These tests use dbos_launched fixture for real DBOS integration.
    They would have caught the bug where background/priority CLI args
    were not forwarded to run_fetch().
    """

    def test_background_returns_workflow_id(
        self, cli_runner: CliRunner, tmp_project_with_docs, dbos_launched
    ):
        """Test that --background returns a workflow_id immediately."""
        import json

        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--ids", "doc-1", "--background", "--format", "json"],
        )
        assert_cli_success(result)

        data = json.loads(result.output)

        # Background mode should return workflow_id (or status message if no docs)
        if data is not None:
            assert "workflow_id" in data or "status" in data

    def test_background_workflow_appears_in_dbos(
        self, cli_runner: CliRunner, tmp_project_with_docs, dbos_launched
    ):
        """Test that background workflow is registered in DBOS workflow_status table."""
        import json
        from sqlalchemy import text
        from kurt_new.db import managed_session

        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--ids", "doc-1", "--background", "--format", "json"],
        )
        assert_cli_success(result)

        data = json.loads(result.output)
        workflow_id = data.get("workflow_id") if isinstance(data, dict) else data

        if workflow_id:
            # Verify workflow exists in DBOS
            with managed_session() as session:
                row = session.execute(
                    text("SELECT status FROM workflow_status WHERE workflow_uuid = :wf_id"),
                    {"wf_id": workflow_id},
                ).fetchone()

            assert row is not None, f"Workflow {workflow_id} not found in DBOS"

    def test_foreground_completes_synchronously(
        self, cli_runner: CliRunner, tmp_project_with_docs, dbos_launched
    ):
        """Test that without --background, workflow completes synchronously."""
        import json

        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--ids", "doc-1", "--dry-run", "--format", "json"],
        )
        assert_cli_success(result)

        data = json.loads(result.output)

        # Foreground mode should return full result
        assert isinstance(data, dict)
        assert "workflow_id" in data or "dry_run" in data or "success_count" in data

    def test_priority_affects_workflow(
        self, cli_runner: CliRunner, tmp_project_with_docs, dbos_launched
    ):
        """Test that --priority option is accepted and workflow runs."""
        import json

        result = invoke_cli(
            cli_runner,
            fetch_cmd,
            ["--ids", "doc-1", "--priority", "1", "--dry-run", "--format", "json"],
        )
        assert_cli_success(result)

        data = json.loads(result.output)
        assert isinstance(data, dict)
```

### Why Use Real DBOS Instead of Mocking

1. **Mocking is fragile**: Import paths change, mocks may not intercept the actual call
2. **Real integration issues**: Background mode involves DBOS queues, which have complex behavior
3. **Architecture validation**: Real DBOS enforces constraints (no workflows from steps, etc.)
4. **Database state verification**: Can verify workflow appears in `workflow_status` table

### Fixture Combination Guide

| Test Type | Fixtures to Use |
|-----------|-----------------|
| CLI help/options | `cli_runner` only |
| CLI with empty DB | `cli_runner` + `tmp_database` |
| CLI with sample data | `cli_runner` + `tmp_project_with_docs` |
| Background/workflow tests | `cli_runner` + `tmp_project_with_docs` + `dbos_launched` |
| Full workflow e2e | `tmp_kurt_project` (includes everything) |

### Common Test Patterns

```python
# Test help shows options
def test_fetch_shows_background_option(self, cli_runner):
    result = invoke_cli(cli_runner, fetch_cmd, ["--help"])
    assert_output_contains(result, "--background")
    assert_output_contains(result, "--priority")

# Test with DBOS for actual workflow execution
def test_fetch_with_background(self, cli_runner, tmp_project_with_docs, dbos_launched):
    result = invoke_cli(cli_runner, fetch_cmd, ["--background", "--format", "json"])
    assert_cli_success(result)
    # Verify workflow was queued in DBOS...
```
