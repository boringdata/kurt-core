"""
Generic DBOS workflow runner for dbt-like pipelines.

Any pipeline can use this - just define a PipelineConfig and call run_workflow().
"""

import logging
from typing import Any, Dict, Optional

from dbos import DBOS

from kurt.content.filtering import DocumentFilters

from .dbos_events import emit_batch_status
from .model_runner import ModelContext, run_pipeline
from .pipeline import PipelineConfig

logger = logging.getLogger(__name__)


@DBOS.workflow()
async def run_workflow(
    pipeline: PipelineConfig,
    filters: DocumentFilters,
    incremental_mode: str = "full",
    workflow_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generic DBOS workflow for any dbt-like pipeline.

    dbt-like execution:
    1. Store workflow context (filters, mode)
    2. Run pipeline models in sequence (each reads from upstream tables)
    3. Emit status events for monitoring

    Args:
        pipeline: PipelineConfig defining which models to run
        filters: Document filters to apply
        incremental_mode: Processing mode ("full" or "delta")
        workflow_id: Optional workflow ID (defaults to DBOS.workflow_id)

    Returns:
        Dict containing model results and workflow metadata

    Example:
        from kurt.content.indexing_new.framework import run_workflow, PipelineConfig

        MY_PIPELINE = PipelineConfig(
            name="my_pipeline",
            models=["my.first_model", "my.second_model"],
        )

        result = await run_workflow(
            pipeline=MY_PIPELINE,
            filters=DocumentFilters(ids="doc1,doc2"),
            incremental_mode="full",
        )
    """
    workflow_id = workflow_id or DBOS.workflow_id

    logger.info(
        "Workflow '%s' started (mode=%s, workflow_id=%s)",
        pipeline.name,
        incremental_mode,
        workflow_id,
    )

    await emit_batch_status(
        {
            "batch_status": "processing",
            "workflow_id": workflow_id,
            "pipeline": pipeline.name,
        }
    )

    # Run pipeline - models read from tables via sources={}
    ctx = ModelContext(filters=filters, incremental_mode=incremental_mode, workflow_id=workflow_id)
    pipeline_result = await run_pipeline(pipeline, ctx)

    # Get document stats from first model result (if available)
    first_model = pipeline.models[0] if pipeline.models else None
    first_result = pipeline_result["results"].get(first_model, {}) if first_model else {}
    total_docs = first_result.get("documents_processed", 0)
    skipped_docs = first_result.get("documents_skipped", 0)

    await emit_batch_status(
        {
            "batch_total": total_docs,
            "batch_status": "complete",
            "active_docs": total_docs - skipped_docs,
            "skipped_docs": skipped_docs,
            "workflow_done": True,
            "pipeline": pipeline.name,
        }
    )

    return {
        "workflow_id": workflow_id,
        "pipeline": pipeline.name,
        "total_documents": total_docs,
        "documents_processed": total_docs - skipped_docs,
        "skipped_docs": skipped_docs,
        "models_executed": pipeline_result["models_executed"],
        "errors": pipeline_result["errors"],
        **pipeline_result["results"],
    }
