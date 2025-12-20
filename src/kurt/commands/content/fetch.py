"""Fetch command - Download + index content (root-level command)."""

import click

from kurt.admin.telemetry.decorators import track_command
from kurt.commands.content._shared_options import (
    add_background_options,
    add_confirmation_options,
    add_output_options,
    exclude_option,
    ids_option,
    in_cluster_option,
    include_option,
    limit_option,
    with_content_type_option,
    with_status_option,
)


@click.command("fetch")
@track_command
@click.argument("identifier", required=False)
# Standard filter options from _shared_options
@include_option
@click.option(
    "--url",
    hidden=True,
    help="[DEPRECATED: use positional IDENTIFIER] Single source URL",
)
@click.option("--urls", help="Comma-separated list of source URLs (auto-creates if don't exist)")
@click.option(
    "--file",
    "file_path",
    hidden=True,
    help="[DEPRECATED: use positional IDENTIFIER] Local file path",
)
@click.option("--files", "files_paths", help="Comma-separated list of local file paths to index")
@ids_option
@in_cluster_option
@with_status_option
@with_content_type_option
@exclude_option
@limit_option
# Fetch-specific options
@click.option(
    "--concurrency",
    type=int,
    default=5,
    help="Parallel requests (default: 5, warns if >20)",
)
@click.option(
    "--engine",
    type=click.Choice(["firecrawl", "trafilatura", "httpx"], case_sensitive=False),
    default=None,
    help="Fetch engine (trafilatura=free, firecrawl=API, httpx=httpx+trafilatura)",
)
@click.option(
    "--skip-index",
    is_flag=True,
    help="Skip LLM indexing (download only, saves ~$0.005/doc)",
)
@click.option(
    "--refetch",
    is_flag=True,
    help="Include already FETCHED documents (default: skip them)",
)
# Standard safety/output/background options from _shared_options
@add_confirmation_options(with_deprecated_force=True)
@add_output_options()
@add_background_options()
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
    exclude_pattern: str,
    limit: int,
    concurrency: int,
    engine: str,
    skip_index: bool,
    refetch: bool,
    dry_run: bool,
    yes_flag: bool,
    force: bool,
    output_format: str,
    background: bool,
    priority: int,
):
    """
    Fetch and index content from URLs, local files, or CMS.

    IDENTIFIER can be a document ID, URL, or file path.

    \b
    Examples:
        kurt content fetch 04303ee5              # By ID
        kurt content fetch https://example.com   # By URL (auto-creates)
        kurt content fetch ./docs/article.md     # By file path
        kurt content fetch --include "*/docs/*"  # By pattern
        kurt content fetch --in-cluster "Docs"   # By cluster
        kurt content fetch --with-status ERROR   # Retry failed
        kurt content fetch --dry-run             # Preview only
    """
    # Lazy import all dependencies when command is actually run
    import logging
    import time

    from rich.console import Console

    from kurt.commands.content._fetch_helpers import (
        check_guardrails,
        display_dry_run_preview,
        display_json_output,
        display_no_documents_help,
        display_result_messages,
        get_engine_display,
        merge_identifier_into_filters,
    )
    from kurt.core.display import display_summary, print_info, print_warning
    from kurt.utils import should_force
    from kurt.utils.filtering import select_documents_for_fetch
    from kurt.workflows.cli_helpers import dbos_cleanup_context

    console = Console()
    logger = logging.getLogger(__name__)

    # Step 1: Merge identifier into appropriate filter
    urls, files_paths, ids = merge_identifier_into_filters(
        identifier, url, urls, file_path, files_paths, ids
    )

    # Step 2: Handle deprecated --force flag (inlined - was trivial helper)
    if force and not yes_flag and not refetch:
        print_warning(
            "--force is deprecated, use --yes/-y for confirmations and --refetch to re-fetch documents"
        )
    effective_refetch = refetch or force

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
            exclude=exclude_pattern,
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
    display_result_messages(result)

    docs = result["docs"]
    doc_ids_to_fetch = result["doc_ids"]
    excluded_fetched_count = result.get("excluded_fetched_count", 0)

    # Step 5: Display warnings about re-fetching (inlined - was trivial helper)
    if refetch and excluded_fetched_count > 0:
        print_warning(
            f"{excluded_fetched_count} document(s) are already FETCHED and will be re-fetched (--refetch enabled)"
        )
        print_info("This will re-download and re-index content, which may incur LLM costs")

    # Step 6: Handle case with no documents
    if not docs:
        display_no_documents_help(excluded_fetched_count, in_cluster, include_pattern, urls, ids)
        return

    # Step 7: Dry-run mode
    if dry_run:
        display_dry_run_preview(docs, concurrency, result)
        return

    # Step 8: Check guardrails
    force_mode = should_force(yes_flag or force)
    if not check_guardrails(docs, concurrency, force_mode):
        return

    # Step 9: JSON output format
    if output_format == "json":
        if not display_json_output(docs):
            return

    # Step 10: Display intro block (inlined build_intro_messages - was trivial helper)
    engine_display = get_engine_display(docs, engine)
    print_info(
        f"Fetching {len(doc_ids_to_fetch)} document(s) with {concurrency} parallel downloads"
    )
    print_info(f"Engine: {engine_display}")
    if not skip_index:
        print_info(f"LLM Indexing: enabled (parallel with concurrency={concurrency})")
    else:
        print_info("LLM Indexing: skipped")

    # Step 11-12: Execute fetch and indexing workflows
    with dbos_cleanup_context():
        try:
            from kurt.utils.filtering import DocumentFilters
            from kurt.workflows.cli_helpers import run_pipeline_simple

            overall_start = time.time()

            # Create filters for the pipeline
            filters = DocumentFilters(ids=",".join(doc_ids_to_fetch))

            # Create FetchConfig with runtime values if engine is specified
            model_configs = None
            if engine:
                from kurt.models.landing.fetch import FetchConfig

                fetch_config = FetchConfig(fetch_engine=engine)
                model_configs = {"landing.fetch": fetch_config}

            # Run fetch workflow (display handled by framework)
            fetch_result = run_pipeline_simple(
                target="landing.fetch",
                filters=filters,
                model_configs=model_configs,
                background=background,
                priority=priority,
            )

            # Background mode returns early
            if background:
                return

            # Extract stats from pipeline result
            documents_fetched = fetch_result.get("landing.fetch", {}).get("documents_fetched", 0)
            documents_failed = fetch_result.get("landing.fetch", {}).get("documents_failed", 0)

            # Display errors if any
            errors = fetch_result.get("errors", {})
            if errors:
                console.print("\n[bold red]Errors:[/bold red]")
                for model_name, error in errors.items():
                    console.print(f"  [red]✗[/red] {model_name}: {error}")

            # Indexing stage
            indexed = 0
            kg_result = None

            if not skip_index and documents_fetched > 0:
                # Run indexing workflow (display handled by framework)
                index_result = run_pipeline_simple(
                    target="staging",
                    filters=filters,
                    incremental_mode="full",
                    reprocess_unchanged=False,
                )

                # Extract stats
                indexed = index_result.get("documents_processed", 0)
                index_failed = len(index_result.get("errors", {}))

                # Display indexing errors if any
                if index_failed > 0:
                    index_errors = index_result.get("errors", {})
                    if index_errors:
                        console.print("\n[bold red]Indexing errors:[/bold red]")
                        for model_name, error in index_errors.items():
                            console.print(f"  [red]✗[/red] {model_name}")
                            console.print(f"    [dim red]Error: {error}[/dim red]")

                # Extract KG stats
                entity_resolution_result = index_result.get("staging.entity_resolution", {})
                if entity_resolution_result:
                    kg_result = {
                        "entities_created": entity_resolution_result.get("entities_created", 0),
                        "entities_linked": entity_resolution_result.get("entities_linked", 0),
                        "relationships_created": entity_resolution_result.get(
                            "relationships_created", 0
                        ),
                    }

            # Build summary stats
            overall_elapsed = time.time() - overall_start
            summary_stats = {
                "fetched": f"{documents_fetched} document(s)",
                "elapsed": overall_elapsed,
            }

            if not skip_index and documents_fetched > 0:
                summary_stats["indexed"] = f"{indexed} document(s)"
                if indexed > 0 and kg_result:
                    summary_stats["entities_created"] = kg_result["entities_created"]
                    summary_stats["entities_linked"] = kg_result["entities_linked"]
                    summary_stats["relationships"] = kg_result["relationships_created"]

            if documents_failed > 0:
                summary_stats["failed"] = f"{documents_failed} document(s)"

            display_summary(summary_stats, console=console)

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            logger.exception("Fetch failed")
            raise click.Abort()
