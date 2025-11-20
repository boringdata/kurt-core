"""Main orchestration for update process."""

import difflib
import shutil
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .detector import FileUpdate, detect_updates
from .hasher import record_installed_file
from .merger import apply_settings_merge

console = Console()


def show_update_summary(summary) -> None:
    """Display a summary of available updates."""
    from kurt import __version__

    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]Kurt Update Check[/bold cyan]\n"
            f"[dim]Current version: {__version__}[/dim]",
            border_style="cyan",
        )
    )
    console.print()

    # Group files by category
    categories = {}
    for file_list in [summary.needs_update, summary.modified_locally]:
        for file in file_list:
            if file.category not in categories:
                categories[file.category] = {
                    "needs_update": [],
                    "modified_locally": [],
                }
            categories[file.category][file.status].append(file)

    if not summary.needs_update and not summary.modified_locally:
        console.print("[green]✓ All plugin files are up to date[/green]")
        console.print()
        return

    # Create summary table
    table = Table(title="Updates Available", show_header=True)
    table.add_column("Component", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Files", justify="right")

    category_names = {
        "claude_main": "Claude Code (CLAUDE.md)",
        "claude_instructions": "Claude Instructions",
        "claude_commands": "Claude Commands",
        "cursor_rules": "Cursor Rules",
        "templates": "Shared Templates (kurt/)",
    }

    for category, files in categories.items():
        needs = len(files["needs_update"])
        modified = len(files["modified_locally"])

        if needs + modified == 0:
            continue

        status_parts = []
        if needs > 0:
            status_parts.append(f"[green]{needs} to update[/green]")
        if modified > 0:
            status_parts.append(f"[yellow]{modified} modified[/yellow]")

        status = ", ".join(status_parts)
        total = needs + modified

        table.add_row(category_names.get(category, category), status, str(total))

    console.print(table)
    console.print()

    # Show user-created files preservation
    if summary.user_created:
        console.print(
            f"[dim]Note: {len(summary.user_created)} custom file(s) will be preserved[/dim]"
        )
        console.print()


def show_file_diff(file: FileUpdate) -> None:
    """Display diff between local and package file."""
    console.print()
    console.print(f"[bold]Diff for {file.rel_path}:[/bold]")
    console.print()

    try:
        with open(file.local_path) as f:
            local_lines = f.readlines()
        with open(file.package_path) as f:
            package_lines = f.readlines()

        diff = difflib.unified_diff(
            local_lines,
            package_lines,
            fromfile=f"current/{file.rel_path}",
            tofile=f"updated/{file.rel_path}",
            lineterm="",
        )

        for line in diff:
            if line.startswith("+++") or line.startswith("---"):
                console.print(f"[bold]{line}[/bold]")
            elif line.startswith("+"):
                console.print(f"[green]{line}[/green]")
            elif line.startswith("-"):
                console.print(f"[red]{line}[/red]")
            elif line.startswith("@@"):
                console.print(f"[cyan]{line}[/cyan]")
            else:
                console.print(f"[dim]{line}[/dim]")

    except Exception as e:
        console.print(f"[red]Error showing diff: {e}[/red]")

    console.print()


def prompt_for_update(file: FileUpdate, auto_confirm: bool = False) -> str:
    """
    Prompt user whether to update a file.

    Args:
        file: FileUpdate object
        auto_confirm: If True, auto-confirm (for --yes mode)

    Returns:
        User's choice: "y", "n", or "diff"
    """
    if auto_confirm:
        return "y"

    status_msg = ""
    if file.status == "modified_locally":
        status_msg = " [yellow](modified locally)[/yellow]"

    prompt = f"Update {file.rel_path}{status_msg}? (y/N/diff): "
    response = console.input(prompt).strip().lower()

    return response


def apply_file_update(file: FileUpdate) -> None:
    """Apply an update by copying package file to local."""
    # Ensure parent directory exists
    file.local_path.parent.mkdir(parents=True, exist_ok=True)

    # Copy file
    shutil.copy2(file.package_path, file.local_path)

    # Record installation
    from kurt import __version__

    record_installed_file(file.rel_path, file.local_path, __version__)

    console.print(f"  [green]✓[/green] Updated {file.rel_path}")


def update_category(
    category: str, files: list[FileUpdate], auto_confirm: bool, dry_run: bool
) -> tuple[int, int]:
    """
    Update all files in a category.

    Returns:
        Tuple of (updated_count, skipped_count)
    """
    category_names = {
        "claude_main": "Claude Code Main File",
        "claude_instructions": "Claude Instructions",
        "claude_commands": "Claude Commands",
        "cursor_rules": "Cursor Rules",
        "templates": "Shared Templates",
    }

    if not files:
        return 0, 0

    console.print()
    console.print(f"[bold cyan]{category_names.get(category, category)}[/bold cyan]")

    updated = 0
    skipped = 0

    for file in files:
        while True:
            response = prompt_for_update(file, auto_confirm)

            if response == "diff":
                show_file_diff(file)
                continue  # Ask again
            elif response in ["y", "yes"]:
                if not dry_run:
                    apply_file_update(file)
                else:
                    console.print(f"  [dim]Would update {file.rel_path}[/dim]")
                updated += 1
                break
            else:
                console.print(f"  [dim]Skipped {file.rel_path}[/dim]")
                skipped += 1
                break

    return updated, skipped


def update_files(
    ide: str | None = None, auto_confirm: bool = False, dry_run: bool = False
) -> dict[str, int]:
    """
    Main update orchestration.

    Args:
        ide: Specific IDE to update ("claude", "cursor", or None for all)
        auto_confirm: Skip all prompts and update everything
        dry_run: Show what would be updated without applying changes

    Returns:
        Dict with update statistics
    """
    from kurt.config.base import config_file_exists

    # Check if project is initialized
    if not config_file_exists():
        console.print("[red]Error:[/red] Kurt project not initialized")
        console.print("Run [cyan]kurt init[/cyan] first")
        return {"error": 1}

    # Detect updates
    console.print("[dim]Checking for updates...[/dim]")
    summary = detect_updates()

    # Filter by IDE if specified
    if ide:
        summary.needs_update = [f for f in summary.needs_update if ide in f.category]
        summary.modified_locally = [f for f in summary.modified_locally if ide in f.category]

    # Show summary
    show_update_summary(summary)

    # If nothing to update, exit
    if not summary.needs_update and not summary.modified_locally:
        return {"updated": 0, "skipped": 0}

    # Confirm before proceeding
    if not auto_confirm and not dry_run:
        console.print("[bold]Proceed with updates?[/bold]")
        proceed = console.input("Continue? (y/N): ").strip().lower()
        if proceed not in ["y", "yes"]:
            console.print("[dim]Update cancelled[/dim]")
            return {"updated": 0, "skipped": 0, "cancelled": 1}

    # Group files by category
    categories = {}
    for file in summary.needs_update + summary.modified_locally:
        if file.category not in categories:
            categories[file.category] = []
        categories[file.category].append(file)

    # Update each category
    total_updated = 0
    total_skipped = 0

    for category in sorted(categories.keys()):
        files = categories[category]
        updated, skipped = update_category(category, files, auto_confirm, dry_run)
        total_updated += updated
        total_skipped += skipped

    # Handle settings.json separately (smart merge)
    if "claude" in [f.category for f in summary.needs_update + summary.modified_locally]:
        settings_local = Path.cwd() / ".claude" / "settings.json"
        settings_pkg = Path(__file__).parent.parent / "claude_plugin" / "settings.json"

        if settings_pkg.exists():
            console.print()
            console.print("[bold cyan]Claude Settings[/bold cyan]")

            if not auto_confirm:
                response = console.input("Merge settings.json? (Y/n): ").strip().lower()
            else:
                response = "y"

            if response in ["", "y", "yes"]:
                if not dry_run:
                    apply_settings_merge(settings_local, settings_pkg)
                    from kurt import __version__

                    record_installed_file(".claude/settings.json", settings_local, __version__)
                    console.print("  [green]✓[/green] Merged settings.json")
                else:
                    console.print("  [dim]Would merge settings.json[/dim]")
                total_updated += 1

    # Summary
    console.print()
    if dry_run:
        console.print(
            Panel.fit(
                f"[bold]Dry Run Complete[/bold]\n"
                f"Would update: {total_updated} file(s)\n"
                f"Would skip: {total_skipped} file(s)",
                border_style="yellow",
            )
        )
    else:
        console.print(
            Panel.fit(
                f"[bold green]Update Complete![/bold green]\n"
                f"Updated: {total_updated} file(s)\n"
                f"Skipped: {total_skipped} file(s)",
                border_style="green",
            )
        )
    console.print()

    return {
        "updated": total_updated,
        "skipped": total_skipped,
    }
