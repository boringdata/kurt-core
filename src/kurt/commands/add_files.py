"""File-based content addition - handles single files and directories of .md files."""

from pathlib import Path

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

console = Console()


def handle_file_add(
    source: str,
    *,
    fetch_only: bool = False,
    dry_run: bool = False,
    limit: int = None,
    force: bool = False,
):
    """
    Handle adding content from local files or directories.

    Args:
        source: File path or directory path
        fetch_only: Only add files, skip indexing with LLM
        dry_run: Preview only, no changes
        limit: Maximum number of files to process
        force: Skip confirmation prompts
    """
    from kurt.ingestion.add_files import add_directory, add_single_file, should_confirm_file_batch
    from kurt.ingestion.source_detection import detect_source_type, discover_markdown_files

    source_type = detect_source_type(source)

    # Single file
    if source_type == "file":
        file_path = Path(source)

        if dry_run:
            console.print(f"[cyan]Would add file:[/cyan] {file_path}")
            console.print("[dim]Type:[/dim] Markdown file")
            return

        console.print(f"[cyan]Adding file:[/cyan] {file_path}")

        try:
            result = add_single_file(
                file_path,
                index=(not fetch_only),
            )

            if result.get("skipped"):
                console.print(f"[yellow]Skipped:[/yellow] {result['reason']}")
                return

            console.print(f"[green]✓[/green] Created document: {result['doc_id']}")
            console.print(f"  Title: {result['title']}")
            console.print(f"  Content: {result['content_length']} characters")

            if result.get("indexed"):
                index_result = result["index_result"]
                console.print(f"[green]✓[/green] Indexed: {index_result['content_type']}")
                if index_result.get("topics"):
                    console.print(f"  Topics: {', '.join(index_result['topics'][:3])}")

            console.print(f"\n[green]✓ Done![/green] Document ID: [cyan]{result['doc_id']}[/cyan]")

        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise click.Abort()

    # Directory
    elif source_type == "directory":
        directory = Path(source)

        # Discover files for preview
        md_files = discover_markdown_files(directory, recursive=True)

        if not md_files:
            console.print(f"[yellow]No markdown files found in:[/yellow] {directory}")
            return

        # Apply limit if specified
        if limit:
            md_files = md_files[:limit]

        if dry_run:
            console.print(
                f"[cyan]Would add {len(md_files)} markdown files from:[/cyan] {directory}"
            )
            console.print("\n[bold]Files:[/bold]")
            for file_path in md_files[:10]:
                console.print(f"  • {file_path.relative_to(directory)}")
            if len(md_files) > 10:
                console.print(f"  ... and {len(md_files) - 10} more")
            return

        console.print(f"[cyan]Discovered {len(md_files)} markdown files in:[/cyan] {directory}\n")

        # Show confirmation if needed
        if should_confirm_file_batch(len(md_files), force):
            console.print(f"[yellow]This will add {len(md_files)} markdown files.[/yellow]\n")

            # Show sample files
            console.print("[bold]Sample files:[/bold]")
            for file_path in md_files[:5]:
                console.print(f"  • {file_path.relative_to(directory)}")
            if len(md_files) > 5:
                console.print(f"  ... and {len(md_files) - 5} more")

            if not click.confirm("\nContinue?", default=False):
                console.print("[yellow]Aborted[/yellow]")
                return

        # Add directory
        console.print("\n[cyan]Adding files...[/cyan]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Processing files...", total=len(md_files))

            result = add_directory(
                directory,
                recursive=True,
                index=(not fetch_only),
            )

            progress.update(task, completed=len(md_files))

        # Display results
        console.print(f"\n[green]✓ Created:[/green] {result['created']} new documents")
        if result["skipped"] > 0:
            console.print(f"[yellow]Skipped:[/yellow] {result['skipped']} duplicates")
        if result["errors"] > 0:
            console.print(f"[red]✗ Errors:[/red] {result['errors']} files")

        if result["indexed"] > 0:
            console.print(f"[green]✓ Indexed:[/green] {result['indexed']} documents")

        # Show errors if any
        errors = [f for f in result["files"] if "error" in f]
        if errors:
            console.print("\n[bold red]Errors:[/bold red]")
            for error_file in errors[:3]:
                console.print(f"  [dim]{error_file['path']}: {error_file['error']}[/dim]")

        console.print("\n[bold green]✓ Done![/bold green]")
        console.print(f"  Total: {result['total']} files")
        console.print(f"  Created: {result['created']} documents")
        console.print(f"  Indexed: {result['indexed']} documents")
