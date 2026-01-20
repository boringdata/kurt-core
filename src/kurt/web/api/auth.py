"""Authentication middleware for Kurt Cloud mode.

This module provides JWT verification and tenant context setup
for cloud deployments with Supabase authentication.
"""

from __future__ import annotations

import json
import os
import urllib.request
from functools import lru_cache
from typing import Any, Optional

from fastapi import HTTPException, Request

from kurt.db.tenant import is_cloud_auth_enabled  # noqa: F401 - re-exported


class AuthUser:
    """Authenticated user from JWT token."""

    def __init__(
        self,
        user_id: str,
        email: Optional[str] = None,
        workspace_id: Optional[str] = None,
        roles: Optional[list[str]] = None,
    ):
        self.user_id = user_id
        self.email = email
        self.workspace_id = workspace_id
        self.roles = roles or []

    def __repr__(self) -> str:
        return f"<AuthUser(user_id={self.user_id}, email={self.email})>"


@lru_cache(maxsize=1)
def get_supabase_config() -> dict[str, str]:
    """Get Supabase configuration from environment."""
    return {
        "url": os.environ.get("SUPABASE_URL", "").strip(),
        "anon_key": os.environ.get("SUPABASE_ANON_KEY", "").strip(),
        "jwt_secret": os.environ.get("SUPABASE_JWT_SECRET", "").strip(),
    }


def extract_bearer_token(request: Request) -> Optional[str]:
    """Extract Bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    if not auth_header.startswith("Bearer "):
        return None
    return auth_header[7:]  # Remove "Bearer " prefix


def verify_token_with_supabase(token: str) -> dict[str, Any]:
    """Verify token by calling Supabase auth API.

    This is more secure than local JWT verification as it checks
    token revocation and session validity.
    """
    config = get_supabase_config()
    if not config["url"] or not config["anon_key"]:
        raise HTTPException(
            status_code=500,
            detail="Supabase not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY.",
        )
    url = f"{config['url']}/auth/v1/user"

    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("apikey", config["anon_key"])

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        raise HTTPException(status_code=500, detail=f"Auth verification failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auth verification failed: {e}")


def get_authenticated_user(request: Request) -> Optional[AuthUser]:
    """Get authenticated user from request.

    Returns None if not in cloud mode or no token provided.
    Raises HTTPException if token is invalid.
    """
    if not is_cloud_auth_enabled():
        return None

    token = extract_bearer_token(request)
    if not token:
        return None

    # Verify token with Supabase
    user_data = verify_token_with_supabase(token)

    return AuthUser(
        user_id=user_data.get("id"),
        email=user_data.get("email"),
        workspace_id=user_data.get("user_metadata", {}).get("workspace_id"),
        roles=user_data.get("app_metadata", {}).get("roles", []),
    )


def require_authenticated_user(request: Request) -> AuthUser:
    """Require authenticated user or raise 401.

    Use this as a dependency for protected endpoints.
    """
    if not is_cloud_auth_enabled():
        raise HTTPException(
            status_code=500, detail="Auth required but KURT_CLOUD_AUTH is not enabled"
        )

    token = extract_bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Missing authentication token")

    user_data = verify_token_with_supabase(token)

    return AuthUser(
        user_id=user_data.get("id"),
        email=user_data.get("email"),
        workspace_id=user_data.get("user_metadata", {}).get("workspace_id"),
        roles=user_data.get("app_metadata", {}).get("roles", []),
    )


async def auth_middleware_setup(request: Request, call_next):
    """FastAPI middleware for authentication.

    In cloud mode:
    - Extracts JWT from Authorization header
    - Verifies token with Supabase
    - Sets tenant context (user_id, workspace_id) for RLS

    In local mode:
    - Passes through without authentication
    """
    from kurt.db.tenant import clear_workspace_context, set_workspace_context

    if not is_cloud_auth_enabled():
        # Local mode - no auth required
        response = await call_next(request)
        return response

    # Skip auth for health checks and public endpoints
    public_paths = ["/health", "/api/health", "/docs", "/openapi.json"]
    if request.url.path in public_paths:
        response = await call_next(request)
        return response

    # Extract and verify token
    token = extract_bearer_token(request)
    if token:
        try:
            user_data = verify_token_with_supabase(token)
            user_id = user_data.get("id")
            workspace_id = user_data.get("user_metadata", {}).get("workspace_id")

            # Set tenant context for this request
            set_workspace_context(
                workspace_id=workspace_id or user_id,
                user_id=user_id,
            )
        except HTTPException:
            # Token invalid - clear context and continue (will fail on protected endpoints)
            clear_workspace_context()
    else:
        clear_workspace_context()

    try:
        response = await call_next(request)
        return response
    finally:
        # Clear context after request
        clear_workspace_context()
