"""Show plan.md update checklist command."""

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command

console = Console()


@click.command()
@track_command
def plan_updates_cmd():
    """
    Display plan.md update checklist.

    Shows when and how to update the project plan.md file, which is the
    single source of truth for project state. Extracted from agent instructions.

    Examples:
        kurt show plan-updates
    """
    console.print()
    console.print("[bold cyan]📋 plan.md Update Checklist[/bold cyan]")
    console.print()

    # WHEN Section
    console.print("[bold]WHEN to Update (immediately after):[/bold]")
    console.print()
    console.print('  ✅ Gathering sources → "Sources of Ground Truth" section')
    console.print('  ✅ Completing research → "Research Required" + findings')
    console.print("  ✅ Outlining/drafting/editing → Document status + checkboxes")
    console.print('  ✅ Fetching content → Add to "Sources of Ground Truth" with path/purpose')
    console.print("  ✅ Any task completion → Mark checkbox [x]")
    console.print("  ✅ Status changes → Update relevant section")
    console.print()

    # HOW Section
    console.print("[bold]HOW to Update:[/bold]")
    console.print()
    console.print("  [dim]Sources format:[/dim]")
    console.print(
        '  [cyan]- path: /sources/domain/file.md, purpose: "why this source matters"[/cyan]'
    )
    console.print()
    console.print("  [dim]Status format:[/dim]")
    console.print('  [cyan]Update document status fields (e.g., "Status: draft")[/cyan]')
    console.print()
    console.print("  [dim]Checkboxes:[/dim]")
    console.print("  [cyan][x][/cyan] = completed, [cyan][ ][/cyan] = pending")
    console.print()
    console.print("  [dim]Preferred method:[/dim]")
    console.print("  Use agent's native todo/task tracking tool if available")
    console.print("  (automatically updates checkboxes)")
    console.print()
    console.print("  [dim]Manual method:[/dim]")
    console.print("  Edit plan.md file directly")
    console.print()

    # Important Note
    console.print("[bold yellow]⚠️ IMPORTANT:[/bold yellow]")
    console.print(
        "   Always read plan.md FIRST when working on a project to understand current state"
    )
    console.print()

    console.print(
        "[dim]💡 Full details: See @kurt-main rule 'plan.md Update Checklist' section[/dim]"
    )
    console.print()
