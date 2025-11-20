# Kurt Cloud Architecture

## Overview

Kurt Cloud is a managed multi-tenant SaaS service that enables teams to share metadata (entities, relationships, classifications) while keeping content files local.

## Key Design Decisions

### 1. Single Source of Truth: kurt-core owns the schema

**Problem**: How to keep database schema synchronized between kurt-cloud (Supabase) and kurt-core (CLI)?

**Solution**:
- **kurt-cloud depends on kurt-core** as a Python package
- Schema is defined once in `kurt-core/src/kurt/db/models.py` using SQLModel
- SQL migrations are **generated from the SQLModel models**
- No schema duplication

```toml
# kurt-cloud/pyproject.toml
[project]
dependencies = ["kurt-core>=0.3.0"]
```

### 2. No Localhost OAuth Callback

**Problem**: Traditional OAuth requires running a local web server for callbacks.

**Solution**: Use **Device Flow** (like GitHub CLI `gh auth login`):

1. CLI requests device code from Supabase
2. User visits activation URL in browser
3. User authenticates with Google/GitHub (handled by Supabase)
4. User enters device code
5. CLI polls Supabase until authorized
6. JWT token saved to `.env`

**Benefits**:
- No localhost web server
- No port conflicts
- No firewall issues
- Better UX for SSH/remote environments

### 3. Admin-Driven Metadata Sync

**Problem**: How to share local metadata with team?

**Solution**: Explicit sync command (no automated background sync):

```bash
kurt cloud sync
```

Admins decide when to share their local metadata with the cloud workspace.

## Repository Structure

```
kurt-core/                          # ← CLI tool + Schema definition
├── src/kurt/
│   ├── db/
│   │   ├── models.py              # ← SINGLE SOURCE OF TRUTH
│   │   ├── sqlite.py
│   │   └── postgresql.py
│   └── commands/
│       ├── admin/
│       │   ├── migrate.py         # migrate-db (SQLite → PostgreSQL)
│       │   └── workspace.py       # workspace management
│       └── cloud/                 # Cloud commands
│           ├── login.py           # kurt cloud login (device flow)
│           └── sync.py            # kurt cloud sync
├── scripts/
│   └── generate_postgres_schema.py # Generate SQL from models
└── pyproject.toml

kurt-cloud/                         # ← Managed service
├── pyproject.toml                 # depends on kurt-core
├── supabase/
│   ├── migrations/
│   │   ├── 20240101_schema.sql    # Generated from kurt-core
│   │   └── 20240102_rls.sql       # Row-Level Security
│   └── config.toml
├── web/                           # Next.js dashboard
│   └── app/
│       ├── login/
│       └── activate/              # Device flow activation page
└── scripts/
    └── sync_schema.sh             # Generate migration from kurt-core
```

## Data Flow

### Schema Changes

```
┌────────────────────────────────────────────────────────┐
│ 1. Update models in kurt-core                          │
│    src/kurt/db/models.py                               │
└──────────────────┬─────────────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────────────┐
│ 2. Generate SQL migration                              │
│    uv run python scripts/generate_postgres_schema.py   │
│    > supabase/migrations/XXX.sql                       │
└──────────────────┬─────────────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────────────┐
│ 3. Apply to Supabase                                   │
│    cd kurt-cloud && supabase db push                   │
└──────────────────┬─────────────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────────────┐
│ 4. Release new kurt-core version                       │
│    git tag v0.3.1 && git push --tags                   │
└──────────────────┬─────────────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────────────┐
│ 5. Update kurt-cloud dependency                        │
│    pyproject.toml: kurt-core>=0.3.1                    │
└────────────────────────────────────────────────────────┘
```

### Authentication Flow

```
┌─────────────┐                    ┌─────────────┐
│   User      │                    │   CLI       │
└──────┬──────┘                    └──────┬──────┘
       │                                  │
       │  kurt cloud login                │
       │─────────────────────────────────►│
       │                                  │
       │                                  │ Request device code
       │                                  ├──────────────┐
       │                                  │              │
       │  Visit: kurt.cloud/activate      │◄─────────────┘
       │  Code: WXYZ-1234                 │
       │◄─────────────────────────────────│
       │                                  │
┌──────▼──────┐                           │
│   Browser   │                           │
└──────┬──────┘                           │
       │                                  │
       │  Login with Google/GitHub        │
       ├─────────────────────────┐        │
       │                         │        │
       │  Enter device code      │        │
       │─────────────────────────┘        │
       │                                  │
       │  Authorized!                     │
       │─────────────────────────────────►│
       │                                  │
       │                                  │ Poll for token
       │                                  ├──────────────┐
       │                                  │              │
       │                                  │ JWT + refresh│
       │                                  │◄─────────────┘
       │                                  │
       │                                  │ Save to .env
       │  ✓ Authenticated                 ├──────────────┐
       │◄─────────────────────────────────│              │
       │                                  │◄─────────────┘
       │                                  │
```

### Metadata Sync Flow

```
┌──────────────┐                  ┌──────────────┐                  ┌──────────────┐
│ Local SQLite │                  │     CLI      │                  │  PostgreSQL  │
└──────┬───────┘                  └──────┬───────┘                  └──────┬───────┘
       │                                 │                                 │
       │  kurt cloud sync                │                                 │
       │────────────────────────────────►│                                 │
       │                                 │                                 │
       │  Read entities                  │                                 │
       │◄────────────────────────────────┤                                 │
       │                                 │                                 │
       │  entities[]                     │                                 │
       ├────────────────────────────────►│                                 │
       │                                 │                                 │
       │                                 │  Add tenant_id                  │
       │                                 │  Upload entities                │
       │                                 ├────────────────────────────────►│
       │                                 │                                 │
       │                                 │  Merge (upsert)                 │
       │                                 │◄────────────────────────────────┤
       │                                 │                                 │
       │  Read relationships             │                                 │
       │◄────────────────────────────────┤                                 │
       │                                 │                                 │
       │  relationships[]                │                                 │
       ├────────────────────────────────►│                                 │
       │                                 │                                 │
       │                                 │  Upload relationships           │
       │                                 ├────────────────────────────────►│
       │                                 │                                 │
       │                                 │  ✓ Synced                       │
       │  ✓ Complete                     │◄────────────────────────────────┤
       │◄────────────────────────────────┤                                 │
       │                                 │                                 │
```

## Security: Row-Level Security (RLS)

All tables with `tenant_id` use PostgreSQL Row-Level Security:

```sql
-- Enable RLS
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their workspace data
CREATE POLICY workspace_isolation ON documents
  FOR ALL
  USING (tenant_id = (auth.jwt() ->> 'workspace_id')::uuid);
```

The JWT token from Supabase Auth includes `workspace_id` claim, which RLS policies use for automatic data isolation.

## Configuration

### kurt-core (.env)

```bash
# Supabase connection
SUPABASE_URL="https://xxx.supabase.co"
SUPABASE_ACCESS_TOKEN="eyJ..."     # From device flow
SUPABASE_REFRESH_TOKEN="..."

# Database (automatically configured after login)
DATABASE_URL="postgresql://postgres:pass@db.xxx.supabase.co:5432/postgres"
WORKSPACE_ID="workspace-uuid"

# API keys
OPENAI_API_KEY="sk-..."
```

### kurt-cloud (.env)

```bash
# Supabase admin credentials
SUPABASE_URL="https://xxx.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="eyJ..."  # For migrations

# Next.js public keys
NEXT_PUBLIC_SUPABASE_URL="https://xxx.supabase.co"
NEXT_PUBLIC_SUPABASE_ANON_KEY="eyJ..."
```

## Commands

### Authentication

```bash
# Login with device flow
kurt cloud login

# Logout
kurt cloud logout

# Check current user
kurt cloud status
```

### Workspace Management

```bash
# View current workspace
kurt admin workspace current

# List all workspaces (user has access to)
kurt admin workspace list

# Switch workspace
kurt admin workspace set <workspace-id>
```

### Metadata Sync

```bash
# Sync local metadata to cloud
kurt cloud sync

# Dry run (preview changes)
kurt cloud sync --dry-run

# Sync specific types
kurt cloud sync --entities --relationships
```

## Implementation Phases

### Phase 1: Schema Generation ✓

- [x] Create `scripts/generate_postgres_schema.py`
- [x] Test schema generation from SQLModel models
- [x] Document in KURT_CLOUD.md

### Phase 2: kurt-cloud Repository Setup

- [ ] Create kurt-cloud repository
- [ ] Add kurt-core as dependency
- [ ] Initialize Supabase project
- [ ] Generate initial migration from kurt-core models
- [ ] Set up RLS policies

### Phase 3: Device Flow Authentication

- [ ] Implement `kurt cloud login` command
- [ ] Build activation page in kurt-cloud web
- [ ] Token storage in .env
- [ ] Token refresh logic

### Phase 4: Metadata Sync

- [ ] Implement `kurt cloud sync` command
- [ ] Entity sync
- [ ] Relationship sync
- [ ] Classification sync
- [ ] Dry-run mode

### Phase 5: Web Dashboard

- [ ] Next.js app setup
- [ ] Workspace management UI
- [ ] Entity browser
- [ ] Relationship visualizer
- [ ] Usage analytics

## Benefits

### For Solo Users
- Start local with SQLite
- Upgrade to cloud when ready
- Access metadata from anywhere
- No infrastructure management

### For Teams
- Share entity knowledge base
- Collaborative classification
- Centralized relationship graph
- Version control for content files (Git)
- Database isolation per workspace

### For Kurt Maintainers
- Single schema definition (kurt-core)
- No schema drift between CLI and cloud
- Automated migration generation
- Managed PostgreSQL (Supabase)
- Built-in auth (no custom OAuth)

## Comparison: SQLite vs PostgreSQL

| Feature | SQLite (Local) | PostgreSQL (Cloud) |
|---------|----------------|-------------------|
| Setup | Automatic | `kurt cloud login` |
| Storage | `.kurt/kurt.sqlite` | Supabase PostgreSQL |
| Access | Single machine | Any machine (with auth) |
| Collaboration | Git only (content) | Real-time (metadata) |
| Search | Full-text search | pgvector + full-text |
| Workspace | N/A | Multi-tenant isolation |
| Cost | Free | Supabase pricing |

## Next Steps

1. Set up kurt-cloud repository
2. Initialize Supabase project
3. Generate initial migration
4. Implement device flow auth
5. Build metadata sync
6. Deploy web dashboard

See [KURT_CLOUD.md](../KURT_CLOUD.md) for detailed implementation guide.
