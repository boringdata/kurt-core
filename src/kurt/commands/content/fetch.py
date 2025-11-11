"""Fetch command - Download + index content (root-level command)."""

import logging

import click
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from kurt.utils import should_force

console = Console()
logger = logging.getLogger(__name__)


@click.command("fetch")
@click.option(
    "--include",
    "include_pattern",
    help="FILTER: Glob pattern matching source_url or content_path (repeatable)",
)
@click.option("--url", help="FILTER: Single source URL (auto-creates if doesn't exist)")
@click.option(
    "--urls", help="FILTER: Comma-separated list of source URLs (auto-creates if don't exist)"
)
@click.option(
    "--file", "file_path", help="FILTER: Local file path to index (skips fetch, only indexes)"
)
@click.option(
    "--files", "files_paths", help="FILTER: Comma-separated list of local file paths to index"
)
@click.option("--ids", help="FILTER: Comma-separated list of document IDs")
@click.option("--in-cluster", help="FILTER: All documents in specified cluster")
@click.option(
    "--with-status",
    type=click.Choice(["NOT_FETCHED", "FETCHED", "ERROR"]),
    help="FILTER: All documents with specified ingestion status (requires confirmation if >100 docs, use --force to skip)",
)
@click.option(
    "--with-content-type",
    help="FILTER: All documents with specified content type (tutorial | guide | blog | reference | etc)",
)
@click.option(
    "--exclude",
    help="REFINEMENT: Glob pattern matching source_url or content_path (works with any filter above)",
)
@click.option(
    "--limit",
    type=int,
    help="REFINEMENT: Max documents to process (default: no limit, warns if >100)",
)
@click.option(
    "--concurrency",
    type=int,
    default=5,
    help="PROCESSING: Parallel requests (default: 5, warns if >20 for rate limit risk, use --force to skip)",
)
@click.option(
    "--engine",
    type=click.Choice(["firecrawl", "trafilatura", "httpx"], case_sensitive=False),
    default=None,
    help="PROCESSING: Fetch engine (defaults to kurt.config INGESTION_FETCH_ENGINE, trafilatura=free, firecrawl=API, httpx=httpx for fetching + trafilatura for extraction)",
)
@click.option(
    "--skip-index",
    is_flag=True,
    help="PROCESSING: Skip LLM indexing (download content only, saves ~$0.005/doc in LLM API costs)",
)
@click.option(
    "--refetch",
    is_flag=True,
    help="PROCESSING: Include already FETCHED documents (default: filters exclude FETCHED, warns about duplicates, implied with --with-status FETCHED)",
)
@click.option(
    "--force",
    is_flag=True,
    help="SAFETY: Skip all safety prompts and guardrails (bypasses: batch confirmations, concurrency warnings, refetch warnings, use for automation/CI or set KURT_FORCE=1)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="SAFETY: Preview what would be fetched (shows: doc count, URLs, estimated cost, time estimate, no API calls, no DB changes)",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "text"]),
    default="text",
    help="Output format for AI agents",
)
@click.option(
    "--background",
    is_flag=True,
    help="Run as background workflow (non-blocking, useful for large batches)",
)
@click.option(
    "--priority",
    type=int,
    default=10,
    help="Priority for background execution (1=highest, default=10)",
)
def fetch_cmd(
    include_pattern: str,
    url: str,
    urls: str,
    file_path: str,
    files_paths: str,
    ids: str,
    in_cluster: str,
    with_status: str,
    with_content_type: str,
    exclude: str,
    limit: int,
    concurrency: int,
    engine: str,
    skip_index: bool,
    refetch: bool,
    force: bool,
    dry_run: bool,
    output_format: str,
    background: bool,
    priority: int,
):
    """
    Fetch and index content from URLs or local files.

    \b
    What it does:
    - Downloads content from web URLs using Trafilatura or Firecrawl
    - Indexes local markdown/text files
    - Extracts metadata with LLM (unless --skip-index)
    - Auto-creates document records (no need to run 'kurt map' first)
    - Updates document status: NOT_FETCHED → FETCHED or ERROR

    \b
    Usage patterns:
    1. Single URL:      kurt fetch --url "https://example.com/article"
    2. Multiple URLs:   kurt fetch --urls "url1,url2,url3"
    3. Local file:      kurt fetch --file "./docs/article.md"
    4. Pattern match:   kurt fetch --include "*/docs/*"
    5. By cluster:      kurt fetch --in-cluster "Tutorials"

    \b
    Examples:
        # Fetch by pattern
        kurt fetch --include "*/docs/*"

        # Fetch single URL (auto-creates if doesn't exist)
        kurt fetch --url "https://example.com/article"

        # Fetch specific URLs (auto-creates if don't exist)
        kurt fetch --urls "https://example.com/page1,https://example.com/page2"

        # Index local file (skips fetch, only indexes)
        kurt fetch --file "./docs/article.md"

        # Index multiple local files
        kurt fetch --files "./docs/page1.md,./docs/page2.md"

        # Fetch by cluster
        kurt fetch --in-cluster "Tutorials"

        # Fetch by content type (after clustering)
        kurt fetch --with-content-type tutorial

        # Fetch all NOT_FETCHED
        kurt fetch --with-status NOT_FETCHED

        # Retry failed fetches
        kurt fetch --with-status ERROR

        # Fetch with exclusions
        kurt fetch --include "*/docs/*" --exclude "*/api/*"

        # Combine filters
        kurt fetch --with-content-type tutorial --include "*/docs/*"

        # Download only (skip LLM indexing to save costs)
        kurt fetch --with-status NOT_FETCHED --skip-index

        # Dry-run to preview
        kurt fetch --with-status NOT_FETCHED --dry-run
    """
    from kurt.content.fetch import fetch_content, fetch_documents_batch

    # Merge --url into --urls (--url is just convenience for single URL)
    if url:
        if urls:
            # Combine --url with --urls
            urls = f"{url},{urls}"
        else:
            urls = url

    # Merge --file into --files (--file is just convenience for single file)
    if file_path:
        if files_paths:
            # Combine --file with --files
            files_paths = f"{file_path},{files_paths}"
        else:
            files_paths = file_path

    # Call ingestion layer for filtering and validation
    try:
        result = fetch_content(
            include_pattern=include_pattern,
            urls=urls,
            files=files_paths,
            ids=ids,
            in_cluster=in_cluster,
            with_status=with_status,
            with_content_type=with_content_type,
            exclude=exclude,
            limit=limit,
            concurrency=concurrency,
            engine=engine,
            skip_index=skip_index,
            refetch=refetch,
        )
    except ValueError as e:
        # If no filter provided, show full help
        if "Requires at least ONE filter" in str(e):
            ctx = click.get_current_context()
            click.echo(ctx.get_help())
            ctx.exit()
        else:
            console.print(f"[red]Error:[/red] {e}")
            console.print("\n[dim]Examples:[/dim]")
            console.print("  kurt fetch --include '*/docs/*'")
            console.print("  kurt fetch --in-cluster 'Tutorials'")
            console.print("  kurt fetch --with-status NOT_FETCHED")
            raise click.Abort()

    # Display warnings
    for warning in result["warnings"]:
        console.print(f"[yellow]Warning:[/yellow] {warning}")

    # Display errors
    for error in result["errors"]:
        console.print(f"[red]Error:[/red] {error}")

    docs = result["docs"]
    doc_ids_to_fetch = result["doc_ids"]
    excluded_fetched_count = result.get("excluded_fetched_count", 0)

    # Warn about duplicates when using --refetch with already FETCHED documents
    if refetch and excluded_fetched_count > 0:
        console.print(
            f"[yellow]⚠️  Note:[/yellow] {excluded_fetched_count} document(s) are already FETCHED and will be re-fetched (--refetch enabled)"
        )
        console.print(
            "[dim]This will re-download and re-index content, which may incur LLM costs[/dim]\n"
        )

    if not docs:
        # Show explicit message about excluded FETCHED documents
        if excluded_fetched_count > 0:
            console.print(
                f"[yellow]Found {excluded_fetched_count} document(s), but all are already FETCHED[/yellow]"
            )
            console.print(
                "\n[dim]By default, 'kurt fetch' skips documents that are already FETCHED.[/dim]"
            )
            console.print("[dim]To re-fetch these documents, use the --refetch flag:[/dim]")

            if in_cluster:
                console.print(f"\n  [cyan]kurt fetch --in-cluster '{in_cluster}' --refetch[/cyan]")
            elif include_pattern:
                console.print(
                    f"\n  [cyan]kurt fetch --include '{include_pattern}' --refetch[/cyan]"
                )
            elif urls:
                console.print(f"\n  [cyan]kurt fetch --urls '{urls}' --refetch[/cyan]")
            else:
                console.print("\n  [cyan]kurt fetch <your-filters> --refetch[/cyan]")

            console.print("\n[dim]To view already fetched content, use:[/dim]")
            if in_cluster:
                console.print(f"  [cyan]kurt content list --in-cluster '{in_cluster}'[/cyan]")
            else:
                console.print("  [cyan]kurt content list --with-status FETCHED[/cyan]")
        else:
            console.print("[yellow]No documents found matching filters[/yellow]")

        return

    # Dry-run mode
    if dry_run:
        console.print("[bold]DRY RUN - Preview only (no actual fetching)[/bold]\n")
        console.print(f"[cyan]Would fetch {len(docs)} documents:[/cyan]\n")
        for doc in docs[:10]:
            console.print(f"  • {doc.source_url or doc.content_path}")
        if len(docs) > 10:
            console.print(f"  [dim]... and {len(docs) - 10} more[/dim]")

        # Estimate time based on concurrency and average fetch time
        avg_fetch_time_seconds = 3  # Conservative estimate: 3 seconds per document
        estimated_time_seconds = (len(docs) / concurrency) * avg_fetch_time_seconds

        if estimated_time_seconds < 60:
            time_estimate = f"{int(estimated_time_seconds)} seconds"
        else:
            time_estimate = f"{int(estimated_time_seconds / 60)} minutes"

        console.print(
            f"\n[dim]Estimated cost: ${result['estimated_cost']:.2f} (LLM indexing)[/dim]"
        )
        console.print(
            f"[dim]Estimated time: ~{time_estimate} (with concurrency={concurrency})[/dim]"
        )
        return

    # Check force mode (CLI flag or KURT_FORCE=1 env var)
    force_mode = should_force(force)

    # Guardrail: warn if concurrency >20 (rate limit risk)
    if concurrency > 20 and not force_mode:
        console.print(
            f"[yellow]⚠️  High concurrency ({concurrency}) may trigger rate limits[/yellow]"
        )
        console.print("[dim]Use --force or set KURT_FORCE=1 to skip this warning[/dim]")
        if not click.confirm("Continue anyway?"):
            console.print("[dim]Aborted[/dim]")
            return

    # Guardrail: warn if >100 docs without --force
    if len(docs) > 100 and not force_mode:
        console.print(f"[yellow]⚠️  About to fetch {len(docs)} documents[/yellow]")
        if not click.confirm("Continue?"):
            console.print("[dim]Aborted[/dim]")
            return

    # JSON output format
    if output_format == "json":
        import json

        output = {
            "total": len(docs),
            "documents": [{"id": str(d.id), "url": d.source_url or d.content_path} for d in docs],
        }
        console.print(json.dumps(output, indent=2))
        if not click.confirm("\nProceed with fetch?"):
            return

    # Display fetch configuration
    # Resolve engine (None means use default from config)
    from kurt.content.fetch import _get_fetch_engine

    resolved_engine = _get_fetch_engine(override=engine)

    engine_displays = {
        "trafilatura": "Trafilatura (free)",
        "firecrawl": "Firecrawl (API)",
        "httpx": "httpx (fetching) + trafilatura (extraction)",
    }
    engine_display = engine_displays.get(resolved_engine, f"{resolved_engine} (unknown)")
    console.print(
        f"[cyan]Fetching {len(doc_ids_to_fetch)} documents with {concurrency} parallel downloads[/cyan]"
    )
    console.print(f"[dim]Engine: {engine_display}[/dim]")
    if not skip_index:
        console.print(f"[dim]LLM Indexing: enabled (parallel with concurrency={concurrency})[/dim]")
    else:
        console.print("[dim]LLM Indexing: skipped[/dim]")
    console.print()

    # Background mode support
    if background:
        from kurt.workflows.cli_helpers import run_with_background_support
        from kurt.workflows.fetch import fetch_batch_workflow

        console.print("[dim]Enqueueing workflow...[/dim]\n")

        result = run_with_background_support(
            workflow_func=fetch_batch_workflow,
            workflow_args={
                "identifiers": doc_ids_to_fetch,
                "fetch_engine": engine,
                "skip_index": skip_index,
            },
            background=True,
            workflow_id=None,
            priority=priority,
        )
        return  # Background mode complete, exit early

    # Fetch in parallel with progress bar
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            # Step 1: Fetch documents
            fetch_task = progress.add_task("Fetching content...", total=len(doc_ids_to_fetch))

            results = fetch_documents_batch(
                doc_ids_to_fetch,
                max_concurrent=concurrency,
                fetch_engine=engine,
            )

            progress.update(fetch_task, completed=len(doc_ids_to_fetch))

            # Step 2: Index successfully fetched documents in parallel (unless --skip-index)
            successful = [r for r in results if r["success"]]

            if not skip_index and successful:
                import asyncio

                from kurt.content.index import batch_extract_document_metadata

                index_task = progress.add_task("Indexing with LLM...", total=len(successful))

                # Extract document IDs and run batch indexing
                doc_ids = [str(r["document_id"]) for r in successful]
                index_results = asyncio.run(
                    batch_extract_document_metadata(doc_ids, max_concurrent=concurrency)
                )

                indexed = index_results["succeeded"]
                index_errors = index_results["errors"]

                progress.update(index_task, completed=len(successful))

                if index_errors:
                    console.print(
                        f"\n[yellow]⚠ Indexing warnings:[/yellow] {len(index_errors)} documents"
                    )
                    for err in index_errors[:3]:
                        console.print(f"  [dim]{err['document_id']}: {err['error']}[/dim]")

        # Summary
        failed = [r for r in results if not r["success"]]

        console.print(f"\n[green]✓ Fetched:[/green] {len(successful)}/{len(results)} documents")
        if not skip_index and successful:
            console.print(f"[green]✓ Indexed:[/green] {indexed}/{len(successful)} documents")
        if failed:
            console.print(f"[red]✗ Failed:[/red] {len(failed)} documents")
            for r in failed[:5]:  # Show first 5 errors
                console.print(
                    f"  [dim]{r.get('document_id', 'unknown')}: {r.get('error', 'Unknown error')}[/dim]"
                )
            if len(failed) > 5:
                console.print(f"  [dim]... and {len(failed) - 5} more[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Fetch failed")
        raise click.Abort()
