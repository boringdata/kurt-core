# Kurt Database Modes

Kurt supports three database modes via the `DATABASE_URL` configuration in `kurt.config`.

## Mode 1: SQLite (Local Development)

**Configuration:**
```
DATABASE_URL="sqlite:///.kurt/kurt.sqlite"
```

Or using legacy config:
```
PATH_DB=".kurt/kurt.sqlite"
```

**Characteristics:**
- File-based, no server required
- Single-user, local development
- Full SQL support including JOINs and VIEWs
- Migrations run via Alembic
- Document queries use SQLAlchemy `outerjoin()`

**Use Cases:**
- Local development
- Testing
- Single-user projects
- Offline work

**Tested:**
- ✅ `kurt content list` - Works with SQLAlchemy JOIN
- ✅ `kurt content get` - Works
- ✅ Migrations skip PostgreSQL-only features (VIEWs, RLS)

---

## Mode 2: PostgreSQL (Direct Connection)

**Configuration:**
```
DATABASE_URL="postgresql://user:password@host:5432/database"
```

**Characteristics:**
- Direct PostgreSQL connection via psycopg2
- Full SQL support
- Supports database VIEWs and foreign keys
- Can use RLS policies (if configured)
- Multi-user capable

**Use Cases:**
- Self-hosted PostgreSQL
- Local Postgres.app
- Development/staging servers
- Direct database access needed

**Tested:**
- ✅ Migrations create VIEWs and foreign keys
- ✅ Document queries can use `document_lifecycle` VIEW
- ✅ Full SQLAlchemy support

---

## Mode 3: Kurt Cloud (PostgREST via Supabase)

**Configuration:**
```
DATABASE_URL="kurt"
```

**Characteristics:**
- Uses PostgREST API (not direct SQL)
- Automatic multi-tenancy via RLS
- Requires authentication: `kurt cloud login`
- JOINs must use pre-defined database VIEWs
- PostgREST quirks:
  - Returns string `'null'` for NULL values (handled automatically)
  - JSON fields returned as strings (parsed automatically)
  - No arbitrary SQL - only REST API calls

**Authentication:**
```bash
kurt cloud login
```

**Use Cases:**
- Production deployments
- Multi-tenant SaaS
- Automatic RLS isolation
- No database server management

**Database VIEWs:**
- `document_lifecycle`: Joins `map_documents` LEFT OUTER JOIN `fetch_documents`
  - Used automatically when querying documents
  - Detected in `SupabaseSession._exec_join_query()`
  - RLS policies apply automatically

**Tested:**
- ✅ `kurt content list` - Uses `document_lifecycle` VIEW
- ✅ `kurt content get` - Works with VIEW-based JOINs
- ✅ PostgREST null handling
- ✅ JSON parsing for metadata fields
- ✅ RLS enforcement via JWT

**CLI Behavior:**
- Migration warnings are suppressed in cloud mode (migrations managed via kurt-cloud)
- `kurt admin migrate` commands are not available in cloud mode

---

## Implementation Details

### JOIN Strategy

**SQLite & PostgreSQL (Direct):**
- Use SQLAlchemy `select(MapDocument, FetchDocument).outerjoin()`
- JOIN executed by database engine
- Returns tuples of `(MapDocument, FetchDocument)`

**Kurt Cloud (PostgREST):**
- Detect JOIN in `SupabaseSession._exec_join_query()`
- If `map_documents + fetch_documents`: Query `document_lifecycle` VIEW
- Otherwise: Fetch tables separately, join in Python
- Parse PostgREST quirks (string 'null', JSON strings)
- Return `SupabaseJoinResult` with model tuples

### Migration Strategy

**Kurt-Core Migrations:**
- Located in `src/kurt/db/migrations/versions/`
- Run via: `alembic upgrade head`
- Skip PostgreSQL features on SQLite (VIEWs, RLS, foreign keys)
- Example: `20260115_add_foreign_keys_for_documents.py`

**Kurt-Cloud Migrations:**
- Located in `src/kurt_cloud/db/migrations/versions/`
- Manage `cloud` schema tables (admin, workspaces, etc.)
- Kurt-core migrations run against Supabase via script:
  ```bash
  cd kurt-cloud
  python scripts/run_core_migrations.py
  ```

### Adding New VIEWs

When adding JOINs for other workflows:

1. **Create migration in kurt-core:**
   ```python
   def upgrade() -> None:
       if context.get_context().dialect.name != "postgresql":
           return

       op.execute("""
           CREATE VIEW my_workflow_lifecycle AS
           SELECT t1.*, t2.col as prefixed_col
           FROM table1 t1
           LEFT OUTER JOIN table2 t2
           ON t1.id = t2.id
       """)
   ```

2. **Update `SupabaseSession._exec_join_query()`:**
   ```python
   if (left_table == "table1" and right_table == "table2"):
       rows = self._client.select("my_workflow_lifecycle", limit=limit)
       # Parse and split view results...
   ```

3. **Run migration:**
   ```bash
   # SQLite/PostgreSQL
   alembic upgrade head

   # Kurt Cloud
   cd kurt-cloud && python scripts/run_core_migrations.py
   ```

---

## Testing All Modes

### SQLite Mode
```bash
cd project-with-sqlite
cat kurt.config  # DATABASE_URL="sqlite:///.kurt/kurt.sqlite"
kurt content list --limit 5
```

### PostgreSQL Mode
```bash
cd project-with-postgres
cat kurt.config  # DATABASE_URL="postgresql://..."
kurt content list --limit 5
```

### Kurt Cloud Mode
```bash
cd project-with-cloud
cat kurt.config  # DATABASE_URL="kurt"
kurt cloud login
kurt content list --limit 5
```

---

## Troubleshooting

### "Could not find table ... JOIN ..." (PostgREST)
- **Cause:** PostgREST doesn't support arbitrary JOINs
- **Fix:** Create a database VIEW and update `_exec_join_query()`

### "Input should be a valid dictionary" (Pydantic)
- **Cause:** PostgREST returns JSON as strings
- **Fix:** Parse JSON fields in `_exec_join_query()` (already handled for `document_lifecycle`)

### "Foreign key constraint" error during migration
- **Cause:** Orphaned data in child table
- **Fix:** Clean up orphans before adding FK (see migration example)

### "Column specified more than once"
- **Cause:** Both tables have columns with same name
- **Fix:** Alias columns in VIEW (`f.col as fetch_col`)
