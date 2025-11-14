"""Kurt CLI - Telemetry management commands."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from kurt.admin.telemetry.config import (
    get_telemetry_status,
    is_telemetry_enabled,
    set_telemetry_enabled,
)

console = Console()


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
        kurt telemetry enable
    """
    if is_telemetry_enabled():
        console.print("[yellow]Telemetry is already enabled[/yellow]")
        return

    set_telemetry_enabled(True)
    console.print("[green]✓ Telemetry enabled[/green]")
    console.print()
    console.print("[dim]Thank you for helping improve Kurt![/dim]")
    console.print("[dim]Run 'kurt telemetry status' to see what we collect[/dim]")


@telemetry.command()
def disable():
    """
    Disable telemetry collection.

    You can also disable telemetry by:
    - Setting DO_NOT_TRACK environment variable
    - Setting KURT_TELEMETRY_DISABLED environment variable

    Example:
        kurt telemetry disable
    """
    if not is_telemetry_enabled():
        console.print("[yellow]Telemetry is already disabled[/yellow]")
        return

    set_telemetry_enabled(False)
    console.print("[green]✓ Telemetry disabled[/green]")
    console.print()
    console.print("[dim]You can re-enable anytime with 'kurt telemetry enable'[/dim]")


@telemetry.command()
def status():
    """
    Show current telemetry status and what data is collected.

    Example:
        kurt telemetry status
    """
    status_info = get_telemetry_status()

    # Create status panel
    if status_info["enabled"]:
        status_text = "[bold green]Enabled[/bold green]"
        status_emoji = "✓"
    else:
        status_text = "[bold red]Disabled[/bold red]"
        status_emoji = "✗"

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
    console.print("  • Command name (e.g., 'kurt ingest fetch')")
    console.print("  • Execution time and success/failure")
    console.print("  • Operating system and version")
    console.print("  • Python version")
    console.print("  • Kurt version")
    console.print()
    console.print("[bold]What we DON'T collect:[/bold]")
    console.print("  • Personal information (names, emails)")
    console.print("  • File paths or URLs")
    console.print("  • Command arguments")
    console.print("  • Any sensitive data")
    console.print()
    console.print("[dim]To disable: kurt telemetry disable[/dim]")
    console.print("[dim]Or set DO_NOT_TRACK environment variable[/dim]")
