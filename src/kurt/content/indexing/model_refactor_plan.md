# Indexing Pipeline Refactor Plan

This document describes the framework contract, current state, and migration steps for the new model-based indexing pipeline.

## Architecture Overview

The pipeline follows a **dbt-style declarative architecture**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CLI / Entry Point                                                          │
│    └─► resolve_filters() → DocumentFilters (with resolved UUIDs in .ids)   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Workflow                                                                   │
│    - Receives DocumentFilters with .ids = "uuid1,uuid2,uuid3" (resolved)   │
│    - Passes filters to each model                                          │
│    - Models use declarative sources={} to load upstream data               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Models (dbt-style)                                                         │
│    - Each model = one file, self-contained                                 │
│    - Each model = creates one table as output                              │
│    - Models declare sources={} for upstream dependencies (auto-loaded)     │
│    - Filter upstream data by document_id IN (filters.ids)                  │
│    - Use __init__ for row transformations (SQLModel + table=True caveat)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **Tables are the interface** between models (like dbt refs)
2. **Models are independent** - can be tested and run in isolation
3. **Filters flow through** - `DocumentFilters` passed from workflow to all models
4. **Filter resolution happens once** - at CLI/entry point via `filtering.py`
5. **Models are dumb consumers** - they receive resolved document_ids, no resolution logic
6. **Cross-section processing** - batch processing enables clustering across ALL sections in batch

### Data Flow (Updated Dec 15, 2024)

```
documents (source)
       │
       ▼ sources={"documents": ("documents", {"load_content": True})}
       │
┌──────┴──────┐
│ document_   │ ← OUT: indexing_document_sections table
│ sections    │    (splits docs into chunks with overlap)
└──────┬──────┘
       │ sources={"sections": "indexing_document_sections"}
       ▼
┌──────┴──────┐
│ section_    │ ← OUT: indexing_section_extractions table
│ extractions │    (entities, relationships, claims per section)
└──────┬──────┘
       │ sources={"extractions": "indexing_section_extractions"}
       ▼
┌──────┴──────┐
│ entity_     │ ← OUT: entities, document_entities tables
│ resolution  │    (cluster → resolve → create/link entities)
└──────┬──────┘
       │ sources={"extractions": "indexing_section_extractions", "entities": "entities"}
       ▼
┌──────┴──────┐
│ claim_      │ ← OUT: claims table
│ resolution  │    (dedupe → conflict detection → store claims)
└─────────────┘
```

**Key Change**: No intermediate `document_extractions` step! Entity resolution reads directly from `section_extractions` and clusters across ALL entities in the batch.

## Framework Contract

### Model File Structure (Updated)

```python
"""Model docstring."""
import logging
from typing import Any, Dict, Optional

import pandas as pd
from sqlmodel import Field

from kurt.content.indexing_new.framework import (
    PipelineModelBase,
    LLMTelemetryMixin,  # if using LLM
    TableWriter,
    model,
    _serialize,
    apply_dspy_telemetry,
    apply_field_renames,
)

logger = logging.getLogger(__name__)

# Section 1: constants / parameters
MAX_SECTION_CHARS = 5000

# Section 2: SQLModel schema with __init__ for transformations
class MyModelRow(PipelineModelBase, LLMTelemetryMixin, table=True):
    __tablename__ = "indexing_my_model"
    document_id: str = Field(primary_key=True)
    # ... model-specific fields

    def __init__(self, **data: Any):
        """Transform input data before creating row.

        Note: Using __init__ instead of model_validator because SQLModel
        with table=True doesn't properly support Pydantic v2 model_validator.
        """
        # Field renames
        apply_field_renames(data, {"old_name": "new_name"})

        # DSPy result serialization
        if "dspy_result" in data:
            r = data.pop("dspy_result")
            if r is not None:
                data["output_json"] = _serialize(r.output, {})

        # Telemetry extraction
        apply_dspy_telemetry(data)

        super().__init__(**data)

# Section 3: DSPy signatures (if model uses LLM)
class MySignature(dspy.Signature):
    ...

# Section 4: model function with declarative sources
@model(
    name="indexing.my_model",
    db_model=MyModelRow,
    primary_key=["document_id"],
    write_strategy="replace",
    description="...",
    sources={"upstream": "indexing_upstream_table"},  # auto-loaded!
)
def my_model(
    sources: Dict[str, pd.DataFrame],
    writer: TableWriter,
    **kwargs
):
    upstream_df = sources["upstream"]  # already loaded and filtered!

    # Process and write
    rows = [MyModelRow(**row) for row in upstream_df.to_dict("records")]
    return writer.write(rows)
```

### Sources Parameter Options

```python
# Simple: table name with default document_id filter
sources={"sections": "indexing_document_sections"}

# Custom filter function
sources={"entities": ("entities", lambda f: {"cluster_id": f.in_cluster})}

# Options dict (e.g., load file content for documents table)
sources={"documents": ("documents", {"load_content": True})}
```

### SQLModel Caveat: Use __init__ not model_validator

SQLModel with `table=True` doesn't properly support Pydantic v2's `model_validator(mode='before')`. Use custom `__init__` instead:

```python
# ❌ Doesn't work with SQLModel table=True
@model_validator(mode="before")
@classmethod
def transform(cls, data: dict) -> dict:
    ...

# ✅ Works correctly
def __init__(self, **data: Any):
    # Transform data here
    super().__init__(**data)
```

---

## Migration Status

### Stage 1 – Framework & Document Splitting ✅ COMPLETE
- Implemented decorator/registry, TableReader/Writer on SQLModel, DSPy helpers, DBOS integration.
- `step_document_sections` uses `sources={"documents": ("documents", {"load_content": True})}`.
- Framework auto-loads document content from files.

### Stage 2 – Section Extraction ✅ COMPLETE
- `step_extract_sections` uses `sources={"sections": "indexing_document_sections"}`.
- Uses `PipelineModelBase` + `LLMTelemetryMixin` for common columns.
- Uses `__init__` for DSPy result transformation.
- DSPy extracts entities, relationships, claims per section.

### Stage 3 – Entity Resolution 📋 PLANNED

**Key Insight**: Since we process batches of sections together, clustering can be done across ALL entities in the batch (not per-document). This improves deduplication quality.

#### New Architecture: Single Model

Replace the complex `workflow_entity_resolution.py` with a single `step_entity_resolution.py`:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  step_entity_resolution                                                      │
│                                                                              │
│  Input: indexing_section_extractions (all sections in batch)                │
│  Output: entities, document_entities tables (via direct DB writes)          │
│                                                                              │
│  Steps (all in one model):                                                  │
│  1. Collect ALL entities from ALL sections in batch                         │
│  2. Separate into "existing" (matched during extraction) vs "new"           │
│  3. Link existing entities to documents (Stage 2 logic)                     │
│  4. Cluster ALL new entities together (DBSCAN on embeddings)               │
│  5. Fetch similar existing entities for each cluster                        │
│  6. Resolve clusters with LLM (CREATE_NEW / MERGE_WITH / link to existing) │
│  7. Validate merge decisions                                                │
│  8. Create entities and document-entity links                               │
│  9. Create relationships                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Implementation Details

```python
@model(
    name="indexing.entity_resolution",
    db_model=EntityResolutionRow,  # tracking table for resolution decisions
    primary_key=["entity_name", "workflow_id"],
    write_strategy="replace",
    description="Resolve entities across all sections in batch",
    sources={"extractions": "indexing_section_extractions"},
    writes_to=["entities", "document_entities", "entity_relationships"],
)
def entity_resolution(
    sources: Dict[str, pd.DataFrame],
    writer: TableWriter,
    **kwargs
):
    extractions_df = sources["extractions"]

    # 1. Collect all entities from all sections
    all_entities, all_relationships = collect_entities_and_relationships(extractions_df)

    # 2. Separate existing vs new
    existing_entities, new_entities = partition_entities(all_entities)

    # 3. Link existing entities (reuse graph_resolution.link_existing_entities)
    link_existing_entities_batch(existing_entities)

    # 4. Cluster ALL new entities (cross-section clustering!)
    #    This is the key improvement: entities like "Python" appearing in
    #    different documents get clustered together
    groups = cluster_entities_by_similarity(new_entities, eps=0.25, min_samples=1)

    # 5. Fetch similar existing entities for each cluster
    group_tasks = fetch_similar_entities_for_groups(groups)

    # 6. Resolve with LLM (reuse resolution.resolve_single_group)
    resolutions = resolve_groups_with_llm(group_tasks)

    # 7. Validate merge decisions
    validated = validate_merge_decisions(resolutions)

    # 8-9. Create entities, links, relationships (reuse graph_resolution)
    entity_name_to_id = create_entities_and_links(validated, ...)
    create_relationships(all_relationships, entity_name_to_id)

    # Write tracking rows for observability
    return writer.write([...resolution tracking rows...])
```

#### Benefits of Cross-Section Clustering

1. **Better deduplication**: "Python" mentioned in doc A and "Python language" in doc B get clustered together
2. **Fewer LLM calls**: One resolution call per cluster instead of per-document
3. **Consistent entities**: Same entity gets same ID across all documents in batch
4. **Simpler pipeline**: No intermediate aggregation step needed

#### Reuse from Existing Code

- `kurt.db.graph_entities.cluster_entities_by_similarity` - DBSCAN clustering
- `kurt.db.graph_similarity.search_similar_entities` - vector similarity search
- `kurt.content.indexing.resolution.resolve_single_group` - LLM resolution
- `kurt.content.indexing.resolution.validate_merge_decisions` - validation
- `kurt.db.graph_resolution.*` - all DB operations (link, cleanup, create)

### Stage 4 – Claim Resolution 📋 PLANNED

Similar simplification:

```python
@model(
    name="indexing.claim_resolution",
    db_model=ClaimResolutionRow,
    primary_key=["claim_hash", "workflow_id"],
    sources={
        "extractions": "indexing_section_extractions",
        "entities": ("entities", lambda f: ...),  # resolved entities
    },
    writes_to=["claims"],
)
def claim_resolution(sources, writer, **kwargs):
    # 1. Collect all claims from all sections
    # 2. Deduplicate by statement similarity
    # 3. Link claims to resolved entities
    # 4. Detect conflicts between claims
    # 5. Store claims with confidence scores
    ...
```

---

## Workflow Architecture (Updated Dec 15, 2024)

### Declarative Pipeline Execution

The workflow uses a **declarative pipeline architecture** where:
- **Pipeline is defined as a list of model names** (`PipelineConfig`)
- **Models are pure Python functions** - testable without DBOS
- **DBOS wrapping happens at runtime** - each model becomes a named DBOS step
- **Framework handles orchestration** - loading sources, tracking results

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  @DBOS.workflow()                                                           │
│  indexing_workflow()                                                        │
│    ├─ _load_documents_step()  ← DBOS step                                  │
│    └─ run_pipeline(INDEXING_PIPELINE, ctx)                                 │
│         ├─ indexing.document_sections  ← DBOS step (named)                 │
│         ├─ indexing.section_extractions ← DBOS step (named)                │
│         ├─ indexing.entity_clustering   ← DBOS step (named)                │
│         └─ indexing.entity_upserts      ← DBOS step (named)                │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  Testing (no DBOS required)                                                 │
│    execute_model_sync("indexing.document_sections", ctx)                   │
│    # or call model function directly:                                       │
│    document_sections(sources=mock_df, writer=mock_writer)                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pipeline Definition

```python
# workflow_indexing.py
from kurt.content.indexing_new.framework import PipelineConfig

INDEXING_PIPELINE = PipelineConfig(
    name="indexing",
    models=[
        "indexing.document_sections",      # Split documents into sections
        "indexing.section_extractions",    # Extract entities/relationships with LLM
        "indexing.entity_clustering",      # Cluster entities + LLM resolution decisions
        "indexing.entity_upserts",         # Create entities/relationships in DB
    ],
)
```

### Key Framework Components

| Component | Purpose |
|-----------|---------|
| `PipelineConfig` | Declarative pipeline definition (list of models + options) |
| `ModelContext` | Execution context (filters, workflow_id, incremental_mode) |
| `run_pipeline()` | Execute pipeline with DBOS steps (production) |
| `execute_model_sync()` | Execute single model without DBOS (testing) |
| `@model` decorator | Register model in registry, auto-load sources |

### Why This Design?

1. **Testability**: Models are pure functions, can be tested with mock sources/writers
2. **DBOS Benefits**: Each model is a named DBOS step for tracking/resumability
3. **Declarative**: Pipeline defined as config, not imperative code
4. **Separation of Concerns**: Models don't know about DBOS, framework handles wrapping

### Testing Models

```python
# Direct model call (no DBOS, no framework)
from kurt.content.indexing_new.models.step_document_sections import document_sections

result = document_sections(
    sources={"documents": mock_dataframe},
    writer=mock_writer,
)

# Via framework (no DBOS)
from kurt.content.indexing_new.framework import execute_model_sync, ModelContext

ctx = ModelContext(filters=filters, workflow_id="test")
result = execute_model_sync("indexing.document_sections", ctx, payloads=[...])
```

---

### Cutover & CLI Integration

- Add feature flag `USE_NEW_INDEXING_PIPELINE` in `kurt.config`
- New workflow: `workflow_indexing.py` calls models in sequence
- Once tested, retire legacy tasks and workflows
