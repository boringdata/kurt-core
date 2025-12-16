# Indexing Pipeline Framework

A **dbt-style declarative framework** for building data pipelines with SQLModel, DBOS, and DSPy.

## Quick Start

```python
from kurt.content.indexing_new.framework import (
    model,
    PipelineModelBase,
    TableWriter,
    PipelineConfig,
    run_pipeline,
    ModelContext,
)

# 1. Define your output schema
class MyModelRow(PipelineModelBase, table=True):
    __tablename__ = "my_output_table"
    document_id: str = Field(primary_key=True)
    result: str

# 2. Create a model with declarative sources
@model(
    name="my.model",
    db_model=MyModelRow,
    primary_key=["document_id"],
    sources={"input": "upstream_table"},  # Auto-loaded!
)
def my_model(sources, writer):
    df = sources["input"]  # Already loaded and filtered
    rows = [MyModelRow(document_id=r["id"], result=r["data"]) for r in df.to_dict("records")]
    return writer.write(rows)

# 3. Define a pipeline
PIPELINE = PipelineConfig(name="my_pipeline", models=["my.model"])

# 4. Run it
ctx = ModelContext(filters=filters, workflow_id="wf-123")
result = await run_pipeline(PIPELINE, ctx)
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Workflow (@DBOS.workflow)                                                  │
│    └─ run_pipeline(PIPELINE, ctx)                                          │
│         ├─ model_1 → DBOS step (named, resumable)                          │
│         ├─ model_2 → DBOS step (named, resumable)                          │
│         └─ ...                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  Models (pure Python functions)                                             │
│    - Declare sources={} for upstream data (auto-loaded)                    │
│    - Receive sources dict + writer                                          │
│    - Return writer.write(rows)                                              │
│    - Testable without DBOS                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### `@model` Decorator

Registers a model function with metadata for the framework.

```python
@model(
    name="indexing.document_sections",      # Unique model name
    db_model=DocumentSectionRow,            # SQLModel class for output
    primary_key=["document_id", "section_id"],
    write_strategy="replace",               # "append", "merge", or "replace"
    description="Split documents into sections",
    sources={"documents": ("documents", {"load_content": True})},
    config_schema=DocumentSectionsConfig,   # Optional: auto-inject config
)
def document_sections(sources, writer, config, **kwargs):
    batch_size = config.batch_size  # Access config values
    ...
```

### `sources` Parameter

Declare upstream dependencies. The framework auto-loads them filtered by `document_id`.

```python
# Simple: table name (filtered by document_id)
sources={"sections": "indexing_document_sections"}

# With options (e.g., load file content)
sources={"documents": ("documents", {"load_content": True})}

# Custom filter function
sources={"entities": ("entities", lambda f: {"cluster_id": f.in_cluster})}
```

### `PipelineConfig`

Declarative pipeline definition.

```python
INDEXING_PIPELINE = PipelineConfig(
    name="indexing",
    models=[
        "indexing.document_sections",
        "indexing.section_extractions",
        "indexing.entity_resolution",
    ],
    stop_on_error=True,  # Stop pipeline on first error (default)
)
```

### `ModelContext`

Execution context passed to all models.

```python
ctx = ModelContext(
    filters=DocumentFilters(ids="uuid1,uuid2"),  # Resolved document IDs
    incremental_mode="full",                      # "full" or "delta"
    workflow_id="wf-123",                         # For tracking
    metadata={"extra": "data"},                   # Passed to all models
)
```

### `run_pipeline()` vs `execute_model_sync()`

| Function | DBOS | Use Case |
|----------|------|----------|
| `run_pipeline()` | Yes | Production - each model is a DBOS step |
| `execute_model_sync()` | No | Testing - direct model execution |

```python
# Production (with DBOS)
result = await run_pipeline(PIPELINE, ctx)

# Testing (no DBOS)
result = execute_model_sync("indexing.document_sections", ctx)
```

## Output Schemas

### `PipelineModelBase`

Base class with common fields for all pipeline outputs.

```python
class PipelineModelBase(SQLModel):
    workflow_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_name: Optional[str]
    error: Optional[str]
```

### `LLMTelemetryMixin`

Mixin for models that use LLM (DSPy).

```python
class LLMTelemetryMixin(SQLModel):
    llm_model: Optional[str]
    llm_input_tokens: Optional[int]
    llm_output_tokens: Optional[int]
    llm_cost_usd: Optional[float]
    llm_latency_ms: Optional[int]
```

### Example Model Schema

```python
class SectionExtractionRow(PipelineModelBase, LLMTelemetryMixin, table=True):
    __tablename__ = "indexing_section_extractions"

    # Primary key
    document_id: str = Field(primary_key=True)
    section_id: str = Field(primary_key=True)

    # Model output
    entities_json: Optional[str]
    relationships_json: Optional[str]

    def __init__(self, **data):
        # Transform DSPy result before storing
        apply_dspy_telemetry(data)
        super().__init__(**data)
```

## Table I/O

### `TableReader`

Read data from tables with filtering.

```python
reader = TableReader(filters=ctx.filters, workflow_id=ctx.workflow_id)

# Load with document_id filter
df = reader.load("indexing_document_sections", where={"document_id": doc_ids})

# Load documents with file content
df = reader.load("documents", where={"id": doc_ids}, load_content=True)
```

### `TableWriter`

Write SQLModel rows to tables.

```python
writer = TableWriter(workflow_id=ctx.workflow_id)
result = writer.write(rows)  # Returns {"rows_written": N, "table_name": "..."}
```

## Testing Models

Models are pure Python functions - test them directly without DBOS.

```python
from unittest.mock import MagicMock
import pandas as pd

def test_my_model():
    # Create mock sources
    sources = {"input": pd.DataFrame([{"id": "1", "data": "test"}])}

    # Create mock writer
    mock_writer = MagicMock()
    mock_writer.write.return_value = {"rows_written": 1}

    # Call model directly
    result = my_model(sources=sources, writer=mock_writer)

    # Verify
    assert result["rows_written"] == 1
    mock_writer.write.assert_called_once()
```

## DSPy Integration

### Helper Functions

```python
from kurt.content.indexing_new.framework import (
    _serialize,
    apply_dspy_telemetry,
    apply_field_renames,
)

# In your SQLModel __init__:
def __init__(self, **data):
    # Rename fields from DSPy output
    apply_field_renames(data, {"old_name": "new_name"})

    # Extract telemetry from DSPy result
    apply_dspy_telemetry(data)

    # Serialize complex objects to JSON
    if "dspy_result" in data:
        data["output_json"] = _serialize(data.pop("dspy_result").output, {})

    super().__init__(**data)
```

## File Structure

```
framework/
├── __init__.py          # Public exports
├── decorator.py         # @model decorator, sources loading
├── model_runner.py      # PipelineConfig, run_pipeline, execute_model_sync
├── registry.py          # ModelRegistry for model lookup
├── table_io.py          # TableReader, TableWriter
├── mixins.py            # PipelineModelBase, LLMTelemetryMixin
├── dspy_helpers.py      # DSPy serialization utilities
├── dbos_events.py       # DBOS event emission
├── dbos_integration.py  # DBOS configuration
├── display.py           # Progress display utilities
└── testing.py           # Test utilities
```

## Key Design Principles

1. **Tables are the interface** - Models communicate via database tables (like dbt refs)
2. **Models are pure functions** - No DBOS dependency, testable in isolation
3. **DBOS wrapping at runtime** - Framework adds durability/tracking when needed
4. **Declarative sources** - Models declare dependencies, framework handles loading
5. **Filter resolution once** - `DocumentFilters` resolved at entry point, passed through

## See Also

- [Model Refactor Plan](../../../indexing/model_refactor_plan.md) - Full architecture documentation
- [Workflow Definition](../../workflows/workflow_indexing.py) - Pipeline definition example
- [Model Examples](../../models/) - Implemented models
