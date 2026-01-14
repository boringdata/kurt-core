"""Kurt Cloud CLI - Authentication, workspace management, and team collaboration."""

import click
from rich.console import Console

console = Console()


@click.group(name="cloud")
def cloud_group():
    """Kurt Cloud operations - authentication and team collaboration.

    Login to sync your local Kurt data with a shared PostgreSQL database.
    Team members share a workspace and can collaborate on content.

    Examples:
        kurt cloud login
        kurt cloud status
        kurt cloud invite user@example.com
    """
    pass


# =============================================================================
# Authentication Commands (delegate to auth module)
# =============================================================================


@cloud_group.command(name="login")
def login_cmd():
    """Login to Kurt Cloud via browser.

    Opens the Kurt Cloud login page in your browser.
    After authentication, credentials are saved locally.

    Example:
        kurt cloud login
    """
    import json
    import time
    import urllib.request
    import webbrowser

    from kurt.cli.auth.credentials import Credentials, get_cloud_api_url, save_credentials

    cloud_url = get_cloud_api_url()

    # Step 1: Create CLI session
    console.print("[dim]Creating login session...[/dim]")
    try:
        req = urllib.request.Request(f"{cloud_url}/auth/cli-session", method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            session_data = json.loads(resp.read().decode())
    except Exception as e:
        console.print(f"[red]Failed to create login session: {e}[/red]")
        raise click.Abort()

    session_id = session_data["session_id"]
    login_url = session_data["login_url"]

    # Step 2: Open browser
    console.print()
    console.print("[bold]Opening browser for login...[/bold]")
    console.print("[dim]If browser doesn't open, visit:[/dim]")
    console.print(f"  {login_url}")
    console.print()

    webbrowser.open(login_url)

    # Step 3: Poll for completion
    console.print("[dim]Waiting for authentication...[/dim]")

    timeout = 600  # 10 minutes
    poll_interval = 2  # seconds
    start = time.time()

    while time.time() - start < timeout:
        time.sleep(poll_interval)

        try:
            req = urllib.request.Request(f"{cloud_url}/auth/cli-session/{session_id}")
            with urllib.request.urlopen(req, timeout=10) as resp:
                status_data = json.loads(resp.read().decode())
        except Exception:
            continue  # Network error, retry

        status = status_data.get("status")

        if status == "completed":
            # Success! Save credentials
            expires_at = int(time.time()) + status_data.get("expires_in", 3600)

            # Get workspace_id from local config if available
            workspace_id = None
            try:
                from kurt.config import config_file_exists, get_config

                if config_file_exists():
                    config = get_config()
                    workspace_id = config.WORKSPACE_ID
            except Exception:
                pass

            creds = Credentials(
                access_token=status_data["access_token"],
                refresh_token=status_data.get("refresh_token", ""),
                user_id=status_data.get("user_id", ""),
                email=status_data.get("email"),
                workspace_id=workspace_id,
                expires_at=expires_at,
            )
            save_credentials(creds)

            console.print()
            console.print(f"[green]✓ Logged in as {creds.email or creds.user_id}[/green]")
            console.print(f"[dim]User ID: {creds.user_id}[/dim]")
            if workspace_id:
                console.print(f"[dim]Workspace: {workspace_id}[/dim]")
            return

        elif status == "expired":
            console.print("[red]Login session expired. Please try again.[/red]")
            raise click.Abort()

        # status == "pending", continue polling

    console.print("[red]Authentication timed out. Please try again.[/red]")
    raise click.Abort()


@cloud_group.command(name="logout")
def logout_cmd():
    """Logout from Kurt Cloud.

    Removes stored credentials from ~/.kurt/credentials.json.

    Example:
        kurt cloud logout
    """
    from kurt.cli.auth.credentials import clear_credentials, load_credentials

    creds = load_credentials()
    if creds is None:
        console.print("[yellow]Not logged in.[/yellow]")
        return

    clear_credentials()
    console.print("[green]✓ Logged out successfully.[/green]")


@cloud_group.command(name="status")
def status_cmd():
    """Show authentication and workspace status.

    Displays:
    - Login status and user info
    - Current workspace ID
    - Database connection mode

    Example:
        kurt cloud status
    """
    from kurt.cli.auth.credentials import load_credentials
    from kurt.config import config_file_exists, get_config
    from kurt.db import get_mode

    console.print()
    console.print("[bold]Kurt Cloud Status[/bold]")
    console.print()

    # Auth status
    creds = load_credentials()
    if creds:
        console.print("[green]✓ Authenticated[/green]")
        console.print(f"  Email: {creds.email or 'N/A'}")
        console.print(f"  User ID: {creds.user_id}")
        if creds.is_expired():
            console.print("  Token: [yellow]expired (will refresh on next use)[/yellow]")
        else:
            console.print("  Token: [green]active[/green]")
    else:
        console.print("[yellow]Not logged in[/yellow]")
        console.print("[dim]Run 'kurt cloud login' to authenticate[/dim]")

    console.print()

    # Workspace status
    if config_file_exists():
        config = get_config()
        if config.WORKSPACE_ID:
            console.print(f"Workspace ID: {config.WORKSPACE_ID}")
        else:
            console.print("Workspace ID: [yellow]not set[/yellow]")

        # Database mode
        mode = get_mode()
        mode_display = {
            "local_sqlite": "Local SQLite (.kurt/kurt.sqlite)",
            "local_postgres": "Shared PostgreSQL",
            "cloud_postgres": "Kurt Cloud (managed)",
        }.get(mode, mode)
        console.print(f"Database: {mode_display}")

        # Show masked DATABASE_URL if set
        if config.DATABASE_URL:
            url = config.DATABASE_URL
            if "://" in url and "@" in url:
                parts = url.split("@")
                prefix = parts[0]
                if ":" in prefix.split("://")[1]:
                    user_part = prefix.split("://")[1].split(":")[0]
                    scheme = prefix.split("://")[0]
                    masked = f"{scheme}://{user_part}:***@{parts[1]}"
                else:
                    masked = url
            else:
                masked = url
            console.print(f"  URL: {masked}")
    else:
        console.print("[yellow]No kurt.config found[/yellow]")
        console.print("[dim]Run 'kurt init' to initialize a project[/dim]")


@cloud_group.command(name="whoami")
def whoami_cmd():
    """Show current user info from Kurt Cloud.

    Fetches fresh user data from the server.

    Example:
        kurt cloud whoami
    """
    import time

    from kurt.cli.auth.commands import get_user_info, refresh_access_token
    from kurt.cli.auth.credentials import Credentials, load_credentials, save_credentials

    creds = load_credentials()
    if creds is None:
        console.print("[red]Not logged in.[/red]")
        console.print("[dim]Run 'kurt cloud login' first.[/dim]")
        raise click.Abort()

    # Refresh token if expired
    if creds.is_expired() and creds.refresh_token:
        console.print("[dim]Token expired, refreshing...[/dim]")
        result = refresh_access_token(creds.refresh_token)
        if result:
            creds = Credentials(
                access_token=result["access_token"],
                refresh_token=result.get("refresh_token", creds.refresh_token),
                user_id=result.get("user_id", creds.user_id),
                email=result.get("email", creds.email),
                workspace_id=creds.workspace_id,
                expires_at=int(time.time()) + result.get("expires_in", 3600),
            )
            save_credentials(creds)
        else:
            console.print("[red]Token refresh failed.[/red]")
            console.print("[dim]Please run 'kurt cloud login' again.[/dim]")
            raise click.Abort()

    try:
        user_info = get_user_info(creds.access_token)
    except click.ClickException as e:
        console.print(f"[red]{e.message}[/red]")
        raise click.Abort()

    console.print()
    console.print(f"[bold]User ID:[/bold] {user_info['user_id']}")
    console.print(f"[bold]Email:[/bold] {user_info.get('email', 'N/A')}")


# =============================================================================
# Workspace Commands
# =============================================================================


@cloud_group.command(name="invite")
@click.argument("email")
@click.option(
    "--role",
    "-r",
    type=click.Choice(["member", "admin"]),
    default="member",
    help="Role for the invited user",
)
def invite_cmd(email: str, role: str):
    """Invite a user to your workspace.

    Sends an invite to the specified email address.
    They can accept by logging in and running 'kurt cloud join'.

    Example:
        kurt cloud invite user@example.com
        kurt cloud invite user@example.com --role admin
    """
    import json
    import urllib.request

    from kurt.cli.auth.credentials import get_cloud_api_url, load_credentials
    from kurt.config import config_file_exists, get_config

    # Check auth
    creds = load_credentials()
    if creds is None:
        console.print("[red]Not logged in.[/red]")
        console.print("[dim]Run 'kurt cloud login' first.[/dim]")
        raise click.Abort()

    # Check workspace
    if not config_file_exists():
        console.print("[red]No kurt.config found.[/red]")
        console.print("[dim]Run 'kurt init' first.[/dim]")
        raise click.Abort()

    config = get_config()
    workspace_id = config.WORKSPACE_ID

    if not workspace_id:
        console.print("[red]No WORKSPACE_ID in kurt.config.[/red]")
        console.print("[dim]Run 'kurt init' to generate one.[/dim]")
        raise click.Abort()

    # Call the workspace API to invite
    cloud_url = get_cloud_api_url()
    url = f"{cloud_url}/api/v1/workspaces/{workspace_id}/members"

    data = json.dumps({"email": email, "role": role}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {creds.access_token}")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())

        console.print()
        console.print(f"[green]✓ Invited {email} to workspace[/green]")
        console.print(f"  Role: {result.get('role', role)}")
        console.print(f"  Status: {result.get('status', 'pending')}")
        console.print()
        console.print("[dim]They can accept by:[/dim]")
        console.print("  1. Run 'kurt cloud login'")
        console.print(f"  2. Run 'kurt cloud join {workspace_id}'")

    except urllib.error.HTTPError as e:
        try:
            error_body = json.loads(e.read().decode())
            detail = error_body.get("detail", str(e))
        except Exception:
            detail = str(e)
        console.print(f"[red]Failed to invite: {detail}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Failed to invite: {e}[/red]")
        raise click.Abort()


@cloud_group.command(name="use")
@click.argument("workspace_id")
def use_cmd(workspace_id: str):
    """Switch to a different workspace.

    Updates your local config to use the specified workspace.
    You must be a member of the workspace (run 'kurt cloud workspaces' first).

    Example:
        kurt cloud use abc123-def456-...
    """
    import json
    import re
    import urllib.request

    from kurt.cli.auth.credentials import (
        Credentials,
        get_cloud_api_url,
        load_credentials,
        save_credentials,
    )
    from kurt.config import config_file_exists, get_config_path

    # Check auth
    creds = load_credentials()
    if creds is None:
        console.print("[red]Not logged in.[/red]")
        console.print("[dim]Run 'kurt cloud login' first.[/dim]")
        raise click.Abort()

    # Verify user has access to this workspace
    cloud_url = get_cloud_api_url()
    url = f"{cloud_url}/api/v1/workspaces/{workspace_id}"

    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {creds.access_token}")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            workspace = json.loads(resp.read().decode())

    except urllib.error.HTTPError as e:
        if e.code == 404:
            console.print("[red]Workspace not found or you don't have access.[/red]")
            console.print("[dim]Run 'kurt cloud workspaces' to see available workspaces.[/dim]")
        else:
            try:
                error_body = json.loads(e.read().decode())
                detail = error_body.get("detail", str(e))
            except Exception:
                detail = str(e)
            console.print(f"[red]Failed: {detail}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Failed: {e}[/red]")
        raise click.Abort()

    # Update local config file
    if config_file_exists():
        config_path = get_config_path()
        content = config_path.read_text()

        if re.search(r"^WORKSPACE_ID\s*=", content, re.MULTILINE):
            content = re.sub(
                r"^WORKSPACE_ID\s*=.*$",
                f'WORKSPACE_ID="{workspace_id}"',
                content,
                flags=re.MULTILINE,
            )
        else:
            content += f'\nWORKSPACE_ID="{workspace_id}"\n'

        config_path.write_text(content)

    # Update credentials with new workspace_id
    creds = Credentials(
        access_token=creds.access_token,
        refresh_token=creds.refresh_token,
        user_id=creds.user_id,
        email=creds.email,
        workspace_id=workspace_id,
        expires_at=creds.expires_at,
    )
    save_credentials(creds)

    console.print()
    console.print(f"[green]✓ Switched to workspace: {workspace.get('name', workspace_id)}[/green]")
    console.print(f"  Role: {workspace.get('role', 'member')}")
    console.print(f"  ID: {workspace_id}")


@cloud_group.command(name="workspaces")
def workspaces_cmd():
    """List your workspaces.

    Shows all workspaces you own or are a member of.
    Pending invites are automatically accepted.

    Example:
        kurt cloud workspaces
    """
    import json
    import urllib.request

    from kurt.cli.auth.credentials import get_cloud_api_url, load_credentials
    from kurt.config import config_file_exists, get_config

    # Check auth
    creds = load_credentials()
    if creds is None:
        console.print("[red]Not logged in.[/red]")
        console.print("[dim]Run 'kurt cloud login' first.[/dim]")
        raise click.Abort()

    # Get current workspace from config
    current_workspace_id = None
    if config_file_exists():
        config = get_config()
        current_workspace_id = config.WORKSPACE_ID

    # Call the workspace API
    cloud_url = get_cloud_api_url()
    url = f"{cloud_url}/api/v1/workspaces"

    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {creds.access_token}")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            workspaces = json.loads(resp.read().decode())

    except urllib.error.HTTPError as e:
        try:
            error_body = json.loads(e.read().decode())
            detail = error_body.get("detail", str(e))
        except Exception:
            detail = str(e)
        console.print(f"[red]Failed to list workspaces: {detail}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Failed to list workspaces: {e}[/red]")
        raise click.Abort()

    if not workspaces:
        console.print()
        console.print("[yellow]No workspaces found.[/yellow]")
        console.print("[dim]Create one with 'kurt init' or ask someone to invite you.[/dim]")
        return

    console.print()
    console.print("[bold]Your Workspaces[/bold]")
    console.print()

    for ws in workspaces:
        role = ws.get("role", "member")
        name = ws.get("name", "Unnamed")
        ws_id = ws.get("id", "")

        role_color = {"owner": "green", "admin": "blue", "member": "dim"}.get(role, "dim")

        # Mark current workspace
        current_marker = " [green]← current[/green]" if ws_id == current_workspace_id else ""

        console.print(f"  [{role_color}]{role:6}[/{role_color}]  {name}{current_marker}")
        console.print(f"          [dim]{ws_id}[/dim]")
        console.print()

    console.print("[dim]Use 'kurt cloud use <workspace_id>' to switch workspaces[/dim]")


@cloud_group.command(name="members")
def members_cmd():
    """List members of the current workspace.

    Shows all members and their roles.

    Example:
        kurt cloud members
    """
    import json
    import urllib.request

    from kurt.cli.auth.credentials import get_cloud_api_url, load_credentials
    from kurt.config import config_file_exists, get_config

    # Check auth
    creds = load_credentials()
    if creds is None:
        console.print("[red]Not logged in.[/red]")
        console.print("[dim]Run 'kurt cloud login' first.[/dim]")
        raise click.Abort()

    # Get current workspace from config
    if not config_file_exists():
        console.print("[red]No kurt.config found.[/red]")
        console.print("[dim]Run 'kurt init' first.[/dim]")
        raise click.Abort()

    config = get_config()
    workspace_id = config.WORKSPACE_ID

    if not workspace_id:
        console.print("[red]No WORKSPACE_ID in kurt.config.[/red]")
        console.print("[dim]Run 'kurt cloud workspaces' and 'kurt cloud use <id>'.[/dim]")
        raise click.Abort()

    # Call the workspace API
    cloud_url = get_cloud_api_url()
    url = f"{cloud_url}/api/v1/workspaces/{workspace_id}/members"

    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {creds.access_token}")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            members = json.loads(resp.read().decode())

    except urllib.error.HTTPError as e:
        try:
            error_body = json.loads(e.read().decode())
            detail = error_body.get("detail", str(e))
        except Exception:
            detail = str(e)
        console.print(f"[red]Failed to list members: {detail}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Failed to list members: {e}[/red]")
        raise click.Abort()

    if not members:
        console.print()
        console.print("[yellow]No members found.[/yellow]")
        return

    console.print()
    console.print("[bold]Workspace Members[/bold]")
    console.print()

    for m in members:
        role = m.get("role", "member")
        email = m.get("email", "")
        status = m.get("status", "active")

        role_color = {"owner": "green", "admin": "blue", "member": "dim"}.get(role, "dim")
        status_marker = " [yellow](pending)[/yellow]" if status == "pending" else ""

        console.print(f"  [{role_color}]{role:6}[/{role_color}]  {email}{status_marker}")

    console.print()
    console.print("[dim]Invite with 'kurt cloud invite <email>'[/dim]")
