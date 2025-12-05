"""Update agent instructions to latest version."""

import shutil
from pathlib import Path

import click
from rich.console import Console

console = Console()


@click.command()
@click.option(
    "--backup/--no-backup",
    default=True,
    help="Create backup before updating (default: yes)",
)
def update(backup: bool):
    """
    Update agent instructions (.agents/AGENTS.md) to latest version.

    This updates your workspace agent instructions to match the latest
    version from the kurt package. Useful after upgrading kurt via pip.

    Example:
        kurt update
        kurt update --no-backup
    """
    console.print("[bold]Updating agent instructions...[/bold]\n")

    try:
        # Get source AGENTS.md from package
        package_agents = Path(__file__).parent.parent / "agents" / "AGENTS.md"

        if not package_agents.exists():
            console.print("[red]✗[/red] Package AGENTS.md not found")
            return

        # Get workspace AGENTS.md
        workspace_agents = Path.cwd() / ".agents" / "AGENTS.md"

        if not workspace_agents.exists():
            console.print("[yellow]⚠[/yellow] No .agents/AGENTS.md found in workspace")
            console.print("[dim]Run 'kurt init' first to initialize agent instructions[/dim]")
            return

        # Create backup if requested
        if backup:
            backup_path = workspace_agents.parent / "AGENTS.md.backup"
            shutil.copy2(workspace_agents, backup_path)
            console.print(f"[green]✓[/green] Created backup: {backup_path}")

        # Read versions
        old_content = workspace_agents.read_text()
        new_content = package_agents.read_text()

        if old_content == new_content:
            console.print("[green]✓[/green] Agent instructions are already up to date")
            return

        # Update the file
        shutil.copy2(package_agents, workspace_agents)
        console.print("[green]✓[/green] Updated .agents/AGENTS.md")

        # Check if any IDE files need attention
        ide_notes = []

        # Check Claude
        claude_md = Path.cwd() / ".claude" / "CLAUDE.md"
        if claude_md.exists() and not claude_md.is_symlink():
            ide_notes.append(".claude/CLAUDE.md is not a symlink - you may want to review it")

        # Check Cursor
        cursor_mdc = Path.cwd() / ".cursor" / "rules" / "KURT.mdc"
        if cursor_mdc.exists() and not cursor_mdc.is_symlink():
            ide_notes.append(".cursor/rules/KURT.mdc is not a symlink - you may want to review it")

        if ide_notes:
            console.print()
            console.print("[yellow]Note:[/yellow]")
            for note in ide_notes:
                console.print(f"  • {note}")

        console.print()
        console.print("[bold green]✓ Update complete[/bold green]")
        console.print(
            "[dim]The symlinks in .claude/ and .cursor/ will automatically use the updated version[/dim]"
        )

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()
