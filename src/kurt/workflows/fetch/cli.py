"""CLI command for fetch workflow."""

from __future__ import annotations

import os

import click
from rich.console import Console
from rich.table import Table

from kurt.admin.telemetry.decorators import track_command
from kurt.cli.options import (
    add_background_options,
    add_filter_options,
    dry_run_option,
    format_option,
)
from kurt.cli.output import print_json, print_workflow_status

console = Console()


def _check_engine_status(engine: str) -> tuple[str, str]:
    """Check if engine is ready (has required API key).

    Returns:
        Tuple of (status, message) where status is 'ready' or 'missing'
    """
    if engine == "trafilatura":
        return "ready", "Free local extraction (default)"
    elif engine == "httpx":
        return "ready", "HTTP + trafilatura (proxy-friendly)"
    elif engine == "firecrawl":
        if os.getenv("FIRECRAWL_API_KEY"):
            return "ready", "Firecrawl API"
        return "missing", "Set FIRECRAWL_API_KEY"
    elif engine == "tavily":
        if os.getenv("TAVILY_API_KEY"):
            return "ready", "Tavily Extract API"
        return "missing", "Set TAVILY_API_KEY"
    return "unknown", "Unknown engine"


def _list_engines(output_format: str) -> None:
    """List available fetch engines and their status."""
    engines = ["trafilatura", "httpx", "firecrawl", "tavily"]
    engine_info = []

    for engine in engines:
        status, description = _check_engine_status(engine)
        engine_info.append(
            {
                "engine": engine,
                "status": status,
                "description": description,
            }
        )

    if output_format == "json":
        print_json({"engines": engine_info})
        return

    # Rich table output
    table = Table(title="Available Fetch Engines")
    table.add_column("Engine", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Description")

    for info in engine_info:
        status_style = "green" if info["status"] == "ready" else "yellow"
        status_text = f"[{status_style}]{info['status']}[/{status_style}]"
        table.add_row(info["engine"], status_text, info["description"])

    console.print(table)
    console.print()
    console.print("[dim]Batch Support:[/dim]")
    console.print("  tavily     Up to 20 URLs per request")
    console.print("  firecrawl  Unlimited URLs per request")


@click.command("fetch")
@click.argument("identifier", required=False)
@add_filter_options(exclude=True)
@click.option("--url", "single_url", help="Single URL to fetch (auto-creates if doesn't exist)")
@click.option("--urls", help="Comma-separated list of URLs (auto-creates if don't exist)")
@click.option("--file", "single_file", help="Single local file path to fetch")
@click.option("--files", "files_paths", help="Comma-separated list of local file paths")
@click.option(
    "--engine",
    type=click.Choice(["firecrawl", "trafilatura", "httpx", "tavily"], case_sensitive=False),
    help="Fetch engine to use",
)
@click.option(
    "--batch-size",
    type=int,
    default=None,
    help="Batch size for engines with batch support (tavily: max 20, firecrawl: unlimited)",
)
@click.option("--list-engines", is_flag=True, help="List available engines and exit")
@click.option("--refetch", is_flag=True, help="Re-fetch already FETCHED documents")
@add_background_options()
@dry_run_option
@format_option
@track_command
def fetch_cmd(
    identifier: str | None,
    include_pattern: str | None,
    url_contains: str | None,
    ids: str | None,
    in_cluster: str | None,
    with_status: str | None,
    with_content_type: str | None,
    limit: int | None,
    exclude_pattern: str | None,
    single_url: str | None,
    urls: str | None,
    single_file: str | None,
    files_paths: str | None,
    engine: str | None,
    batch_size: int | None,
    list_engines: bool,
    refetch: bool,
    background: bool,
    priority: int,
    dry_run: bool,
    output_format: str,
):
    """
    Fetch and index documents from URLs or local files.

    \b
    Engines:
      trafilatura   Free, local extraction (default)
      httpx         HTTP fetch + trafilatura (respects proxies)
      firecrawl     Firecrawl API - requires FIRECRAWL_API_KEY
      tavily        Tavily Extract API - requires TAVILY_API_KEY

    \b
    Examples:
      kurt content fetch                              # Fetch all pending docs
      kurt content fetch --url "https://..."          # Single URL
      kurt content fetch --engine tavily --url "..."  # Use Tavily
      kurt content fetch --list-engines               # Show available engines

    \b
    Filtering:
      kurt content fetch --limit 10                   # Fetch first 10 documents
      kurt content fetch --include "*.md"             # Fetch markdown files
      kurt content fetch --url-contains "/docs/"      # URLs containing /docs/
      kurt content fetch --source-type url            # Only web URLs
      kurt content fetch --refetch                    # Re-fetch already fetched
    """
    # Handle --list-engines early exit
    if list_engines:
        _list_engines(output_format)
        return

    from kurt.documents import resolve_documents

    from .config import FetchConfig
    from .workflow import run_fetch

    # Merge --url into --urls for backward compatibility
    if single_url:
        urls = f"{urls},{single_url}" if urls else single_url

    # Merge --file into --files for backward compatibility
    if single_file:
        files_paths = f"{files_paths},{single_file}" if files_paths else single_file

    # Handle --urls: auto-create documents if they don't exist
    if urls:
        import hashlib

        from kurt.db import managed_session
        from kurt.workflows.map.models import MapDocument, MapStatus

        url_list = [u.strip() for u in urls.split(",") if u.strip()]
        with managed_session() as session:
            for url in url_list:
                # Check if document exists
                existing = session.query(MapDocument).filter(MapDocument.source_url == url).first()
                if not existing:
                    # Generate document_id from URL hash
                    doc_id = hashlib.sha256(url.encode()).hexdigest()[:12]
                    # Auto-create the document
                    doc = MapDocument(
                        document_id=doc_id,
                        source_url=url,
                        source_type="url",
                        status=MapStatus.SUCCESS,
                        discovery_method="cli",
                    )
                    session.add(doc)
            session.commit()

    # Handle --files: auto-create documents for file paths
    if files_paths:
        import hashlib
        from pathlib import Path

        from kurt.db import managed_session
        from kurt.workflows.map.models import MapDocument, MapStatus

        file_list = [f.strip() for f in files_paths.split(",") if f.strip()]
        with managed_session() as session:
            for file_path in file_list:
                # Resolve to absolute path
                abs_path = str(Path(file_path).resolve())
                # Check if document exists
                existing = (
                    session.query(MapDocument).filter(MapDocument.source_url == abs_path).first()
                )
                if not existing:
                    # Generate document_id from path hash
                    doc_id = hashlib.sha256(abs_path.encode()).hexdigest()[:12]
                    # Auto-create the document
                    doc = MapDocument(
                        document_id=doc_id,
                        source_url=abs_path,
                        source_type="file",
                        status=MapStatus.SUCCESS,
                        discovery_method="cli",
                    )
                    session.add(doc)
            session.commit()

    # Determine effective status filter
    # --refetch allows re-fetching FETCHED documents
    effective_status = with_status
    if not effective_status:
        if refetch:
            effective_status = None  # No status filter, fetch all
        else:
            effective_status = "NOT_FETCHED"  # Default: only unfetched

    # Resolve documents to fetch
    docs = resolve_documents(
        identifier=identifier,
        include_pattern=include_pattern,
        ids=ids if not urls and not files_paths else None,  # Don't use ids if urls/files provided
        in_cluster=in_cluster,
        with_status=effective_status,
        with_content_type=with_content_type,
        limit=limit,
        exclude_pattern=exclude_pattern,
        url_contains=url_contains,
        # Pass urls/files for filtering if provided
        urls=urls,
        files=files_paths,
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

    # Build config with CLI overrides
    config_overrides = {"dry_run": dry_run}
    if engine:
        config_overrides["fetch_engine"] = engine.lower()
    if batch_size is not None:
        config_overrides["batch_size"] = batch_size
    config = FetchConfig.from_config("fetch", **config_overrides)

    # Build CLI command string for replay
    import sys

    cli_command = "kurt " + " ".join(sys.argv[1:])

    # Run workflow
    result = run_fetch(
        docs, config, background=background, priority=priority, cli_command=cli_command
    )

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
