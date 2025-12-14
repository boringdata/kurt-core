"""
DBOS workflow for the new indexing pipeline.

This workflow orchestrates the execution of indexing models using the final runtime contract:
- Documents are loaded once at the workflow level
- Models are executed via run_models with proper context
- DBOS events are emitted for monitoring and progress tracking
"""

import logging
from typing import Any, Dict, Optional

from dbos import DBOS

from kurt.content.filtering import DocumentFilters
from kurt.content.indexing_new.framework import (
    ModelContext,
    run_models,
)
from kurt.content.indexing_new.framework.dbos_events import emit_batch_status
from kurt.content.indexing_new.loaders import load_documents

logger = logging.getLogger(__name__)


@DBOS.step()
def _load_documents_step(filters: DocumentFilters, incremental_mode: str, workflow_id: str):
    """Load documents as a DBOS step."""
    return load_documents(
        filters,
        incremental_mode=incremental_mode,
        workflow_id=workflow_id,
        force=False,
    )


@DBOS.workflow()
async def indexing_workflow(
    filters: DocumentFilters,
    incremental_mode: str = "full",
    workflow_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Main DBOS workflow for the indexing pipeline.

    This workflow loads documents once and orchestrates model execution,
    currently only running document_sections but designed to easily add more models.

    Args:
        filters: Document filters to apply
        incremental_mode: Processing mode ("full" or "delta")
        workflow_id: Optional workflow ID (defaults to DBOS.workflow_id)

    Returns:
        Dict containing model results, skipped documents, and workflow metadata
    """
    workflow_id = workflow_id or DBOS.workflow_id

    logger.info(
        "Indexing workflow started (mode=%s, workflow_id=%s)", incremental_mode, workflow_id
    )

    payloads = await _load_documents_step(filters, incremental_mode, workflow_id)
    total_docs = len(payloads)
    skipped_docs = [doc["document_id"] for doc in payloads if doc.get("skip")]
    active_docs = total_docs - len(skipped_docs)

    await emit_batch_status(
        {
            "batch_total": total_docs,
            "batch_status": "splitting",
            "active_docs": active_docs,
            "skipped_docs": len(skipped_docs),
        }
    )

    ctx = ModelContext(filters=filters, incremental_mode=incremental_mode, workflow_id=workflow_id)
    models = [
        ("indexing.document_sections", ctx, payloads),
        # Future models go here...
        # ("indexing.section_extractions", ctx, None),  # Will read from sections table
        # ("indexing.entity_resolution", ctx, None),
        # ("indexing.claim_extraction", ctx, None),
    ]

    results = await run_models(models)

    await emit_batch_status(
        {
            "batch_total": total_docs,
            "batch_status": "complete",
            "active_docs": active_docs,
            "skipped_docs": len(skipped_docs),
            "workflow_done": True,
        }
    )

    return {
        "workflow_id": workflow_id,
        "total_documents": total_docs,
        "documents_processed": active_docs,
        "skipped_docs": skipped_docs,
        "models_executed": list(results.keys()),
        "document_sections": results.get("indexing.document_sections", {}),
    }


@DBOS.workflow()
async def indexing_workflow_full_pipeline(
    filters: DocumentFilters,
    incremental_mode: str = "full",
    workflow_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extended workflow that will run the complete pipeline once all models are migrated.

    This is a placeholder that currently just calls the main workflow,
    but will be expanded to include all models in sequence.
    """
    # For now, just delegate to the main workflow
    return await indexing_workflow(filters, incremental_mode, workflow_id)


def run_section_splitting(
    filters: Optional[DocumentFilters] = None,
    incremental_mode: str = "full",
    workflow_id: Optional[str] = None,
    db_path: Optional[str] = None,  # Allow override for testing
) -> dict:
    """
    Synchronous wrapper for section splitting (backward compatibility).

    This function provides a synchronous interface to the section splitting
    functionality, primarily used for testing and non-DBOS contexts.
    """
    from kurt.content.indexing_new.framework import TableReader, TableWriter
    from kurt.content.indexing_new.loaders import load_documents as load_documents_fn
    from kurt.content.indexing_new.models import document_sections

    # Use default filters if not provided
    if filters is None:
        filters = DocumentFilters()

    logger.info(
        f"Starting section splitting workflow "
        f"(mode: {incremental_mode}, workflow_id: {workflow_id})"
    )

    # Load documents once
    payloads = load_documents_fn(
        filters,
        incremental_mode=incremental_mode,
        workflow_id=workflow_id,
        force=False,  # Respect incremental mode
    )

    logger.info(f"Loaded {len(payloads)} documents for processing")

    # Create reader and writer for the model
    reader = TableReader(db_path=db_path)  # Required by decorator but unused
    writer = TableWriter(db_path=db_path, workflow_id=workflow_id)

    # Execute the document_sections model with the loaded payloads
    result = document_sections(
        reader=reader,
        writer=writer,
        payloads=payloads,
        incremental_mode=incremental_mode,
    )

    logger.info(
        f"Section splitting workflow completed: "
        f"{result.get('rows_written', 0)} sections written"
    )

    return result
