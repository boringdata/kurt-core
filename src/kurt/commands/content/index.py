"""Index command - Extract metadata from documents using LLM."""

import click

from kurt.admin.telemetry.decorators import track_command
from kurt.commands.content._shared_options import (
    add_background_options,
    add_filter_options,
)


@click.command("index")
@track_command
@click.argument("identifier", required=False)
@add_filter_options(exclude=False, limit=False)
@click.option("--limit", type=int, default=100, help="Max documents to process")
@click.option(
    "--all",
    is_flag=True,
    help="Index all FETCHED documents that haven't been indexed yet",
)
@click.option(
    "--force",
    is_flag=True,
    help="Re-index documents even if already indexed",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show detailed step-by-step tables during indexing",
)
@add_background_options()
def index(
    identifier: str,
    include_pattern: str,
    ids: str,
    in_cluster: str,
    with_status: str,
    with_content_type: str,
    all: bool,
    force: bool,
    verbose: bool,
    limit: int,
    background: bool,
    priority: int,
):
    """
    Index documents: extract metadata, entities, and relationships.

    IDENTIFIER can be a document ID, URL, or file path (nominal case).

    \b
    What it extracts:
    - Content metadata (type, topics, tools, structure)
    - Knowledge graph entities (products, technologies, concepts)
    - Relationships between entities

    \b
    Note: Only works on FETCHED documents (use 'kurt fetch' first).
    Cost: ~$0.004 per document (OpenAI API) - 33% cheaper than before!

    \b
    Examples:
        # Index by document ID (nominal case)
        kurt index 44ea066e

        # Index by URL (nominal case)
        kurt index https://example.com/article

        # Index by file path (nominal case)
        kurt index ./docs/article.md

        # Index multiple documents by IDs
        kurt index --ids "44ea066e,550e8400,a73af781"

        # Index all documents in a cluster
        kurt index --in-cluster "Tutorials"

        # Index all documents matching pattern
        kurt index --include "*/docs/*"

        # Index all un-indexed documents
        kurt index --all

        # Index with a limit
        kurt index --all --limit 10

        # Re-index already indexed documents
        kurt index --include "*/docs/*" --force

        # Run in background
        kurt index --all --background

        # Verbose mode - show detailed tables for each step
        kurt index 44ea066e -v
    """
    # Lazy import all dependencies when command is actually run
    import logging
    import time

    from rich.console import Console

    from kurt.core.display import display_summary, print_info
    from kurt.db.documents import list_documents_for_indexing
    from kurt.utils.filtering import DocumentFilters, resolve_filters
    from kurt.workflows.cli_helpers import dbos_cleanup_context, run_pipeline_simple

    console = Console()
    logger = logging.getLogger(__name__)

    with dbos_cleanup_context():
        try:
            # Resolve and merge filters (handles identifier merging)
            filters = resolve_filters(
                identifier=identifier,
                ids=ids,
                include_pattern=include_pattern,
                in_cluster=in_cluster,
                with_status=with_status.upper() if with_status else None,
                with_content_type=with_content_type,
                limit=None,  # Will apply limit later
            )

            documents = list_documents_for_indexing(
                ids=filters.ids,
                include_pattern=filters.include_pattern,
                in_cluster=filters.in_cluster,
                with_status=filters.with_status,
                with_content_type=filters.with_content_type,
                all_flag=all,
            )
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            if "Must provide either" in str(e):
                console.print("Use --help for examples")
            raise click.Abort()

        if not documents:
            console.print("[yellow]No documents found matching criteria[/yellow]")
            return

        # Apply limit if specified
        intro_messages = []
        if limit and len(documents) > limit:
            intro_messages.append(
                f"[dim]Limiting to first {limit} documents out of {len(documents)} found[/dim]"
            )
            documents = documents[:limit]

        intro_messages.append(f"Indexing {len(documents)} document(s)...")

        # Print intro block
        for msg in intro_messages:
            print_info(msg)

        # Run indexing pipeline
        start_time = time.time()

        # Create filters from document IDs
        document_ids = [str(doc.id) for doc in documents]
        filters = DocumentFilters(ids=",".join(document_ids))
        incremental_mode = "full" if force else "delta"

        # Run the indexing pipeline (display handled by framework)
        workflow_result = run_pipeline_simple(
            target="staging.indexing",
            filters=filters,
            incremental_mode=incremental_mode,
            reprocess_unchanged=force,
            background=background,
            priority=priority,
            verbose=verbose,
        )

        # Background mode returns early
        if background:
            return

        # Extract stats
        indexed_count = workflow_result.get("documents_processed", 0)
        skipped_count = workflow_result.get("skipped_docs", 0)
        error_count = len(workflow_result.get("errors", {}))

        # Display the knowledge graph for single document
        if len(documents) == 1 and indexed_count > 0:
            from kurt.core.display import display_knowledge_graph
            from kurt.db.graph_queries import get_document_knowledge_graph

            try:
                doc_id = str(documents[0].id)
                kg = get_document_knowledge_graph(doc_id)
                if kg:
                    display_knowledge_graph(kg, console)
            except Exception as e:
                logger.debug(f"Could not retrieve KG for display: {e}")

        # Process any pending metadata sync queue items
        from kurt.db.metadata_sync import process_metadata_sync_queue

        process_metadata_sync_queue()

        # Print summary using helper
        elapsed = time.time() - start_time
        display_summary(
            {
                "indexed": f"{indexed_count} document(s)",
                "skipped": f"{skipped_count} document(s)" if skipped_count > 0 else None,
                "failed": f"{error_count} document(s)" if error_count > 0 else None,
                "elapsed": elapsed,
            },
            console=console,
        )
