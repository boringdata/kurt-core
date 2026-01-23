"""Branch management CLI commands.

Provides commands for managing synchronized Git+Dolt branches:
- kurt branch create <name>: Create branch in both systems
- kurt branch list: Show branches with sync status
- kurt branch switch <name>: Switch both systems to branch
- kurt branch delete <name>: Delete from both systems
"""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

console = Console()


def _get_dolt_db():
    """Get DoltDB instance for the current project."""
    from kurt.config import get_config
    from kurt.db.dolt import DoltDB

    config = get_config()
    dolt_path = config.get("DOLT_PATH", ".dolt")
    return DoltDB(dolt_path)


def _get_git_path() -> Path:
    """Get the Git repository path."""
    return Path.cwd()


@click.group(name="branch")
def branch_group():
    """Manage synchronized Git+Dolt branches."""
    pass


@branch_group.command(name="create")
@click.argument("name")
@click.option(
    "--no-switch",
    is_flag=True,
    default=False,
    help="Create branch without switching to it",
)
def create_cmd(name: str, no_switch: bool):
    """Create a new branch in both Git and Dolt.

    Creates the branch in Git first, then in Dolt. If creation fails in Dolt,
    the Git branch is rolled back to maintain consistency.

    Branch naming conventions (suggestions, not enforced):
    - main: default branch
    - feature/<name>: feature work
    - agent/<task_id>: agent-created branches
    - user/<username>/<name>: user experiments

    Example:
        kurt branch create feature/my-feature
        kurt branch create --no-switch experiment/test
    """
    from kurt.isolation import BranchSyncError, create_both

    try:
        dolt_db = _get_dolt_db()
        git_path = _get_git_path()

        result = create_both(
            name=name,
            git_path=git_path,
            dolt_db=dolt_db,
            switch=not no_switch,
        )

        if result.created:
            console.print(f"[green]Created branch '{name}' in Git and Dolt[/green]")
        else:
            console.print(f"[yellow]Branch '{name}' already exists[/yellow]")

        if not no_switch:
            console.print(f"[dim]Switched to branch '{name}'[/dim]")

    except BranchSyncError as e:
        console.print(f"[red]Error: {e.message}[/red]")
        if e.details:
            console.print(f"[dim]{e.details}[/dim]")
        raise click.Abort()


@branch_group.command(name="list")
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Output as JSON",
)
def list_cmd(as_json: bool):
    """List branches with sync status.

    Shows all branches from both Git and Dolt, with their sync status.

    Output columns:
    - Branch: Name (current branch marked with *)
    - Sync: Whether branch exists in both systems
    - Git: Git commit hash (or --- if missing)
    - Dolt: Dolt commit hash (or --- if missing)
    - Status: clean, git missing, or dolt missing

    Example:
        kurt branch list
        kurt branch list --json
    """
    import json as json_module

    from kurt.isolation import BranchSyncError, list_branches

    try:
        dolt_db = _get_dolt_db()
        git_path = _get_git_path()

        statuses = list_branches(git_path=git_path, dolt_db=dolt_db)

        if as_json:
            data = [
                {
                    "branch": s.branch,
                    "git_commit": s.git_commit,
                    "dolt_commit": s.dolt_commit,
                    "in_sync": s.in_sync,
                    "is_current": s.is_current,
                    "status": s.status,
                }
                for s in statuses
            ]
            console.print(json_module.dumps(data, indent=2))
            return

        if not statuses:
            console.print("[yellow]No branches found[/yellow]")
            return

        table = Table(title="Branches")
        table.add_column("Branch", style="cyan")
        table.add_column("Sync", justify="center")
        table.add_column("Git", justify="center")
        table.add_column("Dolt", justify="center")
        table.add_column("Status")

        for s in statuses:
            # Format branch name with current indicator
            branch_name = f"* {s.branch}" if s.is_current else f"  {s.branch}"

            # Sync indicator
            sync_icon = "[green]Y[/green]" if s.in_sync else "[red]X[/red]"

            # Commit hashes
            git_hash = s.git_commit or "[dim]---[/dim]"
            dolt_hash = s.dolt_commit or "[dim]---[/dim]"

            # Status styling
            if s.status == "clean":
                status_styled = "[green]clean[/green]"
            elif "missing" in s.status:
                status_styled = f"[yellow]{s.status}[/yellow]"
            else:
                status_styled = s.status

            table.add_row(branch_name, sync_icon, git_hash, dolt_hash, status_styled)

        console.print(table)

    except BranchSyncError as e:
        console.print(f"[red]Error: {e.message}[/red]")
        if e.details:
            console.print(f"[dim]{e.details}[/dim]")
        raise click.Abort()


@branch_group.command(name="switch")
@click.argument("name")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Force switch, discarding local changes",
)
def switch_cmd(name: str, force: bool):
    """Switch to a branch in both Git and Dolt.

    Switches Git first, then Dolt. If the branch exists in one system but
    not the other, it will be created in the missing system.

    Example:
        kurt branch switch feature/my-feature
        kurt branch switch main --force
    """
    from kurt.isolation import BranchSyncError, switch_both

    try:
        dolt_db = _get_dolt_db()
        git_path = _get_git_path()

        result = switch_both(
            name=name,
            git_path=git_path,
            dolt_db=dolt_db,
            force=force,
        )

        console.print(f"[green]Switched to branch '{name}'[/green]")
        if result.created:
            console.print("[dim]Created missing branch in one system[/dim]")

    except BranchSyncError as e:
        console.print(f"[red]Error: {e.message}[/red]")
        if e.details:
            console.print(f"[dim]{e.details}[/dim]")
        raise click.Abort()


@branch_group.command(name="delete")
@click.argument("name")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    default=False,
    help="Force delete even if not merged",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    default=False,
    help="Skip confirmation prompt",
)
def delete_cmd(name: str, force: bool, yes: bool):
    """Delete a branch from both Git and Dolt.

    Deletes the branch from Git first, then from Dolt.
    Cannot delete the current branch or 'main' (unless --force --force).

    Example:
        kurt branch delete feature/old-feature
        kurt branch delete feature/old-feature --force --yes
    """
    from kurt.isolation import BranchSyncError, delete_both

    # Protect main branch (requires double --force)
    if name == "main" and not (force and yes):
        console.print("[red]Error: Cannot delete 'main' branch[/red]")
        console.print("[dim]Use --force --yes to force delete main branch[/dim]")
        raise click.Abort()

    # Confirmation prompt
    if not yes:
        if not click.confirm(f"Delete branch '{name}' from Git and Dolt?"):
            console.print("[yellow]Aborted[/yellow]")
            return

    try:
        dolt_db = _get_dolt_db()
        git_path = _get_git_path()

        delete_both(
            name=name,
            git_path=git_path,
            dolt_db=dolt_db,
            force=force,
        )

        console.print(f"[green]Deleted branch '{name}' from Git and Dolt[/green]")

    except BranchSyncError as e:
        console.print(f"[red]Error: {e.message}[/red]")
        if e.details:
            console.print(f"[dim]{e.details}[/dim]")
        raise click.Abort()
