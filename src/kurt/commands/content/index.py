"""Index command - Extract metadata from documents using LLM."""

import logging

import click
from rich.console import Console

from kurt.admin.telemetry.decorators import track_command
from kurt.commands.content._shared_options import add_filter_options

console = Console()
logger = logging.getLogger(__name__)


@click.command("index")
@track_command
@click.argument("identifier", required=False)
@add_filter_options()
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
def index(
    identifier: str,
    include_pattern: str,
    ids: str,
    in_cluster: str,
    with_status: str,
    with_content_type: str,
    all: bool,
    force: bool,
    limit: int,
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
    """
    from kurt.content.document import list_documents_for_indexing

    try:
        # Get documents to index using service layer function
        try:
            from kurt.content.filtering import resolve_filters

            # Resolve and merge filters (handles identifier merging)
            filters = resolve_filters(
                identifier=identifier,
                ids=ids,
                include_pattern=include_pattern,
                in_cluster=in_cluster,
                with_status=with_status,
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

        intro_messages.append(f"Indexing {len(documents)} document(s)...\n")

        # Print intro block
        from kurt.commands.content._live_display import print_intro_block

        print_intro_block(console, intro_messages)

        # Use workflow-based indexing for all documents (single or batch)
        from kurt.commands.content._live_display import (
            index_and_finalize_with_two_stage_progress,
        )

        # Two-stage indexing: metadata extraction + entity resolution
        result = index_and_finalize_with_two_stage_progress(documents, console, force=force)

        batch_result = result["indexing"]
        # Note: "succeeded" already excludes skipped documents (from workflow_indexing.py)
        indexed_count = batch_result["succeeded"]
        _skipped_count = batch_result["skipped"]  # noqa: F841
        _error_count = batch_result["failed"]  # noqa: F841

        # Display the knowledge graph for single document
        if len(documents) == 1 and indexed_count > 0:
            from kurt.commands.content._live_display import display_knowledge_graph
            from kurt.db.graph_queries import get_document_knowledge_graph

            try:
                doc_id = str(documents[0].id)
                kg = get_document_knowledge_graph(doc_id)
                if kg:
                    display_knowledge_graph(kg, console)
            except Exception as e:
                logger.debug(f"Could not retrieve KG for display: {e}")

        # Process any pending metadata sync queue items
        # (handles SQL/agent updates that bypassed normal indexing)
        from kurt.db.metadata_sync import process_metadata_sync_queue

        queue_result = process_metadata_sync_queue()
        _queue_synced = queue_result["processed"]  # noqa: F841

        # Note: Summary is now displayed by index_and_finalize_with_two_stage_progress for all documents
        # No need for separate single-document summary

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()
