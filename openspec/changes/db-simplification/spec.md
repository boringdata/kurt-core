# Database Module Simplification Spec

## Summary

The `src/kurt/db/` module has 12 files (~4000 LOC). After code review, here are the verified issues:

1. **Circular import**: `register_all_models()` in models.py imports from tools/ - creates db/ -> tools/ dependency
2. **Dual storage system**: Dolt (MySQL-based) vs SQLModel/SQLite - different tables for same purpose
3. **Overlapping utilities**: `documents.py` and `tool_tables.py` both do Dolt document operations

## Verified Findings

### `register_all_models()` Usage (CONFIRMED ISSUE)

**Called from 3 locations:**
- `src/kurt/db/sqlite.py:95-97` - in `init_database()`
- `src/kurt/db/postgresql.py:60-62` - in `init_database()`
- `src/kurt/core/tests/conftest.py:168-171` - in `tmp_database` fixture

**Imports these tool models:**
```python
from kurt.tools.fetch.models import FetchDocument
from kurt.tools.agent.models import AgentExecution
from kurt.tools.analytics.models import AnalyticsDomain, PageAnalytics
from kurt.tools.batch_embedding.models import BatchEmbeddingRecord
from kurt.tools.map.models import MapDocument
from kurt.tools.research.models import ResearchDocument
from kurt.tools.signals.models import MonitoringSignal
```

**Why this is bad**: db/ should be infrastructure layer. Having db/ import tools/ creates:
- Circular import risk
- Tight coupling
- Tool models must exist for db init to work

### `tool_tables.py` Usage (CONFIRMED USED)

**Used by 2 tools:**
- `src/kurt/tools/map/utils.py:134` - `batch_insert_map_results`
- `src/kurt/tools/fetch/utils.py:256` - `batch_insert_fetch_results`

**Purpose**: Insert rows into Dolt tables (`document_registry`, `map_results`, `fetch_results`)

**Re-exported in** `src/kurt/db/__init__.py:83-92`

### `documents.py` Usage (CONFIRMED USED)

**Used by 5 modules:**
- `src/kurt/documents/dolt_registry.py` - `get_dolt_db()` (3 locations)
- `src/kurt/documents/__init__.py` - `get_dolt_db()`, `upsert_documents()`
- `src/kurt/status/queries.py` - `get_dolt_db()`, `get_status_counts()`, `get_domain_counts()`
- `src/kurt/cli/show/tools_py.py` - `get_dolt_db()`
- `src/kurt/tools/map/utils.py` - `get_dolt_db()`
- `src/kurt/tools/fetch/utils.py` - `get_dolt_db()`
- `src/kurt/tools/fetch/cli.py` - `get_dolt_db()`, `upsert_documents()`

**Purpose**: Dolt-specific document CRUD for the unified `documents` table

## Dual Storage Architecture (CONFIRMED COMPLEXITY)

### SQLModel Tables (SQLite/PostgreSQL via Alembic)

Defined in `src/kurt/db/migrations/versions/20260108_002_workflow_tables.py`:
- `map_documents`
- `fetch_documents`
- `research_documents`
- `monitoring_signals`
- `analytics_domains`
- `page_analytics`

### Dolt Tables (MySQL-like via dolt_schema.sql)

Defined in `src/kurt/db/dolt_schema.sql`:
- `document_registry` - central registry
- `map_results` - MapTool output (keyed by document_id + run_id)
- `fetch_results` - FetchTool output (keyed by document_id + run_id)
- `embed_results` - EmbedTool output
- `documents` VIEW - joins all tool tables
- `workflow_runs`, `step_logs`, `step_events` - workflow observability
- `llm_traces` - LLM call tracking

### Key Difference

| Aspect | SQLModel Tables | Dolt Tables |
|--------|-----------------|-------------|
| Primary key | `document_id` | `(document_id, run_id)` |
| History | Overwrites | Preserves all runs |
| Updates | Single row per doc | New row per run |
| Use case | Current state | Full history |

**Both systems currently coexist.** Tools write to Dolt tables, SQLModel tables exist but are used inconsistently.

## Updated Files Inventory

| File | LOC | Purpose | Status |
|------|-----|---------|--------|
| `dolt.py` | 1019 | Dolt client (transactions, branching) | KEEP |
| `dolt_schema.sql` | 267 | Dolt schema definition | KEEP |
| `documents.py` | 410 | Dolt document operations (CRUD + counts) | KEEP (rename?) |
| `tool_tables.py` | 417 | Dolt insert helpers for tool results | KEEP (merge into documents.py?) |
| `tenant.py` | 414 | Workspace context, RLS | KEEP |
| `database.py` | 175 | Session management | KEEP |
| `models.py` | 122 | Mixins + LLMTrace + register_all_models | MODIFY |
| `base.py` | 109 | DatabaseClient interface | KEEP |
| `sqlite.py` | 202 | SQLite client | MODIFY |
| `postgresql.py` | 134 | PostgreSQL client | MODIFY |
| `cloud_api.py` | 68 | Cloud auth helpers | KEEP |
| `routing.py` | 55 | Mode-based routing | KEEP |
| `__init__.py` | 160 | Exports | KEEP |

## Phase 1: Remove Circular Import

### Problem

`register_all_models()` creates db/ -> tools/ dependency.

### Solution

Delete `register_all_models()`. SQLModel models auto-register when imported.

### Changes

1. **Delete `register_all_models()` from `models.py`** (lines 15-35)

2. **Update `sqlite.py` init_database()**
   ```python
   # Before (lines 95-97):
   from kurt.db.models import register_all_models
   register_all_models()

   # After:
   # Removed - models register on import
   ```

3. **Update `postgresql.py` init_database()**
   ```python
   # Before (lines 60-62):
   from kurt.db.models import register_all_models
   register_all_models()

   # After:
   # Removed - models register on import
   ```

4. **Update `conftest.py` tmp_database fixture**
   ```python
   # Before (lines 168-171):
   from kurt.db.models import register_all_models
   SQLModel.metadata.clear()
   register_all_models()

   # After:
   SQLModel.metadata.clear()
   # Import models that need to exist for tests
   from kurt.db.models import LLMTrace  # noqa: F401
   ```

### Why This Works

SQLModel uses a global MetaData registry. Models register when their module is imported:
- `class LLMTrace(SQLModel, table=True)` -> auto-registers
- `SQLModel.metadata.create_all(engine)` creates all registered tables

Tools import their own models when run. The db/ layer doesn't need to pre-register them.

### Verification

```bash
# Run db tests
uv run pytest src/kurt/db/tests/ -v

# Run tool tests (verify tools still work)
uv run pytest src/kurt/tools/map/tests/ -v
uv run pytest src/kurt/tools/fetch/tests/ -v
```

## Phase 2: Consolidate Dolt Utilities (Future)

### Problem

Two overlapping modules for Dolt document operations:
- `documents.py` - CRUD on `documents` table
- `tool_tables.py` - inserts to `document_registry`, `map_results`, `fetch_results`

### Analysis

`documents.py` functions:
- `get_dolt_db()` - factory (WIDELY USED)
- `upsert_document()` / `upsert_documents()` - write to `documents` table
- `get_document()` / `get_document_by_url()` - read single doc
- `list_documents()` / `count_documents()` - list with filters
- `get_existing_ids()` - check existence
- `get_status_counts()` / `get_domain_counts()` - aggregations

`tool_tables.py` functions:
- `register_document()` - upsert to `document_registry`
- `insert_map_result()` / `batch_insert_map_results()` - write to `map_results`
- `insert_fetch_result()` / `batch_insert_fetch_results()` - write to `fetch_results`
- `insert_embed_result()` - write to `embed_results`
- `get_documents_for_fetch()` - read from `documents` VIEW
- `get_existing_document_ids()` - check registry

### Recommendation

Keep both for now. They serve different purposes:
- `documents.py` - reads/queries
- `tool_tables.py` - tool-specific writes

Rename consideration:
- `documents.py` -> `dolt_queries.py` (more accurate)
- `tool_tables.py` -> `dolt_inserts.py` (more accurate)

## Phase 3: Resolve SQLModel vs Dolt (CRITICAL FINDING)

### Current State

**BOTH systems are actively used** - this is more complex than initially thought.

SQLModel tables (`map_documents`, `fetch_documents`):
- Defined in migrations and SQLModel classes (`MapDocument`, `FetchDocument`)
- Used by `DocumentRegistry` class (`src/kurt/documents/registry.py`)
- Joins `map_documents` and `fetch_documents` to build unified `DocumentView`
- Persisted via `persist_map_documents()` and `persist_fetch_documents()` in tool utils

Dolt tables (`document_registry`, `map_results`, `fetch_results`):
- Defined in `dolt_schema.sql`
- Used by `tool_tables.py` functions
- Different schema: composite PK `(document_id, run_id)` preserves history
- Persisted via `batch_insert_map_results()` and `batch_insert_fetch_results()`

### Actual Tool Flow (CRITICAL BUG FOUND)

**MapTool writes ONLY to Dolt:**
- `persist_map_documents()` -> `batch_insert_map_results()` -> Dolt `document_registry` + `map_results`
- **Does NOT write to SQLModel `map_documents` table**

**FetchTool writes ONLY to Dolt:**
- `persist_fetch_documents()` -> `batch_insert_fetch_results()` -> Dolt `fetch_results`
- **Does NOT write to SQLModel `fetch_documents` table**

**DocumentRegistry reads ONLY from SQLModel:**
- `build_joined_query()` -> SQLModel `select(MapDocument, FetchDocument)`
- **Does NOT read from Dolt tables**

**DATA INCONSISTENCY**: Tools write to Dolt, but queries read from SQLModel. This means:
- Production data goes to Dolt but is invisible to DocumentRegistry
- Test fixtures populate SQLModel tables directly
- CLI/web UI queries DocumentRegistry which sees empty tables in production

This explains why test fixtures use `session.add(MapDocument(...))` - they're populating the tables that DocumentRegistry queries.

### Key Classes

`DocumentRegistry` (`src/kurt/documents/registry.py`):
- Uses SQLModel/SQLAlchemy queries
- Joins `map_documents` LEFT JOIN `fetch_documents`
- Returns `DocumentView` dataclass

`DoltDocumentView` (`src/kurt/documents/dolt_registry.py`):
- Uses Dolt `documents` VIEW (joins `document_registry`, `map_results_latest`, etc.)
- Different field set than `DocumentView`

### Decision Needed

**Option A: Standardize on SQLModel** (RECOMMENDED)
- Keep SQLModel tables as source of truth
- Remove Dolt tables for document storage
- Keep Dolt only for: branching, diffing, workflow observability
- Pros: Simpler, one source of truth, standard ORM patterns
- Cons: Lose per-run history (can add `run_id` column if needed)

**Option B: Standardize on Dolt**
- Delete SQLModel workflow tables
- Update `DocumentRegistry` to query Dolt `documents` VIEW
- Pros: Built-in history, branching
- Cons: Non-standard queries (raw SQL), no SQLAlchemy integration

**Option C: Keep Both** (Current - NOT RECOMMENDED)
- Data written twice to two different systems
- High complexity, risk of inconsistency
- Hard to maintain

### Recommendation

**URGENT**: Fix the data flow before anything else. Currently:
- Tools write to Dolt
- Queries read from SQLModel
- **Data is lost/invisible**

**Option A** - Fix by standardizing on SQLModel (RECOMMENDED):
1. Update `persist_map_documents()` to write to SQLModel `map_documents` table
2. Update `persist_fetch_documents()` to write to SQLModel `fetch_documents` table
3. Remove Dolt document table writes (keep only workflow observability)
4. Deprecate `dolt_registry.py`

**Option B** - Fix by standardizing on Dolt:
1. Rewrite `DocumentRegistry` to query Dolt `documents` VIEW
2. Remove SQLModel workflow migrations
3. Keep using current persist functions

**Migration Steps** (Option A):
```python
# In persist_map_documents():
from kurt.db import managed_session
from kurt.tools.map.models import MapDocument

with managed_session() as session:
    for row in rows:
        doc = MapDocument(
            document_id=row["document_id"],
            source_url=row["source_url"],
            ...
        )
        session.merge(doc)  # upsert
```

5. Remove Dolt document tables from `dolt_schema.sql` (keep workflow_runs, step_logs, etc.)
6. Update CLAUDE.md with final architecture

## Tasks

### Phase 0 (URGENT) - Fix Data Flow Bug
The current architecture has a critical bug: tools write to Dolt, queries read from SQLModel.

**Option A - Write to SQLModel (RECOMMENDED):**
- [ ] Update `persist_map_documents()` in `src/kurt/tools/map/utils.py` to write to SQLModel
- [ ] Update `persist_fetch_documents()` in `src/kurt/tools/fetch/utils.py` to write to SQLModel
- [ ] Verify with test: `uv run pytest src/kurt/documents/tests/ -v`

**Option B - Read from Dolt:**
- [ ] Rewrite `DocumentRegistry` to use Dolt `documents` VIEW
- [ ] Update `build_joined_query()` to query Dolt instead of SQLModel

### Phase 1 - Remove Circular Import
- [ ] Delete `register_all_models()` from `db/models.py` (lines 15-35)
- [ ] Remove call from `sqlite.py` (lines 95-97)
- [ ] Remove call from `postgresql.py` (lines 60-62)
- [ ] Update `conftest.py` fixture (lines 168-171) - just import LLMTrace directly
- [ ] Run tests: `uv run pytest src/kurt/db/tests/ -v`
- [ ] Run tool tests: `uv run pytest src/kurt/tools/map/tests/ src/kurt/tools/fetch/tests/ -v`

### Phase 2 - Document Architecture
- [ ] Add docstring to `documents.py` explaining it's for Dolt unified `documents` table
- [ ] Add docstring to `tool_tables.py` explaining it's for tool-specific result tables
- [ ] Consider rename: `documents.py` -> `dolt_documents.py` (clarity)
- [ ] Document storage architecture in CLAUDE.md

### Phase 3 - Clean Up Unused Storage
After Phase 0, one storage system will be unused:
- [ ] If using SQLModel: Remove Dolt document tables from `dolt_schema.sql`
- [ ] If using SQLModel: Deprecate `dolt_registry.py` and `tool_tables.py`
- [ ] If using Dolt: Remove SQLModel workflow tables from migrations
- [ ] Update CLAUDE.md with final architecture

### Verification Commands
```bash
# Phase 1 - verify circular import fix
uv run python -c "from kurt.db import init_database"
uv run pytest src/kurt/db/tests/ -v
uv run pytest src/kurt/tools/map/tests/ src/kurt/tools/fetch/tests/ -v

# Check which storage system is actually queried
grep -r "session.exec\|session.query" src/kurt/documents/ --include="*.py"
grep -r "db.query\|db.execute" src/kurt/documents/ --include="*.py"
```

## Appendix: File References

```
src/kurt/db/
├── __init__.py          # Exports from all modules
├── base.py              # DatabaseClient abstract base
├── cloud_api.py         # Kurt cloud auth
├── database.py          # Session management (managed_session)
├── documents.py         # Dolt document CRUD (get_dolt_db, upsert_documents, etc.)
├── dolt.py              # DoltDB client class
├── dolt_schema.sql      # Dolt table definitions
├── models.py            # LLMTrace model + mixins + register_all_models
├── postgresql.py        # PostgreSQL client
├── routing.py           # Mode-based routing helper
├── sqlite.py            # SQLite client
├── tenant.py            # Workspace context + RLS
├── tool_tables.py       # Tool-specific Dolt insert helpers
├── migrations/          # Alembic migrations (SQLModel tables)
└── schema/              # Additional schema files
```
