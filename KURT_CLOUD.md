# Kurt Cloud Architecture

This document describes the architecture for `kurt-cloud`, the managed multi-tenant SaaS service for Kurt.

## Quick Start

### For kurt-cloud Developers

Set up the kurt-cloud repository with one command:

```bash
# From kurt-core directory
./scripts/setup_kurt_cloud.sh ../kurt-cloud
```

This will:
- Create directory structure
- Add kurt-core as dependency
- Initialize Supabase
- Generate initial schema migration
- Create RLS policies

Then:

```bash
cd ../kurt-cloud
supabase login
supabase link --project-ref YOUR-PROJECT-ID
supabase db push
```

### For kurt-core Users

Authenticate and sync metadata:

```bash
# Login with device flow
kurt cloud login

# Sync local metadata to cloud
kurt cloud sync
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        kurt-cloud                            │
│  (Managed Service - Supabase + Web Dashboard)                │
│                                                              │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │  Supabase         │      │  Next.js Web     │            │
│  │  - PostgreSQL     │◄────►│  - Dashboard     │            │
│  │  - Auth           │      │  - Workspace UI  │            │
│  │  - RLS            │      │  - Device Flow   │            │
│  └──────────────────┘      └──────────────────┘            │
│         ▲                                                    │
└─────────┼────────────────────────────────────────────────────┘
          │
          │ PostgreSQL connection + JWT auth
          │
┌─────────▼────────────────────────────────────────────────────┐
│                        kurt-core                             │
│  (CLI Tool - Installed by Users)                             │
│                                                              │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │  SQLModel Models  │      │  Cloud Commands  │            │
│  │  (Source of Truth)│◄────►│  - login         │            │
│  │  - Document       │      │  - sync          │            │
│  │  - Entity         │      │  - workspace     │            │
│  └──────────────────┘      └──────────────────┘            │
│                                                              │
│  Local Storage: Git + SQLite (optional)                      │
└──────────────────────────────────────────────────────────────┘
```

## Key Principles

### 1. Single Source of Truth: kurt-core Models

**kurt-core defines the data models** (`src/kurt/db/models.py`) using SQLModel.

**kurt-cloud generates migrations** from these models:

```bash
# In kurt-cloud repo
cd kurt-cloud
python -c "import sys; sys.path.insert(0, '../kurt-core/src'); exec(open('../kurt-core/scripts/generate_postgres_schema.py').read())" > supabase/migrations/20240101_init.sql
```

Or better yet, kurt-cloud installs kurt-core as a dependency:

```toml
# kurt-cloud/pyproject.toml
[project]
dependencies = ["kurt-core>=0.3.0"]
```

Then:

```bash
# In kurt-cloud repo
uv run python ../kurt-core/scripts/generate_postgres_schema.py > supabase/migrations/$(date +%Y%m%d%H%M%S)_schema.sql
```

### 2. Authentication: No Localhost Callback

**Problem**: Local OAuth callback requires running a web server on localhost.

**Solution**: Use **Device Flow** (like GitHub CLI):

```bash
$ kurt cloud login

→ Visit: https://kurt.cloud/activate
→ Enter code: WXYZ-1234

Waiting for authorization...
✓ Authenticated as user@example.com
✓ Workspace: acme-corp
```

**How it works**:

1. CLI generates device code via Supabase API
2. User visits activation URL in browser
3. User logs in with Google/GitHub OAuth (handled by Supabase)
4. User enters device code
5. CLI polls Supabase until authorization complete
6. CLI receives JWT token and stores in `.env`

**Alternative**: Magic Link Flow

```bash
$ kurt cloud login user@example.com

→ Check your email for authentication link
→ Waiting for confirmation...

✓ Authenticated as user@example.com
```

### 3. Background Sync: Admin-Driven from CLI

**Not automated** - admins explicitly sync their local metadata:

```bash
$ kurt cloud sync

Syncing local metadata to workspace 'acme-corp'...
→ Uploading 45 entities
→ Uploading 120 relationships
→ Uploading 89 classifications
✓ Sync complete (2.3s)
```

**Implementation**:

```python
# src/kurt/commands/cloud/sync.py

@cloud.command("sync")
def sync_metadata():
    """Sync local SQLite metadata to cloud PostgreSQL workspace."""

    # 1. Load both databases
    local_client = SQLiteClient()
    cloud_client = PostgreSQLClient(
        database_url=os.getenv("DATABASE_URL"),
        workspace_id=os.getenv("WORKSPACE_ID")
    )

    # 2. Sync entities
    with local_client.get_session() as local_session:
        with cloud_client.get_session() as cloud_session:
            entities = local_session.exec(select(Entity)).all()

            for entity in entities:
                # Add tenant_id for multi-tenancy
                entity.tenant_id = cloud_client.workspace_id
                cloud_session.merge(entity)  # Upsert

            cloud_session.commit()

    click.echo("✓ Sync complete")
```

## Repository Structure

### kurt-cloud Repository

```
kurt-cloud/
├── pyproject.toml                # Depends on kurt-core
├── README.md
├── supabase/
│   ├── config.toml
│   ├── migrations/
│   │   ├── 20240101_init_schema.sql       # Generated from kurt-core
│   │   ├── 20240102_add_rls.sql           # RLS policies
│   │   └── 20240103_add_workspaces.sql    # Workspace management
│   └── functions/                         # Edge Functions (minimal)
│       └── workspace-invite/              # Only if needed
├── web/                                   # Next.js dashboard
│   ├── app/
│   │   ├── login/page.tsx                 # Login page
│   │   ├── activate/page.tsx              # Device flow activation
│   │   ├── workspace/
│   │   │   ├── [id]/page.tsx              # Workspace details
│   │   │   └── settings/page.tsx          # Workspace settings
│   │   └── layout.tsx
│   ├── components/
│   │   ├── workspace-selector.tsx
│   │   └── entity-browser.tsx
│   └── package.json
├── scripts/
│   └── sync_schema.sh                     # Copy schema from kurt-core
└── .env.example
    # SUPABASE_URL=https://xxx.supabase.co
    # SUPABASE_ANON_KEY=eyJ...
```

### kurt-core Repository (Updated)

```
kurt-core/
├── src/kurt/
│   ├── db/
│   │   ├── models.py                      # ← SINGLE SOURCE OF TRUTH
│   │   ├── sqlite.py
│   │   └── postgresql.py
│   └── commands/
│       ├── admin/
│       │   └── migrate.py                 # migrate-db command
│       └── cloud/                         # ← New cloud commands
│           ├── __init__.py
│           ├── login.py                   # kurt cloud login
│           ├── sync.py                    # kurt cloud sync
│           └── workspace.py               # kurt cloud workspace
├── scripts/
│   └── generate_postgres_schema.py        # Generate SQL from models
└── pyproject.toml
```

## Implementation Phases

### Phase 1: Schema Generation (✓ Done)

- [x] Created `scripts/generate_postgres_schema.py`
- [ ] Test schema generation
- [ ] Document usage in KURT_CLOUD.md

### Phase 2: kurt-cloud Repository Setup

```bash
# Create kurt-cloud repo (sibling to kurt-core)
cd ~/projects
mkdir kurt-cloud
cd kurt-cloud

# Initialize with kurt-core dependency
cat > pyproject.toml <<EOF
[project]
name = "kurt-cloud"
version = "0.1.0"
dependencies = [
    "kurt-core>=0.3.0",
    "supabase>=2.0.0",
]
EOF

# Initialize Supabase
supabase init

# Generate initial migration from kurt-core
cd ../kurt-core
uv run python scripts/generate_postgres_schema.py > ../kurt-cloud/supabase/migrations/20240101_init_schema.sql
```

### Phase 3: Device Flow Authentication

Implement in `kurt-core/src/kurt/commands/cloud/login.py`:

```python
@cloud.command("login")
def login():
    """Authenticate with Kurt Cloud using device flow."""

    # 1. Request device code from Supabase
    response = requests.post(
        f"{SUPABASE_URL}/auth/v1/device/code",
        json={"scope": "openid profile email"}
    )

    device_code = response.json()["device_code"]
    user_code = response.json()["user_code"]
    verification_uri = response.json()["verification_uri"]

    # 2. Show user instructions
    click.echo(f"\n→ Visit: {verification_uri}")
    click.echo(f"→ Enter code: {user_code}\n")

    # 3. Poll for authorization
    click.echo("Waiting for authorization...")

    while True:
        time.sleep(5)

        token_response = requests.post(
            f"{SUPABASE_URL}/auth/v1/device/token",
            json={"device_code": device_code}
        )

        if token_response.status_code == 200:
            # Success!
            tokens = token_response.json()

            # 4. Save to .env
            update_env_file({
                "SUPABASE_ACCESS_TOKEN": tokens["access_token"],
                "SUPABASE_REFRESH_TOKEN": tokens["refresh_token"],
                "WORKSPACE_ID": tokens["user"]["workspace_id"],
            })

            click.echo(f"✓ Authenticated as {tokens['user']['email']}")
            break
```

### Phase 4: Metadata Sync

Implement in `kurt-core/src/kurt/commands/cloud/sync.py`:

```python
@cloud.command("sync")
@click.option("--dry-run", is_flag=True)
def sync_metadata(dry_run: bool):
    """Sync local metadata to cloud workspace."""

    # Verify authenticated
    if not os.getenv("SUPABASE_ACCESS_TOKEN"):
        click.echo("Error: Not authenticated. Run 'kurt cloud login' first.")
        return

    # Load clients
    local_client = SQLiteClient()
    cloud_client = get_database_client()  # Uses DATABASE_URL from .env

    # Sync entities, relationships, classifications
    sync_entities(local_client, cloud_client, dry_run)
    sync_relationships(local_client, cloud_client, dry_run)
    sync_classifications(local_client, cloud_client, dry_run)
```

### Phase 5: Web Dashboard

Next.js app for workspace management and metadata browsing.

## Environment Variables

### kurt-core (.env)

```bash
# Authentication
SUPABASE_URL="https://xxx.supabase.co"
SUPABASE_ACCESS_TOKEN="eyJ..."
SUPABASE_REFRESH_TOKEN="..."

# Database
DATABASE_URL="postgresql://postgres:pass@db.xxx.supabase.co:5432/postgres"
WORKSPACE_ID="workspace-uuid"

# API Keys (existing)
OPENAI_API_KEY="sk-..."
FIRECRAWL_API_KEY="fc-..."
```

### kurt-cloud (.env)

```bash
# Supabase credentials (for admin/migrations)
SUPABASE_URL="https://xxx.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="eyJ..."  # Admin key for migrations
SUPABASE_ANON_KEY="eyJ..."

# Next.js
NEXT_PUBLIC_SUPABASE_URL="https://xxx.supabase.co"
NEXT_PUBLIC_SUPABASE_ANON_KEY="eyJ..."
```

## Security: Row-Level Security (RLS)

Supabase migrations will include RLS policies:

```sql
-- supabase/migrations/20240102_add_rls.sql

-- Enable RLS on all tables
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_entities ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see data in their workspace
CREATE POLICY workspace_isolation ON documents
  FOR ALL
  USING (tenant_id = auth.jwt() ->> 'workspace_id');

CREATE POLICY workspace_isolation ON entities
  FOR ALL
  USING (tenant_id = auth.jwt() ->> 'workspace_id');
```

The JWT token from Supabase Auth includes `workspace_id`, which RLS uses for isolation.

## Workflow Example

### Initial Setup (Admin)

```bash
# 1. Install kurt-core
uv pip install kurt-core

# 2. Authenticate with Kurt Cloud
kurt cloud login
→ Visit: https://kurt.cloud/activate
→ Enter code: WXYZ-1234
✓ Authenticated as admin@acme.com

# 3. Sync local metadata
kurt cloud sync
✓ Synced 150 entities to workspace 'acme-corp'
```

### Team Member Workflow

```bash
# 1. Install kurt-core
uv pip install kurt-core

# 2. Authenticate (same flow)
kurt cloud login
✓ Authenticated as dev@acme.com

# 3. Query shared metadata
kurt content list-entities topic
# Shows entities from workspace 'acme-corp'
```

## Next Steps

1. **Test schema generation script** - Run it and verify SQL output
2. **Create kurt-cloud repository** - Initialize with Supabase
3. **Implement device flow** - Add login command to kurt-core
4. **Implement sync command** - Add metadata sync to kurt-core
5. **Build web dashboard** - Next.js app for workspace management

## Questions Answered

### Why no localhost callback?

Device flow eliminates need for local web server. User authenticates in browser, CLI polls for completion. Better UX, no port conflicts.

### How to maintain single source of truth?

kurt-core owns the SQLModel schema. kurt-cloud generates SQL migrations from it using `scripts/generate_postgres_schema.py`. Schema changes always start in kurt-core.

### Background sync?

Admin-driven via `kurt cloud sync`. No automated sync - users explicitly choose when to share metadata with team.
