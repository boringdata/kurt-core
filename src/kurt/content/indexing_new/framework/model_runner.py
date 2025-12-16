"""
Model runner for executing indexing models via DBOS.

This module provides the run_models function that orchestrates the execution
of multiple models in a workflow, handling context, error recovery, and result aggregation.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from dbos import DBOS

from kurt.content.filtering import DocumentFilters

logger = logging.getLogger(__name__)


@dataclass
class PipelineContext:
    """Context passed to pipeline steps during execution.

    This context object provides:
    - filters: DocumentFilters with document IDs to process
    - workflow_id: Unique identifier for this workflow run
    - incremental_mode: "full" or "delta" processing mode
    - metadata: Additional key-value pairs for custom data

    Steps can access this context to get filtering info, workflow tracking, etc.
    References can use this context for filtering operations.
    """

    filters: DocumentFilters
    workflow_id: Optional[str] = None
    incremental_mode: str = "full"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def document_ids(self) -> List[str]:
        """Get list of document IDs from filters."""
        if self.filters and self.filters.ids:
            return [id.strip() for id in self.filters.ids.split(",")]
        return []


# Backward compatibility alias
ModelContext = PipelineContext


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
    from kurt.content.indexing_new.framework.registry import ModelRegistry
    from kurt.content.indexing_new.framework.table_io import TableReader, TableWriter

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
    model_name: str, ctx: PipelineContext, payloads: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Execute a single model.

    This is a convenience function for running a single model.

    Args:
        model_name: Name of the model to execute
        ctx: PipelineContext with execution parameters
        payloads: Optional document payloads

    Returns:
        Model execution result
    """
    results = await run_models([(model_name, ctx, payloads)])
    return results.get(model_name, {})
