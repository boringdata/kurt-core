"""CLI commands for document management.

This module aggregates all content-related commands:
- Document listing/viewing (list, get, delete)
- Workflow commands imported from their respective modules
"""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

from kurt.admin.telemetry.decorators import track_command
from kurt.tools.core import (
    add_confirmation_options,
    add_filter_options,
    format_option,
    format_table_option,
    print_json,
)

console = Console()


@click.group()
def content_group():
    """
    Document management commands.

    \b
    Commands:
      list     List documents with filters
      get      Get document details
      delete   Delete documents

    \b
    Note: Use 'kurt tool map' and 'kurt tool fetch' for content discovery and fetching.
    """
    pass


# =============================================================================
# Document Commands
# =============================================================================


@content_group.command("list")
@add_filter_options()
@format_table_option
@track_command
def list_cmd(
    include_pattern: str | None,
    url_contains: str | None,
    ids: str | None,
    in_cluster: str | None,
    with_status: str | None,
    with_content_type: str | None,
    limit: int | None,
    output_format: str,
):
    """
    List documents with filters.

    \b
    Examples:
        kurt content list                           # List all documents
        kurt content list --limit 10                # List first 10
        kurt content list --with-status FETCHED     # List fetched documents
        kurt content list --format json             # JSON output for agents
    """
    from kurt.documents import DocumentFilters
    from kurt.tools.fetch.models import FetchStatus

    # Build filters
    filters = DocumentFilters(
        ids=ids.split(",") if ids else None,
        include=include_pattern,
        url_contains=url_contains,
        limit=limit,
    )

    # Map CLI status to internal status
    if with_status:
        status_map = {
            "NOT_FETCHED": None,  # Will use not_fetched flag
            "FETCHED": FetchStatus.SUCCESS,
            "ERROR": FetchStatus.ERROR,
        }
        if with_status.upper() == "NOT_FETCHED":
            filters.not_fetched = True
        else:
            filters.fetch_status = status_map.get(with_status.upper())

    # Query documents (routes to local or cloud)
    docs = _list_documents(filters)

    if output_format == "json":
        print_json([_doc_to_dict(d) for d in docs])
        return

    if not docs:
        console.print("[dim]No documents found[/dim]")
        return

    # Display as table - use no_wrap to prevent broken rows in narrow terminals
    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="dim", width=8, no_wrap=True)
    table.add_column("Source URL", overflow="ellipsis", no_wrap=True)
    table.add_column("Map", width=10, no_wrap=True)
    table.add_column("Fetch", width=10, no_wrap=True)
    table.add_column("Length", width=8, justify="right", no_wrap=True)

    for doc in docs:
        table.add_row(
            doc.document_id[:8] if doc.document_id else "-",
            _truncate(doc.source_url, 50),
            _status_style(doc.map_status),
            _status_style(doc.fetch_status),
            str(doc.content_length or "-"),
        )

    console.print(table)
    console.print(f"\n[dim]Total: {len(docs)} document(s)[/dim]")


@content_group.command("get")
@click.argument("identifier")
@format_option
@track_command
def get_cmd(identifier: str, output_format: str):
    """
    Get document details by ID or URL.

    \b
    Examples:
        kurt content get abc123              # Get by partial ID
        kurt content get https://example.com # Get by URL
    """
    # Query document (routes to local or cloud)
    doc = _get_document(identifier)

    if not doc:
        if output_format == "json":
            print_json({"error": "Document not found", "identifier": identifier})
        else:
            console.print(f"[red]Document not found:[/red] {identifier}")
        return

    if output_format == "json":
        print_json(_doc_to_dict(doc))
        return

    # Display details
    console.print(f"[bold]Document {doc.document_id}[/bold]\n")
    console.print(f"  Source URL:    {doc.source_url}")
    console.print(f"  Source Type:   {doc.source_type or '-'}")
    console.print(f"  Title:         {doc.title or '-'}")
    console.print()
    console.print(f"  Map Status:    {_status_style(doc.map_status)}")
    console.print(f"  Discovery:     {doc.discovery_method or '-'}")
    console.print(f"  Discovered:    {doc.discovered_at or '-'}")
    console.print()
    console.print(f"  Fetch Status:  {_status_style(doc.fetch_status)}")
    console.print(f"  Fetch Engine:  {doc.fetch_engine or '-'}")
    console.print(f"  Content Len:   {doc.content_length or '-'}")
    console.print(f"  Fetched:       {doc.fetched_at or '-'}")

    if doc.error:
        console.print()
        console.print(f"  [red]Error:[/red] {doc.error}")


@content_group.command("delete")
@click.argument("identifier", required=False)
@add_filter_options(cluster=False, status=False, content_type=False)
@add_confirmation_options()
@track_command
def delete_cmd(
    identifier: str | None,
    include_pattern: str | None,
    ids: str | None,
    url_contains: str | None,
    limit: int | None,
    dry_run: bool,
    yes_flag: bool,
):
    """
    Delete documents by ID, URL pattern, or filters.

    \b
    Examples:
        kurt content delete abc123           # Delete by ID
        kurt content delete --ids a,b,c      # Delete multiple IDs
        kurt content delete --include "*test*" --dry-run  # Preview deletion
    """
    from kurt.documents import DocumentFilters
    from kurt.documents.dolt_registry import delete_documents_dolt, list_documents_dolt

    # Build filters
    filters = DocumentFilters(
        ids=[identifier] if identifier else (ids.split(",") if ids else None),
        include=include_pattern,
        url_contains=url_contains,
        limit=limit,
    )

    # Get documents to delete
    docs = list_documents_dolt(filters)

    if not docs:
        console.print("[dim]No documents found matching criteria[/dim]")
        return

    console.print(f"[dim]Found {len(docs)} document(s) to delete[/dim]")

    if dry_run:
        for doc in docs[:10]:
            console.print(f"  [dim]-[/dim] {doc.document_id[:8]} {_truncate(doc.source_url, 50)}")
        if len(docs) > 10:
            console.print(f"  [dim]... and {len(docs) - 10} more[/dim]")
        console.print("\n[dim]Dry run - no documents were deleted[/dim]")
        return

    if not yes_flag:
        if not click.confirm(f"Delete {len(docs)} document(s)?"):
            console.print("[dim]Cancelled[/dim]")
            return

    # Delete documents from Dolt
    doc_ids = [doc.document_id for doc in docs]
    deleted_count = delete_documents_dolt(doc_ids)

    console.print(f"[green]✓[/green] Deleted {deleted_count} document(s)")


# =============================================================================
# Helpers
# =============================================================================


def _list_documents(filters):
    """
    List documents from Dolt database.

    In Dolt-only architecture, we query directly from Dolt tables.
    """
    from kurt.documents.dolt_registry import list_documents_dolt

    return list_documents_dolt(filters)


def _get_document(identifier: str):
    """
    Get document by ID from Dolt database.

    In Dolt-only architecture, we query directly from Dolt tables.
    """
    from kurt.documents.dolt_registry import get_document_dolt

    return get_document_dolt(identifier)


def _doc_to_dict(doc) -> dict:
    """Convert DocumentView to dict for JSON output."""
    return {
        "document_id": doc.document_id,
        "source_url": doc.source_url,
        "source_type": doc.source_type,
        "title": doc.title,
        "map_status": str(doc.map_status) if doc.map_status else None,
        "fetch_status": str(doc.fetch_status) if doc.fetch_status else None,
        "content_length": doc.content_length,
        "error": doc.error,
        "discovered_at": str(doc.discovered_at) if doc.discovered_at else None,
        "fetched_at": str(doc.fetched_at) if doc.fetched_at else None,
    }


def _truncate(s: str | None, max_len: int) -> str:
    """Truncate string with ellipsis."""
    if not s:
        return "-"
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def _status_style(status) -> str:
    """Format status with color."""
    if status is None:
        return "[dim]-[/dim]"
    s = str(status)
    if "SUCCESS" in s or "DISCOVERED" in s:
        return f"[green]{s}[/green]"
    if "ERROR" in s or "FAILED" in s:
        return f"[red]{s}[/red]"
    if "PENDING" in s:
        return f"[yellow]{s}[/yellow]"
    return s


# =============================================================================
# Command Groups
# =============================================================================


@click.group(name="docs")
def docs_group():
    """
    Document management commands.

    \b
    Commands:
      list     List documents with filters
      get      Get document details
      delete   Delete documents
    """
    pass


docs_group.add_command(list_cmd, name="list")
docs_group.add_command(get_cmd, name="get")
docs_group.add_command(delete_cmd, name="delete")
