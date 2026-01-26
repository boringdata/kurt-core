"""Admin CLI commands.

This module consolidates all administrative CLI commands:
- feedback: Log feedback telemetry events
- telemetry: Manage telemetry settings
- sync: Git+Dolt version control (imported from kurt.cli.sync)
"""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from kurt.admin.telemetry.decorators import track_command
from kurt.db.isolation.cli import sync_group

console = Console()


# ============================================================================
# Admin Group
# ============================================================================


@click.group()
def admin():
    """Administrative commands."""
    pass


# ============================================================================
# Feedback Commands
# ============================================================================


@click.group()
def feedback():
    """Log feedback telemetry events (called by Claude Code plugin)."""
    pass


@feedback.command("log-submission")
@click.option("--rating", required=True, type=int, help="User rating (1-5)")
@click.option(
    "--has-comment", is_flag=True, default=False, help="Whether user provided text feedback"
)
@click.option(
    "--issue-category",
    type=click.Choice(
        ["tone", "structure", "info", "comprehension", "length", "examples", "other"]
    ),
    help="Category of identified issue",
)
@click.option("--event-id", required=True, help="UUID of feedback event")
@track_command
def log_submission(
    rating: int,
    has_comment: bool,
    issue_category: str | None,
    event_id: str,
):
    """
    Log a feedback submission event (for telemetry only).

    This is called by the Claude Code feedback-skill when a user submits feedback.
    The actual feedback data is stored in the local database by the skill.
    This command only sends telemetry events for analytics.

    Example:
        kurt admin feedback log-submission --rating 3 --issue-category tone --event-id abc123
    """
    from kurt.admin.telemetry.feedback_tracker import track_feedback_submitted

    track_feedback_submitted(
        rating=rating,
        has_comment=has_comment,
        issue_category=issue_category,
    )

    console.print(f"[dim]Logged feedback submission: {event_id}[/dim]")


# ============================================================================
# Telemetry Commands
# ============================================================================


@click.group()
def telemetry():
    """Manage telemetry and anonymous usage analytics."""
    pass


@telemetry.command()
def enable():
    """
    Enable anonymous telemetry collection.

    Telemetry helps us understand how Kurt is used and improve it.
    We collect:
    - Commands run (no arguments or file paths)
    - Execution time and success/failure
    - Operating system and Python version
    - Kurt version

    We do NOT collect:
    - Personal information (names, emails)
    - File paths or URLs
    - Command arguments
    - Any sensitive data

    Example:
        kurt admin telemetry enable
    """
    from kurt.admin.telemetry.config import is_telemetry_enabled, set_telemetry_enabled

    if is_telemetry_enabled():
        console.print("[yellow]Telemetry is already enabled[/yellow]")
        return

    set_telemetry_enabled(True)
    console.print("[green]Telemetry enabled[/green]")
    console.print()
    console.print("[dim]Thank you for helping improve Kurt![/dim]")
    console.print("[dim]Run 'kurt admin telemetry status' to see what we collect[/dim]")


@telemetry.command()
def disable():
    """
    Disable telemetry collection.

    You can also disable telemetry by:
    - Setting DO_NOT_TRACK environment variable
    - Setting KURT_TELEMETRY_DISABLED environment variable

    Example:
        kurt admin telemetry disable
    """
    from kurt.admin.telemetry.config import is_telemetry_enabled, set_telemetry_enabled

    if not is_telemetry_enabled():
        console.print("[yellow]Telemetry is already disabled[/yellow]")
        return

    set_telemetry_enabled(False)
    console.print("[green]Telemetry disabled[/green]")
    console.print()
    console.print("[dim]You can re-enable anytime with 'kurt admin telemetry enable'[/dim]")


@telemetry.command("status")
def telemetry_status():
    """
    Show current telemetry status and what data is collected.

    Example:
        kurt admin telemetry status
    """
    from kurt.admin.telemetry.config import get_telemetry_status

    status_info = get_telemetry_status()

    # Create status panel
    if status_info["enabled"]:
        status_text = "[bold green]Enabled[/bold green]"
        status_emoji = "+"
    else:
        status_text = "[bold red]Disabled[/bold red]"
        status_emoji = "x"

    console.print()
    console.print(
        Panel(
            f"{status_emoji} Telemetry is {status_text}",
            title="Telemetry Status",
            border_style="green" if status_info["enabled"] else "red",
        )
    )

    # Show details
    console.print()
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Property", style="cyan")
    table.add_column("Value")

    table.add_row("Status", "Enabled" if status_info["enabled"] else "Disabled")

    if status_info["disabled_reason"]:
        table.add_row("Disabled by", status_info["disabled_reason"])

    table.add_row("Config file", status_info["config_path"])

    if status_info["enabled"] and status_info["machine_id"]:
        table.add_row("Machine ID", status_info["machine_id"][:16] + "...")

    table.add_row("CI environment", "Yes" if status_info["is_ci"] else "No")

    console.print(table)

    # Show what we collect
    console.print()
    console.print("[bold]What we collect:[/bold]")
    console.print("  - Command name (e.g., 'kurt content fetch')")
    console.print("  - Execution time and success/failure")
    console.print("  - Operating system and version")
    console.print("  - Python version")
    console.print("  - Kurt version")
    console.print()
    console.print("[bold]What we DON'T collect:[/bold]")
    console.print("  - Personal information (names, emails)")
    console.print("  - File paths or URLs")
    console.print("  - Command arguments")
    console.print("  - Any sensitive data")
    console.print()
    console.print("[dim]To disable: kurt admin telemetry disable[/dim]")
    console.print("[dim]Or set DO_NOT_TRACK environment variable[/dim]")


# ============================================================================
# Register all commands with admin group
# ============================================================================

admin.add_command(feedback)
admin.add_command(telemetry)
admin.add_command(sync_group, name="sync")
