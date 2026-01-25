"""Kurt status command - comprehensive project status."""

from __future__ import annotations

import json
import os

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command

console = Console()


@click.command()
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["pretty", "json"]),
    default="pretty",
    help="Output format",
)
@click.option(
    "--hook-cc",
    is_flag=True,
    help="Output in Claude Code hook format",
)
@track_command
def status(output_format: str, hook_cc: bool):
    """
    Show comprehensive Kurt project status.

    Displays initialization status, document counts, and project summaries.

    Examples:
        kurt status
        kurt status --format json
        kurt status --hook-cc
    """
    from kurt.config import config_file_exists, load_config

    # Check if Kurt is initialized
    if not config_file_exists():
        if hook_cc:
            _auto_init_hook()
            return

        message = "Kurt project not initialized. Run: kurt init"
        if output_format == "json":
            print(json.dumps({"initialized": False, "message": message}, indent=2))
        else:
            console.print(f"[yellow]{message}[/yellow]")
        return

    try:
        config = load_config()
        db_path = config.PATH_DB

        # Check if database exists
        if not os.path.exists(db_path):
            if hook_cc:
                _init_database_hook()
                return

            message = "Database not found. Run: kurt init"
            if output_format == "json":
                print(
                    json.dumps(
                        {"initialized": False, "config_exists": True, "database_exists": False},
                        indent=2,
                    )
                )
            else:
                console.print(f"[yellow]{message}[/yellow]")
            return

        # Hook mode: auto-apply migrations + generate status
        if hook_cc:
            _handle_hook_output()
            return

        # Check for pending migrations
        migration_info = _check_pending_migrations()

        # Get status data (routes to local or cloud)
        status_data = _get_status_data()
        status_data["migrations"] = migration_info

        if output_format == "json":
            print(json.dumps(status_data, indent=2, default=str))
        else:
            _print_pretty_status(status_data, migration_info)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if os.environ.get("KURT_DEBUG"):
            import traceback

            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise click.Abort()


def _auto_init_hook():
    """Auto-initialize Kurt in hook mode."""
    from kurt.config import create_config

    create_config()

    # Initialize Dolt database
    try:
        from pathlib import Path

        from kurt.db.dolt import DoltDB, init_observability_schema

        dolt_path = Path(".dolt")
        if not dolt_path.exists():
            # Initialize dolt repo
            import subprocess

            subprocess.run(["dolt", "init"], check=True, capture_output=True)

        db = DoltDB(dolt_path)
        init_observability_schema(db)
    except Exception:
        pass  # Dolt init is optional

    output = {
        "systemMessage": "Kurt project initialized!",
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": (
                "**Kurt initialized**\\n\\n"
                "- Configuration: `kurt.config`\\n"
                "- Database: `.dolt/` (Dolt)\\n\\n"
                "Get started: `kurt content fetch <url>`"
            ),
        },
    }
    print(json.dumps(output, indent=2))


def _init_database_hook():
    """Initialize Dolt database in hook mode."""
    try:
        from pathlib import Path

        from kurt.db.dolt import DoltDB, init_observability_schema

        dolt_path = Path(".dolt")
        if not dolt_path.exists():
            import subprocess

            subprocess.run(["dolt", "init"], check=True, capture_output=True)

        db = DoltDB(dolt_path)
        init_observability_schema(db)
    except Exception:
        pass

    output = {
        "systemMessage": "Database initialized!",
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "Database created at `.dolt/` (Dolt)",
        },
    }
    print(json.dumps(output, indent=2))


def _handle_hook_output():
    """Generate hook-compatible output with status."""
    status_data = _get_status_data()

    # Build user-facing summary
    doc_counts = status_data.get("documents", {})
    total_docs = doc_counts.get("total", 0)

    status_parts = ["**Kurt Status:**", f"Documents: {total_docs}"]

    user_message = " | ".join(status_parts)

    # Build detailed markdown
    markdown = _generate_status_markdown(status_data)

    output = {
        "systemMessage": user_message,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": markdown,
        },
    }
    print(json.dumps(output, indent=2))


def _get_status_data() -> dict:
    """
    Get status data - routes to local queries or cloud API based on mode.

    Local mode: Direct SQLAlchemy queries
    Cloud mode: HTTP request to kurt-cloud API
    """
    from kurt.db.routing import route_by_mode

    return route_by_mode(_get_status_data_from_db, _get_status_data_from_api)


def _get_status_data_from_db() -> dict:
    """Get status data using Dolt queries (local mode)."""
    from .queries import get_status_data

    return get_status_data()


def _get_status_data_from_api() -> dict:
    """
    Get status data from web API (cloud mode).

    Calls the /core/api/status endpoint (kurt-core mounted at /core prefix).
    In cloud mode, this is hosted on kurt-cloud.
    """
    from kurt.db.cloud_api import api_request

    return api_request("/core/api/status")


def _generate_status_markdown(data: dict) -> str:
    """Generate markdown summary of status."""
    lines = ["# Kurt Status", ""]

    docs = data.get("documents", {})
    lines.append(f"## Documents: {docs.get('total', 0)}")
    lines.append("")

    by_status = docs.get("by_status", {})
    lines.append(f"- Fetched: {by_status.get('fetched', 0)}")
    lines.append(f"- Not fetched: {by_status.get('not_fetched', 0)}")
    lines.append(f"- Error: {by_status.get('error', 0)}")

    by_domain = docs.get("by_domain", {})
    if by_domain:
        lines.append("")
        lines.append("## By Domain")
        lines.append("")
        for domain, count in sorted(by_domain.items(), key=lambda x: -x[1])[:10]:
            lines.append(f"- {domain}: {count}")

    return "\n".join(lines)


def _check_pending_migrations() -> dict:
    """Check if there are pending database migrations.

    Returns:
        Dict with 'has_pending', 'count', and 'migrations' keys
    """
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


def _print_pretty_status(data: dict, migration_info: dict):
    """Print status in human-readable format."""
    from rich.markdown import Markdown

    # Show migration warning first if needed
    if migration_info.get("has_pending"):
        console.print()
        console.print(f"[yellow]⚠ {migration_info['count']} pending database migration(s)[/yellow]")
        console.print("[dim]Run: `kurt admin migrate apply` to update the database[/dim]")
        for migration_name in migration_info.get("migrations", []):
            console.print(f"[dim]  - {migration_name}[/dim]")
        console.print()

    markdown = _generate_status_markdown(data)
    console.print(Markdown(markdown))
