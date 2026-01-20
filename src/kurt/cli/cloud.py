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
    import http.server
    import threading
    import time
    import webbrowser

    from kurt.cli.auth.credentials import Credentials, get_cloud_api_url, save_credentials

    cloud_url = get_cloud_api_url()

    # Result container for the callback
    auth_result = {"tokens": None, "error": None}
    server_ready = threading.Event()

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        """Handle OAuth callback from browser."""

        def log_message(self, format, *args):
            pass  # Suppress HTTP logs

        def do_GET(self):  # noqa: N802
            """Handle GET request with tokens in query params."""
            from urllib.parse import parse_qs, urlparse

            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            if "access_token" in params:
                auth_result["tokens"] = {
                    "access_token": params["access_token"][0],
                    "refresh_token": params.get("refresh_token", [""])[0],
                    "expires_in": int(params.get("expires_in", ["3600"])[0]),
                    "user_id": params.get("user_id", [""])[0],
                    "email": params.get("email", [""])[0],
                }
            elif "error" in params:
                auth_result["error"] = params.get("error_description", params["error"])[0]
            else:
                auth_result["error"] = "No tokens received"

            # Send success response
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = """<!DOCTYPE html><html><head><title>Kurt Cloud</title>
            <style>body{font-family:system-ui;max-width:400px;margin:100px auto;text-align:center;}
            .success{color:#22c55e;}.error{color:#ef4444;}</style></head><body>
            <h1 class="success">✓ Login Successful</h1>
            <p>You can close this window and return to your terminal.</p>
            </body></html>"""
            if auth_result["error"]:
                html = html.replace("success", "error").replace(
                    "✓ Login Successful", "Login Failed"
                )
                html = html.replace("You can close this window", auth_result["error"])
            self.wfile.write(html.encode())

        def do_POST(self):  # noqa: N802
            """Handle POST request with tokens in body."""
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode()

            try:
                import json as json_module

                data = json_module.loads(body)
                auth_result["tokens"] = {
                    "access_token": data.get("access_token", ""),
                    "refresh_token": data.get("refresh_token", ""),
                    "expires_in": int(data.get("expires_in", 3600)),
                    "user_id": data.get("user_id", ""),
                    "email": data.get("email", ""),
                }
            except Exception as e:
                auth_result["error"] = str(e)

            # Send CORS headers and response
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')

        def do_OPTIONS(self):  # noqa: N802
            """Handle CORS preflight."""
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

    # Start local server
    port = 9876
    server = None
    for p in [port, port + 1, port + 2]:
        try:
            server = http.server.HTTPServer(("127.0.0.1", p), CallbackHandler)
            port = p
            break
        except OSError:
            continue

    if not server:
        console.print("[red]Failed to start local auth server (ports 9876-9878 in use)[/red]")
        raise click.Abort()

    def run_server():
        server_ready.set()
        server.handle_request()  # Handle one request then stop

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    server_ready.wait()

    # Build login URL with callback to local server
    login_url = f"{cloud_url}/auth/login-page?cli_callback=http://127.0.0.1:{port}"

    # Open browser
    console.print()
    console.print("[bold]Opening browser for login...[/bold]")
    console.print("[dim]If browser doesn't open, visit:[/dim]")
    console.print(f"  {login_url}")
    console.print()

    webbrowser.open(login_url)

    # Wait for callback
    console.print("[dim]Waiting for authentication...[/dim]")

    timeout = 300  # 5 minutes
    start = time.time()

    while time.time() - start < timeout:
        if auth_result["tokens"] or auth_result["error"]:
            break
        time.sleep(0.5)

    server.server_close()

    if auth_result["error"]:
        console.print(f"[red]Login failed: {auth_result['error']}[/red]")
        raise click.Abort()

    if not auth_result["tokens"]:
        console.print("[red]Authentication timed out. Please try again.[/red]")
        raise click.Abort()

    # Success! Save credentials
    tokens = auth_result["tokens"]
    expires_at = int(time.time()) + tokens.get("expires_in", 3600)

    # Extract user_id and email from JWT if not in params
    user_id = tokens.get("user_id", "")
    email = tokens.get("email", "")
    if not user_id or not email:
        try:
            import base64
            import json as json_module

            # Decode JWT payload (second part)
            token_parts = tokens["access_token"].split(".")
            if len(token_parts) >= 2:
                # Add proper base64 padding
                payload_b64 = token_parts[1]
                padding = 4 - len(payload_b64) % 4
                if padding != 4:
                    payload_b64 += "=" * padding
                payload = json_module.loads(base64.urlsafe_b64decode(payload_b64))
                user_id = user_id or payload.get("sub", "")
                email = email or payload.get("email", "")
        except Exception:
            pass

    # Get workspace_id from cloud (if available) or local config
    workspace_id = None
    server_workspace_id = None
    try:
        from kurt.cli.auth.commands import get_user_info

        user_info = get_user_info(tokens["access_token"])
        server_workspace_id = user_info.get("user_metadata", {}).get("workspace_id")
    except Exception:
        pass

    try:
        from kurt.config import config_file_exists, get_config_file_path, load_config

        if config_file_exists():
            import re
            import uuid as uuid_module

            config = load_config()
            workspace_id = config.WORKSPACE_ID
            config_path = get_config_file_path()
            content = config_path.read_text()
            updated = False

            if not workspace_id:
                workspace_id = server_workspace_id or str(uuid_module.uuid4())
                if re.search(r"^WORKSPACE_ID\s*=", content, re.MULTILINE):
                    content = re.sub(
                        r"^WORKSPACE_ID\s*=.*$",
                        f'WORKSPACE_ID="{workspace_id}"',
                        content,
                        flags=re.MULTILINE,
                    )
                else:
                    content += (
                        f'\n# Auto-generated workspace identifier\nWORKSPACE_ID="{workspace_id}"\n'
                    )
                updated = True

            # Enable cloud auth when DATABASE_URL is configured
            if config.DATABASE_URL:
                if re.search(r"^CLOUD_AUTH\s*=", content, re.MULTILINE):
                    content = re.sub(
                        r"^CLOUD_AUTH\s*=.*$",
                        "CLOUD_AUTH=true",
                        content,
                        flags=re.MULTILINE,
                    )
                else:
                    content += "\n# Cloud auth for shared databases\nCLOUD_AUTH=true\n"
                updated = True

            if updated:
                config_path.write_text(content)
    except Exception:
        pass

    if not workspace_id:
        workspace_id = server_workspace_id

    # Save credentials (auth only, no workspace_id - that's in kurt.config)
    creds = Credentials(
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token", ""),
        user_id=user_id,
        email=email,
        expires_at=expires_at,
    )
    save_credentials(creds)

    # Register workspace path for tracking
    if workspace_id:
        from pathlib import Path

        from kurt.cli.auth.credentials import register_workspace_path

        project_path = str(Path.cwd().resolve())
        register_workspace_path(workspace_id, project_path)

    console.print()
    console.print(f"[green]✓ Logged in as {creds.email or creds.user_id}[/green]")
    console.print(f"[dim]User ID: {creds.user_id}[/dim]")
    if workspace_id:
        console.print(f"[dim]Workspace (from config): {workspace_id}[/dim]")


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
    - Pending migrations

    Example:
        kurt cloud status
    """
    from kurt.cli.auth.credentials import load_credentials
    from kurt.config import config_file_exists, load_config
    from kurt.db import get_mode

    console.print()
    console.print("[bold]Kurt Cloud Status[/bold]")
    console.print()

    # Check for pending migrations first
    migration_info = _check_pending_migrations()
    if migration_info.get("has_pending"):
        console.print(f"[yellow]⚠ {migration_info['count']} pending database migration(s)[/yellow]")
        console.print("[dim]Run: `kurt admin migrate apply` to update the database[/dim]")
        for migration_name in migration_info.get("migrations", []):
            console.print(f"[dim]  - {migration_name}[/dim]")
        console.print()

    # Auth status - auto-refresh token if needed
    from kurt.cli.auth.credentials import ensure_fresh_token

    original_creds = load_credentials()
    creds = ensure_fresh_token()
    token_was_refreshed = (
        original_creds and creds and original_creds.access_token != creds.access_token
    )

    if creds:
        console.print("[green]✓ Authenticated[/green]")
        console.print(f"  Email: {creds.email or 'N/A'}")
        console.print(f"  User ID: {creds.user_id}")
        if creds.is_expired():
            console.print("  Token: [yellow]expired (will refresh on next use)[/yellow]")
        else:
            if token_was_refreshed:
                console.print("  Token: [green]active[/green] [dim](refreshed)[/dim]")
            else:
                console.print("  Token: [green]active[/green]")
    else:
        console.print("[yellow]Not logged in[/yellow]")
        console.print("[dim]Run 'kurt cloud login' to authenticate[/dim]")

    console.print()

    # Workspace status
    if config_file_exists():
        config = load_config()
        workspace_id = config.WORKSPACE_ID

        # If workspace_id not in config, try to get from user metadata via cloud API
        if not workspace_id and creds:
            try:
                from kurt.cli.auth.commands import get_user_info

                user_info = get_user_info(creds.access_token)
                candidate_workspace_id = user_info.get("user_metadata", {}).get(
                    "workspace_id"
                )
                if candidate_workspace_id:
                    from kurt.db.tenant import _set_workspace_id_in_config

                    if _set_workspace_id_in_config(candidate_workspace_id):
                        workspace_id = candidate_workspace_id
            except Exception:
                pass

        if workspace_id:
            console.print(f"Workspace ID: {workspace_id}")
        else:
            console.print("Workspace ID: [yellow]not set[/yellow]")

        # Database mode
        mode = get_mode()
        mode_display = {
            "sqlite": "Local SQLite (.kurt/kurt.sqlite)",
            "postgres": "Shared PostgreSQL",
            "kurt-cloud": "Kurt Cloud (managed)",
        }.get(mode, mode)
        console.print(f"Database: {mode_display}")

        # Schema version
        try:
            from kurt.db.migrations.utils import get_current_version

            schema_version = get_current_version()
            if schema_version:
                console.print(f"  Schema: {schema_version}")
        except Exception:
            pass

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

        # Fetch workspace details from cloud if in cloud mode
        if mode == "kurt-cloud" and workspace_id and creds:
            try:
                import json
                import urllib.request

                from kurt.cli.auth.credentials import get_cloud_api_url

                cloud_url = get_cloud_api_url()
                url = f"{cloud_url}/api/v1/workspaces/{workspace_id}"

                req = urllib.request.Request(url)
                req.add_header("Authorization", f"Bearer {creds.access_token}")

                with urllib.request.urlopen(req, timeout=5) as resp:
                    workspace = json.loads(resp.read().decode())

                    # Display GitHub repository if linked
                    if workspace.get("github_repo"):
                        console.print(f"  GitHub: https://github.com/{workspace['github_repo']}")
            except urllib.error.HTTPError as e:
                # Try to read error body
                try:
                    import json as json_module

                    error_body = json_module.loads(e.read().decode())
                    console.print(
                        f"  [dim]API Error ({e.code}): {error_body.get('detail', error_body)}[/dim]"
                    )
                except Exception:
                    console.print(f"  [dim]Could not fetch workspace details: HTTP {e.code}[/dim]")
            except Exception as e:
                console.print(f"  [dim]Could not fetch workspace details: {e}[/dim]")
    else:
        console.print("[yellow]No kurt.config found[/yellow]")
        console.print("[dim]Run 'kurt init' to initialize a project[/dim]")


def _check_pending_migrations() -> dict:
    """Check if there are pending database migrations."""
    try:
        from kurt.db.migrations.utils import (
            check_migrations_needed,
            get_pending_migrations,
        )

        has_pending = check_migrations_needed()
        if has_pending:
            pending = get_pending_migrations()
            return {
                "has_pending": True,
                "count": len(pending),
                "migrations": [revision_id for revision_id, _ in pending],
            }

        return {"has_pending": False, "count": 0, "migrations": []}
    except ImportError:
        return {"has_pending": False, "count": 0, "migrations": []}
    except Exception:
        return {"has_pending": False, "count": 0, "migrations": []}


@cloud_group.command(name="whoami")
def whoami_cmd():
    """Show current user info from Kurt Cloud.

    Fetches fresh user data from the server.

    Example:
        kurt cloud whoami
    """

    from kurt.cli.auth.commands import get_user_info
    from kurt.cli.auth.credentials import load_credentials

    creds = load_credentials()
    if creds is None:
        console.print("[red]Not logged in.[/red]")
        console.print("[dim]Run 'kurt cloud login' first.[/dim]")
        raise click.Abort()

    # Auto-refresh token if expired
    from kurt.cli.auth.credentials import ensure_fresh_token

    creds = ensure_fresh_token()
    if not creds:
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


@cloud_group.command(name="invite", hidden=True)
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
    They can accept by logging in and configuring the shared workspace.

    Example:
        kurt cloud invite user@example.com
        kurt cloud invite user@example.com --role admin
    """
    import json
    import urllib.request

    from kurt.cli.auth.credentials import ensure_fresh_token, get_cloud_api_url
    from kurt.config import config_file_exists, load_config

    # Check auth and refresh token if needed
    creds = ensure_fresh_token()
    if creds is None:
        console.print("[red]Not logged in.[/red]")
        console.print("[dim]Run 'kurt cloud login' first.[/dim]")
        raise click.Abort()

    # Check workspace
    if not config_file_exists():
        console.print("[red]No kurt.config found.[/red]")
        console.print("[dim]Run 'kurt init' first.[/dim]")
        raise click.Abort()

    config = load_config()
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
        console.print("  2. Add WORKSPACE_ID and DATABASE_URL to kurt.config")
        console.print("  3. Run 'kurt admin migrate apply'")

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


@cloud_group.command(name="use", hidden=True)
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
        register_workspace_path,
        save_credentials,
    )
    from kurt.config import config_file_exists, get_config_file_path

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
        config_path = get_config_file_path()
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

    # Note: workspace_id is stored only in kurt.config, not in credentials

    # Register current project path with this workspace
    if config_file_exists():
        project_path = str(get_config_file_path().parent.absolute())
        register_workspace_path(workspace_id, project_path, workspace.get("name"))

    console.print()
    console.print(f"[green]✓ Switched to workspace: {workspace.get('name', workspace_id)}[/green]")
    console.print(f"  Role: {workspace.get('role', 'member')}")
    console.print(f"  ID: {workspace_id}")


@cloud_group.command(name="workspace-create")
@click.argument("name")
@click.option("--github-repo", required=True, help="GitHub repository (owner/repo format)")
def workspace_create_cmd(name: str, github_repo: str):
    """Create a new workspace.

    Creates a workspace in Kurt Cloud. You will be the owner.

    Example:
        kurt cloud workspace-create "My Project" --github-repo boringdata/kurt-demo
    """
    import json
    import re
    import urllib.request

    from kurt.cli.auth.credentials import (
        Credentials,
        get_cloud_api_url,
        load_credentials,
        register_workspace_path,
        save_credentials,
    )
    from kurt.config import config_file_exists, get_config_file_path

    # Check auth
    creds = load_credentials()
    if creds is None:
        console.print("[red]Not logged in.[/red]")
        console.print("[dim]Run 'kurt cloud login' first.[/dim]")
        raise click.Abort()

    # Call the workspace API
    cloud_url = get_cloud_api_url()
    url = f"{cloud_url}/api/v1/workspaces"

    data = json.dumps({"name": name, "github_repo": github_repo}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {creds.access_token}")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            workspace = json.loads(resp.read().decode())

        workspace_id = workspace.get("id")

        # Automatically switch to the new workspace
        # Update local config file
        if config_file_exists():
            config_path = get_config_file_path()
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

            # Register current project path with this workspace
            project_path = str(config_path.parent.absolute())
            register_workspace_path(workspace_id, project_path, workspace.get("name"))

        # Note: workspace_id is stored only in kurt.config, not in credentials

        console.print()
        console.print(f"[green]✓ Created workspace: {workspace.get('name', name)}[/green]")
        console.print(f"  ID: {workspace_id}")
        console.print(f"  Role: {workspace.get('role', 'owner')}")
        if workspace.get("github_repo"):
            console.print(f"  GitHub: https://github.com/{workspace['github_repo']}")
        if config_file_exists():
            console.print("  [dim]Automatically switched to this workspace[/dim]")

    except urllib.error.HTTPError as e:
        try:
            error_body = json.loads(e.read().decode())
            detail = error_body.get("detail", str(e))
        except Exception:
            detail = str(e)
        console.print(f"[red]Failed to create workspace: {detail}[/red]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Failed to create workspace: {e}[/red]")
        raise click.Abort()


@cloud_group.command(name="workspaces", hidden=True)
def workspaces_cmd():
    """List your workspaces.

    Shows all workspaces you own or are a member of.
    Pending invites are automatically accepted.

    Example:
        kurt cloud workspaces

    Note: This command is hidden until workspace support is fully configured.
    """
    import json
    import urllib.request

    from kurt.cli.auth.credentials import (
        ensure_fresh_token,
        get_cloud_api_url,
        get_workspace_paths,
    )
    from kurt.config import config_file_exists, load_config

    # Check auth and refresh token if needed
    creds = ensure_fresh_token()
    if creds is None:
        console.print("[red]Not logged in.[/red]")
        console.print("[dim]Run 'kurt cloud login' first.[/dim]")
        raise click.Abort()

    # Get current workspace from config
    current_workspace_id = None
    if config_file_exists():
        config = load_config()
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

        # Show local paths associated with this workspace
        paths = get_workspace_paths(ws_id)
        if paths:
            for path in paths:
                console.print(f"          [dim]📁 {path}[/dim]")

        console.print()

    console.print("[dim]Use 'kurt cloud use <workspace_id>' to switch workspaces[/dim]")


@cloud_group.command(name="members", hidden=True)
def members_cmd():
    """List members of the current workspace.

    Shows all members and their roles.

    Example:
        kurt cloud members
    """
    import json
    import urllib.request

    from kurt.cli.auth.credentials import ensure_fresh_token, get_cloud_api_url
    from kurt.config import config_file_exists, load_config

    # Check auth and refresh token if needed
    creds = ensure_fresh_token()
    if creds is None:
        console.print("[red]Not logged in.[/red]")
        console.print("[dim]Run 'kurt cloud login' first.[/dim]")
        raise click.Abort()

    # Get current workspace from config
    if not config_file_exists():
        console.print("[red]No kurt.config found.[/red]")
        console.print("[dim]Run 'kurt init' first.[/dim]")
        raise click.Abort()

    config = load_config()
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
