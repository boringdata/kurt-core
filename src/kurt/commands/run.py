"""Kurt run command - dbt-style model execution.

Run pipeline models with document filtering:
    kurt run landing.discovery --source-url https://example.com
    kurt run landing.fetch --ids doc1,doc2
    kurt run landing --with-status NOT_FETCHED
"""

import asyncio
import logging
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from kurt.admin.telemetry.decorators import track_command
from kurt.commands.content._shared_options import add_filter_options
from kurt.utils.filtering import DocumentFilters

console = Console()
logger = logging.getLogger(__name__)


@click.command()
@click.argument("target")
@add_filter_options(exclude=True)
@click.option(
    "--mode",
    type=click.Choice(["full", "delta"], case_sensitive=False),
    default="full",
    help="Processing mode: full (default) or delta (incremental)",
)
@click.option(
    "--reprocess",
    is_flag=True,
    help="Reprocess documents even if content unchanged",
)
@click.option(
    "--source-url",
    help="URL to discover content from (for landing.discovery)",
)
@click.option(
    "--source-folder",
    help="Local folder path to scan (for landing.discovery)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be executed without running",
)
@click.option(
    "--workflow-id",
    help="Reuse an existing workflow's context (to rerun a step with existing data)",
)
@track_command
def run(
    target: str,
    include_pattern: Optional[str],
    ids: Optional[str],
    in_cluster: Optional[str],
    with_status: Optional[str],
    with_content_type: Optional[str],
    limit: Optional[int],
    exclude_pattern: Optional[str],
    mode: str,
    reprocess: bool,
    source_url: Optional[str],
    source_folder: Optional[str],
    dry_run: bool,
    workflow_id: Optional[str],
):
    """
    Run pipeline models (dbt-style).

    TARGET can be:
    - Model name: landing.discovery, landing.fetch, staging.indexing
    - Namespace: landing (runs all models in that namespace)
    - File path: ./models/my_model.py

    \b
    Examples:
        # Discover URLs from a website
        kurt run landing.discovery --source-url https://example.com

        # Fetch content for discovered documents
        kurt run landing.fetch --with-status NOT_FETCHED

        # Fetch specific documents
        kurt run landing.fetch --ids doc1,doc2,doc3

        # Run all landing models
        kurt run landing --source-url https://example.com

        # Run with document pattern filtering
        kurt run landing.fetch --include-pattern '*/docs/*'

        # Rerun a step using data from an existing workflow
        # (useful to retry after fixing code or config)
        kurt run staging.indexing.entity_clustering --workflow-id e9208e1e-910a-47a1-b2e1-a357bb5dbfd6

    \b
    Model names follow the convention:
        <layer>.<step>
        - landing.discovery  → landing_discovery table
        - landing.fetch      → landing_fetch table
        - staging.indexing   → staging_indexing table
    """
    # Import models to register them
    _import_models(target)

    # Build document filters
    filters = DocumentFilters(
        ids=ids,
        include_pattern=include_pattern,
        in_cluster=in_cluster,
        with_status=with_status.upper() if with_status else None,
        with_content_type=with_content_type,
        limit=limit,
        exclude_pattern=exclude_pattern,
    )

    # Build config for discovery models
    config = {}
    if source_url:
        config["source_url"] = source_url
    if source_folder:
        config["source_folder"] = source_folder

    if dry_run:
        _show_dry_run(target, filters, config, mode, reprocess)
        return

    # Run the pipeline with DBOS context
    from kurt.workflows.cli_helpers import dbos_cleanup_context

    with dbos_cleanup_context():
        try:
            result = asyncio.run(
                _run_pipeline(
                    target=target,
                    filters=filters,
                    config=config,
                    mode=mode,
                    reprocess=reprocess,
                    workflow_id=workflow_id,
                )
            )
            _show_result(result)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise click.Abort()
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            logger.exception("Pipeline execution failed")
            raise click.Abort()


def _import_models(target: str) -> None:
    """Import model modules to register them."""
    # Always import landing models
    try:
        import kurt.models.landing  # noqa: F401
    except ImportError:
        pass

    # Import staging models if targeting staging
    if target.startswith("staging") or target.startswith("indexing"):
        try:
            import kurt.models.staging  # noqa: F401
        except ImportError:
            pass


async def _run_pipeline(
    target: str,
    filters: DocumentFilters,
    config: dict,
    mode: str,
    reprocess: bool,
    workflow_id: Optional[str] = None,
) -> dict:
    """Run the pipeline workflow."""
    from kurt.core import run_pipeline_workflow

    # TODO: Pass config to models that need it (e.g., discovery)
    # For now, config is passed via environment or direct model invocation

    result = await run_pipeline_workflow(
        target=target,
        filters=filters,
        incremental_mode=mode,
        workflow_id=workflow_id,
        reprocess_unchanged=reprocess,
    )
    return result


def _show_dry_run(
    target: str,
    filters: DocumentFilters,
    config: dict,
    mode: str,
    reprocess: bool,
) -> None:
    """Show what would be executed."""
    from kurt.core import resolve_pipeline

    console.print("\n[bold]Dry Run - Pipeline Execution Plan[/bold]\n")

    # Resolve pipeline
    try:
        pipeline = resolve_pipeline(target)
    except ValueError as e:
        console.print(f"[red]Error resolving target:[/red] {e}")
        return

    # Show pipeline info
    table = Table(show_header=False, box=None)
    table.add_column("Key", style="dim")
    table.add_column("Value")

    table.add_row("Target", target)
    table.add_row("Pipeline", pipeline.name)
    table.add_row("Mode", mode)
    table.add_row("Reprocess", str(reprocess))

    console.print(table)
    console.print()

    # Show models to execute
    console.print("[bold]Models to execute:[/bold]")
    for i, model_name in enumerate(pipeline.models, 1):
        table_name = model_name.replace(".", "_")
        console.print(f"  {i}. {model_name} → [dim]{table_name}[/dim]")

    console.print()

    # Show filters
    if any([filters.ids, filters.include_pattern, filters.with_status, filters.limit]):
        console.print("[bold]Filters:[/bold]")
        if filters.ids:
            console.print(f"  IDs: {filters.ids}")
        if filters.include_pattern:
            console.print(f"  Include pattern: {filters.include_pattern}")
        if filters.exclude_pattern:
            console.print(f"  Exclude pattern: {filters.exclude_pattern}")
        if filters.with_status:
            console.print(f"  Status: {filters.with_status}")
        if filters.in_cluster:
            console.print(f"  Cluster: {filters.in_cluster}")
        if filters.limit:
            console.print(f"  Limit: {filters.limit}")
        console.print()

    # Show config
    if config:
        console.print("[bold]Configuration:[/bold]")
        for key, value in config.items():
            console.print(f"  {key}: {value}")
        console.print()

    console.print("[dim]Run without --dry-run to execute[/dim]")


def _show_result(result: dict) -> None:
    """Display pipeline execution results."""
    console.print()

    # Summary
    workflow_id = result.get("workflow_id", "unknown")
    pipeline_name = result.get("pipeline", "unknown")
    models_executed = result.get("models_executed", 0)
    errors = result.get("errors", [])

    console.print("[bold green]Pipeline Complete[/bold green]")
    console.print(f"  Pipeline: {pipeline_name}")
    console.print(f"  Workflow ID: [dim]{workflow_id}[/dim]")
    console.print(f"  Models executed: {models_executed}")

    if result.get("documents_processed"):
        console.print(f"  Documents processed: {result['documents_processed']}")
    if result.get("skipped_docs"):
        console.print(f"  Documents skipped: {result['skipped_docs']}")

    # Show errors if any
    if errors:
        console.print()
        console.print(f"[yellow]Warnings ({len(errors)}):[/yellow]")
        for error in errors[:5]:  # Show first 5
            console.print(f"  - {error}")
        if len(errors) > 5:
            console.print(f"  ... and {len(errors) - 5} more")

    console.print()
