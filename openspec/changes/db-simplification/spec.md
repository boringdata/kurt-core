# Database Module Simplification Spec

## Summary

The `src/kurt/db/` module has 12 files (~4000 LOC). Key issues:
1. **Circular import**: `register_all_models()` imports from tools/
2. **Unclear boundaries**: documents.py, tool_tables.py overlap with tool responsibilities
3. **Dual storage**: Some tools use Dolt, others use SQLModel - inconsistent

## Current Files

| File | LOC | Purpose | Status |
|------|-----|---------|--------|
| `dolt.py` | 1019 | Dolt client (transactions, branching) | KEEP |
| `documents.py` | 410 | Dolt document operations | EVALUATE |
| `tool_tables.py` | 417 | Insert helpers for tool results | EVALUATE |
| `tenant.py` | 414 | Workspace context, RLS | KEEP |
| `database.py` | 175 | Session management | KEEP |
| `models.py` | 122 | Mixins + LLMTrace | MODIFY |
| `base.py` | 109 | DatabaseClient interface | KEEP |
| `sqlite.py` | 202 | SQLite client | KEEP |
| `postgresql.py` | 134 | PostgreSQL client | KEEP |
| `cloud_api.py` | 68 | Cloud auth helpers | KEEP |
| `routing.py` | 55 | Mode-based routing | KEEP |
| `__init__.py` | 160 | Exports | KEEP |

## Issues

### 1. Circular Import (Critical)

```python
# db/models.py lines 23-34 - imports from tools/
def register_all_models():
    from kurt.tools.fetch.models import FetchDocument
    from kurt.tools.agent.models import AgentExecution
    from kurt.tools.batch_embedding.models import BatchEmbeddingRecord
    # ... etc
```

**Problem**: db/ should be infrastructure layer, not depend on tools/

**Fix**: Delete `register_all_models()`. Tools register models at import time via SQLModel metadata.

### 2. Unclear Document/Table Boundaries

- `documents.py` - Dolt-specific document operations
- `tool_tables.py` - Generic insert helpers for map_results, fetch_results, etc.

**Question**: Should tools own their persistence logic?

**Options**:
1. Keep db/ as thin infrastructure, move logic to tools/
2. Keep db/ as shared utilities, tools call these helpers

### 3. Dolt vs SQLModel Duality

Some tools write to Dolt tables, others to SQLModel tables. This creates confusion.

**Current state**:
- `map_tool` → writes to Dolt (dolt.py)
- `fetch_tool` → writes to SQLModel (migrations) AND Dolt
- `batch_embedding_tool` → writes to SQLModel

**Decision needed**: Standardize on Dolt OR SQLModel for tool output tables.

## Phase 1: Remove Circular Import

### Changes

1. **Delete `register_all_models()` from models.py**
   - Remove lines 15-35
   - Tools already register models when imported

2. **Update database.py**
   - Remove call to `register_all_models()` if present

3. **Verify SQLModel metadata**
   - Models auto-register when imported
   - `SQLModel.metadata.create_all(engine)` will find them

### Tests
```bash
uv run pytest src/kurt/db/tests/ -v
```

## Phase 2: Audit Utilities (Future)

After Phase 1, audit:
- Is `documents.py` used? By which tools?
- Is `tool_tables.py` used? By which tools?
- Can they be consolidated into `dolt.py` or deleted?

## Phase 3: Standardize Storage (Future)

**Decision**: Use Dolt for all tool output tables
- Dolt provides versioning, branching, diffing
- SQLModel migrations only for infrastructure (LLMTrace)

This aligns with the overall simplification - tools/ owns business logic, db/ is infrastructure.

## Tasks

- [ ] Delete `register_all_models()` from db/models.py
- [ ] Verify no callers depend on it
- [ ] Run db tests
- [ ] Audit documents.py usage
- [ ] Audit tool_tables.py usage
- [ ] Document Dolt vs SQLModel decision
