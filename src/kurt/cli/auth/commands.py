"""Authentication commands for Kurt Cloud."""

from __future__ import annotations

import http.server
import json
import socket
import threading
import time
import urllib.parse
import urllib.request
from typing import Optional

import click

from .credentials import (
    Credentials,
    clear_credentials,
    get_supabase_anon_key,
    get_supabase_url,
    load_credentials,
    save_credentials,
)


def find_free_port() -> int:
    """Find a free port for the OAuth callback server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class MagicLinkCallbackHandler(http.server.BaseHTTPRequestHandler):
    """Handle magic link callback from Supabase."""

    def log_message(self, format: str, *args) -> None:
        """Suppress HTTP server logs."""
        pass

    def do_GET(self) -> None:  # noqa: N802
        """Handle the magic link callback."""
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/callback":
            # For fragment-based auth, we need JavaScript to extract tokens
            self._send_fragment_extractor()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        """Handle POST requests (token submission from JavaScript)."""
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/token":
            # Receive tokens via POST from JavaScript fragment extractor
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = json.loads(body)

            if data.get("access_token"):
                self.server.auth_result = {
                    "access_token": data.get("access_token"),
                    "refresh_token": data.get("refresh_token"),
                    "expires_in": int(data.get("expires_in", 3600)),
                    "token_type": data.get("token_type", "bearer"),
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "ok"}')
            else:
                self.server.auth_error = data.get("error", "No access token")
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "error"}')
        else:
            self.send_response(404)
            self.end_headers()

    def _send_fragment_extractor(self) -> None:
        """Send HTML page that extracts tokens from URL fragment."""
        html = """<!DOCTYPE html>
<html>
<head><title>Kurt Cloud Login</title>
<style>
body { font-family: system-ui, sans-serif; max-width: 500px; margin: 50px auto; padding: 20px; }
h1 { color: #333; }
.success { color: #22c55e; }
.error { color: #ef4444; }
</style>
</head>
<body>
<h1>Processing login...</h1>
<p id="status">Extracting authentication tokens...</p>
<script>
const hash = window.location.hash.substring(1);
const params = new URLSearchParams(hash);
const data = {
    access_token: params.get('access_token'),
    refresh_token: params.get('refresh_token'),
    expires_in: params.get('expires_in'),
    token_type: params.get('token_type'),
    error: params.get('error'),
    error_description: params.get('error_description')
};

if (data.error) {
    document.querySelector('h1').textContent = 'Login failed';
    document.querySelector('h1').className = 'error';
    document.getElementById('status').textContent = data.error_description || data.error;
} else if (data.access_token) {
    fetch('/token', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data)
    }).then(r => {
        if (r.ok) {
            document.querySelector('h1').textContent = 'Login successful!';
            document.querySelector('h1').className = 'success';
            document.getElementById('status').textContent = 'You can close this window and return to the terminal.';
        } else {
            document.querySelector('h1').textContent = 'Login failed';
            document.querySelector('h1').className = 'error';
            document.getElementById('status').textContent = 'Failed to save credentials.';
        }
    });
} else {
    document.querySelector('h1').textContent = 'Login failed';
    document.querySelector('h1').className = 'error';
    document.getElementById('status').textContent = 'No access token received. The magic link may have expired.';
}
</script>
</body>
</html>"""
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())


def send_magic_link(email: str, supabase_url: str, redirect_to: str) -> bool:
    """Send magic link email via Supabase."""
    url = f"{supabase_url}/auth/v1/otp"
    data = json.dumps(
        {
            "email": email,
            "options": {
                "emailRedirectTo": redirect_to,
            },
        }
    ).encode()

    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("apikey", get_supabase_anon_key())

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        raise click.ClickException(f"Failed to send magic link: {error_body}")
    except Exception as e:
        raise click.ClickException(f"Failed to send magic link: {e}")


def get_user_info(access_token: str, supabase_url: str) -> dict:
    """Get user info from Supabase using the access token."""
    url = f"{supabase_url}/auth/v1/user"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("apikey", get_supabase_anon_key())

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        raise click.ClickException(f"Failed to get user info: {e}")


def refresh_access_token(refresh_token: str, supabase_url: str) -> Optional[dict]:
    """Refresh the access token using the refresh token."""
    url = f"{supabase_url}/auth/v1/token?grant_type=refresh_token"
    data = json.dumps({"refresh_token": refresh_token}).encode()

    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("apikey", get_supabase_anon_key())

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


@click.command()
@click.option(
    "--email",
    "-e",
    prompt="Email address",
    help="Your email address for magic link login",
)
def login(email: str) -> None:
    """Login to Kurt Cloud via email magic link.

    Sends a magic link to your email. Click the link to authenticate.
    Your credentials are stored locally for future use.
    """
    url = get_supabase_url()

    # Start local callback server on fixed port (must match Supabase redirect URL config)
    port = 9876  # Fixed port - add http://localhost:9876 to Supabase redirect URLs
    redirect_uri = f"http://localhost:{port}/callback"

    try:
        server = http.server.HTTPServer(("localhost", port), MagicLinkCallbackHandler)
    except OSError as e:
        if "Address already in use" in str(e):
            raise click.ClickException(
                f"Port {port} is already in use. Please close other applications using this port."
            )
        raise
    server.auth_result = None
    server.auth_error = None

    # Send magic link
    click.echo(f"Sending magic link to {email}...")
    send_magic_link(email, url, redirect_uri)

    click.echo("Check your email and click the magic link.")
    click.echo("Waiting for authentication (timeout: 5 minutes)...")

    # Handle requests in background
    def handle_requests():
        while server.auth_result is None and server.auth_error is None:
            server.handle_request()

    thread = threading.Thread(target=handle_requests)
    thread.daemon = True
    thread.start()

    # Wait with timeout (5 minutes for email)
    timeout = 300
    start = time.time()
    while (
        server.auth_result is None and server.auth_error is None and time.time() - start < timeout
    ):
        time.sleep(0.5)

    if server.auth_error:
        raise click.ClickException(f"Authentication failed: {server.auth_error}")

    if server.auth_result is None:
        raise click.ClickException("Authentication timed out. Please try again.")

    # Get user info
    access_token = server.auth_result["access_token"]
    user_info = get_user_info(access_token, url)

    # Calculate expiry timestamp
    expires_at = int(time.time()) + server.auth_result["expires_in"]

    # Save credentials
    creds = Credentials(
        access_token=access_token,
        refresh_token=server.auth_result["refresh_token"],
        user_id=user_info["id"],
        email=user_info.get("email"),
        expires_at=expires_at,
        supabase_url=url,
    )
    save_credentials(creds)

    click.echo(f"Logged in as {creds.email or creds.user_id}")


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
        click.echo("Run 'kurt auth login' to authenticate.")
        return

    click.echo(f"Logged in as: {creds.email or creds.user_id}")
    click.echo(f"User ID: {creds.user_id}")

    if creds.workspace_id:
        click.echo(f"Workspace: {creds.workspace_id}")

    if creds.is_expired():
        click.echo("Status: Token expired (will refresh on next use)")
    else:
        click.echo("Status: Active")

    if creds.supabase_url:
        click.echo(f"Supabase: {creds.supabase_url}")


@click.command()
def whoami() -> None:
    """Show current user info.

    Fetches fresh user data from Kurt Cloud.
    """
    creds = load_credentials()
    if creds is None:
        raise click.ClickException("Not logged in. Run 'kurt auth login' first.")

    # Refresh token if expired
    if creds.is_expired() and creds.refresh_token and creds.supabase_url:
        click.echo("Token expired, refreshing...")
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
            raise click.ClickException("Token refresh failed. Please run 'kurt auth login' again.")

    # Fetch current user info
    if not creds.supabase_url:
        raise click.ClickException("Supabase URL not stored. Please login again.")

    user_info = get_user_info(creds.access_token, creds.supabase_url)

    click.echo(f"User ID: {user_info['id']}")
    click.echo(f"Email: {user_info.get('email', 'N/A')}")
    if user_info.get("user_metadata"):
        meta = user_info["user_metadata"]
        if meta.get("full_name"):
            click.echo(f"Name: {meta['full_name']}")
        if meta.get("avatar_url"):
            click.echo(f"Avatar: {meta['avatar_url']}")
