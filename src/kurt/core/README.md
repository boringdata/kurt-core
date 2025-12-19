# Indexing Pipeline Framework – Full Reference

The `kurt.core` package is the authoritative implementation of our dbt-style indexing framework. It combines SQLModel schemas, lazy data references, DBOS workflow orchestration, and DSPy utilities so every indexing step is a pure Python function that can be tested in isolation yet run as a resilient workflow step.

This document explains every moving part:

1. **Conceptual overview** – how workflows, contexts, and models interact
2. **Authoring models** – schemas, configuration, references, writers
3. **Framework modules** – what lives in `kurt/core`
4. **DB helpers you should reuse** – avoid re‑inventing query + persistence logic
5. **Pipeline execution + workflows** – building DAGs, running with/without DBOS
6. **Testing + tooling** – utilities for unit, integration, and end-to-end tests
7. **Best practices checklist** – quick reminders when creating new steps

---

## 1. Conceptual Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  DBOS Workflow (kurt.core.workflow.run_workflow / run_pipeline_workflow)│
│    • Resolves filters (DocumentFilters)                                   │
│    • Creates PipelineContext (workflow_id, incremental_mode, metadata)    │
│    • Calls run_pipeline() with PipelineConfig                             │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Pipeline Runner (kurt.core.model_runner.run_pipeline)                │
│    • Discovers dependencies via Reference()                           │
│    • Builds DAG & executes each level in parallel                     │
│    • Wraps each model in a named DBOS step and streams events         │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Model Function (@kurt.core.model decorator)                          │
│    • Receives PipelineContext + bound References + TableWriter        │
│    • Loads upstream tables lazily (auto filtering; load_content)      │
│    • Creates SQLModel rows and calls writer.write(rows)               │
│    • Returns dict {rows_written, extra stats}                         │
└──────────────────────────────────────────────────────────────────────┘
```

Every model is **pure Python**: no DBOS calls, no implicit globals. The framework injects everything (context, readers, config) via dependency injection, which keeps tests simple and production runs resilient.

---

## 2. New API: @table Decorator & Lazy References

The framework now provides a cleaner API that separates schema definition from table creation and makes data access explicit.

### 2.1 Define Schema with @table Decorator

Use pure Pydantic schemas and let `@table` generate the SQLModel table:

```python
from pydantic import BaseModel
from typing import Optional
from kurt.core import model, table, Reference, TableWriter

# 1. Pure Pydantic schema
class DocumentSchema(BaseModel):
    title: str
    source_url: Optional[str] = None
    content: str

# 2. Model with @table decorator
@model(name="indexing.documents", primary_key=["id"])
@table(DocumentSchema)  # Generates SQLModel with: id, title, source_url, content, created_at, updated_at
def documents(ctx, writer: TableWriter):
    ...
```

**Column ordering** is guaranteed:
1. `id` (UUID primary key) - first
2. User-defined fields - in schema order
3. `created_at`, `updated_at` - always last

**Timestamp triggers** are auto-generated for SQLite to update `updated_at` on every write.

### 2.2 Lazy References (SQLAlchemy Query)

References no longer prefetch data. Instead, they return a **lazy SQLAlchemy Query** that you filter and execute in your model code:

```python
@model(name="indexing.summaries", primary_key=["id"])
@table(SummarySchema)
def summaries(ctx, sections=Reference("indexing.sections"), writer: TableWriter):
    # Get the query (no data fetched yet)
    query = sections.query

    # Filter in your code (SQL pushdown)
    filtered = query.filter(sections.model_class.document_id.in_(ctx.document_ids))

    # Execute and get DataFrame
    df = sections.df(filtered)

    # Or get list of model instances
    rows = filtered.all()
```

**Reference API:**
- `.query` - Returns SQLAlchemy Query (lazy)
- `.model_class` - Returns SQLModel class for filter conditions
- `.df(query)` - Execute query and return DataFrame
- `.all(query)` - Execute query and return list

### 2.3 apply_dspy_on_df - Explicit LLM Processing

Instead of implicit `@llm` decorators, use `apply_dspy_on_df` to explicitly apply DSPy to DataFrame rows:

```python
import dspy
from kurt.core import apply_dspy_on_df

# Define your DSPy signature
class SummarizeDoc(dspy.Signature):
    """Summarize document content."""
    text: str = dspy.InputField()
    summary: str = dspy.OutputField()

@model(name="indexing.summaries", primary_key=["id"])
@table(SummarySchema)
def summaries(ctx, sections=Reference("indexing.sections"), writer: TableWriter):
    # 1. Get filtered data
    query = sections.query.filter(sections.model_class.document_id.in_(ctx.document_ids))
    df = sections.df(query)

    # 2. Apply DSPy explicitly (only processes rows you need!)
    df = apply_dspy_on_df(
        df,
        SummarizeDoc,
        input_fields={"text": "content"},       # Map signature inputs to df columns
        output_fields={"summary": "summary"},   # Map signature outputs to df columns
    )

    # 3. Write results
    writer.write(df)
```

**apply_dspy_on_df parameters:**
- `df` - Input DataFrame
- `signature` - DSPy Signature class
- `predictor_class` - DSPy predictor (default: `dspy.Predict`, can use `dspy.ChainOfThought`, etc.)
- `input_fields` - Map signature inputs to df columns `{"sig_field": "df_column"}`
- `output_fields` - Map signature outputs to df columns
- `pre_hook` - `(row_dict) -> row_dict` to preprocess each row
- `post_hook` - `(row_dict, result) -> row_dict` to postprocess
- `batch_size` - Number of rows per batch (default: 1)
- `progress` - Show tqdm progress bar (default: True)

**Example with ChainOfThought and hooks:**

```python
def clean_content(row):
    row["content"] = row["content"].strip()
    return row

def add_metadata(row, result):
    row["summary"] = result.summary
    row["word_count"] = len(result.summary.split())
    return row

df = apply_dspy_on_df(
    df,
    SummarizeDoc,
    predictor_class=dspy.ChainOfThought,  # Use CoT for better reasoning
    input_fields={"text": "content"},
    output_fields={"summary": "summary"},
    pre_hook=clean_content,
    post_hook=add_metadata,
    batch_size=10,
)
```

---

## 3. Legacy API (Still Supported)

The legacy API with explicit `db_model` and eager `Reference` loading still works:

```python
from kurt.core import (
    ConfigParam,
    ModelConfig,
    PipelineContext,
    PipelineModelBase,
    Reference,
    TableWriter,
    model,
)
```

### 3.1 Define Configuration (optional)

```python
class SectionConfig(ModelConfig):
    max_chars: int = ConfigParam(default=5_000, ge=500, le=20_000)
    overlap_chars: int = ConfigParam(default=200, ge=0, le=1_000)
```

`ModelConfig` ensures all runtime tuning knobs live in one place and can inherit from `ConfigParam` definitions.

### 3.2 Define Output Schema

```python
class SectionRow(PipelineModelBase, table=True):
    __tablename__ = "indexing_document_sections"
    document_id: str = Field(primary_key=True)
    section_id: str = Field(primary_key=True)
    content: str
    section_number: int
    error: Optional[str] = None  # Already provided by PipelineModelBase
```

`PipelineModelBase` adds `workflow_id`, timestamps, `model_name`, and `error`. Add `LLMTelemetryMixin` if the step calls DSPy or other LLMs.

### 3.3 Declare References

References describe upstream dependencies and how to load them.

- `Reference("indexing.section_extractions", filter={"workflow_id": lambda ctx: ctx.workflow_id})`
- `Reference("documents", load_content={"document_id_column": "document_id"}, filter="id")`
- Use `filter="column"` to push down DocumentFilter `ids`
- Use `filter={"column": lambda ctx: ...}` for runtime parameters (workflow_id, batches, etc.)
- Use callable filters (`lambda df, ctx`) only for niche scenarios—they require loading the entire table

### 3.4 Implement the Model

```python
@model(
    name="indexing.document_sections",
    db_model=SectionRow,
    primary_key=["document_id", "section_id"],
    config_schema=SectionConfig,
)
def document_sections(
    ctx: PipelineContext,
    documents=Reference(
        "documents",
        load_content={"document_id_column": "document_id"},
        filter="id",  # respects ctx.filters.ids
    ),
    writer: TableWriter = None,
    config: SectionConfig = None,
):
    docs_df = documents.df  # lazy load
    rows = [...]
    result = writer.write(rows)
    return {**result, "documents_processed": len(rows)}
```

### 3.5 Reuse DB Utilities When Possible

- `kurt.db.graph_queries.get_documents_entities()` and `get_document_entities()` for bulk entity lookups (avoids N+1 queries).
- `kurt.db.graph_resolution` helpers (`collect_entities_from_extractions`, `link_existing_entities`, `create_entities`, `create_relationships`) when building KG steps.
- `kurt.db.claim_operations.create_claim()` / `link_claim_to_entities()` / `detect_duplicate_claims()` for claim persistence and dedupe logic.

These modules encapsulate validations, UUID conversions, and logging—prefer them over handwritten SQL.

---

## 4. Framework Modules (kurt/core)

| Module | Purpose |
|--------|---------|
| `decorator.py` | `@model` decorator, reference binding, config injection, DBOS events, timing |
| `model_runner.py` | `PipelineContext`, `PipelineConfig`, DAG execution, async parallelism |
| `references.py` | `Reference` class, filter mechanics, dependency graph builder |
| `table_io.py` | `TableReader` (`load`, `load_content`, `query`) and `TableWriter` (bulk write, metadata, `update_indexed_hash`) |
| `mixins.py` | `PipelineModelBase`, `LLMTelemetryMixin`, `_serialize`, field helpers |
| `dspy_helpers.py` | `run_batch` / `run_batch_sync`, telemetry capture, model configuration |
| `dbos_events.py` + `display.py` | Event emission, CLI progress output |
| `workflow.py` | Generic DBOS workflows (`run_workflow`, `run_pipeline_workflow`, `resolve_pipeline`) |
| `testing.py` | Mocks for writers/readers, DSPy helpers, fixture loaders |

Import everything from `kurt.core` rather than private paths.

---

## 5. Quick Start Example (Legacy API)

```python
from uuid import uuid4
import pandas as pd
from sqlmodel import Field

from kurt.core import (
    ConfigParam,
    ModelConfig,
    PipelineContext,
    PipelineModelBase,
    Reference,
    TableWriter,
    model,
    PipelineConfig,
    run_pipeline,
)

class SummaryConfig(ModelConfig):
    include_code: bool = ConfigParam(default=True)

class SummaryRow(PipelineModelBase, table=True):
    __tablename__ = "indexing_document_summaries"
    document_id: str = Field(primary_key=True)
    summary: str

@model(
    name="indexing.document_summaries",
    db_model=SummaryRow,
    primary_key=["document_id"],
    config_schema=SummaryConfig,
)
def document_summaries(
    ctx: PipelineContext,
    sections=Reference(
        "indexing.document_sections",
        filter={"workflow_id": lambda ctx: ctx.workflow_id},
    ),
    writer: TableWriter = None,
    config: SummaryConfig = None,
):
    df = sections.df
    rows = []
    for doc_id, group in df.groupby("document_id"):
        text = "\n\n".join(group["content"])
        if config.include_code is False:
            text = text.replace("```", "")
        rows.append(SummaryRow(document_id=doc_id, summary=text[:1024]))
    return writer.write(rows)

# Run the model inside a pipeline
PIPELINE = PipelineConfig(name="indexing", models=["indexing.document_summaries"])
ctx = PipelineContext(filters=DocumentFilters(ids="..."), workflow_id=str(uuid4()))
result = await run_pipeline(PIPELINE, ctx)
```

---

## 6. Document Loading & References (Legacy)

### Document Filters

`PipelineContext.filters` is always a `DocumentFilters` instance. `TableReader` respects the full filter set (ids, include/exclude patterns, content type, ingestion status, limit). When you use `Reference("documents", filter="id", load_content=True)`:

1. SQL WHERE `id IN (:doc_ids)` is issued
2. File contents are loaded on demand
3. `skip` and `skip_reason` are set based on `indexed_with_hash` (delta mode)

### Reference Filter Types

| Filter Type | Pushdown? | Example |
|-------------|-----------|---------|
| `"column"` | ✅ SQL `WHERE column IN ctx.document_ids` | `filter="document_id"` |
| `{"column": lambda ctx: value}` | ✅ SQL parameter | `filter={"workflow_id": lambda ctx: ctx.workflow_id}` |
| `lambda df, ctx: df[...]` | ❌ In-memory filter (loads entire table) | `filter=lambda df, ctx: df.head(1)` |

Prefer string/dict filters for performance.

---

## 7. Pipeline Execution & Workflows

### Creating a Pipeline Automatically

```python
from kurt.core import get_pipeline
import kurt.content.indexing.models  # Ensure models register

PIPELINE = get_pipeline("indexing")
```

### Running with DBOS (CLI/Production)

```python
from kurt.core import run_pipeline_workflow
from kurt.content.filtering import DocumentFilters

await run_pipeline_workflow(
    target="indexing",  # namespace or path or single model
    filters=DocumentFilters(ids="doc-id-1,doc-id-2"),
    incremental_mode="delta",
    reprocess_unchanged=False,
)
```

### Running Without DBOS (Tests, Scripts)

```python
ctx = PipelineContext(filters=DocumentFilters(ids="doc-id"), workflow_id="dev")
result = await run_pipeline(PIPELINE, ctx)         # async
# or
execute_model_sync("indexing.document_sections", ctx)  # sync
```

### Parallel DAG Execution

`run_pipeline()` builds a dependency graph via `references.build_dependency_graph()` and runs each level concurrently. Logs + DBOS events show precisely which models ran and the rows they wrote. If any model in a level fails and `stop_on_error=True`, downstream levels are skipped.

---

## 8. Testing & Tooling

- `kurt.core.testing.MockTableReader` / `MockTableWriter` for unit tests
- `execute_model_sync()` to run a single model with in-memory data
- `run_pipeline()` inside `pytest.mark.asyncio` for integration tests
- Use `kurt.core.testing.mock_dspy()` to stub DSPy signatures/modules
- `tests/indexing_new/test_workflow_indexing_new.py` shows end-to-end patterns

Recommended structure:

```
models/tests/test_step_<name>.py
    • Unit tests for SQLModel schema + helper functions
    • Tests that mock references and writer

tests/indexing_new/test_workflow_<...>.py
    • Integration tests wiring multiple steps
```

---

## 9. DB Helpers Worth Knowing

| Module | Use Cases |
|--------|-----------|
| `kurt.db.graph_queries` | `get_documents_entities`, `get_document_entities`, `find_documents_with_relationship` |
| `kurt.db.graph_entities` | Bulk entity creation, linking, and dedupe |
| `kurt.db.graph_resolution` | Entity clustering utilities (`collect_entities_from_extractions`, `normalize_entities_for_clustering`, `link_existing_entities`, etc.) |
| `kurt.db.claim_operations` | Claim persistence (`create_claim`, `link_claim_to_entities`, conflict detection) |
| `kurt.db.claim_queries` | Text/embedding search for claim similarity |

Whenever you need to read/write graph or claim data, reach for these utilities before writing raw SQL—they centralize validations, logging, UUID handling, and schema evolution.

---

## 10. Best Practices Checklist

- [ ] Import from `kurt.core` (not internal modules) for decorators, contexts, references, etc.
- [ ] Define a `ModelConfig` even if it only holds defaults—tuning knobs matter later.
- [ ] Use string/dict Reference filters to push down SQL predicates.
- [ ] Use `load_content={"document_id_column": ...}` when reading documents so `skip` flags propagate, and call `writer.update_indexed_hash()` once a document finishes.
- [ ] Reuse helpers from `kurt.db.*` for entity/claim work instead of custom queries.
- [ ] Return `{"rows_written": ..., "rows_deduplicated": ..., "custom_metrics": ...}` – avoid bespoke logging for metrics you want in DBOS/UI.
- [ ] Test with `execute_model_sync()` and `MockTableWriter` for fast feedback; add integration tests for multi-model flows.
- [ ] Keep helper functions at the bottom of the file and mark them `_private` when appropriate.
- [ ] When adding references, ensure they include `workflow_id` filters so runs stay isolated.
- [ ] Emit as much context as possible in DBOS events by returning informative dicts (counts, decisions, etc.).

Following these guidelines ensures every new model plugs cleanly into the framework, scales with the DB, and remains easy to test and evolve. Happy indexing!

Start/end events work because they're emitted from the async context (before/after the thread).

**Alternatives considered:**

- **DBOS Queue**: Also uses worker threads with the same context limitation. See `kurt/workflows/_worker.py` for similar reasoning.
- **Sync execution**: Would work but loses parallelism benefit.

For detailed progress from inside models, use logging (captured to workflow log file).

## Key Design Principles

1. **Tables are the interface** - Models communicate via database tables (like dbt refs)
2. **Models are pure functions** - No DBOS dependency, testable in isolation
3. **DBOS wrapping at runtime** - Framework adds durability/tracking when needed
4. **Declarative sources** - Models declare dependencies, framework handles loading
5. **Filter resolution once** - `DocumentFilters` resolved at entry point, passed through
6. **Parallel by default** - Independent models run concurrently within DAG levels

## See Also

- [Model Refactor Plan](../../../indexing/model_refactor_plan.md) - Full architecture documentation
- [Workflow Definition](../../workflows/workflow_indexing.py) - Pipeline definition example
- [Model Examples](../../models/) - Implemented models
