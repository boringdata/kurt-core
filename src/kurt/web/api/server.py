"""Kurt Web API - FastAPI application.

This module creates the FastAPI app and includes all route modules.
Route handlers are organized into separate modules under routes/.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from kurt.cloud.tenant import is_cloud_mode
from kurt.web.api.auth import auth_middleware_setup
from kurt.web.api.routes.approval import router as approval_router
from kurt.web.api.routes.claude import router as claude_router
from kurt.web.api.routes.documents import router as documents_router
from kurt.web.api.routes.files import router as files_router
from kurt.web.api.routes.system import router as system_router
from kurt.web.api.routes.websockets import router as websockets_router
from kurt.web.api.routes.workflows import router as workflows_router

# Ensure working directory is project root (when running from worktree)
# Skip in cloud deployments where filesystem may be read-only
try:
    project_root = Path(os.environ.get("KURT_PROJECT_ROOT", Path.cwd())).expanduser().resolve()
    if project_root.exists():
        os.chdir(project_root)
except Exception:
    # Skip chdir in environments where it's not needed (e.g., Vercel)
    pass


app = FastAPI(title="Kurt Web API")

allowed_origins_raw = os.environ.get("KURT_WEB_ORIGINS") or os.environ.get(
    "KURT_WEB_ORIGIN",
    "http://localhost:5173,http://127.0.0.1:5173",
)
allowed_origins = [origin.strip() for origin in allowed_origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add auth middleware for cloud mode (DATABASE_URL="kurt")
if is_cloud_mode():
    app.middleware("http")(auth_middleware_setup)

# --- Include route modules ---
app.include_router(system_router)
app.include_router(documents_router)
app.include_router(files_router)
app.include_router(approval_router)
app.include_router(claude_router)
app.include_router(workflows_router)
app.include_router(websockets_router)


# --- Production static file serving ---
# Detect if built frontend assets exist
CLIENT_DIST = Path(__file__).parent.parent / "client" / "dist"

if CLIENT_DIST.exists() and (CLIENT_DIST / "index.html").exists():
    # Mount assets directory for JS/CSS bundles
    assets_dir = CLIENT_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


# --- SPA catch-all route for production ---
# This must be registered LAST to not interfere with API routes
if CLIENT_DIST.exists() and (CLIENT_DIST / "index.html").exists():

    @app.get("/{path:path}")
    async def serve_spa(path: str = ""):
        """Serve the SPA for all non-API routes."""
        # Don't serve SPA for API or WebSocket routes
        if path.startswith("api/") or path.startswith("ws/"):
            raise HTTPException(status_code=404, detail="Not found")
        # Serve index.html for client-side routing
        return FileResponse(str(CLIENT_DIST / "index.html"))
