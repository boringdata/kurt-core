# PostgreSQL & Multi-Tenant Support

Kurt supports both local SQLite and shared PostgreSQL databases. This guide shows how to migrate from SQLite to PostgreSQL and work with multi-tenant (workspace) setups.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Migration](#migration)
- [Workspace Management](#workspace-management)
- [Supabase Setup](#supabase-setup)
- [Team Collaboration](#team-collaboration)

---

## Overview

### Database Modes

| Feature | SQLite (Local) | PostgreSQL (Shared) |
|---------|----------------|---------------------|
| **Storage** | Local `.kurt/kurt.sqlite` | Remote PostgreSQL server |
| **Multi-user** | ❌ Single user | ✅ Multiple users |
| **Workspaces** | ❌ N/A | ✅ Multi-tenant support |
| **Content** | Local `sources/` files | Local `sources/` files |
| **Offline** | ✅ Full functionality | ❌ Needs internet |
| **Setup** | `kurt init` | Manual + migration |
| **Cost** | Free | Depends on provider |

### Architecture

**Key Principle:** PostgreSQL stores **metadata only** (entities, relationships), not content files.

```
┌─────────────────────────────────────────────────┐
│  LOCAL (Git Repo)                               │
│  ├── sources/               ← Content files     │
│  ├── projects/              ← Work products     │
│  └── kurt.config           ← Points to DB       │
└─────────────────────────────────────────────────┘
                    ↕ sync metadata only
┌─────────────────────────────────────────────────┐
│  POSTGRESQL (e.g., Supabase)                    │
│  ├── documents              ← Metadata          │
│  ├── entities               ← Knowledge graph   │
│  └── entity_relationships   ← Connections       │
└─────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

```bash
# Install PostgreSQL dependencies
uv sync  # or: pip install kurt-core
```

### Option 1: Start with PostgreSQL

```bash
# Initialize with PostgreSQL URL
cd my-project
echo 'DATABASE_URL="postgresql://user:pass@host:5432/db"' > .env

# Initialize Kurt
kurt init

# Configuration will use PostgreSQL
kurt status
```

### Option 2: Migrate from SQLite

```bash
# Already using SQLite locally
ls .kurt/kurt.sqlite  # ✓ exists

# Migrate to PostgreSQL
kurt admin migrate migrate-db \
  --target-url "postgresql://user:pass@db.supabase.co:5432/postgres" \
  --workspace-id "my-workspace-id"

# Verify migration
kurt status
kurt content list
```

---

## Configuration

### Environment Variables (.env)

**IMPORTANT:** Store database credentials in `.env` (NOT in `kurt.config`)!

Create a `.env` file in your project root:

```bash
# .env (DO NOT COMMIT TO GIT)

# PostgreSQL connection string
DATABASE_URL="postgresql://user:password@host:5432/database"

# Optional: Workspace/tenant ID for multi-tenant setups
WORKSPACE_ID="workspace-uuid-here"

# Your API keys
OPENAI_API_KEY="sk-..."
FIRECRAWL_API_KEY="fc-..."
```

Add `.env` to `.gitignore`:

```bash
echo ".env" >> .gitignore
```

**Why `.env`?**
- ✅ Keeps secrets out of git
- ✅ Each developer has their own credentials
- ✅ Easy to rotate passwords
- ✅ Works with deployment platforms (Heroku, Vercel, etc.)

### kurt.config

After migration, your `kurt.config` will look like:

```bash
# Kurt Project Configuration
# This file IS committed to git (no secrets!)

PATH_DB=".kurt/kurt.sqlite"  # Ignored when DATABASE_URL is set in .env
PATH_SOURCES="sources"
PATH_PROJECTS="projects"
PATH_RULES="rules"
INDEXING_LLM_MODEL="openai/gpt-4o-mini"
EMBEDDING_MODEL="openai/text-embedding-3-small"
INGESTION_FETCH_ENGINE="trafilatura"
MAX_CONCURRENT_INDEXING=50

# Telemetry Configuration
TELEMETRY_ENABLED=True

# Note: DATABASE_URL and WORKSPACE_ID should be in .env, not here!
```

**Priority:**
1. If `DATABASE_URL` is in `.env` → Uses PostgreSQL
2. If `DATABASE_URL` is in `kurt.config` → Uses PostgreSQL (not recommended)
3. Otherwise → Falls back to SQLite

---

## Migration

### Migrate SQLite to PostgreSQL

```bash
kurt admin migrate migrate-db \
  --target-url "postgresql://user:pass@host:5432/db" \
  --workspace-id "workspace-uuid" \
  --auto-confirm  # Skip prompts
```

**What gets migrated:**
- ✅ Documents (metadata: title, URL, hash, embeddings)
- ✅ Entities (topics, technologies)
- ✅ Entity relationships
- ✅ Document-entity connections
- ✅ Topic clusters
- ✅ Document links
- ❌ Content files (stay in `sources/`)

**What happens:**
1. Creates PostgreSQL schema (tables)
2. Copies all metadata from SQLite
3. Adds `tenant_id` (workspace ID) to all records
4. Updates `kurt.config` to point to PostgreSQL
5. Preserves UUIDs and timestamps

### Verify Migration

```bash
# Check connection
kurt status

# List documents
kurt content list

# Verify entities
kurt content list-entities topic
```

### Backup

```bash
# Before migration, backup SQLite
cp .kurt/kurt.sqlite .kurt/kurt.sqlite.backup

# After migration, keep both
ls .kurt/
# → kurt.sqlite.backup  (original)
# → (no kurt.sqlite, now using PostgreSQL)
```

---

## Workspace Management

### View Current Workspace

```bash
kurt admin workspace current
```

Output:
```
Current Workspace Configuration

Database Type      PostgreSQL
Connection         postgresql://user:***@host:5432/db
Workspace ID       550e8400-e29b-41d4-a716-446655440000

✓ Connected to database (postgresql mode)
```

### Switch Workspace

```bash
# Set active workspace
kurt admin workspace set <workspace-id>

# Remove workspace filter (access all workspaces)
kurt admin workspace unset
```

### List Workspaces

```bash
kurt admin workspace list
```

Output:
```
Available Workspaces (showing 3)

ID                                    Name             Created
550e8400-e29b-41d4-a716-446655440000  Acme Corp        2025-01-15
6ba7b810-9dad-11d1-80b4-00c04fd430c8  Beta Team        2025-01-16
6ba7b811-9dad-11d1-80b4-00c04fd430c8  Marketing        2025-01-17

To switch workspace: kurt admin workspace set <workspace-id>
```

### Create Workspace

```bash
# Create new workspace
kurt admin workspace create "My Team Workspace"

# Create and set as active
kurt admin workspace create "Acme Corp" --set-active
```

---

## Supabase Setup

### 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Create new project
3. Note your connection details:
   - Host: `db.xxx.supabase.co`
   - Database: `postgres`
   - Port: `5432`
   - User: `postgres`
   - Password: (from project settings)

### 2. Enable pgvector

```sql
-- In Supabase SQL Editor
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. Create Multi-Tenant Schema

```sql
-- Workspaces/tenants table
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    plan_type TEXT DEFAULT 'free',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add tenant_id to all Kurt tables
ALTER TABLE documents ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id);
ALTER TABLE entities ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id);
-- ... repeat for other tables

-- Enable Row-Level Security (RLS)
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only see their workspace's documents
CREATE POLICY "tenant_isolation" ON documents
FOR ALL
USING (tenant_id = current_setting('app.current_workspace')::uuid);
```

### 4. Get Connection String

```bash
# From Supabase Dashboard → Settings → Database
# Connection string format:
postgresql://postgres:YOUR-PASSWORD@db.xxx.supabase.co:5432/postgres
```

### 5. Migrate Your Data

```bash
# Create workspace
WORKSPACE_ID=$(uuidgen)

# Migrate SQLite → Supabase
kurt admin migrate migrate-db \
  --target-url "postgresql://postgres:YOUR-PASSWORD@db.xxx.supabase.co:5432/postgres" \
  --workspace-id "$WORKSPACE_ID"
```

---

## Team Collaboration

### Scenario: Share Workspace with Team

**Developer 1 (Owner):**

```bash
# 1. Initialize locally with SQLite
kurt init
kurt content fetch --url https://docs.acme.com

# 2. Set up .env with PostgreSQL credentials (NOT committed to git)
cat > .env <<EOF
DATABASE_URL="postgresql://postgres:YOUR-PASSWORD@db.xxx.supabase.co:5432/postgres"
WORKSPACE_ID="$(uuidgen)"
EOF

# Add .env to .gitignore
echo ".env" >> .gitignore

# 3. Migrate to Supabase (reads from .env)
kurt admin migrate migrate-db \
  --target-url "$DATABASE_URL" \
  --workspace-id "$WORKSPACE_ID"

# 4. Commit content files and config (WITHOUT credentials)
git add sources/ kurt.config .gitignore
git commit -m "Add content and PostgreSQL config"
git push

# 5. Share credentials securely with team (Slack, 1Password, etc.)
# Share: DATABASE_URL and WORKSPACE_ID from .env
```

**Developer 2 (Team Member):**

```bash
# 1. Clone repo (gets content files + kurt.config)
git clone git@github.com:acme/content-project.git
cd content-project

# 2. Get credentials from team lead (via secure channel)
# Create .env file (NOT tracked by git)
cat > .env <<EOF
DATABASE_URL="postgresql://postgres:SHARED-PASSWORD@db.xxx.supabase.co:5432/postgres"
WORKSPACE_ID="acme-workspace-uuid"
EOF

# 3. Verify connection (kurt reads from .env)
kurt status

# 4. You can now access shared data!
kurt content list
kurt content list-entities topic
```

**Developer 3 (Adds New Content):**

```bash
# Fetch new content
kurt content fetch --url https://blog.acme.com

# Metadata is automatically synced to PostgreSQL
# (because DATABASE_URL is set in .env)

# Commit content files to git
git add sources/blog.acme.com/
git commit -m "Add blog content"
git push
```

**Team Workflow:**

1. **Metadata** → Shared via PostgreSQL (entities, relationships)
2. **Content files** → Shared via Git (`sources/`)
3. **Each developer** → Full local copy + shared knowledge graph

### Read-Only Users

```sql
-- Create read-only role in PostgreSQL
CREATE ROLE kurt_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO kurt_reader;

-- Create read-only user
CREATE USER analyst WITH PASSWORD 'read-only-pass';
GRANT kurt_reader TO analyst;
```

```bash
# Analyst uses read-only connection string
DATABASE_URL="postgresql://analyst:read-only-pass@host:5432/db"
kurt content list  # ✓ works
kurt content fetch --url https://example.com  # ✗ fails (no write permission)
```

---

## Troubleshooting

### Connection Issues

```bash
# Test connection
kurt status

# Check configuration
kurt admin workspace current

# Verify PostgreSQL is accessible
psql "postgresql://user:pass@host:5432/db" -c "SELECT 1"
```

### Vector Search Not Working

```bash
# Install pgvector extension in PostgreSQL
psql "postgresql://user:pass@host:5432/db" -c "CREATE EXTENSION vector"
```

### Missing Content Files

```bash
# Content lives in git, not database
git pull  # Get latest content files

# Or fetch from source
kurt content fetch --status NOT_FETCHED
```

### Workspace Not Set

```bash
# If you see "workspace_id is null" errors
kurt admin workspace set <your-workspace-id>
```

---

## Best Practices

1. **Keep SQLite Backup:** Don't delete `.kurt/kurt.sqlite` after migration
2. **Use .env for Secrets:** Never commit `DATABASE_URL` with password to git
3. **Commit Content to Git:** Always `git add sources/` and commit
4. **Separate Workspaces:** Use different workspace IDs for dev/staging/prod
5. **Read-Only Users:** Create read-only database users for analysts
6. **Regular Backups:** Supabase auto-backs up, but export important data

---

## Reference

### CLI Commands

```bash
# Migration
kurt admin migrate migrate-db --target-url <url> --workspace-id <id>

# Workspace management
kurt admin workspace current
kurt admin workspace set <workspace-id>
kurt admin workspace unset
kurt admin workspace list
kurt admin workspace create <name>

# Check status
kurt status
```

### Configuration Files

- **kurt.config** - Database connection (committed to git)
- **.env** - Secrets like DATABASE_URL (NOT committed)
- **sources/** - Content markdown files (committed to git)

### Database Schema

See [src/kurt/db/models.py](src/kurt/db/models.py) for full schema.

Key tables:
- `tenants` - Workspaces
- `documents` - Document metadata (with `tenant_id`)
- `entities` - Topics, technologies (with `tenant_id`)
- `entity_relationships` - Knowledge graph edges
- `document_entities` - Document ↔ Entity connections

---

## Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/kurt-core/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/kurt-core/discussions)
- **Documentation:** [README.md](README.md)
