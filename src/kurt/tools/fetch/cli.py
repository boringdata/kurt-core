"""CLI command for fetch tool."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from kurt.admin.telemetry.decorators import track_command
from kurt.tools.core import (
    add_background_options,
    add_filter_options,
    create_pending_run,
    dry_run_option,
    format_option,
    print_json,
    run_tool_with_tracking,
    spawn_background_run,
)

console = Console()


def _check_engine_status(engine: str) -> tuple[str, str]:
    """Check if engine is ready (has required API key)."""
    if engine == "trafilatura":
        return "ready", "Free local extraction (default)"
    if engine == "httpx":
        return "ready", "HTTP + trafilatura (proxy-friendly)"
    if engine == "firecrawl":
        if os.getenv("FIRECRAWL_API_KEY"):
            return "ready", "Firecrawl API"
        return "missing", "Set FIRECRAWL_API_KEY"
    if engine == "tavily":
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
@add_filter_options(
    exclude=True, file_ext=True, source_type=True, has_content=True, min_content_length=True
)
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
@click.option(
    "--embed/--no-embed",
    "embed",
    default=None,
    help="Generate embeddings after fetch (default: auto-detect from API keys)",
)
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
    file_ext: str | None,
    source_type: str | None,
    has_content: bool | None,
    min_content_length: int | None,
    single_url: str | None,
    urls: str | None,
    single_file: str | None,
    files_paths: str | None,
    engine: str | None,
    batch_size: int | None,
    list_engines: bool,
    refetch: bool,
    embed: bool | None,
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
    """
    if list_engines:
        _list_engines(output_format)
        return

    from kurt.documents import resolve_documents
    from kurt.tools.fetch.config import FetchConfig

    # Merge --url into --urls
    if single_url:
        urls = f"{urls},{single_url}" if urls else single_url

    # Merge --file into --files
    if single_file:
        files_paths = f"{files_paths},{single_file}" if files_paths else single_file

    # Handle --urls: auto-create MapDocument entries if they don't exist
    if urls:
        from sqlmodel import select

        from kurt.db import managed_session
        from kurt.tools.core import make_document_id
        from kurt.tools.map.models import MapDocument, MapStatus

        url_list = [u.strip() for u in urls.split(",") if u.strip()]

        with managed_session() as session:
            for url in url_list:
                # Check if exists
                existing = session.exec(
                    select(MapDocument).where(MapDocument.source_url == url)
                ).first()

                if not existing:
                    doc_id = make_document_id(url)
                    doc = MapDocument(
                        document_id=doc_id,
                        source_url=url,
                        source_type="url",
                        discovery_method="cli",
                        discovery_url=url,
                        status=MapStatus.SUCCESS,
                        is_new=True,
                    )
                    session.add(doc)

    # Handle --files: auto-create MapDocument entries for file paths
    if files_paths:
        from pathlib import Path as FilePath

        from sqlmodel import select

        from kurt.db import managed_session
        from kurt.tools.core import make_document_id
        from kurt.tools.map.models import MapDocument, MapStatus

        file_list = [f.strip() for f in files_paths.split(",") if f.strip()]

        with managed_session() as session:
            for file_path in file_list:
                abs_path = str(FilePath(file_path).resolve())
                # Check if exists
                existing = session.exec(
                    select(MapDocument).where(MapDocument.source_url == abs_path)
                ).first()

                if not existing:
                    doc_id = make_document_id(abs_path)
                    doc = MapDocument(
                        document_id=doc_id,
                        source_url=abs_path,
                        source_type="file",
                        discovery_method="cli",
                        discovery_url=abs_path,
                        status=MapStatus.SUCCESS,
                        is_new=True,
                    )
                    session.add(doc)

    # Determine effective status filter
    effective_status = with_status
    if not effective_status:
        if refetch:
            effective_status = None
        else:
            effective_status = "NOT_FETCHED"

    docs = resolve_documents(
        identifier=identifier,
        include_pattern=include_pattern,
        ids=ids if not urls and not files_paths else None,
        in_cluster=in_cluster,
        with_status=effective_status,
        with_content_type=with_content_type,
        limit=limit,
        exclude_pattern=exclude_pattern,
        url_contains=url_contains,
        file_ext=file_ext,
        source_type=source_type,
        has_content=has_content,
        min_content_length=min_content_length,
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

    config_overrides: dict[str, object] = {"dry_run": dry_run}
    if engine:
        config_overrides["fetch_engine"] = engine.lower()
    if batch_size is not None:
        config_overrides["batch_size"] = batch_size
    if embed is not None:
        config_overrides["embed"] = embed
    config = FetchConfig.from_config("fetch", **config_overrides)

    inputs = [
        {
            "url": d["source_url"],
            "document_id": d["document_id"],
            "source_type": d.get("source_type"),
            "metadata": d.get("metadata_json"),
            "discovery_url": d.get("discovery_url"),
        }
        for d in docs
    ]
    params: dict[str, object] = {
        "inputs": inputs,
        "dry_run": config.dry_run,
        "engine": config.fetch_engine,
        "batch_size": config.batch_size,
        "embed": config.embed,
    }

    cli_command = "kurt " + " ".join(sys.argv[1:])

    if background:
        run_id = create_pending_run(
            "fetch",
            params,
            project_root=str(Path.cwd()),
            cli_command=cli_command,
            priority=priority,
        )
        spawn_background_run(
            "fetch",
            params,
            run_id=run_id,
            project_root=str(Path.cwd()),
            cli_command=cli_command,
            priority=priority,
        )
        if output_format == "json":
            print_json({"run_id": run_id, "background": True})
        else:
            console.print(f"[green]✓[/green] Fetch started (run_id: {run_id})")
            console.print("[dim]Use 'kurt workflow status <run_id>' to check status[/dim]")
        return

    run_id, result = run_tool_with_tracking(
        "fetch",
        params,
        project_root=str(Path.cwd()),
        cli_command=cli_command,
        priority=priority,
    )

    if output_format == "json":
        print_json({"run_id": run_id, **result})
        return

    rows = result.get("data", [])
    success_count = sum(1 for row in rows if row.get("status") == "SUCCESS")
    error_count = sum(1 for row in rows if row.get("status") == "ERROR")
    console.print(f"[green]✓[/green] Fetched {success_count} document(s)")
    if error_count:
        console.print(f"[red]✗[/red] {error_count} errors")
    if dry_run:
        console.print("[dim]Dry run - no documents were saved[/dim]")
