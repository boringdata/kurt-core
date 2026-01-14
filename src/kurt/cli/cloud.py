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
@click.option(
    "--email",
    "-e",
    prompt="Email address",
    help="Your email address for magic link login",
)
def login_cmd(email: str):
    """Login to Kurt Cloud via email magic link.

    Sends a magic link to your email. Click the link to authenticate.
    Your credentials are stored locally for future CLI use.

    After login, your user_id is used to tag all data you create.

    Example:
        kurt cloud login
        kurt cloud login --email user@example.com
    """
    import http.server
    import threading
    import time

    from kurt.cli.auth.commands import (
        MagicLinkCallbackHandler,
        get_supabase_url,
        get_user_info,
        send_magic_link,
    )
    from kurt.cli.auth.credentials import Credentials, get_auth_callback_url, save_credentials

    url = get_supabase_url()

    # Start local callback server
    port = 9876  # Fixed port for local callback
    # Use hosted callback URL - it will redirect tokens back to localhost
    redirect_uri = get_auth_callback_url(cli_port=port)

    try:
        server = http.server.HTTPServer(("localhost", port), MagicLinkCallbackHandler)
    except OSError as e:
        if "Address already in use" in str(e):
            console.print(f"[red]Port {port} is already in use.[/red]")
            console.print("[dim]Please close other applications using this port.[/dim]")
            raise click.Abort()
        raise

    server.auth_result = None
    server.auth_error = None

    # Send magic link
    console.print(f"Sending magic link to [cyan]{email}[/cyan]...")
    try:
        send_magic_link(email, url, redirect_uri)
    except click.ClickException as e:
        console.print(f"[red]{e.message}[/red]")
        raise click.Abort()

    console.print("[green]✓[/green] Check your email and click the magic link.")
    console.print("[dim]Waiting for authentication (timeout: 5 minutes)...[/dim]")

    # Handle requests in background
    def handle_requests():
        while server.auth_result is None and server.auth_error is None:
            server.handle_request()

    thread = threading.Thread(target=handle_requests)
    thread.daemon = True
    thread.start()

    # Wait with timeout
    timeout = 300
    start = time.time()
    while (
        server.auth_result is None and server.auth_error is None and time.time() - start < timeout
    ):
        time.sleep(0.5)

    if server.auth_error:
        console.print(f"[red]Authentication failed: {server.auth_error}[/red]")
        raise click.Abort()

    if server.auth_result is None:
        console.print("[red]Authentication timed out. Please try again.[/red]")
        raise click.Abort()

    # Get user info
    access_token = server.auth_result["access_token"]
    try:
        user_info = get_user_info(access_token, url)
    except click.ClickException as e:
        console.print(f"[red]{e.message}[/red]")
        raise click.Abort()

    # Calculate expiry timestamp
    expires_at = int(time.time()) + server.auth_result["expires_in"]

    # Get workspace_id from local config if available
    workspace_id = None
    try:
        from kurt.config import config_file_exists, get_config

        if config_file_exists():
            config = get_config()
            workspace_id = config.WORKSPACE_ID
    except Exception:
        pass

    # Save credentials
    creds = Credentials(
        access_token=access_token,
        refresh_token=server.auth_result["refresh_token"],
        user_id=user_info["id"],
        email=user_info.get("email"),
        workspace_id=workspace_id,
        expires_at=expires_at,
        supabase_url=url,
    )
    save_credentials(creds)

    console.print()
    console.print(f"[green]✓ Logged in as {creds.email or creds.user_id}[/green]")
    console.print(f"[dim]User ID: {creds.user_id}[/dim]")
    if workspace_id:
        console.print(f"[dim]Workspace: {workspace_id}[/dim]")


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
    if creds.is_expired() and creds.refresh_token and creds.supabase_url:
        console.print("[dim]Token expired, refreshing...[/dim]")
        result = refresh_access_token(creds.refresh_token, creds.supabase_url)
        if result:
            creds = Credentials(
                access_token=result["access_token"],
                refresh_token=result.get("refresh_token", creds.refresh_token),
                user_id=creds.user_id,
                email=creds.email,
                workspace_id=creds.workspace_id,
                expires_at=int(time.time()) + result.get("expires_in", 3600),
                supabase_url=creds.supabase_url,
            )
            save_credentials(creds)
        else:
            console.print("[red]Token refresh failed.[/red]")
            console.print("[dim]Please run 'kurt cloud login' again.[/dim]")
            raise click.Abort()

    if not creds.supabase_url:
        console.print("[red]Supabase URL not stored.[/red]")
        console.print("[dim]Please login again.[/dim]")
        raise click.Abort()

    try:
        user_info = get_user_info(creds.access_token, creds.supabase_url)
    except click.ClickException as e:
        console.print(f"[red]{e.message}[/red]")
        raise click.Abort()

    console.print()
    console.print(f"[bold]User ID:[/bold] {user_info['id']}")
    console.print(f"[bold]Email:[/bold] {user_info.get('email', 'N/A')}")

    if user_info.get("user_metadata"):
        meta = user_info["user_metadata"]
        if meta.get("full_name"):
            console.print(f"[bold]Name:[/bold] {meta['full_name']}")


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

    The invited user must have a Kurt Cloud account.
    They will be added to your current workspace.

    Example:
        kurt cloud invite user@example.com
        kurt cloud invite user@example.com --role admin
    """
    from kurt.cli.auth.credentials import load_credentials
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

    # For now, show instructions (full implementation requires cloud API)
    console.print()
    console.print(f"[bold]Inviting {email} to workspace[/bold]")
    console.print()
    console.print("[yellow]Note: Full invite system coming soon.[/yellow]")
    console.print()
    console.print("For now, share these values with your team member:")
    console.print()
    console.print(f'  WORKSPACE_ID="{workspace_id}"')
    if config.DATABASE_URL:
        # Mask password for display
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
        console.print(f'  DATABASE_URL="{masked}"')
        console.print()
        console.print("[dim]Share the actual DATABASE_URL securely (contains password)[/dim]")
    console.print()
    console.print("They should:")
    console.print("  1. Run 'kurt cloud login' with their email")
    console.print("  2. Add WORKSPACE_ID and DATABASE_URL to their kurt.config")
    console.print("  3. Run 'kurt admin migrate apply'")


@cloud_group.command(name="join")
@click.argument("workspace_id")
def join_cmd(workspace_id: str):
    """Join an existing workspace.

    Updates your kurt.config with the shared workspace ID.
    You must already have DATABASE_URL configured.

    Example:
        kurt cloud join abc123-def456-...
    """
    from kurt.cli.auth.credentials import Credentials, load_credentials, save_credentials
    from kurt.config import config_file_exists, get_config_path

    # Check auth
    creds = load_credentials()
    if creds is None:
        console.print("[red]Not logged in.[/red]")
        console.print("[dim]Run 'kurt cloud login' first.[/dim]")
        raise click.Abort()

    # Check config exists
    if not config_file_exists():
        console.print("[red]No kurt.config found.[/red]")
        console.print("[dim]Run 'kurt init' first, then set DATABASE_URL.[/dim]")
        raise click.Abort()

    # Update workspace in config file
    config_path = get_config_path()
    content = config_path.read_text()

    # Replace or add WORKSPACE_ID
    import re

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
        supabase_url=creds.supabase_url,
    )
    save_credentials(creds)

    console.print()
    console.print(f"[green]✓ Joined workspace: {workspace_id}[/green]")
    console.print()
    console.print("[dim]Next steps:[/dim]")
    console.print("  1. Ensure DATABASE_URL is set in kurt.config")
    console.print("  2. Run 'kurt admin migrate apply'")
    console.print("  3. Run 'kurt db status' to verify")
