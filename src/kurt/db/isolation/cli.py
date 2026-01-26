"""Git+Dolt version control CLI commands.

Provides commands for managing synchronized Git+Dolt:
- sync pull: Pull from Git and Dolt remotes
- sync push: Push to Git and Dolt remotes
- sync branch: Branch management (create, list, switch, delete)
- sync merge: Merge branches atomically
"""

from __future__ import annotations

import json as json_module
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from kurt.db.isolation import (
    BranchSyncError,
    MergeConflict,
    MergeError,
    MergeErrorCode,
    MergeExitCode,
    RemoteError,
    abort_merge,
    check_conflicts,
    create_both,
    delete_both,
    list_branches,
    merge_branch,
    pull,
    push,
    switch_both,
)

console = Console()


# =============================================================================
# Helpers
# =============================================================================


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


# =============================================================================
# Branch Commands
# =============================================================================


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
def branch_create_cmd(name: str, no_switch: bool):
    """Create a new branch in both Git and Dolt.

    Creates the branch in Git first, then in Dolt. If creation fails in Dolt,
    the Git branch is rolled back to maintain consistency.

    Branch naming conventions (suggestions, not enforced):
    - main: default branch
    - feature/<name>: feature work
    - agent/<task_id>: agent-created branches
    - user/<username>/<name>: user experiments

    Example:
        kurt sync branch create feature/my-feature
        kurt sync branch create --no-switch experiment/test
    """
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
def branch_list_cmd(as_json: bool):
    """List branches with sync status.

    Shows all branches from both Git and Dolt, with their sync status.

    Output columns:
    - Branch: Name (current branch marked with *)
    - Sync: Whether branch exists in both systems
    - Git: Git commit hash (or --- if missing)
    - Dolt: Dolt commit hash (or --- if missing)
    - Status: clean, git missing, or dolt missing

    Example:
        kurt sync branch list
        kurt sync branch list --json
    """
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
def branch_switch_cmd(name: str, force: bool):
    """Switch to a branch in both Git and Dolt.

    Switches Git first, then Dolt. If the branch exists in one system but
    not the other, it will be created in the missing system.

    Example:
        kurt sync branch switch feature/my-feature
        kurt sync branch switch main --force
    """
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
def branch_delete_cmd(name: str, force: bool, yes: bool):
    """Delete a branch from both Git and Dolt.

    Deletes the branch from Git first, then from Dolt.
    Cannot delete the current branch or 'main' (unless --force --force).

    Example:
        kurt sync branch delete feature/old-feature
        kurt sync branch delete feature/old-feature --force --yes
    """
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


# =============================================================================
# Merge Command
# =============================================================================


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
      kurt sync merge feature/my-feature      # Merge feature into current
      kurt sync merge feature --squash        # Squash merge
      kurt sync merge feature --no-commit     # Merge without committing
      kurt sync merge feature --dry-run       # Check for conflicts
      kurt sync merge --abort                 # Abort in-progress merge
    """
    # Handle --abort
    if do_abort:
        _handle_abort(as_json)
        return

    # Branch is required if not aborting
    if not branch:
        console.print("[red]Error: Branch name required[/red]")
        console.print("[dim]Usage: kurt sync merge <branch>[/dim]")
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
    from kurt.db.isolation.branch import _git_current_branch

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


# =============================================================================
# Remote Commands (Pull/Push)
# =============================================================================


@click.command(name="pull")
@click.option(
    "--remote",
    "-r",
    default="origin",
    help="Remote name (default: origin)",
)
@click.option(
    "--git-only",
    is_flag=True,
    default=False,
    help="Only pull from Git",
)
@click.option(
    "--dolt-only",
    is_flag=True,
    default=False,
    help="Only pull from Dolt",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Output as JSON",
)
def pull_cmd(remote: str, git_only: bool, dolt_only: bool, as_json: bool):
    """Pull changes from Git and Dolt remotes.

    Pulls in this order:
    1. git fetch (get refs, don't merge)
    2. dolt pull (merge Dolt first - cell-level conflicts easier)
    3. git pull (merge Git - line-level conflicts)

    If a conflict occurs, the operation stops and reports the conflict.
    Resolve conflicts manually, then re-run pull.

    Examples:
        kurt sync pull
        kurt sync pull --remote upstream
        kurt sync pull --dolt-only
        kurt sync pull --git-only
    """
    if git_only and dolt_only:
        console.print("[red]Error: Cannot use both --git-only and --dolt-only[/red]")
        raise click.Abort()

    try:
        dolt_db = _get_dolt_db()
        git_path = _get_git_path()

        result = pull(
            git_path=git_path,
            dolt_db=dolt_db,
            remote=remote,
            git_only=git_only,
            dolt_only=dolt_only,
        )

        if as_json:
            console.print(json_module.dumps(result.to_dict(), indent=2))
            return

        # Display results
        console.print()
        if not dolt_only:
            if result.git.status == "success":
                commits = result.git.commits_pulled
                if commits > 0:
                    console.print(f"[green]Git: Pulled {commits} commit(s)[/green]")
                else:
                    console.print("[green]Git: Already up to date[/green]")
            elif result.git.status == "error":
                console.print(f"[red]Git: {result.git.error}[/red]")

        if not git_only:
            if result.dolt.status == "success":
                commits = result.dolt.commits_pulled
                if commits > 0:
                    console.print(f"[green]Dolt: Pulled {commits} commit(s)[/green]")
                else:
                    console.print("[green]Dolt: Already up to date[/green]")
            elif result.dolt.status == "error":
                console.print(f"[red]Dolt: {result.dolt.error}[/red]")

        console.print()

    except RemoteError as e:
        if as_json:
            error_dict = {
                "error": {
                    "code": e.code.value,
                    "message": e.message,
                    "details": e.details,
                    "suggestion": e.suggestion,
                }
            }
            console.print(json_module.dumps(error_dict, indent=2))
        else:
            console.print(f"[red]Error: {e.message}[/red]")
            if e.details:
                console.print(f"[dim]{e.details}[/dim]")
            if e.suggestion:
                console.print(f"[yellow]Suggestion: {e.suggestion}[/yellow]")
        raise click.Abort()


@click.command(name="push")
@click.option(
    "--remote",
    "-r",
    default="origin",
    help="Remote name (default: origin)",
)
@click.option(
    "--git-only",
    is_flag=True,
    default=False,
    help="Only push to Git",
)
@click.option(
    "--dolt-only",
    is_flag=True,
    default=False,
    help="Only push to Dolt",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    default=False,
    help="Output as JSON",
)
def push_cmd(remote: str, git_only: bool, dolt_only: bool, as_json: bool):
    """Push changes to Git and Dolt remotes.

    Pushes in this order:
    1. dolt push (push data first)
    2. git push (push code)

    If Dolt push fails, the operation stops with an error.
    If Git push fails after Dolt succeeds, a warning is shown
    but the Dolt push is NOT rolled back.

    Examples:
        kurt sync push
        kurt sync push --remote upstream
        kurt sync push --dolt-only
        kurt sync push --git-only
    """
    if git_only and dolt_only:
        console.print("[red]Error: Cannot use both --git-only and --dolt-only[/red]")
        raise click.Abort()

    try:
        dolt_db = _get_dolt_db()
        git_path = _get_git_path()

        result = push(
            git_path=git_path,
            dolt_db=dolt_db,
            remote=remote,
            git_only=git_only,
            dolt_only=dolt_only,
        )

        if as_json:
            console.print(json_module.dumps(result.to_dict(), indent=2))
            return

        # Display results
        console.print()
        if not git_only:
            if result.dolt.status == "success":
                commits = result.dolt.commits_pushed
                if commits > 0:
                    console.print(f"[green]Dolt: Pushed {commits} commit(s)[/green]")
                else:
                    console.print("[green]Dolt: Already up to date[/green]")
            elif result.dolt.status == "error":
                console.print(f"[red]Dolt: {result.dolt.error}[/red]")

        if not dolt_only:
            if result.git.status == "success":
                commits = result.git.commits_pushed
                if commits > 0:
                    console.print(f"[green]Git: Pushed {commits} commit(s)[/green]")
                else:
                    console.print("[green]Git: Already up to date[/green]")
            elif result.git.status == "error":
                console.print(
                    "[yellow]Warning: Git push failed (Dolt push succeeded)[/yellow]"
                )
                console.print(f"[dim]{result.git.error}[/dim]")
                console.print("[dim]Run 'git push' manually to sync Git[/dim]")

        console.print()

    except RemoteError as e:
        if as_json:
            error_dict = {
                "error": {
                    "code": e.code.value,
                    "message": e.message,
                    "details": e.details,
                    "suggestion": e.suggestion,
                }
            }
            console.print(json_module.dumps(error_dict, indent=2))
        else:
            console.print(f"[red]Error: {e.message}[/red]")
            if e.details:
                console.print(f"[dim]{e.details}[/dim]")
            if e.suggestion:
                console.print(f"[yellow]Suggestion: {e.suggestion}[/yellow]")
        raise click.Abort()


# =============================================================================
# Main Sync Group
# =============================================================================


@click.group(name="sync")
def sync_group():
    """
    Git+Dolt version control operations.

    \b
    Commands:
      pull     Pull changes from remote
      push     Push changes to remote
      branch   Branch management
      merge    Merge branches
    """
    pass


sync_group.add_command(pull_cmd, name="pull")
sync_group.add_command(push_cmd, name="push")
sync_group.add_command(branch_group, name="branch")
sync_group.add_command(merge_cmd, name="merge")


__all__ = [
    "sync_group",
    "branch_group",
    "pull_cmd",
    "push_cmd",
    "merge_cmd",
]
