"""
Model runner for executing indexing models via DBOS.

This module provides the run_models function that orchestrates the execution
of multiple models in a workflow, handling context, error recovery, and result aggregation.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from dbos import DBOS

from kurt.content.filtering import DocumentFilters
from kurt.content.indexing_new.framework import TableReader, TableWriter

logger = logging.getLogger(__name__)


@dataclass
class ModelContext:
    """Context passed to models during execution."""

    filters: DocumentFilters
    incremental_mode: str = "full"
    workflow_id: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


async def run_models(
    models: List[Tuple[str, ModelContext, Optional[List[Dict[str, Any]]]]],
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
            - context: ModelContext with filters, incremental_mode, workflow_id
            - payloads: Optional list of document payloads (for first model in chain)

    Returns:
        Dict mapping model names to their execution results
    """
    from kurt.content.indexing_new.framework.registry import ModelRegistry

    results = {}

    for model_name, context, payloads in models:
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
            filters=context.filters,
            workflow_id=context.workflow_id,
        )

        writer = TableWriter(
            workflow_id=context.workflow_id,
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
                    reader=reader,
                    writer=writer,
                    payloads=payloads,
                    incremental_mode=context.incremental_mode,
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
    model_name: str, context: ModelContext, payloads: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Execute a single model.

    This is a convenience function for running a single model.

    Args:
        model_name: Name of the model to execute
        context: ModelContext with execution parameters
        payloads: Optional document payloads

    Returns:
        Model execution result
    """
    results = await run_models([(model_name, context, payloads)])
    return results.get(model_name, {})
