# Tasks: Supabase to Neon Migration

## Epic Overview
Full migration from Supabase (Auth + Postgres) to Neon (Auth + Postgres), including code updates, migration scripts, and stress testing on kurt-demo.

---

## Phase 1: Neon Setup

### 1.1 Project Configuration
- [x] Create Neon project `kurt-cloud`
- [x] Install neonctl CLI
- [x] Authenticate with Neon
- [ ] Configure project settings (autoscaling, suspend timeout)
- [ ] Set up IP allowlist (if needed)

### 1.2 Neon Auth Setup
- [ ] Enable Neon Auth (Better Auth) on project
- [ ] Configure email provider for magic links
- [ ] Customize email templates
- [ ] Configure JWT to include `workspace_id` claim (for RLS)
- [ ] Get JWKS endpoint URL
- [ ] Test auth flow manually (signup, login, logout)

### 1.3 Database Schema Setup
- [ ] Create `cloud` schema
- [ ] Create initial workspace tables
- [ ] Set up RLS policies:
  - User isolation: `auth.user_id()` (from JWT `sub`)
  - Workspace isolation: `auth.session()->>'workspace_id'` (from JWT claim)
- [ ] Create workspace provisioning function (schema creation)
- [ ] Test schema isolation

---

## Phase 2: Kurt-Cloud Code Updates

### 2.1 Dependencies
- [ ] Remove `supabase` from pyproject.toml
- [ ] Add `neon-serverless` driver (if using JS) or `psycopg` with Neon pooler
- [ ] Add `pyjwt` for JWT validation (if not using Neon SDK)
- [ ] Update uv.lock

### 2.2 Environment Variables
- [ ] Add NEON_PROJECT_ID
- [ ] Add NEON_API_KEY
- [ ] Add DATABASE_AUTHENTICATED_URL
- [ ] Add NEON_JWKS_URL
- [ ] Update .env.example
- [ ] Update Vercel env vars

### 2.3 Auth Module (`src/api/auth.py`)
- [ ] Replace Supabase Auth client with Neon Auth
- [ ] Update `/auth/login` - magic link request
- [ ] Update `/auth/callback` - token exchange
- [ ] Update `/auth/logout` - session invalidation
- [ ] Update `/auth/me` - user info from JWT
- [ ] Test all auth endpoints

### 2.4 Middleware (`src/api/middleware.py`)
- [ ] Replace Supabase JWT validation with Neon JWKS
- [ ] Remove `set_config()` dance (Neon handles it)
- [ ] Update error handling for Neon-specific errors
- [ ] Test middleware with valid/invalid JWTs

### 2.5 Database Module (`src/api/database.py`)
- [ ] Update `/database/connection` to return Neon URLs
- [ ] Return `DATABASE_AUTHENTICATED_URL` for client access
- [ ] Update workspace schema lookup
- [ ] Test connection endpoint

### 2.6 Provisioning (`src/api/provisioning.py`)
- [ ] Replace Supabase schema creation with Neon
- [ ] Option: Use neonctl for branch creation
- [ ] Option: Use SQL for schema creation in main branch
- [ ] Update DBOS user creation for Neon
- [ ] Test workspace provisioning

### 2.7 Workspace Service (`src/workspaces/service.py`)
- [ ] Update user lookup for Neon Auth
- [ ] Update invite flow for Neon
- [ ] Test workspace CRUD operations

### 2.8 Remove Deprecated Endpoints
- [ ] Remove `src/api/documents.py` (if exists)
- [ ] Remove `src/api/workflows.py` (if exists)
- [ ] Remove `/core/api/*` mounts (keep only `/core/docs`)
- [ ] Update `src/api/app.py` router config

### 2.9 Client Helpers (Generic) - JavaScript/Web
- [ ] Create `src/lib/database.js` with `createDatabaseClient(jwt)`
- [ ] Create `src/hooks/useDatabase.js` React hook
- [ ] Add error handling wrappers (JWT expiry, RLS errors, cold-start retry)
- [ ] Add token refresh logic
- [ ] Note: Python client `get_authenticated_connection()` is in kurt-core (see 3.6)

### 2.10 Database-Level Protections (See kc-1 epic)
- [ ] kc-2: Per-workspace Postgres role with connection limits
- [ ] kc-3: Per-workspace statement timeout
- [ ] kc-4: Advisory lock rate limiting for writes
- [ ] kc-5: Usage tracking for billing foundation

---

## Phase 3: Kurt-Core Updates

**Worktree:** `../kurt-core-neon-migration` (branch: `neon-migration`)
**Workflow:** Work on branch → Create PR for review → Merge after approval

```bash
cd ../kurt-core-neon-migration
git branch  # Verify: * neon-migration
```

### 3.1 Tenant Module (`src/kurt/db/tenant.py`)
- [ ] Add `is_neon_mode()` detection
- [ ] Update `set_rls_context()` for Neon (no-op, proxy handles it)
- [ ] Support `DATABASE_AUTHENTICATED_URL` pattern
- [ ] Test tenant isolation with Neon

### 3.2 Database Module (`src/kurt/db/database.py`)
- [ ] Support Neon connection string format
- [ ] Handle Neon pooler vs direct connections
- [ ] Update connection pooling for scale-to-zero
- [ ] Test database connections

### 3.3 DBOS Integration (`src/kurt/core/dbos.py`)
- [ ] Test DBOS with Neon connection strings
- [ ] Verify workflow durability across scale-to-zero
- [ ] Test step recovery after compute restart
- [ ] Document any Neon-specific DBOS config

### 3.4 CLI Auth (`src/kurt/cli/auth/`)
- [ ] Update credentials storage for Neon
- [ ] Update `kurt cloud login` for Neon Auth
- [ ] Update `kurt cloud logout`
- [ ] Test CLI auth flow

### 3.5 Remove/Deprecate REST API Endpoints
- [ ] Deprecate `src/kurt/web/api/documents.py` (if exists)
- [ ] Deprecate `src/kurt/web/api/workflows.py` (if exists)
- [ ] Update `src/kurt/web/api/server.py` - remove CRUD routes
- [ ] Keep only: `/docs`, `/health`, `/status` (metadata only)

### 3.6 Python Client Helper
- [ ] Create `src/kurt/db/client.py` with `get_authenticated_connection(jwt)`
- [ ] Support connection via `options=-c auth.jwt={jwt}` (for pg_session_jwt)
- [ ] Add error handling (invalid JWT, RLS errors, cold-start retry)
- [ ] Add usage example in docstring

---

## Phase 3.5: Testing Infrastructure

### 3.5.1 Unit Tests (pytest-postgresql)
- [ ] Add `pytest-postgresql` to dev dependencies
- [ ] Create `tests/conftest.py` with fixtures
- [ ] Mock `auth.user_id()` and `auth.session()` functions
- [ ] Write RLS isolation tests
- [ ] Write rate limiting tests
- [ ] Write connection limit tests

### 3.5.2 Integration Tests (Neon Branch)
- [ ] Create `tests/integration/conftest.py`
- [ ] Fixture to create/delete ephemeral Neon branch
- [ ] Test migrations on real Neon
- [ ] Test DBOS workflows on Neon
- [ ] Test scale-to-zero recovery

### 3.5.3 E2E Tests
- [ ] Test local → cloud migration flow
- [ ] Test direct SQL access with JWT
- [ ] Test web dashboard with direct SQL
- [ ] Test CLI commands in cloud mode

### 3.5.4 CI/CD Setup
- [ ] Add `NEON_API_KEY` secret to GitHub
- [ ] Add `NEON_PROJECT_ID` variable to GitHub
- [ ] Create `.github/workflows/test.yml` (branch per PR)
- [ ] Create `.github/workflows/deploy.yml` (migrate on main)
- [ ] Test PR workflow creates/deletes branches

### 3.5.5 Vercel Deployment Testing
Push to `main` triggers Vercel deployment for testing auth flows in production-like environment.

- [ ] Push kurt-cloud to main → triggers Vercel preview
- [ ] Test auth callback URLs work on Vercel domain
- [ ] Test JWT validation with Neon JWKS
- [ ] Verify environment variables are set correctly

---

## Phase 4: Migration Scripts

### 4.1 Schema Migration (Fresh Start)

**Reset Alembic:** Remove all existing migration files and start fresh.

```bash
# Delete old migrations
rm -rf src/db/migrations/versions/*.py

# Create fresh initial migration
cd src/db/migrations
alembic revision -m "initial_neon_schema"
```

- [ ] Delete existing migration files in `src/db/migrations/versions/`
- [ ] Create fresh `initial_neon_schema` migration with:
  - `cloud` schema creation
  - `workspaces` table
  - `workspace_members` table
  - `rate_limits` table
  - `usage_events` table
  - RLS policies
- [ ] Write script: `scripts/setup_neon.py`
  - Create cloud schema
  - Run Alembic migrations
  - Run kurt-core migrations
  - Create workspace roles with limits
- [ ] Test on fresh Neon project
- [ ] Document manual steps

### 4.2 Data Migration
- [x] **SKIPPED** - Fresh start, no Supabase data to migrate

### 4.3 Local → Cloud Migration
- [ ] Update `kurt cloud push` command
- [ ] Support export to JSONL format
- [ ] Support import from JSONL
- [ ] Handle workspace creation
- [ ] Test full migration flow

---

## Phase 5: Kurt-Demo E2E Test

**Note:** User can create test account with fake email themselves via the auth UI.

### 5.1 Setup Fresh Kurt-Demo
```bash
cd ../kurt-demo
rm -rf .kurt
kurt init
```

### 5.2 Create Test User
- [ ] User creates account via `/auth/login-page` with test email
- [ ] User completes magic link flow (or password signup)
- [ ] Verify user record in Neon Auth tables

### 5.3 Populate Local Data
- [ ] Add map documents
- [ ] Run map workflow
- [ ] Add fetch documents
- [ ] Run fetch workflow
- [ ] Verify local data integrity

### 5.4 Migrate to Cloud
- [ ] `kurt cloud login` (Neon Auth)
- [ ] `kurt cloud workspace create --name kurt-demo-test`
- [ ] `kurt cloud push`
- [ ] Verify migration success

### 5.5 Verify Cloud Operations
- [ ] `DATABASE_URL=kurt kurt map list`
- [ ] `DATABASE_URL=kurt kurt fetch list`
- [ ] Run workflow in cloud mode
- [ ] Check DBOS state persistence
- [ ] Test scale-to-zero recovery (wait 5 min, run again)

### 5.6 Direct SQL Access Test
- [ ] Get JWT from `kurt cloud token`
- [ ] Connect via psycopg: `get_authenticated_connection(jwt)` (see 3.6)
- [ ] Or via JS: `createDatabaseClient(jwt)` (see 2.9)
- [ ] Run SELECT with RLS filtering
- [ ] Verify user can only see own data

---

## Phase 6: Stress Test

### 6.1 Load Test Setup
- [ ] Create 10 test workspaces
- [ ] Populate each with 100 documents
- [ ] Configure concurrent workflow runs

### 6.2 Concurrent Operations
- [ ] Run 5 workflows simultaneously
- [ ] Monitor Neon compute scaling
- [ ] Verify no data cross-contamination
- [ ] Check DBOS handles concurrent steps

### 6.3 Scale-to-Zero Test
- [ ] Let database suspend (5 min idle)
- [ ] Trigger workflow
- [ ] Measure cold start latency
- [ ] Verify workflow resumes correctly

### 6.4 Performance Comparison
- [ ] Benchmark: Supabase vs Neon query latency
- [ ] Benchmark: Workflow completion time
- [ ] Document findings

---

## Phase 7: Cutover

### 7.1 Pre-Cutover
- [ ] Test all critical paths on Neon
- [ ] Update documentation

### 7.2 Cutover
- [ ] Update Vercel env vars to Neon
- [ ] Deploy updated code
- [ ] Monitor for errors
- [ ] Verify auth flow works

### 7.3 Post-Cutover
- [ ] Monitor for 48 hours
- [ ] Address any issues
- [ ] Update CLAUDE.md with Neon instructions

---

## Verification Checks

### Kurt-Core Auth (neon-migration branch)
- [ ] `is_neon_mode()` correctly detects Neon environment
- [ ] `set_rls_context()` is no-op when Neon handles JWT
- [ ] `load_context_from_credentials()` works with Neon tokens
- [ ] CLI auth flow (`kurt cloud login/logout`) works
- [ ] Direct SQL via `get_authenticated_connection()` works

### Kurt-Cloud Lifecycle
- [ ] Auth: Magic link email sent via Neon Auth
- [ ] Auth: Callback extracts tokens correctly
- [ ] Auth: JWT validation via JWKS endpoint
- [ ] Middleware: Extracts `auth.user_id()` from JWT
- [ ] Provisioning: Creates workspace schema + role
- [ ] Database: Returns authenticated connection URL
- [ ] Integration: Kurt-core receives workspace context

---

## Acceptance Criteria

- [ ] All auth flows work (login, logout, token refresh)
- [ ] Workspace isolation verified (RLS working)
- [ ] DBOS workflows survive scale-to-zero
- [ ] Direct SQL access works with JWT (Python + JS)
- [ ] Kurt-demo migrated successfully
- [ ] No data loss during migration
- [ ] Performance meets or exceeds Supabase baseline
- [ ] Rate limiting prevents noisy neighbor
- [ ] Web dashboard works with direct SQL
- [ ] CLI works with direct SQL
