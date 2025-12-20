"""Fetch command - Download + index content (root-level command)."""

import click


@click.command("fetch")
@click.argument("identifier", required=False)
@click.option(
    "--include",
    "include_pattern",
    help="FILTER: Glob pattern matching source_url or content_path (e.g., '*/docs/*' or 'sanity/prod/*')",
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
    Fetch and index content from URLs, local files, or CMS documents.

    IDENTIFIER can be a document ID, URL, or file path (nominal case).

    \b
    What it does:
    - Downloads content from web URLs using Trafilatura or Firecrawl
    - Fetches content from CMS platforms (Sanity) via API
    - Indexes local markdown/text files
    - Extracts metadata with LLM (unless --skip-index)
    - Auto-creates document records (no need to run 'kurt map' first)
    - Updates document status: NOT_FETCHED → FETCHED or ERROR

    \b
    Usage patterns:
    1. Single ID/URL/file: kurt content fetch 04303ee5
    2. Single URL:         kurt content fetch https://example.com/article
    3. Single file:        kurt content fetch ./docs/article.md
    4. Multiple URLs:      kurt content fetch --urls "url1,url2,url3"
    5. Pattern match:      kurt content fetch --include "*/docs/*"
    6. CMS content:        kurt content fetch --include "sanity/prod/*"
    7. By cluster:         kurt content fetch --in-cluster "Tutorials"

    \b
    Examples:
        # Fetch by document ID (nominal case)
        kurt content fetch 04303ee5

        # Fetch by URL (nominal case, auto-creates if doesn't exist)
        kurt content fetch https://example.com/article

        # Fetch by local file (nominal case)
        kurt content fetch ./docs/article.md

        # Fetch by pattern
        kurt content fetch --include "*/docs/*"

        # Fetch CMS-mapped content (use after 'kurt content map cms')
        kurt content fetch --include "sanity/prod/*"

        # Fetch specific URLs (auto-creates if don't exist)
        kurt content fetch --urls "https://example.com/page1,https://example.com/page2"

        # Index multiple local files
        kurt content fetch --files "./docs/page1.md,./docs/page2.md"

        # Fetch by cluster
        kurt content fetch --in-cluster "Tutorials"

        # Fetch by content type (after clustering)
        kurt content fetch --with-content-type tutorial

        # Fetch all NOT_FETCHED
        kurt content fetch --with-status NOT_FETCHED

        # Retry failed fetches
        kurt content fetch --with-status ERROR

        # Fetch with exclusions
        kurt content fetch --include "*/docs/*" --exclude "*/api/*"

        # Combine filters
        kurt content fetch --with-content-type tutorial --include "*/docs/*"

        # Download only (skip LLM indexing to save costs)
        kurt content fetch --with-status NOT_FETCHED --skip-index

        # Dry-run to preview
        kurt content fetch --with-status NOT_FETCHED --dry-run

        # Skip confirmations for automation
        kurt content fetch --with-status NOT_FETCHED --yes
        kurt content fetch --with-status NOT_FETCHED -y
    """
    # Lazy import all dependencies when command is actually run
    import logging
    import time

    from rich.console import Console

    from kurt.admin.telemetry.tracker import track_event
    from kurt.commands.content._fetch_helpers import (
        build_intro_messages,
        check_guardrails,
        display_dry_run_preview,
        display_json_output,
        display_no_documents_help,
        display_refetch_warning,
        display_result_messages,
        get_engine_display,
        handle_force_flag,
        merge_identifier_into_filters,
    )
    from kurt.content.fetch import select_documents_for_fetch
    from kurt.core import run_pipeline_workflow
    from kurt.utils import should_force

    console = Console()
    logger = logging.getLogger(__name__)

    # Track command execution
    track_event("command_started", properties={"command": "kurt content fetch"})

    # Step 1: Merge identifier into appropriate filter
    urls, files_paths, ids = merge_identifier_into_filters(
        identifier, url, urls, file_path, files_paths, ids, console
    )

    # Step 2: Handle deprecated --force flag
    effective_refetch = handle_force_flag(force, yes_flag, refetch, console)

    # Step 3: Select documents for fetching
    try:
        result = select_documents_for_fetch(
            include_pattern=include_pattern,
            urls=urls,
            files=files_paths,
            ids=ids,
            in_cluster=in_cluster,
            with_status=with_status,
            with_content_type=with_content_type,
            exclude=exclude,
            limit=limit,
            skip_index=skip_index,
            refetch=effective_refetch,
        )
    except ValueError as e:
        if "Requires at least ONE filter" in str(e):
            ctx = click.get_current_context()
            click.echo(ctx.get_help())
            ctx.exit()
        else:
            console.print(f"[red]Error:[/red] {e}")
            console.print("\n[dim]Examples:[/dim]")
            console.print("  kurt content fetch --include '*/docs/*'")
            console.print("  kurt content fetch --in-cluster 'Tutorials'")
            console.print("  kurt content fetch --with-status NOT_FETCHED")
            raise click.Abort()

    # Step 4: Display warnings and errors
    display_result_messages(result, console)

    docs = result["docs"]
    doc_ids_to_fetch = result["doc_ids"]
    excluded_fetched_count = result.get("excluded_fetched_count", 0)

    # Step 5: Display warnings about re-fetching
    display_refetch_warning(refetch, excluded_fetched_count, console)

    # Step 6: Handle case with no documents
    if not docs:
        display_no_documents_help(
            excluded_fetched_count, in_cluster, include_pattern, urls, ids, console
        )
        return

    # Step 7: Dry-run mode
    if dry_run:
        display_dry_run_preview(docs, concurrency, result, console)
        return

    # Step 8: Check guardrails
    force_mode = should_force(yes_flag or force)
    if not check_guardrails(docs, concurrency, force_mode, console):
        return

    # Step 9: JSON output format
    if output_format == "json":
        if not display_json_output(docs, console):
            return

    # Step 10: Display intro block
    from kurt.core.display import print_info

    engine_display = get_engine_display(docs, engine)
    intro_messages = build_intro_messages(
        len(doc_ids_to_fetch), concurrency, engine_display, skip_index
    )
    for msg in intro_messages:
        print_info(msg)

    # Step 11: Background mode support
    if background:
        from kurt.content.filtering import DocumentFilters
        from kurt.workflows.cli_helpers import run_with_background_support

        console.print("[dim]Enqueueing workflow...[/dim]\n")

        # Create filters for the new pipeline
        filters = DocumentFilters(ids=",".join(doc_ids_to_fetch))

        run_with_background_support(
            workflow_func=run_pipeline_workflow,
            workflow_args={
                "target": "landing.fetch",
                "filters": filters,
                "incremental_mode": "full",
            },
            background=True,
            workflow_id=None,
            priority=priority,
        )
        return

    # Step 12: Execute fetch and indexing workflows
    try:
        from dbos import DBOS

        from kurt.content.filtering import DocumentFilters
        from kurt.core.display import display as core_display
        from kurt.workflows import get_dbos

        get_dbos()  # Initialize DBOS
        overall_start = time.time()

        # Create filters for the pipeline
        filters = DocumentFilters(ids=",".join(doc_ids_to_fetch))

        # ====================================================================
        # STAGE 1: Fetch Content (new pipeline model)
        # ====================================================================
        core_display.start_step("landing.fetch", f"Fetching {len(doc_ids_to_fetch)} documents")

        # Start fetch workflow using new pipeline
        handle = DBOS.start_workflow(
            run_pipeline_workflow,
            target="landing.fetch",
            filters=filters,
            incremental_mode="full",
        )

        # Wait for result
        fetch_result = handle.get_result()

        # Extract stats from pipeline result
        documents_fetched = fetch_result.get("landing.fetch", {}).get("documents_fetched", 0)
        documents_failed = fetch_result.get("landing.fetch", {}).get("documents_failed", 0)

        core_display.end_step(
            "landing.fetch",
            {
                "status": "completed" if documents_failed == 0 else "completed",
                "documents_fetched": documents_fetched,
                "documents_failed": documents_failed,
            },
        )

        # Display errors if any
        errors = fetch_result.get("errors", {})
        if errors:
            console.print("\n[bold red]Errors:[/bold red]")
            for model_name, error in errors.items():
                console.print(f"  [red]✗[/red] {model_name}: {error}")

        # ====================================================================
        # STAGES 2-3: Indexing (Metadata Extraction + Entity Resolution)
        # ====================================================================
        indexed = 0
        skipped_count = 0
        kg_result = None

        if not skip_index and documents_fetched > 0:
            # ====================================================================
            # STAGE 2: Indexing (new declarative pipeline)
            # ====================================================================
            core_display.start_step("staging", f"Indexing {documents_fetched} documents")

            # Run the indexing workflow using the new pipeline (same filters)
            index_handle = DBOS.start_workflow(
                run_pipeline_workflow,
                target="staging",
                filters=filters,
                incremental_mode="full",
                reprocess_unchanged=False,
            )

            # Wait for result
            index_result = index_handle.get_result()

            # Extract stats from new pipeline result format
            indexed = index_result.get("documents_processed", 0)
            skipped_count = index_result.get("skipped_docs", 0)
            index_failed = len(index_result.get("errors", {}))

            core_display.end_step(
                "staging",
                {
                    "status": "completed" if index_failed == 0 else "failed",
                    "documents_indexed": indexed,
                    "documents_skipped": skipped_count,
                    "documents_failed": index_failed,
                },
            )

            # Display indexing error details if any documents failed
            if index_failed > 0:
                index_errors = index_result.get("errors", {})
                if index_errors:
                    console.print("\n[bold red]Indexing errors:[/bold red]")
                    for model_name, error in index_errors.items():
                        console.print(f"  [red]✗[/red] {model_name}")
                        console.print(f"    [dim red]Error: {error}[/dim red]")

            # Extract KG stats from entity_resolution results
            entity_resolution_result = index_result.get("staging.entity_resolution", {})
            if entity_resolution_result:
                kg_result = {
                    "entities_created": entity_resolution_result.get("entities_created", 0),
                    "entities_linked_existing": entity_resolution_result.get("entities_linked", 0),
                    "relationships_created": entity_resolution_result.get(
                        "relationships_created", 0
                    ),
                }

        # ====================================================================
        # Global Command Summary
        # ====================================================================
        overall_elapsed = time.time() - overall_start
        console.print()
        console.print("[bold]Summary[/bold]")
        console.print(f"  ✓ Fetched: {documents_fetched} document(s)")

        if not skip_index and documents_fetched > 0:
            console.print(f"  ✓ Indexed: {indexed} document(s)")

            if indexed > 0 and kg_result and "error" not in kg_result:
                console.print(f"  ✓ Entities created: {kg_result['entities_created']}")
                console.print(
                    f"  ✓ Entities linked: {kg_result.get('entities_linked_existing', 0)}"
                )
                console.print(f"  ✓ Relationships: {kg_result.get('relationships_created', 0)}")

        if documents_failed > 0:
            console.print(f"  [red]✗ Failed: {documents_failed} document(s)[/red]")

        console.print(f"  [dim]ℹ Time elapsed: {overall_elapsed:.1f}s[/dim]")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        logger.exception("Fetch failed")
        raise click.Abort()
