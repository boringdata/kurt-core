# Kurt Cloud Integration for Status API

## Overview

The status command now uses a clean architecture where:
- **Local mode**: Direct SQLAlchemy queries via `src/kurt/status/queries.py`
- **Cloud mode**: HTTP request to kurt-cloud API, which runs the same queries server-side

## Changes in kurt-core ✅ (Completed)

1. Created `src/kurt/status/` module:
   - `queries.py` - SQLAlchemy queries (works in both modes)
   - `api.py` - FastAPI router definition
   - `cli.py` - Click command that routes based on mode
   - `__init__.py` - Public exports

2. Updated `src/kurt/db/cloud.py`:
   - Added `get_api_base_url()` - Returns kurt-cloud API base URL
   - Added `get_auth_token()` - Returns JWT token for authentication

3. Updated CLI imports:
   - `src/kurt/cli/main.py` - Import status from `kurt.status`
   - `src/kurt/cli/tests/test_status.py` - Updated import

## Changes needed in kurt-cloud

### 1. Update `pyproject.toml` dependency

Ensure kurt-cloud has kurt-core as a dependency so it can import the router:

```toml
[tool.uv]
dependencies = [
    "kurt-core>=X.X.X",  # Update to latest version
    # ... other deps
]
```

### 2. Mount the router in `app/main.py`

```python
from fastapi import FastAPI
from kurt.status.api import router as status_router

app = FastAPI()

# Mount kurt-core routers
app.include_router(status_router)

# ... rest of your app setup
```

### 3. Ensure PostgreSQL connection for API

The API endpoint calls `managed_session()` which needs direct PostgreSQL access (not PostgREST).

In kurt-cloud, make sure:
- PostgreSQL connection string is configured
- RLS (Row Level Security) is properly set up
- JWT token from request is used to set session variables for RLS

Example middleware for RLS:

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
            # Decode JWT to get user_id and workspace_id
            payload = jwt.decode(token, verify=False)  # Supabase validates
            user_id = payload.get("sub")
            workspace_id = payload.get("workspace_id")

            # Store in request state for RLS
            request.state.user_id = user_id
            request.state.workspace_id = workspace_id
        except Exception:
            pass

    response = await call_next(request)
    return response
```

## Testing

### Local mode (SQLite)
```bash
cd /Users/julien/Documents/wik/wikumeo/projects/kurt-core
uv run kurt status
```
✅ Works!

### Cloud mode (once kurt-cloud is updated)
```bash
cd /Users/julien/Documents/wik/wikumeo/projects/kurt-demo
uv run kurt status
```

Expected flow:
1. CLI detects `DATABASE_URL="kurt"` in config
2. Calls `get_api_base_url()` → `https://kurt-cloud.vercel.app`
3. Calls `get_auth_token()` → JWT from `~/.kurt/credentials.json`
4. Makes HTTP GET to `/api/status` with Bearer token
5. Kurt-cloud backend imports `from kurt.status.api import router`
6. Router calls `get_status_data(session)` with PostgreSQL session
7. Returns JSON response to CLI
8. CLI formats and displays

## Benefits

✅ **Single source of truth** - SQL queries in `queries.py` used everywhere
✅ **No PostgREST emulation** - Direct PostgreSQL on backend
✅ **Clean separation** - CLI, queries, and API in dedicated module
✅ **Easy to maintain** - All status logic in `src/kurt/status/`
✅ **Scalable pattern** - Same structure for all future features

## Next Steps

1. Update kurt-cloud to import and mount the status router
2. Test `kurt status` in cloud mode from kurt-demo
3. Apply this pattern to other commands:
   - `kurt content list` → `src/kurt/documents/api.py`
   - `kurt workflows list` → `src/kurt/workflows/api.py`
   - etc.
