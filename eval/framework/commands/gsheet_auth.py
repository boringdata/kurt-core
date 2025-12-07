#!/usr/bin/env python3
"""Google Sheets authentication setup command for eval framework."""

import json
import os
import webbrowser
from pathlib import Path
from typing import Optional

import click


def create_oauth_flow():
    """Create OAuth flow for user authentication."""
    try:
        # Test if packages are available
        import importlib.util

        if not (
            importlib.util.find_spec("google.auth.transport.requests")
            and importlib.util.find_spec("google.oauth2.credentials")
            and importlib.util.find_spec("google_auth_oauthlib.flow")
        ):
            raise ImportError()
    except ImportError:
        click.echo("❌ Required packages not installed. Run: uv pip install google-auth-oauthlib")
        return None

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
    ]

    return scopes


def setup_service_account():
    """Guide user through service account setup."""
    click.echo("\n📋 SERVICE ACCOUNT SETUP (Recommended for automation)")
    click.echo("=" * 60)
    click.echo("\nFollow these steps to create a service account:\n")

    click.echo("1. Go to Google Cloud Console:")
    click.echo("   https://console.cloud.google.com/")
    click.echo()

    if click.confirm("Open Google Cloud Console in browser?"):
        webbrowser.open("https://console.cloud.google.com/")

    click.echo("\n2. Create a new project or select existing one")
    click.echo("   - Click 'Select a project' dropdown")
    click.echo("   - Click 'New Project' if needed")
    click.echo("   - Name it (e.g., 'kurt-eval')")
    click.echo()

    click.echo("3. Enable required APIs:")
    click.echo("   a. Go to 'APIs & Services' > 'Enable APIs and Services'")
    click.echo("   b. Search and enable:")
    click.echo("      - Google Sheets API")
    click.echo("      - Google Drive API")
    click.echo()

    click.echo("4. Create Service Account:")
    click.echo("   a. Go to 'APIs & Services' > 'Credentials'")
    click.echo("   b. Click '+ CREATE CREDENTIALS' > 'Service account'")
    click.echo("   c. Name it (e.g., 'kurt-eval-service')")
    click.echo("   d. Grant role: 'Editor' or 'Owner'")
    click.echo("   e. Click 'Done'")
    click.echo()

    click.echo("5. Download credentials:")
    click.echo("   a. Click on your service account")
    click.echo("   b. Go to 'Keys' tab")
    click.echo("   c. Click 'Add Key' > 'Create new key'")
    click.echo("   d. Choose 'JSON' format")
    click.echo("   e. Save the downloaded file")
    click.echo()

    return True


def setup_oauth():
    """Guide user through OAuth setup for personal use."""
    click.echo("\n🔐 OAUTH SETUP (For personal use)")
    click.echo("=" * 60)
    click.echo("\nThis method uses your personal Google account.\n")

    click.echo("1. Go to Google Cloud Console:")
    click.echo("   https://console.cloud.google.com/")
    click.echo()

    click.echo("2. Create OAuth 2.0 Client ID:")
    click.echo("   a. Go to 'APIs & Services' > 'Credentials'")
    click.echo("   b. Click '+ CREATE CREDENTIALS' > 'OAuth client ID'")
    click.echo("   c. Configure consent screen if needed")
    click.echo("   d. Choose 'Desktop app' as application type")
    click.echo("   e. Download the credentials.json")
    click.echo()

    return True


def validate_credentials_file(path: Path) -> bool:
    """Validate that the credentials file is properly formatted."""
    try:
        with open(path) as f:
            data = json.load(f)

        # Check for service account
        if "type" in data and data["type"] == "service_account":
            required_fields = ["project_id", "private_key", "client_email"]
            if all(field in data for field in required_fields):
                click.echo(f"✅ Valid service account credentials: {data.get('client_email')}")
                return True

        # Check for OAuth client
        if "installed" in data or "web" in data:
            click.echo("✅ Valid OAuth client credentials")
            return True

        click.echo("❌ Invalid credentials format")
        return False

    except Exception as e:
        click.echo(f"❌ Error reading credentials: {e}")
        return False


def save_credentials(creds_path: str, target_path: Path) -> bool:
    """Save credentials to the appropriate location."""
    source = Path(creds_path).expanduser()

    if not source.exists():
        click.echo(f"❌ File not found: {source}")
        return False

    # Validate the credentials
    if not validate_credentials_file(source):
        return False

    # Create target directory if needed
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Copy the file
    import shutil

    shutil.copy2(source, target_path)

    # Set appropriate permissions (read-only for owner)
    os.chmod(target_path, 0o600)

    click.echo(f"✅ Credentials saved to: {target_path}")
    return True


def test_connection(creds_path: Path) -> bool:
    """Test the Google Sheets API connection."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        # Load credentials
        credentials = service_account.Credentials.from_service_account_file(
            str(creds_path), scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )

        # Try to connect to Sheets API
        service = build("sheets", "v4", credentials=credentials)

        # Try to create a test spreadsheet
        spreadsheet = {"properties": {"title": "Kurt Eval - Test Connection"}}

        result = service.spreadsheets().create(body=spreadsheet).execute()
        sheet_id = result.get("spreadsheetId")
        sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}"

        click.echo("✅ Successfully connected to Google Sheets!")
        click.echo(f"📊 Test spreadsheet created: {sheet_url}")

        if click.confirm("Open test spreadsheet in browser?"):
            webbrowser.open(sheet_url)

        return True

    except Exception as e:
        click.echo(f"❌ Connection test failed: {e}")
        return False


@click.command()
@click.option(
    "--method",
    type=click.Choice(["service-account", "oauth", "auto"]),
    default="auto",
    help="Authentication method",
)
@click.option("--credentials-file", help="Path to credentials JSON file")
@click.option("--test", is_flag=True, help="Test the connection after setup")
def gsheet_auth(method: str, credentials_file: Optional[str], test: bool):
    """Set up Google Sheets authentication for eval reports.

    This command helps you configure Google API credentials to enable
    automatic syncing of evaluation results to Google Sheets.
    """
    click.echo("\n🔐 GOOGLE SHEETS AUTHENTICATION SETUP")
    click.echo("=" * 60)

    # Check current status
    config_dir = Path.home() / ".config" / "kurt-eval"
    service_account_path = config_dir / "service_account.json"
    config_dir / "oauth_credentials.json"
    env_var = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    click.echo("\n📍 Current Status:")
    click.echo("-" * 40)

    if env_var:
        click.echo(f"✅ GOOGLE_APPLICATION_CREDENTIALS set: {env_var}")
        if Path(env_var).exists():
            click.echo("   ✅ File exists")
            if test:
                test_connection(Path(env_var))
        else:
            click.echo("   ❌ File not found")
    else:
        click.echo("❌ GOOGLE_APPLICATION_CREDENTIALS not set")

    if service_account_path.exists():
        click.echo(f"✅ Service account found: {service_account_path}")
        if test and not env_var:
            test_connection(service_account_path)
    else:
        click.echo(f"❌ No service account at: {service_account_path}")

    # If credentials file provided, save it
    if credentials_file:
        click.echo(f"\n📁 Setting up credentials from: {credentials_file}")
        if save_credentials(credentials_file, service_account_path):
            click.echo("\n✅ Setup complete! You can now use --sync-gsheet")
            click.echo("\nTo use these credentials, either:")
            click.echo("1. Set environment variable:")
            click.echo(f"   export GOOGLE_APPLICATION_CREDENTIALS='{service_account_path}'")
            click.echo(f"2. Or the framework will auto-detect from: {service_account_path}")

            if test:
                click.echo("\n🧪 Testing connection...")
                test_connection(service_account_path)
        return

    # Interactive setup
    if method == "auto" and not credentials_file:
        click.echo("\n📋 Choose authentication method:")
        click.echo("1. Service Account (Recommended - for automation)")
        click.echo("2. OAuth (Personal - requires browser)")

        choice = click.prompt("Enter choice", type=int, default=1)
        method = "service-account" if choice == 1 else "oauth"

    if method == "service-account":
        if setup_service_account():
            click.echo("\n✅ Service Account Setup Instructions Complete!")
            click.echo("\nAfter downloading the JSON key file, run:")
            click.echo(
                "  uv run python -m eval gsheet-auth --credentials-file /path/to/key.json --test"
            )

    elif method == "oauth":
        if setup_oauth():
            click.echo("\n✅ OAuth Setup Instructions Complete!")
            click.echo("\nAfter downloading credentials.json, run:")
            click.echo(
                "  uv run python -m eval gsheet-auth --credentials-file /path/to/credentials.json"
            )

    click.echo("\n📚 Documentation:")
    click.echo("https://developers.google.com/sheets/api/quickstart/python")
    click.echo()


if __name__ == "__main__":
    gsheet_auth()
