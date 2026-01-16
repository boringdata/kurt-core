"""
GitHub App client for workspace repository access.

This module manages GitHub App authentication and token lifecycle:
1. Generates JWT tokens for authenticating as the app
2. Exchanges installation IDs for installation tokens
3. Auto-refreshes tokens before expiration
4. Provides workspace-scoped GitHub API access

Environment Variables:
    GITHUB_APP_ID: GitHub App ID (e.g., "123456")
    GITHUB_APP_PRIVATE_KEY: PEM-formatted private key (multiline string)
    GITHUB_APP_PRIVATE_KEY_PATH: Path to PEM file (alternative to inline key)

Usage:
    from kurt.github import github_app

    # Get token for workspace (auto-refreshes if needed)
    token = await github_app.get_workspace_token(workspace_id)

    # Use token for GitHub API
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/repos/owner/repo/contents/path",
            headers={"Authorization": f"Bearer {token}"}
        )
"""

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

try:
    import httpx
    import jwt

    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False


class GitHubAppClient:
    """Client for GitHub App API operations."""

    def __init__(
        self,
        app_id: Optional[str] = None,
        private_key: Optional[str] = None,
        private_key_path: Optional[str] = None,
    ):
        """
        Initialize GitHub App client.

        Args:
            app_id: GitHub App ID (defaults to GITHUB_APP_ID env var)
            private_key: PEM-formatted private key (defaults to GITHUB_APP_PRIVATE_KEY)
            private_key_path: Path to PEM file (defaults to GITHUB_APP_PRIVATE_KEY_PATH)

        Raises:
            RuntimeError: If dependencies are missing (httpx, PyJWT)
            ValueError: If credentials are not provided
        """
        if not DEPS_AVAILABLE:
            raise RuntimeError(
                "GitHub App integration requires: pip install httpx PyJWT cryptography"
            )

        # Load configuration
        self.app_id = app_id or os.environ.get("GITHUB_APP_ID")
        if not self.app_id:
            raise ValueError("GITHUB_APP_ID must be set")

        # Load private key (prefer inline, fallback to file)
        if private_key:
            self.private_key = private_key
        elif private_key_path:
            self.private_key = Path(private_key_path).read_text()
        elif os.environ.get("GITHUB_APP_PRIVATE_KEY"):
            self.private_key = os.environ["GITHUB_APP_PRIVATE_KEY"]
        elif os.environ.get("GITHUB_APP_PRIVATE_KEY_PATH"):
            self.private_key = Path(os.environ["GITHUB_APP_PRIVATE_KEY_PATH"]).read_text()
        else:
            raise ValueError(
                "GitHub App private key must be provided via GITHUB_APP_PRIVATE_KEY "
                "or GITHUB_APP_PRIVATE_KEY_PATH"
            )

    def generate_jwt(self) -> str:
        """
        Generate JWT for authenticating as GitHub App.

        The JWT is valid for 10 minutes and allows the app to request
        installation tokens.

        Returns:
            JWT token string

        GitHub API docs:
            https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-json-web-token-jwt-for-a-github-app
        """
        now = int(time.time())
        payload = {
            "iat": now - 60,  # Issued at (60 seconds ago for clock drift)
            "exp": now + 600,  # Expires in 10 minutes
            "iss": self.app_id,  # Issuer = GitHub App ID
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    async def get_installation_token(self, installation_id: int) -> dict:
        """
        Get installation access token for a GitHub App installation.

        Installation tokens allow the app to act on behalf of the installation
        (i.e., access the repos where the app is installed).

        Args:
            installation_id: GitHub App installation ID

        Returns:
            dict with keys:
                - token: Installation access token
                - expires_at: Token expiration time (datetime)

        Raises:
            httpx.HTTPStatusError: If API request fails

        GitHub API docs:
            https://docs.github.com/en/rest/apps/apps?apiVersion=2022-11-28#create-an-installation-access-token-for-an-app
        """
        app_jwt = self.generate_jwt()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.github.com/app/installations/{installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {app_jwt}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

            return {
                "token": data["token"],
                "expires_at": datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00")),
            }

    async def get_workspace_token(self, workspace_id: str) -> str:
        """
        Get valid GitHub token for workspace.

        This method automatically refreshes the token if it's expired or missing.
        The token is stored in the workspace record for reuse.

        Args:
            workspace_id: Workspace ID

        Returns:
            Installation access token (valid for ~1 hour)

        Raises:
            ValueError: If workspace doesn't have GitHub App installed
            RuntimeError: If database is not available
        """
        from kurt.db import managed_session
        from kurt.db.workspace_models import Workspace

        with managed_session() as session:
            workspace = session.get(Workspace, workspace_id)

            if not workspace:
                raise ValueError(f"Workspace not found: {workspace_id}")

            if not workspace.github_installation_id:
                raise ValueError(
                    f"GitHub App not installed for workspace {workspace.slug}. "
                    "User must install the app first."
                )

            # Check if token needs refresh (refresh 5 minutes before expiry)
            now = datetime.now(timezone.utc)
            needs_refresh = (
                not workspace.github_installation_token
                or not workspace.github_installation_token_expires_at
                or workspace.github_installation_token_expires_at <= now + timedelta(minutes=5)
            )

            if needs_refresh:
                # Refresh token
                token_data = await self.get_installation_token(workspace.github_installation_id)
                workspace.github_installation_token = token_data["token"]
                workspace.github_installation_token_expires_at = token_data["expires_at"]
                session.add(workspace)
                session.commit()
                session.refresh(workspace)

            return workspace.github_installation_token

    async def get_installation_info(self, installation_id: int) -> dict:
        """
        Get information about a GitHub App installation.

        Args:
            installation_id: GitHub App installation ID

        Returns:
            dict with installation metadata (account, repositories, etc.)

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        app_jwt = self.generate_jwt()

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/app/installations/{installation_id}",
                headers={
                    "Authorization": f"Bearer {app_jwt}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

    async def list_installation_repositories(self, installation_id: int) -> list[dict]:
        """
        List all repositories accessible by an installation.

        Args:
            installation_id: GitHub App installation ID

        Returns:
            List of repository dicts with keys: id, name, full_name, etc.

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        # Get installation token first
        token_data = await self.get_installation_token(installation_id)
        token = token_data["token"]

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/installation/repositories",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("repositories", [])


# Singleton instance for application-wide use
# This will be None if credentials are not configured
try:
    github_app = GitHubAppClient()
except (ValueError, RuntimeError):
    # Credentials not configured or dependencies missing
    # This is OK for local development or when GitHub integration is not needed
    github_app = None
