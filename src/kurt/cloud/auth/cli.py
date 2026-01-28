"""Authentication CLI commands for Kurt Cloud."""

from __future__ import annotations

import time

import click

from kurt.cloud.auth.api import get_user_info, refresh_access_token
from kurt.cloud.auth.credentials import (
    Credentials,
    clear_credentials,
    get_workspace_id_from_config,
    load_credentials,
    save_credentials,
)


@click.group()
def auth():
    """Authenticate with Kurt Cloud.

    Login to sync your local Kurt data with a shared Postgres database.
    """
    pass


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


# Note: login command is now in kurt.cloud.cli (uses browser + polling)
auth.add_command(logout)
auth.add_command(status)
auth.add_command(whoami)
