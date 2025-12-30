# Iceberg-Inspired Metadata Design for Kurt Content Retrieval

## Executive Summary

This document proposes an Apache Iceberg-inspired metadata architecture for Kurt's content retrieval system. The design brings Iceberg's snapshot-based versioning, hierarchical metadata structure, and efficient query planning to Kurt's knowledge graph and RAG pipeline.

**Key Benefits:**
- **Version control** for content corpus and indexing state
- **Time travel** queries to retrieve content from historical indexing states
- **Efficient pruning** using statistics to skip irrelevant content partitions
- **Incremental indexing** with immutable metadata tracking
- **Reproducible content generation** tied to specific corpus snapshots
- **A/B testing** of different indexing strategies

---

## Background: Apache Iceberg Metadata Architecture

Apache Iceberg uses a hierarchical metadata tree to manage large-scale data tables:

```
Catalog (table name → current metadata.json)
  ↓
metadata.json (schema, partition spec, snapshots list)
  ↓
Snapshot (manifest-list.avro)
  ↓
Manifest List (list of manifest files + stats)
  ↓
Manifest Files (list of data files + column stats)
  ↓
Data Files (Parquet/ORC/Avro files)
```

**Core Principles:**
1. **Immutable metadata**: Each commit creates new metadata files, never modifies existing
2. **Snapshot isolation**: Each table state is a snapshot with unique ID
3. **Statistics for pruning**: Manifest files include min/max/null_count to skip partitions
4. **Self-describing**: JSON/Avro formats readable by any compatible engine
5. **Time travel**: Historical snapshots preserved for point-in-time queries

**Sources:**
- [Apache Iceberg Metadata Explained: Snapshots & Manifests](https://olake.io/blog/2025/10/03/iceberg-metadata/)
- [Understanding Apache Iceberg's metadata.json file](https://dev.to/alexmercedcoder/understanding-apache-icebergs-metadatajson-file-23f)
- [Apache Iceberg Spec](https://iceberg.apache.org/spec/)

---

## Kurt's Current Architecture (Summary)

Kurt's content retrieval system consists of:

1. **Document Storage**: Markdown files in `sources/{domain}/{path}/` + SQLite metadata
2. **Knowledge Graph**: Entities, relationships, and claims extracted via LLM pipeline
3. **Indexing Pipeline**: Multi-stage dbt-style transformations (section extraction → LLM extraction → entity clustering → resolution)
4. **RAG Retrieval**: Multi-signal search (graph traversal, semantic search, claim matching) with Reciprocal Rank Fusion

**Key Challenge**: No versioning of the indexed corpus state. When indexing pipeline changes or new documents are added, there's no way to query "what entities existed in last week's index?" or "reproduce content generated with Tuesday's corpus."

---

## Proposed: Iceberg-Inspired Metadata Architecture for Kurt

### Metadata Hierarchy

```
Corpus Catalog (corpus_name → current corpus-metadata.json)
  ↓
corpus-metadata.json (schema version, partition spec, snapshots)
  ↓
Corpus Snapshot (snapshot manifest at commit time)
  ↓
Partition Manifests (domain, content_type, date_range partitions)
  ↓
Document Manifests (document-level stats: entities, claims, relationships)
  ↓
Entity Manifests (entity-level stats: mention counts, confidence)
  ↓
Source Documents + Knowledge Graph (actual content)
```

### 1. Corpus Catalog Layer

**Purpose**: Maps human-readable corpus names to the latest metadata file location.

**Implementation**: SQLite table `corpus_catalog`:

```sql
CREATE TABLE corpus_catalog (
    corpus_name TEXT PRIMARY KEY,           -- e.g., "default", "blog-only", "docs-2024"
    current_metadata_file TEXT NOT NULL,    -- path to latest corpus-metadata.json
    created_at DATETIME,
    updated_at DATETIME
);
```

**Example**:
```json
{
  "corpus_name": "default",
  "current_metadata_file": "metadata/corpus/v0000042-1234567890.corpus-metadata.json",
  "updated_at": "2025-12-30T10:30:00Z"
}
```

---

### 2. Corpus Metadata File (corpus-metadata.json)

**Purpose**: Root metadata file describing the corpus structure, schema, and all historical snapshots.

**Location**: `metadata/corpus/v{sequence}-{timestamp}.corpus-metadata.json`

**Schema**:
```json
{
  "format-version": 1,
  "corpus-uuid": "a4c9e7f2-8d3b-4a1e-9c5f-7b8a6d4e2c1a",
  "location": "s3://kurt-data/corpora/default",

  "last-sequence-number": 42,
  "last-updated-ms": 1735557000000,

  "schema": {
    "schema-id": 3,
    "fields": [
      {"id": 1, "name": "document_id", "type": "uuid", "required": true},
      {"id": 2, "name": "title", "type": "string"},
      {"id": 3, "name": "source_url", "type": "string"},
      {"id": 4, "name": "content_type", "type": "string"},
      {"id": 5, "name": "published_date", "type": "timestamp"},
      {"id": 6, "name": "entity_count", "type": "int"},
      {"id": 7, "name": "claim_count", "type": "int"},
      {"id": 8, "name": "indexed_at", "type": "timestamp"}
    ]
  },

  "partition-spec": [
    {"id": 1, "name": "domain_partition", "source-id": 3, "transform": "truncate[domain]"},
    {"id": 2, "name": "content_type_partition", "source-id": 4, "transform": "identity"},
    {"id": 3, "name": "date_partition", "source-id": 5, "transform": "month"}
  ],

  "current-snapshot-id": 3827462938472,
  "snapshots": [
    {
      "snapshot-id": 3827462938472,
      "timestamp-ms": 1735557000000,
      "sequence-number": 42,
      "summary": {
        "operation": "incremental-index",
        "added-documents": 25,
        "removed-documents": 0,
        "added-entities": 142,
        "added-claims": 378,
        "indexing-pipeline-version": "v2.1.0",
        "git-commit": "ae44662"
      },
      "manifest-list": "metadata/snapshots/snap-3827462938472-manifest-list.avro"
    },
    {
      "snapshot-id": 3827461234567,
      "timestamp-ms": 1735470600000,
      "sequence-number": 41,
      "summary": {
        "operation": "full-reindex",
        "added-documents": 1250,
        "removed-documents": 1250,
        "added-entities": 8500,
        "indexing-pipeline-version": "v2.0.0"
      },
      "manifest-list": "metadata/snapshots/snap-3827461234567-manifest-list.avro"
    }
  ],

  "snapshot-log": [
    {"snapshot-id": 3827462938472, "timestamp-ms": 1735557000000},
    {"snapshot-id": 3827461234567, "timestamp-ms": 1735470600000}
  ],

  "metadata-log": [
    {
      "metadata-file": "metadata/corpus/v0000041-1735470600000.corpus-metadata.json",
      "timestamp-ms": 1735470600000
    }
  ]
}
```

**Key Fields Explained**:
- `schema`: Evolution-tracked field IDs (never reused) for backward compatibility
- `partition-spec`: How documents are organized (by domain, content type, date)
- `current-snapshot-id`: Points to latest indexed state
- `snapshots`: Full history of all indexing commits
- `summary.operation`: Type of change (incremental-index, full-reindex, entity-merge, schema-migration)
- `indexing-pipeline-version`: Tracks which pipeline version created the snapshot

---

### 3. Snapshot Manifest List

**Purpose**: Lists all partition manifests for a snapshot, with statistics for query pruning.

**Format**: Avro (or JSON for simplicity in Kurt)

**Location**: `metadata/snapshots/snap-{snapshot-id}-manifest-list.avro`

**Schema**:
```json
{
  "snapshot-id": 3827462938472,
  "timestamp-ms": 1735557000000,
  "summary": {
    "total-documents": 1275,
    "total-entities": 8642,
    "total-claims": 24356,
    "total-relationships": 12845
  },
  "manifests": [
    {
      "manifest-path": "metadata/manifests/domain=example.com-3827462938472.manifest.json",
      "manifest-length": 5432,
      "partition-spec-id": 1,
      "added-snapshot-id": 3827462938472,

      "partition": {
        "domain_partition": "example.com",
        "content_type_partition": "blog",
        "date_partition": "2024-12"
      },

      "statistics": {
        "document-count": 48,
        "entity-count": 324,
        "claim-count": 892,

        "entity-types": {
          "Technology": 156,
          "Product": 89,
          "Feature": 79
        },

        "published-date-range": {
          "min": "2024-12-01T00:00:00Z",
          "max": "2024-12-31T23:59:59Z"
        },

        "has-code-examples": true,
        "avg-confidence": 0.87
      }
    },
    {
      "manifest-path": "metadata/manifests/domain=docs.example.com-3827462938472.manifest.json",
      "partition": {
        "domain_partition": "docs.example.com",
        "content_type_partition": "reference",
        "date_partition": "2024-12"
      },
      "statistics": {
        "document-count": 122,
        "entity-count": 1893,
        "claim-count": 5421,
        "entity-types": {
          "Feature": 892,
          "Product": 445,
          "Technology": 334,
          "Integration": 222
        },
        "published-date-range": {
          "min": "2024-12-01T00:00:00Z",
          "max": "2024-12-31T23:59:59Z"
        },
        "has-code-examples": true,
        "avg-confidence": 0.92
      }
    }
  ]
}
```

**Query Pruning Example**:
```python
# Query: "How does FastAPI integrate with PostgreSQL?"
# Extracted entities: ["FastAPI", "PostgreSQL"]
# Entity types: ["Technology", "Technology"]

# Pruning logic:
for manifest in manifest_list["manifests"]:
    stats = manifest["statistics"]

    # Skip if partition has no Technology entities
    if "Technology" not in stats["entity-types"]:
        continue

    # Skip if content type is not relevant (blog posts less likely for integration docs)
    if manifest["partition"]["content_type_partition"] == "blog":
        continue

    # Include this manifest in scan
    manifests_to_scan.append(manifest)
```

---

### 4. Document Partition Manifests

**Purpose**: Lists all documents in a partition with document-level statistics.

**Location**: `metadata/manifests/domain={domain}-{snapshot-id}.manifest.json`

**Schema**:
```json
{
  "manifest-version": 1,
  "snapshot-id": 3827462938472,
  "partition": {
    "domain_partition": "docs.example.com",
    "content_type_partition": "reference",
    "date_partition": "2024-12"
  },

  "documents": [
    {
      "document-id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "source-url": "https://docs.example.com/integrations/postgresql",
      "content-path": "sources/docs.example.com/integrations/postgresql.md",
      "content-hash": "sha256:abc123...",

      "status": "ADDED",  // ADDED, EXISTING, DELETED
      "indexed-at": "2025-12-30T10:15:00Z",

      "metadata": {
        "title": "PostgreSQL Integration Guide",
        "content-type": "reference",
        "published-date": "2024-12-15T00:00:00Z",
        "word-count": 3542,
        "has-code-examples": true,
        "has-step-by-step-procedures": true
      },

      "statistics": {
        "entity-count": 18,
        "claim-count": 45,
        "relationship-count": 22,

        "entities": [
          {
            "entity-id": "ent-fastapi-001",
            "canonical-name": "FastAPI",
            "entity-type": "Technology",
            "mention-count": 12,
            "confidence": 0.95,
            "sections": ["Introduction", "Setup", "Connection Pooling"]
          },
          {
            "entity-id": "ent-postgresql-001",
            "canonical-name": "PostgreSQL",
            "entity-type": "Technology",
            "mention-count": 28,
            "confidence": 0.98,
            "sections": ["Introduction", "Setup", "Connection Pooling", "Migrations"]
          }
        ],

        "relationships": [
          {
            "source-entity": "FastAPI",
            "target-entity": "PostgreSQL",
            "relationship-type": "integrates_with",
            "confidence": 0.92,
            "evidence-count": 8
          }
        ],

        "claims": [
          {
            "claim-id": "claim-12345",
            "claim-text": "FastAPI supports async database queries with asyncpg",
            "claim-type": "Definition",
            "confidence": 0.89,
            "entities": ["FastAPI", "asyncpg"],
            "section": "Connection Pooling"
          }
        ],

        "embedding-norm": 1.0,
        "avg-claim-confidence": 0.87
      }
    }
  ]
}
```

---

### 5. Entity Manifest (Optional Enhancement)

**Purpose**: Provides an entity-centric view for graph-based queries.

**Location**: `metadata/manifests/entities-{snapshot-id}.manifest.json`

**Schema**:
```json
{
  "manifest-version": 1,
  "snapshot-id": 3827462938472,

  "entities": [
    {
      "entity-id": "ent-fastapi-001",
      "canonical-name": "FastAPI",
      "entity-type": "Technology",
      "description": "Modern Python web framework for building APIs",
      "aliases": ["Fast API", "fast-api"],

      "statistics": {
        "total-mentions": 342,
        "document-count": 28,
        "avg-confidence": 0.94,

        "documents": [
          {
            "document-id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "mention-count": 12,
            "sections": ["Introduction", "Setup", "Connection Pooling"]
          }
        ],

        "relationships": [
          {
            "target-entity": "PostgreSQL",
            "relationship-type": "integrates_with",
            "document-count": 8
          },
          {
            "target-entity": "SQLAlchemy",
            "relationship-type": "uses",
            "document-count": 15
          }
        ]
      }
    }
  ]
}
```

---

## Query Planning with Metadata Pruning

### Example: RAG Query with Metadata Pruning

**Query**: "How do I set up PostgreSQL connection pooling with FastAPI?"

**Traditional Kurt RAG** (current):
1. Extract entities: FastAPI, PostgreSQL
2. Search ALL documents via vector similarity
3. Search ALL entities in knowledge graph
4. Merge results with RRF

**Iceberg-Inspired RAG** (proposed):
1. Extract entities: FastAPI, PostgreSQL
2. Load current snapshot manifest list
3. **Prune partitions**:
   - Skip partitions where `entity-types["Technology"] == 0`
   - Skip partitions where `content-type == "blog"` (prefer "reference", "tutorial")
   - Prefer partitions with `has-code-examples == true`
4. Load only relevant document manifests
5. **Prune documents**:
   - Skip documents where neither FastAPI nor PostgreSQL appear in `statistics.entities`
   - Skip documents where `relationship-type != "integrates_with"`
   - Skip documents with `avg-claim-confidence < 0.7`
6. Load only pruned documents' full content
7. Execute semantic search on pruned set
8. Merge results with RRF

**Performance Gain**:
- **Before**: Scan 1,275 documents
- **After**: Scan ~50 documents (96% reduction)

---

## Snapshot Operations

### 1. Creating a Snapshot (Incremental Index)

**Trigger**: New documents fetched, or re-indexing of existing documents

**Process**:
1. Run indexing pipeline on new/changed documents
2. Generate document manifests for affected partitions
3. Create new snapshot manifest list (referencing old + new manifests)
4. Write new `corpus-metadata.json` with updated snapshot
5. Atomically update catalog pointer

**Implementation**:
```python
def create_snapshot(corpus_name: str, operation: str, changes: dict):
    # 1. Load current corpus metadata
    catalog = load_corpus_catalog()
    current_metadata = load_metadata_file(catalog[corpus_name]["current_metadata_file"])

    # 2. Generate new snapshot ID
    new_snapshot_id = generate_snapshot_id()
    sequence_number = current_metadata["last-sequence-number"] + 1

    # 3. Create/update partition manifests
    manifest_list = []
    for partition in get_affected_partitions(changes):
        manifest = create_partition_manifest(
            partition=partition,
            snapshot_id=new_snapshot_id,
            changes=changes[partition]
        )
        manifest_list.append(manifest)

    # 4. Inherit unchanged manifests from previous snapshot
    previous_manifest_list = load_manifest_list(
        current_metadata["snapshots"][-1]["manifest-list"]
    )
    for manifest in previous_manifest_list["manifests"]:
        if manifest["partition"] not in get_affected_partitions(changes):
            manifest_list.append(manifest)

    # 5. Write snapshot manifest list
    snapshot_manifest_path = write_manifest_list(new_snapshot_id, manifest_list)

    # 6. Create new corpus-metadata.json
    new_metadata = copy.deepcopy(current_metadata)
    new_metadata["last-sequence-number"] = sequence_number
    new_metadata["last-updated-ms"] = int(time.time() * 1000)
    new_metadata["current-snapshot-id"] = new_snapshot_id
    new_metadata["snapshots"].append({
        "snapshot-id": new_snapshot_id,
        "timestamp-ms": int(time.time() * 1000),
        "sequence-number": sequence_number,
        "summary": {
            "operation": operation,
            "added-documents": changes["added"],
            "removed-documents": changes["removed"],
            "indexing-pipeline-version": get_pipeline_version(),
            "git-commit": get_git_commit()
        },
        "manifest-list": snapshot_manifest_path
    })

    # 7. Write new metadata file
    new_metadata_path = write_metadata_file(new_metadata, sequence_number)

    # 8. Atomically update catalog
    update_catalog_pointer(corpus_name, new_metadata_path)
```

### 2. Time Travel Query

**Query**: "What entities existed in the December 15 snapshot?"

**Implementation**:
```python
def query_at_timestamp(corpus_name: str, timestamp: datetime, query: str):
    # 1. Load corpus metadata
    metadata = load_current_metadata(corpus_name)

    # 2. Find snapshot at timestamp
    snapshot = find_snapshot_at_time(metadata["snapshots"], timestamp)

    # 3. Load manifest list for that snapshot
    manifest_list = load_manifest_list(snapshot["manifest-list"])

    # 4. Execute query against that snapshot's manifests
    results = execute_rag_query(query, manifest_list, snapshot_id=snapshot["snapshot-id"])

    return results
```

### 3. Schema Evolution

**Use Case**: Adding new entity types or changing extraction logic

**Process**:
1. Create new schema version in `corpus-metadata.json`
2. Assign new field IDs (never reuse old IDs)
3. Re-index documents with new schema
4. Create snapshot with `operation: "schema-migration"`
5. Old snapshots remain queryable with old schema

**Example**:
```json
{
  "schema": {
    "schema-id": 4,  // Incremented
    "fields": [
      {"id": 1, "name": "document_id", "type": "uuid", "required": true},
      // ... existing fields ...
      {"id": 9, "name": "sentiment_score", "type": "float"},  // NEW
      {"id": 10, "name": "complexity_score", "type": "float"}  // NEW
    ]
  }
}
```

---

## Implementation Plan

### Phase 1: Core Metadata Infrastructure (Week 1-2)
- [ ] Define metadata schemas (corpus-metadata.json, manifest list, document manifest)
- [ ] Implement `corpus_catalog` table
- [ ] Create metadata file writers (JSON serialization)
- [ ] Build snapshot creation logic

### Phase 2: Partition Manifests (Week 3)
- [ ] Implement partition spec (domain, content_type, date)
- [ ] Generate partition manifests from existing documents
- [ ] Add statistics computation (entity counts, confidence, date ranges)
- [ ] Create manifest list writer

### Phase 3: Query Pruning (Week 4)
- [ ] Implement manifest list loader
- [ ] Build partition pruning logic
- [ ] Integrate with RAG query planner
- [ ] Benchmark query performance improvements

### Phase 4: Time Travel (Week 5)
- [ ] Implement snapshot log queries
- [ ] Add time-travel API to RAG pipeline
- [ ] Create CLI commands for snapshot management

### Phase 5: Advanced Features (Week 6+)
- [ ] Schema evolution support
- [ ] Entity manifests for graph queries
- [ ] Incremental snapshot creation
- [ ] Snapshot compaction (merge small manifests)
- [ ] Metadata cleanup (expire old snapshots)

---

## Example Use Cases

### Use Case 1: Reproducible Content Generation

**Problem**: Content generated last week can't be reproduced because the corpus has changed.

**Solution**:
```python
# Original generation (2025-12-20)
content = generate_blog_post(
    topic="FastAPI best practices",
    snapshot_id=3827461234567  # Explicitly pinned
)

# Reproduce exactly (2025-12-30)
content_reproduced = generate_blog_post(
    topic="FastAPI best practices",
    snapshot_id=3827461234567  # Same snapshot
)

assert content == content_reproduced  # Guaranteed identical
```

### Use Case 2: A/B Testing Indexing Strategies

**Problem**: Want to compare entity extraction quality between pipeline v2.0 and v2.1.

**Solution**:
```python
# Create parallel snapshots
snapshot_v20 = create_snapshot(
    corpus_name="default-v20",
    pipeline_version="v2.0.0"
)

snapshot_v21 = create_snapshot(
    corpus_name="default-v21",
    pipeline_version="v2.1.0"
)

# Compare results
results_v20 = query(corpus="default-v20", query="FastAPI integration")
results_v21 = query(corpus="default-v21", query="FastAPI integration")

compare_quality(results_v20, results_v21)
```

### Use Case 3: Efficient Query Planning

**Query**: "PostgreSQL migration tutorials published in 2024"

**Pruning**:
```python
manifest_list = load_manifest_list(current_snapshot)

for manifest in manifest_list["manifests"]:
    # Prune by date
    if not overlaps_year(manifest["statistics"]["published-date-range"], 2024):
        continue

    # Prune by content type
    if manifest["partition"]["content_type_partition"] not in ["tutorial", "guide"]:
        continue

    # Prune by entities
    if "PostgreSQL" not in manifest["statistics"]["top-entities"]:
        continue

    # Include this manifest
    manifests_to_scan.append(manifest)
```

---

## Migration Strategy

### Backward Compatibility

1. **Dual-write period**: Write to both old schema and new metadata files
2. **Lazy migration**: Create initial snapshot from existing database state
3. **Gradual rollout**: Enable metadata pruning only for new queries (old queries use full scan)
4. **Feature flags**: Control snapshot creation, time travel, and pruning independently

### Initial Snapshot Creation

```python
def bootstrap_iceberg_metadata():
    """Create initial snapshot from existing Kurt database."""

    # 1. Query all documents
    documents = db.query(Document).all()

    # 2. Partition by domain, content_type, date
    partitions = partition_documents(documents)

    # 3. Generate manifests for each partition
    manifests = []
    for partition_key, docs in partitions.items():
        manifest = create_partition_manifest(
            partition=partition_key,
            documents=docs,
            snapshot_id=generate_snapshot_id()
        )
        manifests.append(manifest)

    # 4. Create initial corpus-metadata.json
    metadata = {
        "format-version": 1,
        "corpus-uuid": str(uuid.uuid4()),
        "last-sequence-number": 1,
        "schema": get_current_schema(),
        "partition-spec": get_partition_spec(),
        "current-snapshot-id": manifests[0]["snapshot-id"],
        "snapshots": [create_snapshot_entry(manifests)]
    }

    # 5. Write metadata files
    write_metadata_file(metadata, sequence_number=1)
    update_catalog_pointer("default", metadata_path)
```

---

## Performance Considerations

### Metadata File Size

**Estimates** (based on 1,275 documents):
- `corpus-metadata.json`: ~10 KB (scales with # snapshots)
- Manifest list per snapshot: ~50 KB (scales with # partitions)
- Document manifest per partition: ~100 KB for 50 documents
- **Total per snapshot**: ~500 KB

**Optimization**: Use Avro for manifest files (50% smaller + schema evolution support)

### Query Planning Overhead

**Metadata Read Cost**:
- Load corpus-metadata.json: ~10 KB
- Load manifest list: ~50 KB
- Load N document manifests: N × 100 KB

**Breakeven Analysis**:
- **Small queries** (< 100 docs needed): Overhead may exceed benefit
- **Large queries** (> 500 docs needed): 10-100x speedup from pruning
- **Recommendation**: Use pruning for complex queries, skip for simple lookups

### Snapshot Retention

**Policy Recommendations**:
- Keep last 30 snapshots (daily indexing = 1 month retention)
- Keep weekly snapshots for 6 months
- Keep monthly snapshots for 2 years
- Compact manifests when merging snapshots

---

## Open Questions

1. **Partition Strategy**: Should we partition by domain, content_type, date, or all three? Trade-off between partition count and pruning effectiveness.

2. **Entity Manifests**: Worth the complexity? Entity-centric queries may benefit, but adds 2x metadata overhead.

3. **Manifest Format**: JSON (readable, debuggable) vs Avro (compact, schema evolution)? Start with JSON, migrate to Avro later?

4. **Snapshot Frequency**: Create snapshot on every incremental index? Daily batched? Manual trigger only?

5. **Distributed Storage**: Keep metadata in SQLite (current) or move to object storage (S3-compatible)? Iceberg uses object storage for scalability.

6. **Claim Deduplication**: Should claims have their own manifests? Currently embedded in document manifests.

---

## Conclusion

This Iceberg-inspired metadata design brings data warehouse-grade versioning and query planning to Kurt's content retrieval system. The hierarchical metadata structure enables:

- **Reproducibility**: Pin content generation to specific corpus snapshots
- **Performance**: Prune irrelevant partitions using statistics
- **Auditability**: Track indexing pipeline evolution over time
- **Flexibility**: Time travel to any historical corpus state

The design is backward-compatible, incrementally adoptable, and aligns with Kurt's existing dbt-style pipeline architecture.

**Next Steps**: Review with team, validate partition strategy with real queries, and begin Phase 1 implementation.
