"""Authentication commands for Kurt Cloud."""

from __future__ import annotations

import json
import time
import urllib.request
from typing import Optional

import click

from .credentials import (
    Credentials,
    clear_credentials,
    get_cloud_api_url,
    load_credentials,
    save_credentials,
)


def get_user_info(access_token: str) -> dict:
    """Get user info from Kurt Cloud using the access token."""
    cloud_url = get_cloud_api_url()
    url = f"{cloud_url}/auth/verify"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {access_token}")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        raise click.ClickException(f"Failed to get user info: {e}")


def refresh_access_token(refresh_token: str) -> Optional[dict]:
    """Refresh the access token via Kurt Cloud API."""
    cloud_url = get_cloud_api_url()
    url = f"{cloud_url}/auth/refresh"
    data = json.dumps({"refresh_token": refresh_token}).encode()

    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


@click.command()
def logout() -> None:
    """Logout from Kurt Cloud.

    Removes stored credentials.
    """
    creds = load_credentials()
    if creds is None:
        click.echo("Not logged in.")
        return

    clear_credentials()
    click.echo("Logged out successfully.")


@click.command()
def status() -> None:
    """Show current authentication status.

    Displays whether you're logged in and token validity.
    """
    creds = load_credentials()
    if creds is None:
        click.echo("Not logged in.")
        click.echo("Run 'kurt cloud login' to authenticate.")
        return

    click.echo(f"Logged in as: {creds.email or creds.user_id}")
    click.echo(f"User ID: {creds.user_id}")

    # Workspace comes from project config (kurt.config), not credentials
    from kurt.cli.auth.credentials import get_workspace_id_from_config

    workspace_id = get_workspace_id_from_config()
    if workspace_id:
        click.echo(f"Workspace: {workspace_id}")

    if creds.is_expired():
        click.echo("Status: Token expired (will refresh on next use)")
    else:
        click.echo("Status: Active")


@click.command()
def whoami() -> None:
    """Show current user info.

    Fetches fresh user data from Kurt Cloud.
    """
    creds = load_credentials()
    if creds is None:
        raise click.ClickException("Not logged in. Run 'kurt cloud login' first.")

    # Refresh token if expired
    if creds.is_expired() and creds.refresh_token:
        click.echo("Token expired, refreshing...")
        result = refresh_access_token(creds.refresh_token)
        if result:
            creds = Credentials(
                access_token=result["access_token"],
                refresh_token=result.get("refresh_token", creds.refresh_token),
                user_id=result.get("user_id", creds.user_id),
                email=result.get("email", creds.email),
                expires_at=int(time.time()) + result.get("expires_in", 3600),
            )
            save_credentials(creds)
        else:
            raise click.ClickException("Token refresh failed. Please run 'kurt cloud login' again.")

    # Fetch current user info
    user_info = get_user_info(creds.access_token)

    click.echo(f"User ID: {user_info['user_id']}")
    click.echo(f"Email: {user_info.get('email', 'N/A')}")
