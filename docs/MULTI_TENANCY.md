# Multi-Tenancy in Kurt

Kurt supports multi-tenant deployments with **the same schema** for both local (SQLite) and cloud (PostgreSQL) modes.

## Schema Design

### Single Source of Truth

**All tables use the same schema** whether running in local or cloud mode:

- `documents` - has `tenant_id`
- `entities` - has `tenant_id`
- `entity_relationships` - has `tenant_id`
- `document_entities` - has `tenant_id`

### Default Tenant ID

In **local SQLite mode**, all records use the default tenant ID:

```
00000000-0000-0000-0000-000000000000
```

This allows:
- Local development without workspace configuration
- Seamless migration from local → cloud
- **Same schema everywhere** (no conditional logic)

### Cloud Workspace ID

In **cloud PostgreSQL mode**, each workspace has its own UUID:

```
e.g., a7f8c3b2-1234-5678-9abc-def012345678
```

Workspace isolation is enforced by:
- PostgreSQL Row-Level Security (RLS) policies
- JWT claims containing `workspace_id`
- Automatic filtering in `PostgreSQLClient.get_session()`

## How It Works

### Local Mode (SQLite)

```python
from kurt.db.sqlite import SQLiteClient

client = SQLiteClient()
client.init_database()

# All records automatically get tenant_id = '00000000-0000-0000-0000-000000000000'
session = client.get_session()
doc = Document(title="My Doc", source_type=SourceType.URL)
session.add(doc)
session.commit()

print(doc.tenant_id)  # UUID('00000000-0000-0000-0000-000000000000')
```

### Cloud Mode (PostgreSQL)

```python
from kurt.db.postgresql import PostgreSQLClient

client = PostgreSQLClient(
    database_url="postgresql://user:pass@host:5432/db",
    workspace_id="a7f8c3b2-1234-5678-9abc-def012345678"
)

# Session automatically filters by workspace_id via RLS
session = client.get_session()

# User can only see documents in their workspace
docs = session.exec(select(Document)).all()  # RLS filters automatically
```

## Migration Path

### SQLite → PostgreSQL

When migrating from SQLite to PostgreSQL:

```bash
# 1. Local SQLite database has default tenant_id on all records
cat .kurt/kurt.sqlite

# 2. Migrate to PostgreSQL with new workspace ID
kurt admin migrate migrate-db \
  --target-url "postgresql://..." \
  --workspace-id "a7f8c3b2-1234-5678-9abc-def012345678"

# 3. Migration updates all tenant_id values to workspace ID
# Old: tenant_id = '00000000-0000-0000-0000-000000000000'
# New: tenant_id = 'a7f8c3b2-1234-5678-9abc-def012345678'
```

The migration command:
1. Reads from local SQLite
2. Updates `tenant_id` to workspace ID
3. Writes to PostgreSQL
4. Updates `kurt.config` with new DATABASE_URL

## Row-Level Security (RLS)

PostgreSQL RLS policies ensure workspace isolation:

```sql
-- Enable RLS
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their workspace
CREATE POLICY workspace_isolation ON documents
  FOR ALL
  USING (tenant_id = (auth.jwt() ->> 'workspace_id')::uuid);
```

RLS policies are automatically enforced:
- No application-level filtering needed
- Database guarantees isolation
- Works with direct SQL queries
- Compatible with Supabase Auth

## Benefits

### ✅ Same Schema Everywhere

- SQLite and PostgreSQL use **identical tables**
- No conditional logic based on database type
- Easy to test locally and deploy to cloud
- Migrations generated once, work everywhere

### ✅ Zero Configuration for Local Mode

- Default `tenant_id` means local mode "just works"
- No workspace setup required
- Single-user experience unchanged

### ✅ Secure Multi-Tenancy in Cloud

- PostgreSQL RLS enforces isolation
- Workspace ID in JWT claims
- Database-level security (not app-level)

### ✅ Easy Migration

- One command: SQLite → PostgreSQL
- Automatic tenant_id updates
- No data loss
- Content files stay in Git

## Implementation Details

### Models (kurt-core/src/kurt/db/models.py)

```python
class Document(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Multi-tenancy field
    tenant_id: Optional[UUID] = Field(
        default=UUID('00000000-0000-0000-0000-000000000000'),
        index=True,
        description="Workspace ID for multi-tenant isolation"
    )

    title: Optional[str] = None
    # ... rest of fields
```

### Migration (20251120_0011_add_tenant_id.py)

```python
def upgrade() -> None:
    """Add tenant_id columns to multi-tenant tables."""

    default_tenant_id = '00000000-0000-0000-0000-000000000000'

    with op.batch_alter_table('documents') as batch_op:
        batch_op.add_column(
            sa.Column('tenant_id', UUID, nullable=True, server_default=default_tenant_id)
        )
        batch_op.create_index('ix_documents_tenant_id', ['tenant_id'])
```

### PostgreSQL Client

```python
class PostgreSQLClient(DatabaseClient):
    def get_session(self) -> Session:
        session = Session(self._engine)

        # Set workspace context for RLS
        if self.workspace_id:
            session.exec(text(f"SET app.current_workspace = '{self.workspace_id}'"))

        return session
```

## Testing

### Local Mode Tests

```python
def test_local_mode_default_tenant():
    """Test default tenant_id in local mode."""
    client = SQLiteClient()
    client.init_database()

    session = client.get_session()
    doc = Document(title="Test", source_type=SourceType.URL)
    session.add(doc)
    session.commit()

    assert doc.tenant_id == UUID('00000000-0000-0000-0000-000000000000')
```

### Cloud Mode Tests

```python
@pytest.mark.integration
def test_workspace_isolation(postgres_url):
    """Test that workspaces are isolated."""
    workspace_1 = str(uuid4())
    workspace_2 = str(uuid4())

    client_1 = PostgreSQLClient(database_url=postgres_url, workspace_id=workspace_1)
    client_2 = PostgreSQLClient(database_url=postgres_url, workspace_id=workspace_2)

    # Create document in workspace 1
    session_1 = client_1.get_session()
    doc_1 = Document(tenant_id=workspace_1, title="Workspace 1 Doc")
    session_1.add(doc_1)
    session_1.commit()

    # Query from workspace 2 - should not see workspace 1 docs
    session_2 = client_2.get_session()
    docs = session_2.exec(select(Document)).all()

    assert len(docs) == 0  # RLS prevents access
```

## Schema Generation

The **same schema** is used for both SQLite and PostgreSQL:

```bash
# Generate PostgreSQL DDL from kurt-core models
uv run python scripts/generate_postgres_schema.py

# Output includes tenant_id:
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    tenant_id UUID,  # ← Same as SQLite
    title VARCHAR,
    ...
);

CREATE INDEX ix_documents_tenant_id ON documents(tenant_id);
```

## Supabase Integration

For kurt-cloud (managed SaaS):

1. **Schema comes from kurt-core** - generated via `generate_postgres_schema.py`
2. **RLS policies added in kurt-cloud** - workspace isolation
3. **JWT contains workspace_id** - from Supabase Auth
4. **Automatic filtering** - PostgreSQL enforces RLS

Example RLS setup (kurt-cloud):

```sql
-- Helper function to get workspace from JWT
CREATE FUNCTION auth.workspace_id() RETURNS uuid AS $$
  SELECT (auth.jwt() ->> 'workspace_id')::uuid;
$$ LANGUAGE SQL STABLE;

-- RLS policy using JWT claim
CREATE POLICY workspace_isolation ON documents
  FOR ALL
  USING (tenant_id = auth.workspace_id());
```

## Summary

**One Schema, Two Modes:**

| Feature | Local (SQLite) | Cloud (PostgreSQL) |
|---------|---------------|-------------------|
| tenant_id | `00000000-...` (default) | Workspace UUID |
| Isolation | Not needed (single user) | RLS policies |
| Configuration | None required | `.env` with DATABASE_URL |
| Migration | Auto-applied | `supabase db push` |

**Key Benefits:**
- ✅ Same models everywhere (kurt-core)
- ✅ Same migrations everywhere
- ✅ Easy local → cloud migration
- ✅ Secure multi-tenancy in cloud
- ✅ Zero config for local development
