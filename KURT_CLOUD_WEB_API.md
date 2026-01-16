# Kurt Cloud - Web API Architecture

## Overview

Kurt uses a **unified web API** architecture where the same FastAPI app serves both the CLI (in cloud mode) and the web UI.

**Architecture**:
```
Local Mode:
  kurt status → status/queries.py → SQLite/PostgreSQL
  kurt serve → web/api/server.py → queries.py (web UI)

Cloud Mode:
  kurt status → HTTP → kurt-cloud → web/api/server.py → queries.py → PostgreSQL
  Web UI → HTTP → kurt-cloud → web/api/server.py → queries.py → PostgreSQL
```

**Benefits**:
✅ Single API definition - no duplication
✅ CLI and web UI use same endpoints
✅ `kurt serve` uses same API that kurt-cloud hosts
✅ Easy local testing - run `kurt serve` and it works exactly like cloud

## Changes in kurt-core ✅ (Completed)

### 1. Created `src/kurt/status/` module
- `queries.py` - SQLAlchemy queries (pure data access)
- `cli.py` - Click command that routes based on mode

### 2. Added `/api/status` endpoint to `src/kurt/web/api/server.py`
```python
@app.get("/api/status")
def api_status():
    """Get comprehensive project status."""
    from kurt.db import managed_session
    from kurt.status.queries import get_status_data

    with managed_session() as session:
        return get_status_data(session)
```

### 3. Updated `src/kurt/db/cloud.py`
- Added `get_api_base_url()` - Returns kurt-cloud URL
- Added `get_auth_token()` - Returns JWT token

### 4. CLI routes to web API in cloud mode
```python
def _get_status_data() -> dict:
    from kurt.db.cloud import is_cloud_mode

    if is_cloud_mode():
        return _get_status_data_from_api()  # HTTP to /api/status
    else:
        return _get_status_data_from_db()   # Direct queries
```

## Kurt-cloud Integration

### Simple Hosting

Kurt-cloud just needs to host the FastAPI app:

```python
# kurt-cloud/app/main.py
from kurt.web.api.server import app

# That's it! The app is already configured with all endpoints.
```

### RLS Multi-tenancy

Add middleware to set PostgreSQL session variables for RLS:

```python
from fastapi import Request
import jwt

@app.middleware("http")
async def set_rls_context(request: Request, call_next):
    """Set PostgreSQL RLS context from JWT token."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            request.state.user_id = payload.get("sub")
            request.state.workspace_id = payload.get("workspace_id")

            # Set RLS context in managed_session
            # This is handled by CloudDatabaseClient automatically
        except Exception:
            pass

    response = await call_next(request)
    return response
```

### Environment Configuration

```bash
# Kurt-cloud environment
DATABASE_URL=postgresql://user:pass@host:5432/db
KURT_CLOUD_AUTH=true  # Enable auth middleware
```

## Testing

### Local mode (SQLite)
```bash
cd kurt-core
uv run kurt status
```
✅ Works - calls queries.py directly

### Local web API
```bash
cd kurt-core
uv run kurt serve  # Starts web API on localhost:8000
curl http://localhost:8000/api/status
```
✅ Works - same endpoint kurt-cloud uses

### Cloud mode (once kurt-cloud is deployed)
```bash
cd kurt-demo
# DATABASE_URL="kurt" in kurt.config
uv run kurt status
```

Expected flow:
1. CLI detects cloud mode
2. Calls `GET https://kurt-cloud.vercel.app/api/status`
3. Kurt-cloud runs `get_status_data(session)` with PostgreSQL
4. Returns JSON to CLI
5. CLI formats and displays

## Pattern for New Features

When adding new read-only query features:

### 1. Create `module/queries.py`
```python
def get_documents_list(session, filters: dict) -> list[dict]:
    from sqlmodel import select
    from kurt.workflows.map.models import MapDocument

    stmt = select(MapDocument)
    if filters.get("status"):
        stmt = stmt.where(MapDocument.status == filters["status"])

    docs = session.exec(stmt).all()
    return [doc.model_dump() for doc in docs]
```

### 2. Add endpoint to `web/api/server.py`
```python
@app.get("/api/documents")
def api_documents(status: str | None = None):
    """List documents with filters."""
    from kurt.db import managed_session
    from kurt.documents.queries import get_documents_list

    with managed_session() as session:
        filters = {"status": status} if status else {}
        return get_documents_list(session, filters)
```

### 3. Create `module/cli.py` with routing
```python
def list_documents(status: str | None = None):
    from kurt.db.cloud import is_cloud_mode

    if is_cloud_mode():
        # Call web API
        import requests
        from kurt.db.cloud import get_api_base_url, get_auth_token

        response = requests.get(
            f"{get_api_base_url()}/api/documents",
            params={"status": status} if status else {},
            headers={"Authorization": f"Bearer {get_auth_token()}"},
        )
        return response.json()
    else:
        # Direct queries
        from kurt.db import managed_session
        from .queries import get_documents_list

        with managed_session() as session:
            return get_documents_list(session, {"status": status} if status else {})
```

## What About Workflows?

**Workflow execution** (map, fetch, research):
- Keep using `@DBOS.workflow()` - already works
- No API changes needed
- DBOS handles cloud execution

**Workflow queries** (list, get, status):
- Already in `web/api/server.py` (`/api/workflows`)
- CLI should use these endpoints in cloud mode
- Same pattern as status

## Summary

✅ **Single API** - `web/api/server.py` serves CLI and web UI
✅ **No duplication** - Same endpoints, same queries
✅ **Easy deployment** - Kurt-cloud just imports and hosts the app
✅ **Consistent behavior** - `kurt serve` == kurt-cloud
✅ **Scalable pattern** - Add query function → Add endpoint → CLI routes

Next: Apply this pattern to documents, workflows, and other query commands.
