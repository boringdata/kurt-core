"""Fetch command - Download + index content (root-level command)."""

import logging

import click
from rich.console import Console

from kurt.utils import should_force

console = Console()
logger = logging.getLogger(__name__)


@click.command("fetch")
@click.argument("identifier", required=False)
@click.option(
    "--include",
    "include_pattern",
    help="FILTER: Glob pattern matching source_url or content_path (repeatable)",
)
@click.option(
    "--url",
    hidden=True,
    help="[DEPRECATED: use positional IDENTIFIER] Single source URL (auto-creates if doesn't exist)",
)
@click.option(
    "--urls", help="FILTER: Comma-separated list of source URLs (auto-creates if don't exist)"
)
@click.option(
    "--file",
    "file_path",
    hidden=True,
    help="[DEPRECATED: use positional IDENTIFIER] Local file path to index (skips fetch, only indexes)",
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
    "--yes",
    "-y",
    "yes_flag",
    is_flag=True,
    help="SAFETY: Skip all confirmation prompts (for automation/CI, or set KURT_FORCE=1)",
)
@click.option(
    "--force",
    is_flag=True,
    hidden=True,
    help="[DEPRECATED: use --yes/-y instead] Skip all safety prompts",
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
    identifier: str,
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
    yes_flag: bool,
    force: bool,
    dry_run: bool,
    output_format: str,
    background: bool,
    priority: int,
):
    """
    Fetch and index content from URLs or local files.

    IDENTIFIER can be a document ID, URL, or file path (nominal case).

    \b
    What it does:
    - Downloads content from web URLs using Trafilatura or Firecrawl
    - Indexes local markdown/text files
    - Extracts metadata with LLM (unless --skip-index)
    - Auto-creates document records (no need to run 'kurt map' first)
    - Updates document status: NOT_FETCHED → FETCHED or ERROR

    \b
    Usage patterns:
    1. Single ID/URL/file: kurt fetch 04303ee5
    2. Single URL:         kurt fetch https://example.com/article
    3. Single file:        kurt fetch ./docs/article.md
    4. Multiple URLs:      kurt fetch --urls "url1,url2,url3"
    5. Pattern match:      kurt fetch --include "*/docs/*"
    6. By cluster:         kurt fetch --in-cluster "Tutorials"

    \b
    Examples:
        # Fetch by document ID (nominal case)
        kurt fetch 04303ee5

        # Fetch by URL (nominal case, auto-creates if doesn't exist)
        kurt fetch https://example.com/article

        # Fetch by local file (nominal case)
        kurt fetch ./docs/article.md

        # Fetch by pattern
        kurt fetch --include "*/docs/*"

        # Fetch specific URLs (auto-creates if don't exist)
        kurt fetch --urls "https://example.com/page1,https://example.com/page2"

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

        # Skip confirmations for automation
        kurt fetch --with-status NOT_FETCHED --yes
        kurt fetch --with-status NOT_FETCHED -y
    """
    import os

    from kurt.content.fetch import fetch_content, fetch_documents_batch

    # Handle positional identifier argument (nominal case: 1 id/url/file)
    if identifier:
        # Detect what type of identifier this is
        if identifier.startswith(("http://", "https://")):
            # It's a URL
            if urls:
                urls = f"{identifier},{urls}"
            else:
                urls = identifier
        elif (
            os.path.exists(identifier)
            or identifier.startswith(("./", "../", "/"))
            or "/" in identifier
        ):
            # It's a file path (exists or looks like a path)
            if files_paths:
                files_paths = f"{identifier},{files_paths}"
            else:
                files_paths = identifier
        else:
            # Assume it's a document ID (could be partial UUID)
            # Resolve partial UUID to full UUID
            from kurt.content.filtering import resolve_identifier_to_doc_id

            try:
                doc_id = resolve_identifier_to_doc_id(identifier)
                if ids:
                    ids = f"{doc_id},{ids}"
                else:
                    ids = doc_id
            except ValueError as e:
                console.print(f"[red]Error:[/red] {e}")
                raise click.Abort()

    # Merge --url into --urls (--url is deprecated, kept for backwards compatibility)
    if url:
        console.print("[yellow]⚠️  --url is deprecated, use positional IDENTIFIER instead[/yellow]")
        console.print("[dim]Example: kurt fetch https://example.com/article[/dim]")
        if urls:
            # Combine --url with --urls
            urls = f"{url},{urls}"
        else:
            urls = url

    # Merge --file into --files (--file is deprecated, kept for backwards compatibility)
    if file_path:
        console.print("[yellow]⚠️  --file is deprecated, use positional IDENTIFIER instead[/yellow]")
        console.print("[dim]Example: kurt fetch ./docs/article.md[/dim]")
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

    # Handle --yes/-y and deprecated --force
    # Show deprecation warning if --force is used
    if force and not yes_flag:
        console.print("[yellow]⚠️  --force is deprecated, use --yes or -y instead[/yellow]")

    # Check force mode (CLI flag or KURT_FORCE=1 env var)
    force_mode = should_force(yes_flag or force)

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

    # Display intro block
    from kurt.commands.content._live_display import print_intro_block
    from kurt.content.fetch import _get_fetch_engine

    resolved_engine = _get_fetch_engine(override=engine)

    engine_displays = {
        "trafilatura": "Trafilatura (free)",
        "firecrawl": "Firecrawl (API)",
        "httpx": "httpx (fetching) + trafilatura (extraction)",
    }
    engine_display = engine_displays.get(resolved_engine, f"{resolved_engine} (unknown)")

    intro_messages = [
        f"Fetching {len(doc_ids_to_fetch)} document(s) with {concurrency} parallel downloads",
        f"[dim]Engine: {engine_display}[/dim]",
    ]

    if not skip_index:
        intro_messages.append(
            f"[dim]LLM Indexing: enabled (parallel with concurrency={concurrency})[/dim]\n"
        )
    else:
        intro_messages.append("[dim]LLM Indexing: skipped[/dim]\n")

    print_intro_block(console, intro_messages)

    # Background mode support
    if background:
        from kurt.workflows.cli_helpers import run_with_background_support
        from kurt.workflows.fetch import fetch_batch_workflow

        console.print("[dim]Enqueueing workflow...[/dim]\n")

        # Build filter description for workflow display
        filter_desc = []
        if include_pattern:
            filter_desc.append(f"include: {include_pattern}")
        if urls:
            filter_desc.append(f"urls: {urls[:50]}...")
        if in_cluster:
            filter_desc.append(f"cluster: {in_cluster}")
        if with_status:
            filter_desc.append(f"status: {with_status}")
        if with_content_type:
            filter_desc.append(f"type: {with_content_type}")

        result = run_with_background_support(
            workflow_func=fetch_batch_workflow,
            workflow_args={
                "identifiers": doc_ids_to_fetch,
                "fetch_engine": engine,
                "extract_metadata": not skip_index,  # Convert skip_index to extract_metadata
                "filter_description": " | ".join(filter_desc)
                if filter_desc
                else None,  # Pass filter info
            },
            background=True,
            workflow_id=None,
            priority=priority,
        )
        return  # Background mode complete, exit early

    # Fetch in parallel with live display using 3-stage structure
    try:
        import asyncio
        import time

        from kurt.commands.content._live_display import (
            LiveProgressDisplay,
            create_fetch_progress_callback,
            finalize_knowledge_graph_with_progress,
            print_command_summary,
            print_stage_header,
            print_stage_summary,
        )

        overall_start = time.time()

        # ====================================================================
        # STAGE 1: Fetch Content
        # ====================================================================
        print_stage_header(console, 1, "FETCH CONTENT")

        with LiveProgressDisplay(console, max_log_lines=10) as display:
            display.start_stage("Fetching content", total=len(doc_ids_to_fetch))

            # Track results and timing as they arrive
            fetch_count = 0

            # Create progress callback that logs as documents are fetched
            def update_fetch_progress():
                nonlocal fetch_count
                fetch_count += 1
                display.update_progress(
                    advance=1,
                    description=f"Fetching content ({fetch_count}/{len(doc_ids_to_fetch)})",
                )

            results = fetch_documents_batch(
                doc_ids_to_fetch,
                max_concurrent=concurrency,
                fetch_engine=engine,
                progress_callback=update_fetch_progress,
            )

            # Log fetch results
            successful = [r for r in results if r["success"]]
            failed = [r for r in results if not r["success"]]

            for result in successful:
                doc_id = str(result["document_id"])
                title = result.get("title") or "Untitled"
                size_kb = (
                    result.get("content_length", 0) / 1024 if result.get("content_length") else 0
                )
                display.log(
                    f"✓ Fetched [{doc_id[:8]}] {title[:50]} ({size_kb:.1f}KB)",
                    style="dim green",
                )

            for result in failed:
                doc_id = str(result["document_id"])
                error = result.get("error", "Unknown error")
                error_short = error[:60] + "..." if len(error) > 60 else error
                display.log(f"✗ Fetch failed [{doc_id[:8]}] {error_short}", style="red")

            display.complete_stage()

        # Stage 1 summary
        print_stage_summary(
            console,
            [
                ("✓", "Fetched", f"{len(successful)} document(s)"),
                ("✗", "Failed", f"{len(failed)} document(s)"),
            ],
        )

        # ====================================================================
        # STAGE 2: Metadata Extraction (unless --skip-index)
        # ====================================================================
        index_results = None
        indexed = 0
        skipped_count = 0

        if not skip_index and successful:
            from kurt.content.indexing import batch_extract_document_metadata

            print_stage_header(console, 2, "METADATA EXTRACTION")

            with LiveProgressDisplay(console, max_log_lines=10) as display:
                display.start_stage("Metadata extraction", total=len(successful))

                # Extract document IDs and run batch indexing
                doc_ids = [str(r["document_id"]) for r in successful]

                # Create progress callback with activity updates and logging
                update_index_progress = create_fetch_progress_callback(display, len(successful))

                # Force re-indexing if --refetch is used
                index_results = asyncio.run(
                    batch_extract_document_metadata(
                        doc_ids,
                        max_concurrent=concurrency,
                        progress_callback=update_index_progress,
                        force=refetch,
                    )
                )

                indexed = index_results["succeeded"] - index_results.get("skipped", 0)
                skipped_count = index_results.get("skipped", 0)

                display.complete_stage()

            # Stage 2 summary
            print_stage_summary(
                console,
                [
                    ("✓", "Indexed", f"{indexed} document(s)"),
                    ("○", "Skipped", f"{skipped_count} document(s)"),
                    ("✗", "Failed", f"{index_results['failed']} document(s)"),
                ],
            )

            # ====================================================================
            # STAGE 3: Entity Resolution
            # ====================================================================
            if indexed > 0:
                print_stage_header(console, 3, "ENTITY RESOLUTION")

                # Get successful results for KG finalization
                results_for_kg = [
                    r
                    for r in index_results.get("results", [])
                    if not r.get("skipped", False) and "error" not in r
                ]

                with LiveProgressDisplay(console, max_log_lines=10) as display:
                    kg_result = finalize_knowledge_graph_with_progress(
                        results_for_kg, console, display=display
                    )

                # Stage 3 summary
                print_stage_summary(
                    console,
                    [
                        ("✓", "Entities created", str(kg_result["entities_created"])),
                        ("✓", "Entities linked", str(kg_result["entities_linked"])),
                        (
                            "✓",
                            "Relationships created",
                            str(kg_result.get("relationships_created", 0)),
                        ),
                    ],
                )

        # ====================================================================
        # Global Command Summary
        # ====================================================================
        overall_elapsed = time.time() - overall_start
        summary_items = [
            ("✓", "Fetched", f"{len(successful)} document(s)"),
        ]

        if not skip_index and successful:
            summary_items.append(("✓", "Indexed", f"{indexed} document(s)"))

            if indexed > 0 and "kg_result" in locals() and kg_result and "error" not in kg_result:
                summary_items.extend(
                    [
                        ("✓", "Entities created", str(kg_result["entities_created"])),
                        ("✓", "Entities linked", str(kg_result["entities_linked"])),
                        (
                            "✓",
                            "Relationships created",
                            str(kg_result.get("relationships_created", 0)),
                        ),
                    ]
                )

        if failed:
            summary_items.append(("✗", "Failed", f"{len(failed)} document(s)"))

        summary_items.append(("ℹ", "Time elapsed", f"{overall_elapsed:.1f}s"))

        print_command_summary(console, "Summary", summary_items)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Fetch failed")
        raise click.Abort()
