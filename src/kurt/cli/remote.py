"""Remote operations CLI commands.

Provides commands for syncing with Git and Dolt remotes:
- kurt pull: Pull from Git and Dolt remotes
- kurt push: Push to Git and Dolt remotes
"""

from __future__ import annotations

import json as json_module
from pathlib import Path

import click
from rich.console import Console

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
        kurt pull
        kurt pull --remote upstream
        kurt pull --dolt-only
        kurt pull --git-only
    """
    from kurt.isolation import RemoteError, pull

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
        kurt push
        kurt push --remote upstream
        kurt push --dolt-only
        kurt push --git-only
    """
    from kurt.isolation import RemoteError, push

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
