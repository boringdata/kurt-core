# Change: Migrate from Supabase to Neon

## Why

- **Scale-to-zero**: Neon pauses idle databases ($0 compute when not in use)
- **Direct SQL + JWT**: Neon proxy validates JWT automatically - clients connect directly
- **Simplification**: Remove REST API layer for CRUD, rely on RLS
- **Branching**: Auth state branches with database (dev/staging environments)
- **Cost**: Supabase $25/project, Neon ~$0 for idle workspaces

## What Changes

### 1. Architecture Simplification

**BEFORE (Supabase):**
```
Client → REST API → Supabase Postgres
         ↑
         Business logic, auth, rate limiting
```

**AFTER (Neon):**
```
Client → Neon Proxy (JWT validation) → Neon Postgres (RLS + rate limiting)
```

### 2. Deprecated Endpoints

Remove these REST endpoints - clients use direct SQL instead:

| Endpoint | Replacement |
|----------|-------------|
| `GET /api/documents` | `SELECT * FROM documents` |
| `POST /api/documents` | `INSERT INTO documents` |
| `PUT /api/documents/:id` | `UPDATE documents WHERE id = ?` |
| `DELETE /api/documents/:id` | `DELETE FROM documents WHERE id = ?` |
| `GET /core/api/workflows` | `SELECT * FROM dbos.workflow_status` |
| `GET /core/api/status` | Direct DBOS queries |

### 3. Kept Endpoints

These require server-side logic:

| Endpoint | Reason |
|----------|--------|
| `/auth/*` | Neon Auth wrapper, token management |
| `/api/workspaces` | Provisioning logic (creates schemas, roles) |
| `/api/database/connection` | Returns JWT connection string |
| `/webhooks/*` | GitHub webhooks, external integrations |

### 4. Database-Level Protections

Replace API-level rate limiting with Postgres:

- **Connection limits**: `CONNECTION LIMIT 20` per workspace role
- **Statement timeout**: `SET statement_timeout = '60s'` per role
- **Rate limiting**: Advisory locks + counters in RLS policies
- **Usage tracking**: Triggers for billing/quota foundation

See epic: `kc-1` (Multi-Tenant Protection & Rate Limiting)

### 5. Database Migration (Supabase → Neon)

- Replace Supabase Postgres with Neon Postgres
- Keep schema-per-workspace model (DBOS requires it)
- Use Neon's `DATABASE_AUTHENTICATED_URL` for JWT-based connections
- Provision via `neonctl` CLI

### 6. Auth Migration (Supabase Auth → Neon Auth)

- Replace Supabase Auth with Neon Auth (Better Auth)
- Users/sessions stored directly in Neon DB
- JWKS per branch for JWT validation
- Keep magic link flow, adapt email templates

## Impact

### Kurt-Cloud - Remove/Simplify

```diff
- src/api/documents.py        # DELETE - use direct SQL
- src/api/workflows.py        # DELETE - use direct SQL
```

### Kurt-Core - Remove/Simplify (in `../kurt-core-neon-migration`)

```diff
- src/kurt/web/api/documents.py   # DEPRECATE - use direct SQL
- src/kurt/web/api/workflows.py   # DEPRECATE - use direct SQL
# Keep only: /docs, /health, /status (metadata)
```

### Kurt-Cloud - Update

```
src/api/middleware.py      # Neon JWT validation (simplified)
src/api/auth.py            # Neon Auth integration
src/api/provisioning.py    # Add role limits, neonctl
src/api/database.py        # Return authenticated URL
src/db/migrations/         # Rate limiting tables
```

### Kurt-Core - Update

```
src/kurt/db/tenant.py      # Neon auth.user_id() support
src/kurt/db/database.py    # Neon connection strings
src/kurt/core/dbos.py      # Neon-compatible config
```

### Environment Variables

```diff
- SUPABASE_URL
- SUPABASE_ANON_KEY
- SUPABASE_JWT_SECRET
+ NEON_PROJECT_ID=lively-mountain-57013733
+ NEON_API_KEY=xxx
+ DATABASE_URL=postgresql://...@neon.tech/neondb
+ DATABASE_AUTHENTICATED_URL=postgresql://...@neon.tech/neondb
```

## Client Migration

### Before (REST API)

```javascript
const response = await fetch('/api/documents', {
  headers: { 'Authorization': `Bearer ${jwt}` }
});
const docs = await response.json();
```

### After (Direct SQL)

```javascript
import { createDatabaseClient } from '@/lib/database';

const sql = createDatabaseClient(jwt);
const docs = await sql`SELECT * FROM documents`;
```

## Resolved Questions

1. **Neon Auth email customization** → Better Auth `sendMagicLink()` hook (see design.md)
2. **DBOS cold-start** → Checkpoints survive, test plan in design.md
3. **Client libraries** → Generic helpers: `createDatabaseClient()` (JS), `get_authenticated_connection()` (Python)

## Open Questions

1. ~~**Token refresh** - How to handle JWT expiry during long sessions?~~ → **RESOLVED** (see design.md Section 13)
2. **Offline handling** - Client reconnection patterns for direct SQL?
