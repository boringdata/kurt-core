"""Merge CLI command.

Provides the 'kurt merge' command for merging Git+Dolt branches atomically.

Usage:
    kurt merge <branch>           # Merge branch into current
    kurt merge --abort            # Abort in-progress merge
    kurt merge --no-commit <branch>  # Merge but don't commit
    kurt merge --squash <branch>  # Squash merge

Exit codes:
    0: merge successful
    1: Dolt conflicts (merge aborted)
    2: Git conflicts (Dolt rolled back)
    3: rollback failed (manual intervention needed)
"""

from __future__ import annotations

import json as json_module
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from kurt.isolation import (
    MergeConflict,
    MergeError,
    MergeErrorCode,
    MergeExitCode,
    abort_merge,
    check_conflicts,
    merge_branch,
)

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


def _format_conflicts(conflicts: MergeConflict, as_json: bool = False) -> None:
    """Format and display merge conflicts."""
    if as_json:
        data = {
            "dolt_conflicts": [
                {
                    "table": c.table,
                    "key": c.key,
                    "ours": c.ours,
                    "theirs": c.theirs,
                }
                for c in conflicts.dolt_conflicts
            ],
            "git_conflicts": conflicts.git_conflicts,
            "resolution_hint": conflicts.resolution_hint,
        }
        console.print(json_module.dumps(data, indent=2))
        return

    # Display Dolt conflicts
    if conflicts.dolt_conflicts:
        console.print("\n[bold red]Dolt Conflicts:[/bold red]")
        table = Table(show_header=True)
        table.add_column("Table", style="cyan")
        table.add_column("Key")
        table.add_column("Ours", style="green")
        table.add_column("Theirs", style="yellow")

        for c in conflicts.dolt_conflicts:
            ours_str = json_module.dumps(c.ours) if c.ours else "---"
            theirs_str = json_module.dumps(c.theirs) if c.theirs else "---"
            table.add_row(c.table, c.key, ours_str, theirs_str)

        console.print(table)

    # Display Git conflicts
    if conflicts.git_conflicts:
        console.print("\n[bold red]Git Conflicts:[/bold red]")
        for f in conflicts.git_conflicts:
            console.print(f"  [dim]-[/dim] {f}")

    # Display resolution hint
    if conflicts.resolution_hint:
        console.print(
            Panel(
                conflicts.resolution_hint,
                title="Resolution Hint",
                border_style="yellow",
            )
        )


@click.command(name="merge")
@click.argument("branch", required=False)
@click.option(
    "--abort",
    "do_abort",
    is_flag=True,
    default=False,
    help="Abort an in-progress merge",
)
@click.option(
    "--no-commit",
    is_flag=True,
    default=False,
    help="Merge but don't commit (for manual review)",
)
@click.option(
    "--squash",
    is_flag=True,
    default=False,
    help="Squash commits during merge",
)
@click.option(
    "-m",
    "--message",
    type=str,
    default=None,
    help="Custom merge commit message",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Output as JSON",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Check for conflicts without merging",
)
def merge_cmd(
    branch: str | None,
    do_abort: bool,
    no_commit: bool,
    squash: bool,
    message: str | None,
    as_json: bool,
    dry_run: bool,
):
    """Merge a branch into the current branch in both Git and Dolt.

    This command performs an atomic merge across Git and Dolt:

    1. First, Dolt is merged (with conflict check)
    2. If Dolt succeeds, Git is merged
    3. If Git fails, Dolt changes are rolled back

    \b
    Exit codes:
      0 - merge successful
      1 - Dolt conflicts (merge aborted)
      2 - Git conflicts (Dolt rolled back)
      3 - rollback failed (manual intervention needed)

    \b
    Examples:
      kurt merge feature/my-feature      # Merge feature into current
      kurt merge feature --squash        # Squash merge
      kurt merge feature --no-commit     # Merge without committing
      kurt merge feature --dry-run       # Check for conflicts
      kurt merge --abort                 # Abort in-progress merge
    """
    # Handle --abort
    if do_abort:
        _handle_abort(as_json)
        return

    # Branch is required if not aborting
    if not branch:
        console.print("[red]Error: Branch name required[/red]")
        console.print("[dim]Usage: kurt merge <branch>[/dim]")
        sys.exit(1)

    try:
        dolt_db = _get_dolt_db()
        git_path = _get_git_path()

        # Handle --dry-run (conflict check only)
        if dry_run:
            _handle_dry_run(branch, git_path, dolt_db, as_json)
            return

        # Perform merge
        result = merge_branch(
            source=branch,
            git_path=git_path,
            dolt_db=dolt_db,
            no_commit=no_commit,
            squash=squash,
            message=message,
        )

        # Success output
        if as_json:
            data = {
                "success": True,
                "source_branch": result.source_branch,
                "target_branch": result.target_branch,
                "dolt_commit_hash": result.dolt_commit_hash,
                "git_commit_hash": result.git_commit_hash,
                "message": result.message,
            }
            console.print(json_module.dumps(data, indent=2))
        else:
            console.print(f"[green]{result.message}[/green]")
            if result.dolt_commit_hash:
                console.print(f"[dim]Dolt commit: {result.dolt_commit_hash}[/dim]")
            if result.git_commit_hash:
                console.print(f"[dim]Git commit: {result.git_commit_hash[:7]}[/dim]")

        sys.exit(MergeExitCode.SUCCESS)

    except MergeError as e:
        _handle_merge_error(e, as_json)


def _handle_abort(as_json: bool) -> None:
    """Handle --abort flag."""
    try:
        dolt_db = _get_dolt_db()
        git_path = _get_git_path()

        success = abort_merge(git_path, dolt_db)

        if as_json:
            console.print(json_module.dumps({"aborted": success}))
        else:
            if success:
                console.print("[green]Merge aborted[/green]")
            else:
                console.print("[yellow]No merge in progress or abort failed[/yellow]")

    except Exception as e:
        if as_json:
            console.print(json_module.dumps({"error": str(e)}))
        else:
            console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def _handle_dry_run(branch: str, git_path: Path, dolt_db, as_json: bool) -> None:
    """Handle --dry-run flag (conflict check)."""
    from kurt.isolation.branch import _git_current_branch

    target = _git_current_branch(git_path) or "main"

    try:
        conflicts = check_conflicts(
            source=branch,
            target=target,
            git_path=git_path,
            dolt_db=dolt_db,
        )

        has_conflicts = bool(conflicts.dolt_conflicts or conflicts.git_conflicts)

        if as_json:
            data = {
                "has_conflicts": has_conflicts,
                "dolt_conflicts": [
                    {"table": c.table, "key": c.key}
                    for c in conflicts.dolt_conflicts
                ],
                "git_conflicts": conflicts.git_conflicts,
            }
            console.print(json_module.dumps(data, indent=2))
        else:
            if has_conflicts:
                console.print(
                    f"[yellow]Conflicts detected when merging '{branch}' into '{target}'[/yellow]"
                )
                _format_conflicts(conflicts)
            else:
                console.print(
                    f"[green]No conflicts detected. '{branch}' can be merged into '{target}'[/green]"
                )

    except MergeError as e:
        if as_json:
            console.print(json_module.dumps({"error": e.message}))
        else:
            console.print(f"[red]Error: {e.message}[/red]")
        sys.exit(1)


def _handle_merge_error(error: MergeError, as_json: bool) -> None:
    """Handle MergeError and exit with appropriate code."""
    if as_json:
        data = {
            "success": False,
            "error_code": error.code.value,
            "message": error.message,
        }
        if error.conflicts:
            data["conflicts"] = {
                "dolt_conflicts": [
                    {
                        "table": c.table,
                        "key": c.key,
                        "ours": c.ours,
                        "theirs": c.theirs,
                    }
                    for c in error.conflicts.dolt_conflicts
                ],
                "git_conflicts": error.conflicts.git_conflicts,
                "resolution_hint": error.conflicts.resolution_hint,
            }
        console.print(json_module.dumps(data, indent=2))
    else:
        console.print(f"[red]Error: {error.message}[/red]")
        if error.conflicts:
            _format_conflicts(error.conflicts)

    # Exit with appropriate code
    if error.code == MergeErrorCode.DOLT_CONFLICT:
        sys.exit(MergeExitCode.DOLT_CONFLICTS)
    elif error.code == MergeErrorCode.GIT_CONFLICT:
        sys.exit(MergeExitCode.GIT_CONFLICTS)
    elif error.code == MergeErrorCode.ROLLBACK_FAILED:
        sys.exit(MergeExitCode.ROLLBACK_FAILED)
    else:
        sys.exit(1)
