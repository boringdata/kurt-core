"""Fetch command - Download + index content (root-level command)."""

import logging
import time

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command
from kurt.commands.content._fetch_helpers import (
    build_background_filter_desc,
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
from kurt.utils import should_force

console = Console()
logger = logging.getLogger(__name__)


@click.command("fetch")
@track_command
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
    from kurt.content.fetch import select_documents_for_fetch
    from kurt.content.fetch.workflow import fetch_workflow

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
    from kurt.commands.content._live_display import print_intro_block

    engine_display = get_engine_display(docs, engine)
    intro_messages = build_intro_messages(
        len(doc_ids_to_fetch), concurrency, engine_display, skip_index
    )
    print_intro_block(console, intro_messages)

    # Step 11: Background mode support
    if background:
        from kurt.workflows.cli_helpers import run_with_background_support

        console.print("[dim]Enqueueing workflow...[/dim]\n")
        filter_desc = build_background_filter_desc(
            include_pattern, urls, in_cluster, with_status, with_content_type
        )

        run_with_background_support(
            workflow_func=fetch_workflow,
            workflow_args={
                "identifiers": doc_ids_to_fetch,
                "fetch_engine": engine,
                "filter_description": filter_desc,
            },
            background=True,
            workflow_id=None,
            priority=priority,
        )
        return

    # Step 12: Execute fetch and indexing workflows
    try:
        from dbos import DBOS

        from kurt.commands.content._live_display import (
            LiveProgressDisplay,
            print_command_summary,
            print_stage_header,
            print_stage_summary,
            read_multiple_streams_parallel,
            read_stream_with_display,
        )
        from kurt.content.indexing.workflow_indexing import complete_indexing_workflow
        from kurt.workflows import get_dbos

        get_dbos()  # Initialize DBOS
        overall_start = time.time()

        # ====================================================================
        # STAGE 1: Fetch & Index Content (combined workflow)
        # ====================================================================
        if skip_index:
            print_stage_header(console, 1, "FETCH CONTENT & GENERATE EMBEDDINGS")
        else:
            print_stage_header(console, 1, "FETCH CONTENT & GENERATE EMBEDDINGS")

        with LiveProgressDisplay(console, max_log_lines=10) as display:
            display.start_stage("Fetching content", total=len(doc_ids_to_fetch))

            # Start fetch workflow and poll events for progress
            import queue
            import threading

            from dbos import DBOS

            handle = DBOS.start_workflow(
                fetch_workflow,
                identifiers=doc_ids_to_fetch,
                fetch_engine=engine,
                max_concurrent=concurrency,
            )

            # Read streams for live progress with sorted display
            total = len(doc_ids_to_fetch)
            completed_count = 0
            completed_lock = threading.Lock()

            # Event queue for sorting by timestamp
            event_queue = queue.Queue()
            display_thread_stop = threading.Event()

            def format_event(update, doc_id):
                """Format an event for display."""
                status = update.get("status")
                duration_ms = update.get("duration_ms")
                timing = f" ({duration_ms}ms)" if duration_ms else ""
                timestamp = update.get("timestamp", "")

                if timestamp:
                    time_str = timestamp.split("T")[1][:12]
                    ts_display = f"[{time_str}] "
                else:
                    ts_display = ""

                if status == "started":
                    return (timestamp, f"{ts_display}⠋ Started [{doc_id}]", "dim")
                elif status == "resolved":
                    return (timestamp, f"{ts_display}→ Resolved [{doc_id}]{timing}", "dim")
                elif status == "fetched":
                    return (timestamp, f"{ts_display}⠋ Fetched [{doc_id}]{timing}", "dim cyan")
                elif status == "embedded":
                    return (
                        timestamp,
                        f"{ts_display}⠋ Embeddings extracted [{doc_id}]{timing}",
                        "dim",
                    )
                elif status == "saved":
                    return (timestamp, f"{ts_display}⠋ Saved [{doc_id}]{timing}", "dim")
                elif status == "links_extracted":
                    return (timestamp, f"{ts_display}→ Extracted links [{doc_id}]{timing}", "dim")
                elif status == "completed":
                    return (timestamp, f"{ts_display}✓ Completed [{doc_id}]{timing}", "dim green")
                elif status == "error":
                    error = update.get("error", "Unknown error")
                    error_short = error[:60] + "..." if len(error) > 60 else error
                    return (timestamp, f"✗ Error [{doc_id}] {error_short}", "dim red")
                return None

            def display_sorted_events():
                """Periodically flush events sorted by timestamp."""
                buffer = []
                while not display_thread_stop.is_set() or not event_queue.empty():
                    # Collect events for 100ms
                    deadline = time.time() + 0.1
                    while time.time() < deadline:
                        try:
                            event = event_queue.get(timeout=0.01)
                            buffer.append(event)
                        except queue.Empty:
                            pass

                    # Sort by timestamp and display
                    if buffer:
                        # Safe sort: treat empty timestamps as very old (sort first)
                        buffer.sort(key=lambda x: x[0] if x[0] else "")
                        for timestamp, message, style in buffer:
                            display.log(message, style=style)
                        buffer = []

            def read_progress_stream(index: int):
                """Read progress stream for one document."""
                nonlocal completed_count
                doc_id = "..."

                try:
                    for update in DBOS.read_stream(handle.workflow_id, f"doc_{index}_progress"):
                        status = update.get("status")

                        # Extract document ID from stream if available
                        if "identifier" in update:
                            identifier = update["identifier"]
                            doc_id = identifier[:8] if len(identifier) > 8 else identifier
                        elif "document_id" in update:
                            document_id = update["document_id"]
                            doc_id = document_id[:8] if len(document_id) > 8 else document_id

                        # Format and queue event
                        formatted = format_event(update, doc_id)
                        if formatted:
                            event_queue.put(formatted)

                        # Update progress for terminal statuses
                        if status in ("completed", "error"):
                            display.update_progress(advance=1)
                            with completed_lock:
                                completed_count += 1

                except Exception as e:
                    event_queue.put(("", f"Stream error for doc_{index}: {str(e)}", "dim red"))

            # Start display thread
            display_thread = threading.Thread(target=display_sorted_events)
            display_thread.start()

            # Start thread for each document stream
            threads = []
            for i in range(total):
                t = threading.Thread(target=read_progress_stream, args=(i,))
                t.start()
                threads.append(t)

            # Wait for all streams to complete
            for t in threads:
                t.join()

            # Stop display thread and wait for final flush
            display_thread_stop.set()
            display_thread.join()

            # Get final result
            fetch_results = handle.get_result()

            # Normalize results to a list
            if isinstance(fetch_results, dict):
                if "results" in fetch_results:
                    # Batch response with results list
                    fetch_results = fetch_results["results"]
                else:
                    # Single document response - wrap in list
                    fetch_results = [fetch_results]

            display.complete_stage()

        # Extract successful/failed from results
        successful = [r for r in fetch_results if r.get("status") == "FETCHED"]
        failed = [r for r in fetch_results if r.get("status") != "FETCHED"]

        # Stage 1 summary
        print_stage_summary(
            console,
            [
                ("✓", "Fetched", f"{len(successful)} document(s)"),
                ("✗", "Failed", f"{len(failed)} document(s)"),
            ],
        )

        # Display error details if any documents failed
        if failed:
            console.print("\n[bold red]Failed documents:[/bold red]")
            for result in failed:
                doc_id = result.get("document_id", "unknown")[:8]
                url = result.get("source_url", result.get("identifier", "unknown"))
                error = result.get("error", "Unknown error")
                console.print(f"  [red]✗[/red] [{doc_id}] {url}")
                console.print(f"    [dim red]Error: {error}[/dim red]")

        # ====================================================================
        # STAGES 2-3: Indexing (Metadata Extraction + Entity Resolution)
        # ====================================================================
        indexed = 0
        skipped_count = 0
        indexed_results = []
        kg_result = None

        if not skip_index and successful:
            from kurt.commands.content._live_display import (
                read_multiple_streams_parallel,
                read_stream_with_display,
            )
            from kurt.content.indexing.workflow_indexing import complete_indexing_workflow

            # Extract document IDs from successful fetch results
            doc_ids_to_index = [r["document_id"] for r in successful]

            # Start indexing workflow (runs both metadata extraction + entity resolution)
            index_handle = DBOS.start_workflow(
                complete_indexing_workflow,
                document_ids=doc_ids_to_index,
                force=False,
                enable_kg=True,
                max_concurrent=concurrency,
            )

            # ====================================================================
            # STAGE 2: Metadata Extraction
            # ====================================================================
            print_stage_header(console, 2, "METADATA EXTRACTION")

            with LiveProgressDisplay(console, max_log_lines=10) as display:
                display.start_stage("Metadata extraction", total=len(doc_ids_to_index))

                # Read document progress streams in parallel
                read_multiple_streams_parallel(
                    workflow_id=index_handle.workflow_id,
                    stream_names=[f"doc_{i}_progress" for i in range(len(doc_ids_to_index))],
                    display=display,
                    on_event=lambda _stream, event: display.update_progress(advance=1)
                    if event.get("advance_progress")
                    else None,
                )

                display.complete_stage()

            # ====================================================================
            # STAGE 3: Entity Resolution
            # ====================================================================
            print_stage_header(console, 3, "ENTITY RESOLUTION")

            with LiveProgressDisplay(console, max_log_lines=10) as display:
                display.start_stage("Entity resolution", total=1)

                # Read entity resolution stream
                read_stream_with_display(
                    workflow_id=index_handle.workflow_id,
                    stream_name="entity_resolution_progress",
                    display=display,
                    on_event=None,
                )

                display.complete_stage()

            # Get final result
            index_result = index_handle.get_result()

            # Extract stats from result
            extract_results = index_result.get("extract_results", {})
            indexed = extract_results.get("succeeded", 0)
            skipped_count = extract_results.get("skipped", 0)
            index_failed = extract_results.get("failed", 0)

            # Stage 2 summary
            print_stage_summary(
                console,
                [
                    ("✓", "Indexed", f"{indexed} document(s)"),
                    ("○", "Skipped", f"{skipped_count} document(s)"),
                    ("✗", "Failed", f"{index_failed} document(s)"),
                ],
            )

            # Display indexing error details if any documents failed
            if index_failed > 0:
                index_errors = extract_results.get("errors", [])
                if index_errors:
                    console.print("\n[bold red]Indexing errors:[/bold red]")
                    for error_result in index_errors:
                        doc_id = error_result.get("document_id", "unknown")[:8]
                        error = error_result.get("error", "Unknown error")
                        console.print(f"  [red]✗[/red] [{doc_id}]")
                        console.print(f"    [dim red]Error: {error}[/dim red]")

            # Stage 3 summary
            kg_result = index_result.get("kg_stats")
            if kg_result:
                print_stage_summary(
                    console,
                    [
                        ("✓", "Entities created", str(kg_result.get("entities_created", 0))),
                        ("✓", "Entities linked", str(kg_result.get("entities_linked_existing", 0))),
                        (
                            "✓",
                            "Relationships created",
                            str(kg_result.get("relationships_created", 0)),
                        ),
                    ],
                )

            # Store results for final summary
            indexed_results = extract_results.get("results", [])

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
                        ("✓", "Entities linked", str(kg_result.get("entities_linked_existing", 0))),
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
