---
name: retrieve-content
description: Query and retrieve content from Kurt - list, filter, get metadata, read documents
---

# Retrieve Content Skill

**Purpose:** Query and access content stored in Kurt database
**Philosophy:** Dual storage (metadata in SQLite, content in markdown files)
**Context:** Used by content-writing-skill, writing-rules-skill, project-management-skill

**Contents:**
- [Storage Architecture](#storage-architecture)
- [Three Access Methods](#three-access-methods)
- [CLI Queries](#cli-queries)
- [SQL Queries](#sql-queries)
- [Python API](#python-api)
- [Command Reference](#command-reference)

---

## Storage Architecture

**Kurt uses dual storage:**

```
┌─────────────────────────────────────────┐
│ SQLite Database (.kurt/kurt.sqlite)    │
│ ────────────────────────────────────    │
│ • Document metadata (title, URL, etc.)  │
│ • Ingestion status (not_fetched/fetched)│
│ • Classification (type, topics, tools)  │
│ • content_path (relative file path)     │
└─────────────────────────────────────────┘
            ↓ References
┌─────────────────────────────────────────┐
│ File System (sources/)                  │
│ ───────────────────────                 │
│ • Markdown content files                │
│ • Organized by domain/path              │
│ • Full text, formatting preserved       │
└─────────────────────────────────────────┘
```

**Key tables:**
- `documents` - All document data (metadata + indexed classifications)
- `topic_clusters` - Extracted topic clusters
- `document_cluster_edges` - Links documents to topic clusters
- `entities` - Extracted entities (products, features, topics)

**Critical:** `content_path` in database is **relative** to `sources/` directory!

**Example:**
```
Database:  content_path = "example.com/docs/tutorial.md"
Filesystem: ./sources/example.com/docs/tutorial.md
```

---

## Three Access Methods

### 1. CLI (Interactive, Human-Friendly)

**Best for:** Daily workflow, exploration, verification

```bash
kurt content list --url-contains "tutorial"
kurt content get-metadata 550e8400
```

**Pros:** Interactive, formatted tables, quick filters
**Cons:** Limited query flexibility

---

### 2. SQL (Power Queries, Analytics)

**Best for:** Complex queries, joins, aggregations, bulk operations

```bash
sqlite3 .kurt/kurt.sqlite "SELECT title, source_url FROM documents WHERE ..."
```

**Pros:** Full SQL power, joins across tables
**Cons:** Requires SQL knowledge, verbose

---

### 3. Python API (Programmatic, Scripts)

**Best for:** Automation, integration with other tools, complex logic

```python
from kurt.document import list_documents, get_document
docs = list_documents(status="fetched", url_prefix="https://example.com")
```

**Pros:** Programmatic, type-safe, composable
**Cons:** Requires Python context

---

## CLI Queries

### List Documents

```bash
# Basic list (first 100)
kurt content list

# With limit
kurt content list --limit 20

# Filter by status
kurt content list --status fetched
kurt content list --status not_fetched
kurt content list --status error

# Filter by URL
kurt content list --url-starts-with https://docs.example.com
kurt content list --url-contains "/tutorials/"

# Combine filters
kurt content list \
  --status fetched \
  --url-contains "tutorial" \
  --limit 10

# JSON output (for scripting)
kurt content list --format json | jq '.[] | .title'
```

---

### Get Document Details

```bash
# Full or partial UUID
kurt content get-metadata 550e8400-e29b-41d4-a716-446655440000
kurt content get-metadata 550e8400

# JSON format
kurt content get-metadata 550e8400 --format json
```

**Output:**
- Title, URL, status
- Author, published_date
- Document type, topics, tools (if indexed)
- content_path (relative)

---

### Statistics

```bash
kurt content stats
```

Shows: Total docs, status breakdown, storage usage

---

## SQL Queries

### Schema Reference

**documents table:**
```sql
-- Core fields
id                          TEXT PRIMARY KEY    -- UUID
title                       TEXT                -- Page title
source_type                 TEXT                -- URL|FILE_UPLOAD|API
source_url                  TEXT UNIQUE         -- Original URL
content_path                TEXT                -- Relative path to .md file
ingestion_status            TEXT                -- NOT_FETCHED|FETCHED|ERROR

-- Content metadata
content_hash                TEXT                -- SHA256 for dedup
description                 TEXT                -- Meta description
author                      JSON                -- ["Author Name"]
published_date              TIMESTAMP           -- Publication date

-- Discovery metadata
is_chronological            BOOLEAN             -- Time-sensitive content (blog, changelog)
discovery_method            TEXT                -- sitemap|blogroll|manual
discovery_url               TEXT                -- URL where doc was discovered

-- Indexing metadata (populated by kurt content index)
indexed_with_hash           TEXT                -- Content hash when last indexed
indexed_with_git_commit     TEXT                -- Git commit when last indexed
content_type                TEXT                -- tutorial|guide|reference|blog|...
primary_topics              JSON                -- ["topic1", "topic2"]
tools_technologies          JSON                -- ["tool1", "tool2"]
has_code_examples           BOOLEAN             -- Contains code blocks
has_step_by_step_procedures BOOLEAN             -- Step-by-step instructions
has_narrative_structure     BOOLEAN             -- Storytelling approach

-- Timestamps
created_at                  TIMESTAMP
updated_at                  TIMESTAMP
```

**Other tables:**
```sql
-- topic_clusters: Extracted topic clusters
id, name, description, created_at, updated_at

-- document_cluster_edges: Links documents to clusters
id, document_id (FK), cluster_id (FK), created_at

-- entities: Extracted entities (products, features, topics)
id, name, entity_type, created_at, updated_at
```

---

### Query Examples

**List all documents:**
```bash
sqlite3 .kurt/kurt.sqlite \
  "SELECT id, title, source_url, ingestion_status FROM documents LIMIT 10;"
```

**Find by URL pattern:**
```bash
sqlite3 .kurt/kurt.sqlite \
  "SELECT title, source_url FROM documents
   WHERE source_url LIKE 'https://example.com%';"
```

**Find tutorials (indexed):**
```bash
sqlite3 .kurt/kurt.sqlite \
  "SELECT title, content_type, primary_topics
   FROM documents
   WHERE content_type = 'tutorial';"
```

**Count by status:**
```bash
sqlite3 .kurt/kurt.sqlite \
  "SELECT ingestion_status, COUNT(*) as count
   FROM documents
   GROUP BY ingestion_status;"
```

**Find duplicates by content hash:**
```bash
sqlite3 .kurt/kurt.sqlite \
  "SELECT content_hash, COUNT(*) as count, GROUP_CONCAT(title, ' | ') as titles
   FROM documents
   WHERE content_hash IS NOT NULL
   GROUP BY content_hash
   HAVING count > 1;"
```

**Documents published in 2024:**
```bash
sqlite3 .kurt/kurt.sqlite \
  "SELECT title, published_date
   FROM documents
   WHERE strftime('%Y', published_date) = '2024'
   ORDER BY published_date DESC;"
```

**Find documents with code examples:**
```bash
sqlite3 .kurt/kurt.sqlite \
  "SELECT title, content_type, has_code_examples, has_step_by_step_procedures
   FROM documents
   WHERE has_code_examples = 1;"
```

**Query by topic:**
```bash
sqlite3 .kurt/kurt.sqlite \
  "SELECT title, primary_topics, tools_technologies
   FROM documents
   WHERE json_extract(primary_topics, '$') LIKE '%authentication%';"
```

---

## Python API

### Import

```python
from kurt.document import (
    list_documents,       # Query documents
    get_document,         # Get by ID
    get_document_stats,   # Statistics
)
from kurt.models.models import IngestionStatus
from kurt.config import load_config
from pathlib import Path
```

---

### Query Documents

```python
# List all (first 100)
docs = list_documents()

# Filter by status
docs = list_documents(status=IngestionStatus.FETCHED, limit=20)

# Filter by URL
docs = list_documents(
    url_prefix="https://docs.example.com",
    url_contains="tutorial"
)

# Iterate results
for doc in docs:
    print(f"{doc['title']} - {doc['source_url']}")
```

---

### Get Document Details

```python
# Full or partial UUID
doc = get_document("550e8400-e29b-41d4-a716-446655440000")
doc = get_document("550e8400")  # Partial works

# Access fields
print(f"Title: {doc['title']}")
print(f"URL: {doc['source_url']}")
print(f"Status: {doc['ingestion_status']}")
print(f"Content path: {doc['content_path']}")
```

---

### Read Content

```python
# Get document
doc = get_document("550e8400")

# Build full path (content_path is relative!)
config = load_config()
source_base = config.get_absolute_source_path()  # Usually ./sources/
full_path = source_base / doc['content_path']

# Read content
content = full_path.read_text()
print(content)
```

**Critical:** Always prepend source directory to `content_path`!

---

### Statistics

```python
stats = get_document_stats()

print(f"Total: {stats['total_count']}")
print(f"Fetched: {stats['fetched_count']}")
print(f"Not fetched: {stats['not_fetched_count']}")
print(f"Errors: {stats['error_count']}")
```

---

## Command Reference

### CLI

```bash
# List documents
kurt content list                                # All (limit 100)
kurt content list --limit 20                     # First 20
kurt content list --status <status>              # By status
kurt content list --url-starts-with <prefix>     # By URL prefix
kurt content list --url-contains <substring>     # By URL substring
kurt content list --format json                  # JSON output

# Get details
kurt content get-metadata <doc-id>               # Document details
kurt content get-metadata <doc-id> --format json # JSON format

# Statistics
kurt content stats                               # Summary
```

### SQL

```bash
# Access database directly
sqlite3 .kurt/kurt.sqlite

# Single query
sqlite3 .kurt/kurt.sqlite "SELECT ..."

# Schema
sqlite3 .kurt/kurt.sqlite ".schema documents"
sqlite3 .kurt/kurt.sqlite ".schema topic_clusters"
sqlite3 .kurt/kurt.sqlite ".schema entities"
```

### Python

```python
from kurt.document import list_documents, get_document, get_document_stats
from kurt.models.models import IngestionStatus

# Query
docs = list_documents(status=IngestionStatus.FETCHED, limit=10)

# Get single
doc = get_document("550e8400")

# Stats
stats = get_document_stats()
```

---

## Tips

1. **Content path is relative:** Always prepend `sources/` when reading files
2. **Partial UUIDs work:** First 8 chars usually unique: `get-metadata 550e8400`
3. **Use CLI for exploration:** Quick checks and interactive queries
4. **Use SQL for analytics:** Complex queries, joins, aggregations
5. **Use Python for automation:** Scripts, integrations, complex logic
6. **Check stats first:** `kurt content stats` shows overview before deep dives
7. **JSON + jq for scripting:** `kurt content list --format json | jq`
8. **Query indexed metadata:** Use `content_type`, `primary_topics`, `tools_technologies` fields for filtered searches
