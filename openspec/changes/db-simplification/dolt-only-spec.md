# Dolt-Only Database Migration

## Goal

Remove SQLite, use Dolt as the single database backend via MySQL protocol.

## Architecture

```
SQLModel models → SQLAlchemy → MySQL driver → Dolt SQL server
                                                    ↓
                                              Git-like versioning
                                              (branches, diffs, history)
```

## Connection String

```
# Local development
DATABASE_URL="mysql://root@localhost:3306/kurt"

# Or with dolt sql-server running on custom port
DATABASE_URL="mysql://root@localhost:3309/kurt"
```

## Changes Required

### 1. Add DoltClient (SQLModel-based)

Create `src/kurt/db/dolt_client.py`:
- Extends `DatabaseClient` interface
- Uses `mysql+pymysql://` connection string
- Runs `dolt sql-server` if not running
- Creates tables via SQLModel metadata

### 2. Update `get_database_client()`

```python
# In base.py
if database_url and database_url.startswith("mysql"):
    from kurt.db.dolt_client import DoltClient
    return DoltClient(database_url)
```

### 3. Auto-start Dolt Server

When using Dolt:
1. Check if Dolt server is running
2. If not, start `dolt sql-server` in background
3. Wait for server to be ready
4. Connect via MySQL protocol

### 4. Schema Migration

SQLModel tables need to be created in Dolt:
- `map_documents`
- `fetch_documents`
- `research_documents`
- `monitoring_signals`
- etc.

Use `SQLModel.metadata.create_all(engine)` - same as SQLite/PostgreSQL.

### 5. Update Test Fixtures

Replace `tmp_sqlmodel_project` to use Dolt:
1. Init Dolt repo: `dolt init`
2. Start SQL server: `dolt sql-server`
3. Connect via MySQL
4. Create tables

### 6. Remove SQLite Client

After migration:
- Delete `src/kurt/db/sqlite.py`
- Remove SQLite-specific code from fixtures
- Update documentation

## Benefits

1. **Single database**: No more SQLite vs Dolt confusion
2. **Versioning**: All data is versioned with git-like semantics
3. **Branching**: Can branch data for experiments
4. **Diffs**: Track what changed between runs
5. **History**: See historical state of any document

## Implementation Steps

1. [ ] Create `DoltClient` class in `db/dolt_client.py`
2. [ ] Add MySQL routing in `base.py`
3. [ ] Update `init_database()` to start Dolt server
4. [ ] Update test fixtures to use Dolt
5. [ ] Test all persistence operations
6. [ ] Remove SQLite client
7. [ ] Update CLAUDE.md documentation

## Dependencies

Need `pymysql` driver:
```toml
# pyproject.toml
dependencies = [
    "pymysql>=1.1.0",
]
```

## Verification

```bash
# Start Dolt server
dolt sql-server --port 3309 &

# Test connection
uv run python -c "
from kurt.db import init_database, managed_session
from kurt.tools.map.models import MapDocument
init_database()
with managed_session() as s:
    s.add(MapDocument(document_id='test', source_url='https://example.com'))
print('Success!')
"

# Check data in Dolt
dolt sql -q "SELECT * FROM map_documents"
```
