"""CLI command for fetch workflow."""

from __future__ import annotations

import click
from rich.console import Console

from kurt_new.admin.telemetry.decorators import track_command
from kurt_new.cli.options import (
    add_background_options,
    add_filter_options,
    dry_run_option,
    format_option,
)
from kurt_new.cli.output import print_json, print_workflow_status

console = Console()


@click.command("fetch")
@click.argument("identifier", required=False)
@add_filter_options(advanced=True, exclude=True)
@add_background_options()
@dry_run_option
@format_option
@track_command
def fetch_cmd(
    identifier: str | None,
    include_pattern: str | None,
    ids: str | None,
    in_cluster: str | None,
    with_status: str | None,
    with_content_type: str | None,
    limit: int | None,
    exclude_pattern: str | None,
    url_contains: str | None,
    file_ext: str | None,
    source_type: str | None,
    has_content: bool | None,
    min_content_length: int | None,
    fetch_engine: str | None,
    background: bool,
    priority: int,
    dry_run: bool,
    output_format: str,
):
    """
    Fetch and index documents from URLs or local files.

    \b
    Examples:
        kurt content fetch                           # Fetch all NOT_FETCHED documents
        kurt content fetch --limit 10                # Fetch first 10 documents
        kurt content fetch --include "*.md"          # Fetch markdown files
        kurt content fetch --dry-run                 # Preview without fetching

    \b
    Advanced Filtering:
        kurt content fetch --url-contains "/docs/"   # URLs containing /docs/
        kurt content fetch --file-ext md             # Only .md files
        kurt content fetch --source-type url         # Only web URLs
        kurt content fetch --exclude "*internal*"    # Exclude internal paths
        kurt content fetch --has-content             # Only docs with content
        kurt content fetch --min-content-length 100  # Min 100 chars
    """
    from kurt_new.documents import resolve_documents

    from .config import FetchConfig
    from .workflow import run_fetch

    # Resolve documents to fetch
    docs = resolve_documents(
        identifier=identifier,
        include_pattern=include_pattern,
        ids=ids,
        in_cluster=in_cluster,
        with_status=with_status or "NOT_FETCHED",  # Default to NOT_FETCHED
        with_content_type=with_content_type,
        limit=limit,
        exclude_pattern=exclude_pattern,
        url_contains=url_contains,
        file_ext=file_ext,
        source_type=source_type,
        has_content=has_content,
        min_content_length=min_content_length,
        fetch_engine=fetch_engine,
    )

    if not docs:
        if output_format == "json":
            print_json(
                {"status": "no_documents", "message": "No documents found matching criteria"}
            )
        else:
            console.print("[yellow]No documents found matching criteria[/yellow]")
        return

    if output_format != "json":
        console.print(f"[dim]Found {len(docs)} document(s) to fetch[/dim]")

    # Build config
    config = FetchConfig.from_config("fetch", dry_run=dry_run)

    # Run workflow
    result = run_fetch(docs, config, background=background, priority=priority)

    # Output result
    # When background=True, result is a string (workflow_id) or None
    # When background=False, result is a dict with workflow results
    if isinstance(result, str):
        # Background mode - result is workflow_id
        if output_format == "json":
            print_json({"workflow_id": result, "background": True})
        else:
            print_workflow_status(result)
    elif output_format == "json":
        print_json(result)
    else:
        workflow_id = result.get("workflow_id") if result else None
        if workflow_id:
            print_workflow_status(workflow_id)
        else:
            # Fallback for direct result
            console.print(f"[green]✓[/green] Fetched {result.get('success_count', 0)} documents")
            if result.get("error_count", 0) > 0:
                console.print(f"[red]✗[/red] {result.get('error_count')} errors")
