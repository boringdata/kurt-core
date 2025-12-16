"""
Model runner for executing indexing models via DBOS.

dbt-like execution model:
- Models declare dependencies via Reference()
- DAG is built automatically from dependencies
- Independent models run in parallel within each DAG level
- Each model is a DBOS step for durability

This module provides:
- PipelineContext: Context object passed to all steps
- run_pipeline: DAG-aware pipeline execution (preferred)
- run_models: Execute multiple models in sequence
- run_model: Single model execution
- execute_model_sync: For testing without DBOS
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from dbos import DBOS

from kurt.content.filtering import DocumentFilters

from .display import display
from .references import build_dependency_graph, topological_sort
from .table_io import TableReader, TableWriter

if TYPE_CHECKING:
    from .pipeline import PipelineConfig

logger = logging.getLogger(__name__)


@dataclass
class PipelineContext:
    """Context passed to pipeline steps during execution.

    This context object provides:
    - filters: DocumentFilters with document IDs to process
    - workflow_id: Unique identifier for this workflow run
    - incremental_mode: "full" or "delta" processing mode
    - reprocess_unchanged: If True, process docs even if content unchanged
    - metadata: Additional key-value pairs for custom data

    Steps can access this context to get filtering info, workflow tracking, etc.
    References can use this context for filtering operations.

    Example:
        def my_step(ctx: PipelineContext, writer: TableWriter):
            # Access document IDs from filters
            doc_ids = ctx.document_ids

            # Access workflow tracking
            workflow_id = ctx.workflow_id

            # Access processing mode
            mode = ctx.incremental_mode

            # Check if unchanged docs should be reprocessed
            if ctx.reprocess_unchanged:
                # Process all docs regardless of hash
                pass
    """

    filters: DocumentFilters
    workflow_id: Optional[str] = None
    incremental_mode: str = "full"
    reprocess_unchanged: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def document_ids(self) -> List[str]:
        """Get list of document IDs from filters."""
        if self.filters and self.filters.ids:
            return [id.strip() for id in self.filters.ids.split(",")]
        return []


# Backward compatibility alias
ModelContext = PipelineContext


def execute_model_sync(
    model_name: str,
    ctx: PipelineContext,
) -> Dict[str, Any]:
    """
    Execute a model synchronously (pure Python, no DBOS).

    Use this for testing models without DBOS context.

    Args:
        model_name: Name of the model in registry
        ctx: PipelineContext with execution parameters

    Returns:
        Model execution result dict
    """
    from .registry import ModelRegistry

    model_metadata = ModelRegistry.get(model_name)
    if not model_metadata:
        raise ValueError(f"Model '{model_name}' not found in registry")

    model_func = model_metadata["function"]

    reader = TableReader(
        filters=ctx.filters,
        workflow_id=ctx.workflow_id,
    )
    writer = TableWriter(
        workflow_id=ctx.workflow_id,
    )

    return model_func(
        ctx=ctx,
        reader=reader,
        writer=writer,
    )


async def run_models(
    models: List[Tuple[str, PipelineContext, Optional[List[Dict[str, Any]]]]],
) -> Dict[str, Any]:
    """
    Execute a list of models in sequence.

    This function orchestrates the execution of models, handling:
    - Model lookup from the registry
    - Reader/Writer initialization with proper context
    - Error handling and result aggregation
    - DBOS step wrapping for durability

    Args:
        models: List of tuples containing:
            - model_name: Name of the model to execute (e.g., "indexing.document_sections")
            - ctx: PipelineContext with filters, incremental_mode, workflow_id
            - payloads: Optional list of document payloads (for first model in chain)

    Returns:
        Dict mapping model names to their execution results
    """
    from .registry import ModelRegistry

    results = {}

    for model_name, ctx, payloads in models:
        logger.info(f"Executing model: {model_name}")

        # Look up the model in the registry
        model_metadata = ModelRegistry.get(model_name)
        if not model_metadata:
            logger.error(f"Model {model_name} not found in registry")
            results[model_name] = {"error": f"Model {model_name} not registered", "rows_written": 0}
            continue

        model_func = model_metadata["function"]

        # Create reader and writer for this model
        reader = TableReader(
            filters=ctx.filters,
            workflow_id=ctx.workflow_id,
        )

        writer = TableWriter(
            workflow_id=ctx.workflow_id,
        )

        try:
            # Execute the model as a DBOS step
            # For models that don't take payloads (read from tables), pass empty list
            if payloads is None:
                payloads = []

            # Models are synchronous, wrap them for DBOS
            @DBOS.step()
            def execute_model():
                return model_func(
                    ctx=ctx,
                    reader=reader,
                    writer=writer,
                    payloads=payloads,
                )

            result = await execute_model()

            logger.info(
                f"Model {model_name} completed: {result.get('rows_written', 0)} rows written"
            )
            results[model_name] = result

        except Exception as e:
            logger.error(f"Error executing model {model_name}: {e}", exc_info=True)
            results[model_name] = {"error": str(e), "rows_written": 0}

    return results


async def run_model(
    model_name: str,
    ctx: PipelineContext,
    payloads: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Execute a single model as a DBOS step.

    Args:
        model_name: Name of the model to execute
        ctx: PipelineContext with execution parameters
        payloads: Optional document payloads

    Returns:
        Model execution result
    """
    results = await run_models([(model_name, ctx, payloads)])
    return results.get(model_name, {})


async def run_pipeline(
    pipeline: "PipelineConfig",
    ctx: PipelineContext,
) -> Dict[str, Any]:
    """
    Execute a declarative pipeline of models using DAG-based ordering.

    Models declare dependencies via Reference(). The pipeline:
    1. Builds a dependency graph from model references
    2. Topologically sorts into execution levels
    3. Executes each level (future: parallel within level)
    4. Each model is wrapped as a named DBOS step for durability

    Args:
        pipeline: PipelineConfig with list of model names
        ctx: PipelineContext with filters, workflow_id, etc.

    Returns:
        Dict with:
            - results: Dict mapping model names to their results
            - models_executed: List of successfully executed model names
            - errors: Dict of model names to error messages (if any)

    Example:
        pipeline = PipelineConfig(
            name="indexing",
            models=[
                "indexing.document_sections",
                "indexing.section_extractions",
            ],
        )
        result = await run_pipeline(pipeline, ctx)
    """
    from .registry import ModelRegistry

    results = {}
    errors = {}
    models_executed = []

    logger.info(f"Starting pipeline '{pipeline.name}' with {len(pipeline.models)} models")

    # Build dependency graph and get execution order
    try:
        dep_graph = build_dependency_graph(pipeline.models)
        execution_levels = topological_sort(dep_graph)
        logger.info(
            f"Execution order: {' → '.join([', '.join(level) for level in execution_levels])}"
        )
    except ValueError as e:
        logger.error(f"Failed to build execution order: {e}")
        return {
            "results": {},
            "models_executed": [],
            "errors": {"pipeline": str(e)},
        }

    # Helper to execute a single model as an async DBOS step
    async def execute_model_step(model_name: str) -> Tuple[str, Dict[str, Any], Optional[str]]:
        """Execute a single model and return (model_name, result, error)."""
        model_metadata = ModelRegistry.get(model_name)
        if not model_metadata:
            error_msg = f"Model '{model_name}' not found in registry"
            logger.error(error_msg)
            display.start_step(model_name, "Model not found")
            display.end_step(model_name, {"status": "failed", "error": error_msg})
            return model_name, {"error": error_msg, "rows_written": 0}, error_msg

        model_func = model_metadata["function"]
        description = model_metadata.get("description", "")

        # Note: display.start_step/end_step are called inside the model wrapper
        # (decorator.py), so we don't call them here to avoid duplicates.

        try:
            reader = TableReader(filters=ctx.filters, workflow_id=ctx.workflow_id)
            table_name = model_metadata.get("table_name")
            writer = TableWriter(
                workflow_id=ctx.workflow_id,
                table_name=table_name,
            )

            # Wrap as named async DBOS step at runtime.
            # Use asyncio.to_thread to run sync model functions without blocking,
            # enabling parallel execution of independent models within a DAG level.
            #
            # Trade-off: DBOS context (write_stream, set_event) is NOT available
            # inside the thread. Progress events from inside models only log.
            # Start/end events are handled by the decorator wrapper (decorator.py).
            #
            # Alternative considered: DBOS Queue also uses worker threads and has
            # the same context limitation. See kurt/workflows/_worker.py for similar
            # reasoning about why they use start_workflow() instead of queues.
            @DBOS.step(name=model_name)
            async def execute_step():
                return await asyncio.to_thread(
                    model_func,
                    ctx=ctx,
                    reader=reader,
                    writer=writer,
                )

            result = await execute_step()

            logger.info(f"Model '{model_name}' completed: {result.get('rows_written', 0)} rows")

            # Note: display.end_step is called inside the model wrapper (decorator.py)

            return model_name, result, None

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Model '{model_name}' failed: {error_msg}", exc_info=True)

            # Note: display.end_step is called inside the model wrapper (decorator.py)

            return model_name, {"error": error_msg, "rows_written": 0}, error_msg

    # Execute models level by level (parallel within each level)
    level_num = 0
    for level in execution_levels:
        level_num += 1
        logger.info(f"Level {level_num}: executing {len(level)} model(s) in parallel: {level}")

        # Execute all models in this level in parallel using asyncio.gather
        level_results = await asyncio.gather(
            *[execute_model_step(model_name) for model_name in level],
            return_exceptions=True,
        )

        # Process results from this level
        level_has_error = False
        for item in level_results:
            if isinstance(item, Exception):
                # Unexpected exception from gather itself
                error_msg = str(item)
                logger.error(f"Unexpected error in level {level_num}: {error_msg}")
                errors["level_" + str(level_num)] = error_msg
                level_has_error = True
                continue

            model_name, result, error = item
            results[model_name] = result
            if error:
                errors[model_name] = error
                level_has_error = True
            else:
                models_executed.append(model_name)

        # Check if we should stop due to error in this level
        if pipeline.stop_on_error and level_has_error:
            logger.warning(f"Pipeline '{pipeline.name}' stopped due to error in level {level_num}")
            break

    logger.info(
        f"Pipeline '{pipeline.name}' completed: "
        f"{len(models_executed)}/{len(pipeline.models)} models executed"
    )

    return {
        "results": results,
        "models_executed": models_executed,
        "errors": errors,
    }
