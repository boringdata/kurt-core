# Kurt Model-Based Architecture Refactor

## Overview

Refactor Kurt's data layer to follow strict **1 model = 1 table** principle. Every table is owned by exactly one model. Data flows through the pipeline - no separate identity tables.

### Layers

| Layer | Prefix | Purpose |
|-------|--------|---------|
| **Landing** | `landing_*` | Raw ingestion (discovery, fetch) |
| **Staging** | `staging_*` | Transformation & enrichment |
| **Graph** | `graph_*` | Final queryable knowledge graph |
| **Retrieval** | `retrieval_*` | Query-time computed data |

## Current Problems

1. **`documents` table is a monolith** - 15+ columns written by multiple sources
2. **`documents` has no owning model** - It's an orphan identity table
3. **Junction tables written as side effects** - `entities`, `document_entities`, etc.
4. **Naming inconsistency** - Some tables use prefixes, others don't

---

## Core Principle: No Identity Tables

**Problem:** The current `documents` table is written by:
- CLI commands (manual add)
- Discovery model
- Fetch model (updates content fields)

**Solution:** `landing_discovery` IS the document registry. The `document_id` is generated there and flows through all downstream models.

```
landing_discovery (document_id generated here)
       ↓
landing_fetch (references document_id)
       ↓
staging_* (references document_id)
       ↓
graph_* (references document_id)
```

---

## Phase 1: Remove `documents` Table

### 1.1 Enhance `landing_discovery` to Be Document Registry

**File:** `src/kurt/models/landing/discovery.py`

```python
class DiscoveryRow(PipelineModelBase, table=True):
    """Document discovery - this IS the document registry."""
    __tablename__ = "landing_discovery"

    # Document identity (generated here, flows downstream)
    id: UUID = Field(default_factory=uuid4, primary_key=True)  # This IS document_id
    source_url: str = Field(unique=True, index=True)
    source_type: SourceType  # URL, FILE_UPLOAD, API

    # CMS identity (optional)
    cms_platform: Optional[str] = Field(default=None, index=True)
    cms_instance: Optional[str] = Field(default=None, index=True)
    cms_document_id: Optional[str] = Field(default=None, index=True)

    # Discovery metadata
    discovery_method: str  # sitemap, blogroll, manual, cms_api
    discovery_url: Optional[str] = None  # Where discovered from
    is_chronological: Optional[bool] = None  # Time-sensitive content

    # Status
    status: str = Field(default="DISCOVERED")  # DISCOVERED, ERROR
```

### 1.2 Update `landing_fetch` to Reference Discovery

**File:** `src/kurt/models/landing/fetch.py`

```python
class FetchRow(PipelineModelBase, table=True):
    """Fetch results for a document."""
    __tablename__ = "landing_fetch"

    document_id: str = Field(primary_key=True)  # FK to landing_discovery.id

    # Fetch results
    status: str = Field(default="pending")  # FETCHED, ERROR
    content_path: Optional[str] = None
    content_hash: Optional[str] = None
    content_length: int = Field(default=0)
    embedding: Optional[bytes] = None

    # Metadata extracted during fetch
    metadata_json: Optional[dict] = None  # title, description, author, published_date
```

### 1.3 Create `get_document()` Function

**File:** `src/kurt/db/documents.py`

```python
def get_document(document_id: UUID, session=None) -> dict:
    """
    Get full document by joining landing tables.

    Joins:
    - landing_discovery (identity + discovery data)
    - landing_fetch (fetch results + metadata)
    """
    discovery = session.query(DiscoveryRow).filter_by(id=document_id).first()
    fetch = session.query(FetchRow).filter_by(document_id=str(document_id)).first()

    return {
        "id": discovery.id,
        "source_url": discovery.source_url,
        "source_type": discovery.source_type,
        "title": fetch.metadata_json.get("title") if fetch else None,
        "status": get_document_status(document_id),
        # ... etc
    }
```

### 1.4 Migration

**File:** `src/kurt/db/migrations/versions/YYYYMMDD_0014_remove_documents_table.py`

1. Copy `documents` data to `landing_discovery` (identity fields)
2. Copy `documents` data to `landing_fetch` (content fields)
3. Update all FKs to point to `landing_discovery.id`
4. Drop `documents` table

---

## Phase 2: Graph Layer for Knowledge Graph

**Goal:** Create explicit models that materialize to knowledge graph tables.

### 2.1 Create Graph Directory Structure

```
src/kurt/models/graph/
├── __init__.py
├── entities/
│   ├── __init__.py
│   ├── entities.py              → graph_entities
│   ├── document_entities.py     → graph_document_entities
│   ├── entity_relationships.py  → graph_entity_relationships
│   └── document_entity_rels.py  → graph_document_entity_relationships
├── claims/
│   ├── __init__.py
│   ├── claims.py                → graph_claims
│   ├── claim_entities.py        → graph_claim_entities
│   └── claim_relationships.py   → graph_claim_relationships
└── topics/
    ├── __init__.py
    ├── topic_clusters.py        → graph_topic_clusters
    └── document_clusters.py     → graph_document_cluster_edges
```

### 2.2 `graph.entities.entities`

**File:** `src/kurt/models/graph/entities/entities.py`

```python
class GraphEntityRow(PipelineModelBase, table=True):
    """Materialized entity from staging data."""
    __tablename__ = "graph_entities"

    id: UUID = Field(primary_key=True)
    name: str = Field(index=True)
    entity_type: str = Field(index=True)
    canonical_name: Optional[str] = Field(index=True)
    aliases_json: Optional[list] = Field(sa_column=Column(JSON))
    description: Optional[str] = None
    embedding: bytes = b""
    confidence_score: float = Field(default=0.0)
    source_mentions: int = Field(default=0)


@model(
    name="graph.entities.entities",
    primary_key=["id"],
    write_strategy="upsert",
    description="Materialize entities from staging resolution",
)
@table(GraphEntityRow)
def entities(
    ctx: PipelineContext,
    entity_resolution=Reference("staging.indexing.entity_resolution"),
    writer: TableWriter = None,
):
    """Read from staging_entity_resolution and materialize to graph_entities."""
    pass
```

### 2.3 `graph.entities.document_entities`

**File:** `src/kurt/models/graph/entities/document_entities.py`

```python
class GraphDocumentEntityRow(PipelineModelBase, table=True):
    """Document-entity link materialized from staging."""
    __tablename__ = "graph_document_entities"

    id: UUID = Field(primary_key=True)
    document_id: UUID = Field(index=True)  # FK to landing_discovery.id
    entity_id: UUID = Field(index=True)    # FK to graph_entities.id
    section_id: Optional[str] = Field(index=True)
    mention_count: int = Field(default=1)
    confidence: float = Field(default=0.0)
    context: Optional[str] = None


@model(
    name="graph.entities.document_entities",
    primary_key=["id"],
    write_strategy="upsert",
    description="Materialize document-entity links from staging",
)
@table(GraphDocumentEntityRow)
def document_entities(
    ctx: PipelineContext,
    entity_resolution=Reference("staging.indexing.entity_resolution"),
    entities=Reference("graph.entities.entities"),
    writer: TableWriter = None,
):
    """Read from staging and graph_entities, write to graph_document_entities."""
    pass
```

### 2.4 Update Staging Models (Remove Side Effects)

**File:** `src/kurt/models/staging/indexing/step_entity_resolution.py`

```python
@model(
    name="staging.indexing.entity_resolution",
    primary_key=["entity_name", "workflow_id"],
    write_strategy="replace",
    description="Track entity resolution decisions (no side effects)",
)
@table(EntityResolutionRow)
def entity_resolution(...):
    """
    BEFORE: Wrote to staging_entity_resolution + entities + document_entities
    AFTER: Only writes to staging_entity_resolution

    Graph models handle materialization.
    """
    # Remove calls to create_entities(), link_existing_entities(), create_relationships()
    pass
```

---

## Phase 3: Rename Tables for Consistency

**Goal:** All tables follow `{layer}_{object}` naming.

### Current → New Names

| Current | New | Model |
|---------|-----|-------|
| `documents` | REMOVED | Use `landing_discovery` |
| `landing_discovery` | `landing_discovery` (keep) | `landing.discovery` |
| `landing_fetch` | `landing_fetch` (keep) | `landing.fetch` |
| `staging_document_sections` | `staging_sections` | `staging.indexing.sections` |
| `staging_section_extractions` | `staging_extractions` | `staging.indexing.extractions` |
| `staging_entity_clustering` | `staging_entity_clusters` | `staging.indexing.entity_clusters` |
| `staging_entity_resolution` | `staging_entity_resolution` (keep) | `staging.indexing.entity_resolution` |
| `staging_claim_clustering` | `staging_claim_clusters` | `staging.indexing.claim_clusters` |
| `staging_claim_resolution` | `staging_claim_resolution` (keep) | `staging.indexing.claim_resolution` |
| `staging_topic_clustering` | `staging_topic_clusters` | `staging.clustering.topics` |
| `retrieval_rag_context` | `retrieval_rag_context` (keep) | `retrieval.rag` |
| `retrieval_cag_context` | `retrieval_cag_context` (keep) | `retrieval.cag` |
| `entities` | `graph_entities` | `graph.entities.entities` |
| `document_entities` | `graph_document_entities` | `graph.entities.document_entities` |
| `entity_relationships` | `graph_entity_relationships` | `graph.entities.entity_relationships` |
| `document_entity_relationships` | `graph_document_entity_rels` | `graph.entities.document_entity_rels` |
| `claims` | `graph_claims` | `graph.claims.claims` |
| `claim_entities` | `graph_claim_entities` | `graph.claims.claim_entities` |
| `claim_relationships` | `graph_claim_relationships` | `graph.claims.claim_relationships` |
| `topic_clusters` | `graph_topic_clusters` | `graph.topics.clusters` |
| `document_cluster_edges` | `graph_document_clusters` | `graph.topics.document_clusters` |
| `document_links` | `landing_links` | `landing.fetch` (extracted during fetch) |

---

## Phase 4: Pipeline DAG

### Complete Pipeline Flow

```
landing.discovery (creates document_id)
       │
       ↓
landing.fetch (fetches content, extracts links)
       │
       ├──────────────────────────────────────────┐
       ↓                                          ↓
staging.indexing.sections              staging.clustering.topics
       ↓                                          ↓
staging.indexing.extractions           graph.topic_clusters
       │                                          ↓
       ├────────────────────┐            graph.document_clusters
       ↓                    ↓
staging.entity_clusters  staging.claim_clusters
       ↓                    ↓
staging.entity_resolution  staging.claim_resolution
       │                    │
       ├────────┐           ├────────┐
       ↓        ↓           ↓        ↓
graph.entities  graph.doc_ents  graph.claims  graph.claim_ents
       │
       ↓
graph.entity_relationships
       │
       ↓
graph.document_entity_rels
```

### CLI Integration

```bash
# Full pipeline
kurt run landing.discovery
kurt run landing.fetch
kurt run staging.indexing.*
kurt run graph.*

# Or single command
kurt index  # Runs fetch → staging → graph
```

---

## Phase 5: Migration Strategy

### 5.1 Incremental PRs

1. **PR 1: Remove documents table**
   - Migrate data to landing_discovery + landing_fetch
   - Update all FKs
   - Delete documents table

2. **PR 2: Create graph layer**
   - Add `graph/` directory with new models
   - Dual-write period (staging + graph)

3. **PR 3: Remove side effects from staging**
   - Staging models only write to staging tables
   - Graph models handle materialization

4. **PR 4: Rename tables**
   - Migration to standardize names

5. **PR 5: Clean up**
   - Remove deprecated code
   - Update all imports

### 5.2 Backward Compatibility

```python
# Deprecated imports (temporary)
from kurt.db.models import Document  # → Use get_document()
from kurt.db.models import Entity     # → Use graph_entities
```

---

## File Changes Summary

### New Files
```
src/kurt/models/graph/__init__.py
src/kurt/models/graph/entities/__init__.py
src/kurt/models/graph/entities/entities.py
src/kurt/models/graph/entities/document_entities.py
src/kurt/models/graph/entities/entity_relationships.py
src/kurt/models/graph/entities/document_entity_rels.py
src/kurt/models/graph/claims/__init__.py
src/kurt/models/graph/claims/claims.py
src/kurt/models/graph/claims/claim_entities.py
src/kurt/models/graph/claims/claim_relationships.py
src/kurt/models/graph/topics/__init__.py
src/kurt/models/graph/topics/clusters.py
src/kurt/models/graph/topics/document_clusters.py
src/kurt/db/migrations/versions/YYYYMMDD_0014_remove_documents_table.py
src/kurt/db/migrations/versions/YYYYMMDD_0015_create_graph_tables.py
src/kurt/db/migrations/versions/YYYYMMDD_0016_rename_tables.py
```

### Modified Files
```
src/kurt/models/landing/discovery.py  # Add identity fields
src/kurt/models/landing/fetch.py      # Add metadata fields
src/kurt/db/documents.py              # Add get_document() function
src/kurt/models/staging/indexing/step_entity_resolution.py  # Remove side effects
src/kurt/models/staging/indexing/step_claim_resolution.py   # Remove side effects
src/kurt/commands/content.py          # Use new query patterns
src/kurt/commands/kg.py               # Use new query patterns
```

### Deleted Files
```
src/kurt/db/models.py                 # Document class removed
src/kurt/db/graph_entities.py         # Logic moves to graph models
src/kurt/db/graph_resolution.py       # Logic moves to graph models
src/kurt/db/claim_resolution.py       # Logic moves to graph models
```

---

## Testing Strategy

### Unit Tests
- Each model has isolated unit tests
- Test that model reads from upstream and writes correctly

### Integration Tests
- Test full pipeline: landing → staging → graph
- Verify document_id flows correctly through all stages

### Migration Tests
- Test migration on copy of production database
- Verify no data loss

---

## Summary

| Before | After |
|--------|-------|
| `documents` table (no model) | REMOVED - use `landing_discovery` |
| Junction tables (side effects) | `graph_*` tables (explicit models) |
| Mixed naming | Consistent `{layer}_{object}` |
| Status stored in documents | Status derived from pipeline tables |

**Every table has exactly one owning model. Data flows through the pipeline.**
