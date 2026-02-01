# Design: Supabase to Neon Migration

## Architecture Overview

```
CURRENT (Supabase)                    TARGET (Neon)
─────────────────                     ─────────────────
Supabase Auth ──┐                     Neon Auth ──────┐
                │                                      │
PostgREST ──────┼── Supabase Postgres    Neon Proxy ──┼── Neon Postgres
                │   (always-on)          (JWT auth)    │   (scale-to-zero)
Direct SQL ─────┘                                      │
(manual set_config)                    Direct SQL ─────┘
                                       (auto JWT validation)
```

## Component Design

### 1. Neon Project Structure

```
Neon Project: kurt-cloud (lively-mountain-57013733)
├── Main Branch: main
│   ├── Schema: public (shared tables + RLS)
│   │   ├── alembic_version
│   │   └── (kurt-core workflow tables)
│   ├── Schema: cloud (kurt-cloud tables)
│   │   ├── workspaces
│   │   ├── workspace_members
│   │   └── alembic_version
│   └── Schema: ws_<id> (per-workspace DBOS)
│       └── (DBOS system tables)
└── Neon Auth (Better Auth)
    ├── Schema: auth (Better Auth tables)
    │   ├── users
    │   ├── sessions
    │   ├── accounts
    │   └── verifications
    └── JWKS endpoint
```

### 2. Connection URLs

```python
# Admin access (migrations, provisioning)
DATABASE_URL = "postgresql://neondb_owner:xxx@ep-xxx.neon.tech/neondb"

# JWT-authenticated access (clients)
DATABASE_AUTHENTICATED_URL = "postgresql://authenticated@ep-xxx.neon.tech/neondb"
# Client passes JWT via authToken parameter
```

### 3. Auth Flow (Neon Auth / Better Auth)

Neon Auth uses [Better Auth](https://better-auth.com) under the hood. Magic link is a plugin.

**Email Template Customization:**
```javascript
// auth.config.js
import { betterAuth } from "better-auth";
import { magicLink } from "better-auth/plugins";

export const auth = betterAuth({
  plugins: [
    magicLink({
      expiresIn: 300, // 5 minutes
      sendMagicLink: async ({ email, token, url }, ctx) => {
        // Custom email sending - use any provider (Resend, SendGrid, etc.)
        await sendEmail({
          to: email,
          subject: "Sign in to Kurt Cloud",
          html: `
            <h1>Welcome to Kurt Cloud</h1>
            <p>Click the link below to sign in:</p>
            <a href="${url}">Sign In</a>
            <p>This link expires in 5 minutes.</p>
          `
        });
      }
    })
  ]
});
```

**Auth Flow:**
```
1. User requests magic link
   POST /auth/magic-link {email}
   └── Better Auth generates token, calls sendMagicLink()

2. User clicks link
   GET /auth/magic-link/verify?token=xxx
   └── Better Auth validates, creates session, returns JWT

3. Client uses JWT for API + direct SQL
   Authorization: Bearer <jwt>
   └── Neon Proxy validates via JWKS
   └── auth.user_id() available in Postgres
```

**JWKS Endpoint:**
```
https://[project].neon.tech/.well-known/jwks.json
```

### 3.1 pg_session_jwt Integration

Neon uses the [pg_session_jwt](https://github.com/neondatabase/pg_session_jwt) extension to make JWT claims available in Postgres.

**How it works:**
1. Client connects with JWT in connection options
2. Neon Proxy validates JWT against JWKS
3. Extension extracts claims into `auth.user_id()` and `auth.session()`

**RLS Policy using auth.user_id():**
```sql
CREATE POLICY "users_own_data" ON documents
    FOR ALL USING (owner_id = auth.user_id());
```

**Custom claims (e.g., workspace_id):**
```sql
-- Access any claim from JWT
CREATE POLICY "workspace_isolation" ON documents
    FOR ALL USING (
        workspace_id = (auth.session()->>'workspace_id')::uuid
    );
```

### 4. Workspace Provisioning

```python
# Option A: Schema per workspace (current model)
async def provision_workspace(workspace_id: str):
    schema = f"ws_{workspace_id[:8]}"
    # Create schema in main branch
    await db.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    # Create DBOS user with limited privileges
    await db.execute(f"CREATE USER ws_{schema}_dbos ...")
    # Set search_path
    return {"schema": schema, "search_path": f"{schema},public"}

# Option B: Branch per workspace (full isolation)
async def provision_workspace(workspace_id: str):
    branch = await neon_api.create_branch(
        project_id=NEON_PROJECT_ID,
        name=f"ws-{workspace_id[:8]}",
        parent="main"
    )
    return {"branch_id": branch.id, "connection_url": branch.connection_uri}
```

### 5. Middleware Changes

```python
# src/api/middleware.py

from neon_auth import verify_jwt  # or manual JWKS validation

class NeonAuthMiddleware:
    async def dispatch(self, request, call_next):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")

        # Validate JWT against Neon JWKS
        payload = await verify_jwt(token, jwks_url=NEON_JWKS_URL)

        user_id = payload.get("sub")
        workspace_id = request.headers.get("X-Workspace-ID")

        # Set context for RLS
        set_workspace_context(workspace_id=workspace_id, user_id=user_id)

        # Neon's auth.user_id() is auto-populated via JWT
        # No need for set_config() like Supabase

        response = await call_next(request)
        clear_workspace_context()
        return response
```

### 6. Kurt-Core Tenant Updates

```python
# src/kurt/db/tenant.py

def set_rls_context(session: Session) -> None:
    """Set PostgreSQL session variables for RLS policies."""
    if not is_neon_mode():
        # Supabase/manual mode - use set_config
        session.execute(text("SET LOCAL app.workspace_id = :ws"), {"ws": workspace_id})
    # Neon mode: auth.user_id() already set by proxy
```

## Migration Scripts

### Schema Migration (Fresh Start)

**Reset Alembic** - Delete all existing migration files and start fresh:

```bash
# 1. Remove old migrations
rm -rf src/db/migrations/versions/*.py

# 2. Create fresh initial migration
cd src/db/migrations
alembic revision -m "initial_neon_schema"
# Edit the generated file to include all tables + RLS policies

# 3. Set Neon DATABASE_URL
export DATABASE_URL="postgresql://neondb_owner:xxx@ep-xxx.neon.tech/neondb"

# 4. Create cloud schema
psql $DATABASE_URL -c "CREATE SCHEMA IF NOT EXISTS cloud"

# 5. Run fresh migrations
alembic upgrade head

# 6. Run kurt-core migrations (public schema)
python scripts/run_core_migrations.py
```

**Why fresh start?**
- No existing data to migrate
- Cleaner schema with rate limiting from day 1
- Avoid carrying over Supabase-specific remnants

### Local → Cloud Migration (kurt-demo example)

```bash
# In kurt-demo project directory

# 1. Export local SQLite data
kurt export --format jsonl --output data.jsonl

# 2. Login to kurt-cloud
kurt cloud login

# 3. Create workspace (provisions Neon schema)
kurt cloud workspace create --name "kurt-demo"

# 4. Import data to cloud
kurt cloud import --file data.jsonl --workspace <workspace-id>

# 5. Switch to cloud mode
kurt config set DATABASE_URL=kurt

# 6. Verify
kurt status
```

## Neon CLI Commands Reference

```bash
# Auth
neonctl auth

# Projects
neonctl projects list
neonctl projects create --name <name>

# Branches
neonctl branches list --project-id <id>
neonctl branches create --project-id <id> --name <name>
neonctl branches delete --project-id <id> --name <name>

# Connection strings
neonctl connection-string --project-id <id>
neonctl connection-string --project-id <id> --branch <branch>

# SQL
neonctl sql --project-id <id> "SELECT version()"

# Roles/Users
neonctl roles list --project-id <id>
neonctl roles create --project-id <id> --name <name>
```

## Testing Strategy

### Unit Tests (pytest + pytest-postgresql)

```python
# tests/conftest.py
import pytest
from pytest_postgresql import factories

# Create test PostgreSQL instance
postgresql_proc = factories.postgresql_proc(
    port=None,  # Random port
    unixsocketdir='/tmp'
)
postgresql = factories.postgresql('postgresql_proc')


@pytest.fixture
def test_db(postgresql):
    """Fresh database with schema for each test."""
    conn = postgresql.connection()

    # Create schemas
    conn.execute("CREATE SCHEMA IF NOT EXISTS cloud")
    conn.execute("CREATE SCHEMA IF NOT EXISTS ws_test")

    # Install pg_session_jwt mock functions
    conn.execute("""
        CREATE OR REPLACE FUNCTION auth.user_id() RETURNS UUID AS $$
            SELECT current_setting('test.user_id', true)::uuid
        $$ LANGUAGE sql;

        CREATE OR REPLACE FUNCTION auth.session() RETURNS JSONB AS $$
            SELECT current_setting('test.session', true)::jsonb
        $$ LANGUAGE sql;
    """)

    # Run migrations
    from alembic import command
    from alembic.config import Config
    alembic_cfg = Config("src/db/migrations/alembic.ini")
    command.upgrade(alembic_cfg, "head")

    yield conn
    conn.close()


@pytest.fixture
def auth_context(test_db):
    """Set auth context for RLS testing."""
    def _set_user(user_id: str, workspace_id: str = None):
        test_db.execute(f"SET test.user_id = '{user_id}'")
        if workspace_id:
            # Set both for compatibility with different RLS patterns
            test_db.execute(f"SET test.workspace_id = '{workspace_id}'")
            # auth.session() returns JSON, so set as JSON object
            session_json = f'{{"workspace_id": "{workspace_id}", "user_id": "{user_id}"}}'
            test_db.execute(f"SET test.session = '{session_json}'")
    return _set_user
```

### Unit Test Examples

```python
# tests/test_rls.py
def test_user_can_only_see_own_documents(test_db, auth_context):
    """RLS prevents cross-workspace access."""
    # Setup: Two users, two workspaces
    auth_context(user_id="user-1", workspace_id="ws-1")
    test_db.execute("INSERT INTO documents (id, workspace_id, title) VALUES ('doc-1', 'ws-1', 'User 1 Doc')")

    auth_context(user_id="user-2", workspace_id="ws-2")
    test_db.execute("INSERT INTO documents (id, workspace_id, title) VALUES ('doc-2', 'ws-2', 'User 2 Doc')")

    # Test: User 1 can only see their doc
    auth_context(user_id="user-1", workspace_id="ws-1")
    result = test_db.execute("SELECT * FROM documents").fetchall()
    assert len(result) == 1
    assert result[0]['title'] == 'User 1 Doc'


def test_rate_limiting_blocks_excessive_writes(test_db, auth_context):
    """Rate limiter blocks after threshold."""
    auth_context(user_id="user-1", workspace_id="ws-1")

    # Write up to limit
    for i in range(100):
        test_db.execute(f"INSERT INTO documents (id, workspace_id, title) VALUES ('doc-{i}', 'ws-1', 'Doc {i}')")

    # Next write should fail
    with pytest.raises(Exception, match="rate limit"):
        test_db.execute("INSERT INTO documents (id, workspace_id, title) VALUES ('doc-101', 'ws-1', 'Over Limit')")


def test_connection_limit_per_workspace(test_db):
    """Workspace role has connection limit."""
    result = test_db.execute("""
        SELECT rolconnlimit FROM pg_roles WHERE rolname = 'ws_test_user'
    """).fetchone()
    assert result['rolconnlimit'] == 20
```

### Integration Tests (Real Neon Branch)

```python
# tests/integration/conftest.py
import os
import pytest
import subprocess

@pytest.fixture(scope="session")
def neon_test_branch():
    """Create ephemeral Neon branch for integration tests."""
    project_id = os.environ["NEON_PROJECT_ID"]
    branch_name = f"test-{os.environ.get('GITHUB_RUN_ID', 'local')}"

    # Create branch
    result = subprocess.run([
        "neonctl", "branches", "create",
        "--project-id", project_id,
        "--name", branch_name,
        "--output", "json"
    ], capture_output=True, text=True)
    branch = json.loads(result.stdout)

    # Get connection string
    conn_result = subprocess.run([
        "neonctl", "connection-string",
        "--project-id", project_id,
        "--branch", branch_name
    ], capture_output=True, text=True)

    os.environ["DATABASE_URL"] = conn_result.stdout.strip()

    yield branch

    # Cleanup: Delete branch
    subprocess.run([
        "neonctl", "branches", "delete",
        "--project-id", project_id,
        "--name", branch_name,
        "--force"
    ])
```

### E2E Test: Local → Cloud Migration

```python
# tests/e2e/test_migration.py
import subprocess
import os

def test_local_to_cloud_migration(neon_test_branch, tmp_path):
    """Full migration flow from SQLite to cloud."""
    project_dir = tmp_path / "kurt-demo"
    project_dir.mkdir()

    # 1. Initialize local project
    subprocess.run(["kurt", "init"], cwd=project_dir, check=True)

    # 2. Add and run local workflow
    subprocess.run(["kurt", "map", "add", "https://example.com"], cwd=project_dir, check=True)
    subprocess.run(["kurt", "map", "run"], cwd=project_dir, check=True)

    # 3. Verify local data
    result = subprocess.run(["kurt", "map", "list", "--json"], cwd=project_dir, capture_output=True, text=True)
    local_docs = json.loads(result.stdout)
    assert len(local_docs) > 0

    # 4. Push to cloud
    subprocess.run(["kurt", "cloud", "push"], cwd=project_dir, check=True, env={
        **os.environ,
        "DATABASE_URL": "kurt"
    })

    # 5. Verify cloud data
    result = subprocess.run(["kurt", "map", "list", "--json"], cwd=project_dir, capture_output=True, text=True, env={
        **os.environ,
        "DATABASE_URL": "kurt"
    })
    cloud_docs = json.loads(result.stdout)
    assert cloud_docs == local_docs


def test_direct_sql_access_with_jwt(neon_test_branch):
    """Client can access data directly with JWT."""
    from kurt.db.client import get_authenticated_connection
    from kurt.cli.auth.credentials import load_credentials

    creds = load_credentials()
    jwt = creds.access_token

    with get_authenticated_connection(jwt) as conn:
        # RLS should filter to user's workspace
        docs = conn.execute("SELECT * FROM documents").fetchall()
        for doc in docs:
            assert doc['workspace_id'] == creds.workspace_id


def test_dbos_survives_scale_to_zero(neon_test_branch):
    """DBOS workflow recovers after compute suspend."""
    import time

    # Start long workflow
    result = subprocess.run(["kurt", "workflow", "run", "--name", "slow-test"], capture_output=True, text=True)
    workflow_id = result.stdout.strip()

    # Wait for Neon to suspend (6+ minutes)
    time.sleep(400)

    # Check workflow status - should have resumed
    result = subprocess.run(["kurt", "workflow", "status", workflow_id], capture_output=True, text=True)
    assert "completed" in result.stdout or "running" in result.stdout
```

### E2E Test: Local → Cloud Migration (CLI)

```bash
# Setup
cd ../kurt-demo
rm -rf .kurt  # Clean slate
kurt init
kurt map add https://example.com
kurt map run

# Migrate
kurt cloud login
kurt cloud workspace create --name test-migration
kurt cloud push

# Verify in cloud
DATABASE_URL=kurt kurt status
DATABASE_URL=kurt kurt map list
```

## CI/CD with GitHub Actions

### Branch per PR (Ephemeral Test Databases)

```yaml
# .github/workflows/test.yml
name: Test with Neon Branch

on:
  pull_request:
    branches: [main]

env:
  NEON_PROJECT_ID: ${{ vars.NEON_PROJECT_ID }}
  NEON_API_KEY: ${{ secrets.NEON_API_KEY }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Create Neon Branch
        id: create-branch
        uses: neondatabase/create-branch-action@v5
        with:
          project_id: ${{ env.NEON_PROJECT_ID }}
          branch_name: pr-${{ github.event.number }}
          api_key: ${{ env.NEON_API_KEY }}

      - name: Run Migrations
        run: |
          export DATABASE_URL="${{ steps.create-branch.outputs.db_url }}"
          cd src/db/migrations && alembic upgrade head

      - name: Run Tests
        run: |
          export DATABASE_URL="${{ steps.create-branch.outputs.db_url }}"
          uv run pytest tests/ -v

      - name: Delete Neon Branch
        if: always()
        uses: neondatabase/delete-branch-action@v3
        with:
          project_id: ${{ env.NEON_PROJECT_ID }}
          branch: pr-${{ github.event.number }}
          api_key: ${{ env.NEON_API_KEY }}
```

### Migration on Main Branch

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install neonctl
        run: npm install -g neonctl

      - name: Run Migrations
        run: |
          export DATABASE_URL="${{ secrets.NEON_DATABASE_URL }}"
          cd src/db/migrations && alembic upgrade head
        env:
          NEON_API_KEY: ${{ secrets.NEON_API_KEY }}

      - name: Deploy to Vercel
        run: vercel --prod
        env:
          VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
```

### Repository Secrets Required

| Secret | Description |
|--------|-------------|
| `NEON_API_KEY` | API key from Neon dashboard |
| `NEON_DATABASE_URL` | Production connection string |
| `VERCEL_TOKEN` | Vercel deployment token |

### Repository Variables Required

| Variable | Description |
|----------|-------------|
| `NEON_PROJECT_ID` | Project ID (e.g., `lively-mountain-57013733`) |

## Rollback Plan

1. Maintain feature flag: `USE_NEON=true/false` (optional, for gradual rollout)
2. Keep Supabase code in separate branch until Neon is stable
3. If critical issues: revert to Supabase branch, redeploy

**Note:** Fresh start - no data migration needed, simplifies rollback.

---

## Missing Pieces Addressed

### 7. Client Access Patterns

**Two connection methods:**
1. **psycopg (Python)**: Pass JWT via connection `options` parameter
2. **@neondatabase/serverless (JS)**: Pass JWT via `authToken` parameter

Both trigger pg_session_jwt to populate `auth.user_id()` and `auth.session()`.

#### Python CLI (Direct SQL via psycopg)

```python
# src/kurt/db/client.py
import os
import psycopg
from urllib.parse import urlencode, urlparse, urlunparse

def get_authenticated_connection(jwt: str):
    """Connect to Postgres with JWT authentication.

    Works with any provider supporting JWT-authenticated connections
    (Neon, custom PgBouncer, etc.)
    """
    base_url = os.environ["DATABASE_AUTHENTICATED_URL"]
    parsed = urlparse(base_url)

    # Add JWT to connection options
    options = f"-c auth.jwt={jwt}"
    if parsed.query:
        new_query = f"{parsed.query}&options={options}"
    else:
        new_query = f"options={options}"

    conn_url = urlunparse(parsed._replace(query=new_query))
    return psycopg.connect(conn_url)

# Usage in CLI
with get_authenticated_connection(jwt) as conn:
    docs = conn.execute("SELECT * FROM documents").fetchall()
```

#### JavaScript/React Dashboard

```javascript
// src/lib/database.js
import { neon } from '@neondatabase/serverless';

// Generic interface - implementation can be swapped
export function createDatabaseClient(jwt) {
  const url = process.env.NEXT_PUBLIC_DATABASE_AUTHENTICATED_URL;
  return neon(url, { authToken: jwt });
}

// Usage in React component
const sql = createDatabaseClient(session.accessToken);
const docs = await sql`SELECT * FROM documents WHERE status = 'active'`;
```

### 8. RLS Policy Definitions

```sql
-- public.documents (shared table)
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Use auth.session() for workspace_id (from JWT claim)
-- Use auth.user_id() for user identification (from JWT sub)
CREATE POLICY "Users see own workspace docs" ON documents
    FOR SELECT USING (
        workspace_id = (auth.session()->>'workspace_id')::uuid
    );

CREATE POLICY "Users insert to own workspace" ON documents
    FOR INSERT WITH CHECK (
        workspace_id = (auth.session()->>'workspace_id')::uuid
        AND check_write_rate(auth.user_id(), 100, 3600)  -- Rate limit
    );

CREATE POLICY "Users update own workspace" ON documents
    FOR UPDATE USING (
        workspace_id = (auth.session()->>'workspace_id')::uuid
    );

CREATE POLICY "Users delete from own workspace" ON documents
    FOR DELETE USING (
        workspace_id = (auth.session()->>'workspace_id')::uuid
    );

-- cloud.workspaces (admin table)
CREATE POLICY "Users see own workspaces" ON cloud.workspaces
    FOR SELECT USING (
        owner_id = auth.user_id()
        OR id IN (SELECT workspace_id FROM cloud.workspace_members WHERE user_id = auth.user_id())
    );
```

**Note:** JWT must include `workspace_id` claim. Set during token generation:
```javascript
// In auth config
generateToken: async (user, session) => ({
  sub: user.id,
  workspace_id: session.activeWorkspaceId,  // Include in JWT
  ...
})
```

**Rate limiting function** (created as part of kc-4):
```sql
-- Check write rate using advisory locks + counters
CREATE OR REPLACE FUNCTION check_write_rate(
    p_user_id UUID,
    p_limit INT,
    p_window_seconds INT
) RETURNS BOOLEAN AS $$
DECLARE
    v_count INT;
BEGIN
    -- Get/increment counter from rate_limits table
    INSERT INTO cloud.rate_limits (user_id, window_start, count)
    VALUES (p_user_id, date_trunc('hour', now()), 1)
    ON CONFLICT (user_id, window_start)
    DO UPDATE SET count = rate_limits.count + 1
    RETURNING count INTO v_count;

    RETURN v_count <= p_limit;
END;
$$ LANGUAGE plpgsql;
```

### 9. DBOS + Scale-to-Zero Risks

**Known Risks:**
1. DBOS holds in-memory state - may be lost on compute suspend
2. Workflow recovery relies on DB checkpoints
3. Long-running workflows may hit scale-to-zero mid-execution

**Mitigations:**
- Set `suspend_timeout_seconds = 300` (5 min) for active workspaces
- DBOS checkpoints after each step - recovery should work
- Test: Start workflow, wait for suspend, resume

**Test Plan:**
```bash
# 1. Start long workflow
kurt workflow run --name slow-test

# 2. Wait for suspend (check Neon dashboard)
sleep 400  # 6+ minutes

# 3. Check workflow status
kurt workflow status <id>
# Should show: resumed from checkpoint
```

### 10. Cost Projection

| Item | Supabase (current) | Neon (projected) |
|------|-------------------|------------------|
| Base plan | $25/mo | $19/mo (Launch) |
| Per-workspace | $25/mo each | ~$0 (idle) |
| 10 active workspaces | $250/mo | ~$25/mo |
| 50 workspaces (40 idle) | $1,250/mo | ~$50/mo |
| Storage (10GB) | Included | $3.50/mo |
| Compute (100 CU-hr) | Included | Included |

**Savings: ~80% for typical multi-tenant usage**

### 11. Rollback Criteria

**Abort if:**
- [ ] Auth flow fails consistently
- [ ] DBOS workflow recovery fails
- [ ] Query latency unacceptable
- [ ] Neon downtime >1 hour

**Rollback steps:**
1. Revert to Supabase branch
2. Redeploy
3. Investigate, fix, retry

### 12. Web Dashboard Changes

**Current (REST API):**
```javascript
// Fetches via API routes
const { data } = await fetch('/api/documents');
```

**After (Direct SQL):**
```javascript
// Direct SQL via serverless driver
import { useDatabase } from '@/hooks/useDatabase';

function DocumentList() {
  const sql = useDatabase();
  const [docs, setDocs] = useState([]);

  useEffect(() => {
    sql`SELECT * FROM documents ORDER BY created_at DESC`
      .then(setDocs);
  }, []);

  return <ul>{docs.map(d => <li>{d.title}</li>)}</ul>;
}
```

**Hook implementation:**
```javascript
// src/hooks/useDatabase.js
import { createDatabaseClient } from '@/lib/database';
import { useSession } from '@/hooks/useSession';
import { useMemo } from 'react';

export function useDatabase() {
  const { accessToken } = useSession();
  return useMemo(
    () => createDatabaseClient(accessToken),
    [accessToken]
  );
}
```

### 13. Token Refresh Flow

**JWT Expiry:**
- Access token: 15 minutes (short-lived)
- Refresh token: 7 days (stored in httpOnly cookie)

**Client-side refresh:**
```javascript
// src/lib/auth.js
export async function refreshTokenIfNeeded() {
  const session = getSession();
  if (!session) return null;

  // Check if token expires in < 5 minutes
  const expiresAt = session.expiresAt * 1000;
  if (Date.now() > expiresAt - 5 * 60 * 1000) {
    const response = await fetch('/auth/refresh', {
      method: 'POST',
      credentials: 'include'  // Send refresh token cookie
    });
    if (response.ok) {
      const newSession = await response.json();
      setSession(newSession);
      return newSession.accessToken;
    }
  }
  return session.accessToken;
}

// Usage in useDatabase hook
export function useDatabase() {
  const [sql, setSql] = useState(null);

  useEffect(() => {
    async function init() {
      const token = await refreshTokenIfNeeded();
      if (token) {
        setSql(createDatabaseClient(token));
      }
    }
    init();
  }, []);

  return sql;
}
```

### 14. Error Handling Patterns

**Client-side error handling:**
```javascript
// src/lib/database.js
export async function query(sql, sqlFn) {
  try {
    return await sqlFn(sql);
  } catch (error) {
    // Handle specific errors
    if (error.code === '28P01') {
      // Invalid JWT - redirect to login
      window.location.href = '/auth/login';
      return;
    }
    if (error.code === '42501') {
      // RLS violation - permission denied
      throw new Error('Access denied to this resource');
    }
    if (error.code === '57P01') {
      // Connection terminated (scale-to-zero wake)
      // Retry once
      await new Promise(r => setTimeout(r, 1000));
      return await sqlFn(sql);
    }
    throw error;
  }
}

// Usage
const docs = await query(sql, s => s`SELECT * FROM documents`);
```

**Python error handling:**
```python
# src/kurt/db/client.py
from psycopg import errors

def safe_query(conn, query, params=None):
    try:
        return conn.execute(query, params).fetchall()
    except errors.InvalidPassword:
        raise AuthError("Invalid or expired token")
    except errors.InsufficientPrivilege:
        raise PermissionError("Access denied by RLS policy")
    except errors.AdminShutdown:
        # Neon compute suspended, retry
        time.sleep(1)
        return conn.execute(query, params).fetchall()
```
