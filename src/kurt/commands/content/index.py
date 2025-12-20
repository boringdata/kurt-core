"""Index command - Extract metadata from documents using LLM."""

import click


@click.command("index")
@click.argument("identifier", required=False)
@click.option("--ids", help="Comma-separated list of document IDs")
@click.option(
    "--include", "include_pattern", help="Glob pattern to match source_url or content_path"
)
@click.option("--in-cluster", help="Cluster name filter")
@click.option("--with-status", help="Status filter")
@click.option("--with-content-type", help="Content type filter")
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
    # Lazy import all dependencies when command is actually run
    import logging

    from rich.console import Console

    from kurt.content.document import list_documents_for_indexing

    console = Console()
    logger = logging.getLogger(__name__)

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

        intro_messages.append(f"Indexing {len(documents)} document(s)...")

        # Print intro block
        from kurt.core.display import print_info

        for msg in intro_messages:
            print_info(msg)

        # Run indexing pipeline
        import time

        from dbos import DBOS

        from kurt.content.filtering import DocumentFilters
        from kurt.core import run_pipeline_workflow
        from kurt.core.display import display as core_display
        from kurt.workflows import get_dbos

        get_dbos()
        start_time = time.time()

        # Create filters from document IDs
        document_ids = [str(doc.id) for doc in documents]
        filters = DocumentFilters(ids=",".join(document_ids))
        incremental_mode = "full" if force else "delta"

        # Run the staging pipeline
        core_display.start_step("staging", f"Indexing {len(documents)} documents")

        handle = DBOS.start_workflow(
            run_pipeline_workflow,
            target="staging",
            filters=filters,
            incremental_mode=incremental_mode,
            reprocess_unchanged=force,
        )

        workflow_result = handle.get_result()

        # Extract stats
        indexed_count = workflow_result.get("documents_processed", 0)
        skipped_count = workflow_result.get("skipped_docs", 0)
        error_count = len(workflow_result.get("errors", {}))

        core_display.end_step(
            "staging",
            {
                "status": "completed" if error_count == 0 else "failed",
                "documents_indexed": indexed_count,
                "documents_skipped": skipped_count,
                "documents_failed": error_count,
            },
        )

        # Display the knowledge graph for single document
        if len(documents) == 1 and indexed_count > 0:
            from kurt.db.graph_queries import get_document_knowledge_graph

            try:
                doc_id = str(documents[0].id)
                kg = get_document_knowledge_graph(doc_id)
                if kg:
                    console.print("\n[bold]Knowledge Graph[/bold]")
                    for entity in kg.get("entities", [])[:5]:
                        console.print(f"  • {entity.get('name', 'Unknown')}")
            except Exception as e:
                logger.debug(f"Could not retrieve KG for display: {e}")

        # Process any pending metadata sync queue items
        from kurt.db.metadata_sync import process_metadata_sync_queue

        process_metadata_sync_queue()

        # Print summary
        elapsed = time.time() - start_time
        console.print()
        console.print("[bold]Summary[/bold]")
        console.print(f"  ✓ Indexed: {indexed_count} document(s)")
        if skipped_count > 0:
            console.print(f"  ○ Skipped: {skipped_count} document(s)")
        if error_count > 0:
            console.print(f"  [red]✗ Failed: {error_count} document(s)[/red]")
        console.print(f"  [dim]ℹ Time elapsed: {elapsed:.1f}s[/dim]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise click.Abort()
    finally:
        # Explicit cleanup to prevent hanging
        import gc
        import sys
        import threading
        import time

        # Force garbage collection
        gc.collect()

        # Ensure DBOS is cleaned up if it was initialized
        try:
            from dbos import DBOS

            # Force immediate DBOS cleanup
            DBOS.destroy(workflow_completion_timeout_sec=0)
        except Exception:
            pass  # Ignore if DBOS wasn't initialized

        # Workaround for DBOS and other executor bugs
        # Force any non-daemon ThreadPoolExecutor threads to become daemons
        time.sleep(0.1)  # Brief pause for normal cleanup
        for thread in threading.enumerate():
            if thread.name.startswith("ThreadPoolExecutor-") and not thread.daemon:
                thread.daemon = True  # Make it daemon so it won't block exit

        # Flush output buffers
        sys.stdout.flush()
        sys.stderr.flush()
