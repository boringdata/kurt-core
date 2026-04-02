"""Kurt status command - comprehensive project status."""

from __future__ import annotations

import json
import os

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command
from kurt.cli.robot import ErrorCode, OutputContext, robot_error, robot_success

console = Console()


@click.command()
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["pretty", "json"]),
    default=None,
    help="Output format (deprecated: use global --json flag)",
)
@click.option(
    "--hook-cc",
    is_flag=True,
    help="Output in Claude Code hook format",
)
@click.pass_context
@track_command
def status(ctx, output_format: str | None, hook_cc: bool):
    """
    Show comprehensive Kurt project status.

    Displays initialization status, document counts, and project summaries.

    Examples:
        kurt status
        kurt --json status
        kurt status --format json
        kurt status --hook-cc
    """
    from kurt.config import config_file_exists, load_config

    # Get output context from global --json flag
    output: OutputContext = ctx.obj.get("output", OutputContext()) if ctx.obj else OutputContext()

    # Hybrid activation: global --json OR local --format json
    use_json = output.json_mode or output_format == "json"

    # Check if Kurt is initialized
    if not config_file_exists():
        if hook_cc:
            _auto_init_hook()
            return

        if use_json:
            print(
                robot_error(
                    ErrorCode.NOT_INITIALIZED,
                    "Kurt project not initialized",
                    hint="Run: kurt init",
                )
            )
        else:
            console.print("[yellow]Kurt project not initialized. Run: kurt init[/yellow]")
        return

    try:
        config = load_config()
        db_path = config.PATH_DB

        # Check if database exists
        if not os.path.exists(db_path):
            if hook_cc:
                _init_database_hook()
                return

            if use_json:
                print(
                    robot_error(
                        ErrorCode.NOT_INITIALIZED,
                        "Database not found",
                        hint="Run: kurt init",
                        config_exists=True,
                        database_exists=False,
                    )
                )
            else:
                console.print("[yellow]Database not found. Run: kurt init[/yellow]")
            return

        # Hook mode: generate status
        if hook_cc:
            _handle_hook_output()
            return

        # Get status data (routes to local or cloud)
        status_data = _get_status_data()

        if use_json:
            print(robot_success(status_data))
        else:
            _print_pretty_status(status_data)

    except Exception as e:
        if use_json:
            print(robot_error(ErrorCode.EXEC_ERROR, str(e)))
        else:
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

        # DoltDB expects project root (dir containing .dolt), not .dolt itself
        db = DoltDB(Path.cwd())
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

        # DoltDB expects project root (dir containing .dolt), not .dolt itself
        db = DoltDB(Path.cwd())
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
    Get status data from Dolt database.

    In Dolt-only architecture, we query directly from Dolt tables.
    """
    from .queries import get_status_data

    return get_status_data()


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


def _print_pretty_status(data: dict):
    """Print status in human-readable format."""
    from rich.markdown import Markdown

    markdown = _generate_status_markdown(data)
    console.print(Markdown(markdown))
