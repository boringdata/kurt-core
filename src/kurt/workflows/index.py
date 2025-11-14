"""
DBOS Workflows for Content Indexing

This module provides durable, resumable workflows for extracting metadata
from documents using LLM-based extraction.

Key Features:
- Automatic checkpointing after each document indexing
- Resume from last completed step on crash/restart
- Priority queue support for urgent indexing
- Batch indexing with progress tracking

Workflows:
- index_document_workflow: Index single document (durable)
- index_batch_workflow: Index multiple documents with checkpoints
"""

from typing import Any

from dbos import DBOS, Queue, SetEnqueueOptions

from kurt.content.indexing import extract_document_metadata

# Create priority-enabled queue for index operations
# Concurrency=3 means max 3 concurrent LLM extractions (to control costs)
index_queue = Queue("index_queue", priority_enabled=True, concurrency=3)


@DBOS.step()
def index_document_step(document_id: str, force: bool = False) -> dict[str, Any]:
    """
    Individual index step - DBOS checkpoints after completion.

    This expensive LLM operation is protected by checkpoint.
    Won't re-run if workflow restarts after this step completes.

    Args:
        document_id: Document UUID
        force: If True, re-index even if content hasn't changed

    Returns:
        dict with metadata extraction results
    """
    return extract_document_metadata(document_id, force=force)


@DBOS.workflow()
def index_document_workflow(document_id: str, force: bool = False) -> dict[str, Any]:
    """
    Durable workflow for indexing a single document.

    If this crashes, DBOS will automatically resume from the last completed step.

    Args:
        document_id: Document UUID
        force: If True, re-index even if content hasn't changed

    Returns:
        dict with metadata extraction results
    """
    result = index_document_step(document_id, force=force)

    return {
        "document_id": document_id,
        "status": "indexed" if result else "failed",
        "metadata": result,
    }


@DBOS.workflow()
def index_batch_workflow(document_ids: list[str], force: bool = False) -> dict[str, Any]:
    """
    Batch index workflow with progress tracking.

    Each document is a separate step - can resume mid-batch if crashed.

    Args:
        document_ids: List of document UUIDs to index
        force: If True, re-index even if content hasn't changed

    Returns:
        dict with keys:
            - total: int
            - successful: int
            - failed: int
            - results: list[dict]
    """
    results = []
    total = len(document_ids)
    successful = 0
    failed = 0

    for i, doc_id in enumerate(document_ids):
        # Each index is checkpointed
        try:
            result = index_document_step(doc_id, force=force)
            results.append({"document_id": doc_id, "status": "indexed", "metadata": result})
            successful += 1

        except Exception as e:
            # Log error and continue
            DBOS.logger.error(f"Failed to index {doc_id}: {e}")
            results.append({"document_id": doc_id, "status": "error", "error": str(e)})
            failed += 1

        # Progress tracking (logs to DBOS)
        DBOS.logger.info(f"Progress: {i+1}/{total} documents indexed")

    return {"total": total, "successful": successful, "failed": failed, "results": results}


# Priority Queue Helper Functions


def enqueue_index_with_priority(
    document_ids: list[str], priority: int = 10, force: bool = False
) -> list[str]:
    """
    Enqueue index jobs with specific priority.

    Priority ranges from 1 (highest) to 2,147,483,647 (lowest).
    Lower number = higher priority.

    Args:
        document_ids: List of document UUIDs to index
        priority: Priority level (1=highest, default=10)
        force: If True, re-index even if content hasn't changed

    Returns:
        List of workflow IDs
    """
    workflow_ids = []

    with SetEnqueueOptions(priority=priority):
        for doc_id in document_ids:
            handle = index_queue.enqueue(index_document_workflow, document_id=doc_id, force=force)
            workflow_ids.append(handle.workflow_id)

    return workflow_ids


def enqueue_batch_index(document_ids: list[str], force: bool = False, priority: int = 10) -> str:
    """
    Enqueue a batch index job (single workflow for all documents).

    This is more efficient than individual workflows when you don't need
    fine-grained priority control per document.

    Args:
        document_ids: List of document UUIDs
        force: If True, re-index even if content hasn't changed
        priority: Priority level (1=highest, default=10)

    Returns:
        Workflow ID
    """
    with SetEnqueueOptions(priority=priority):
        handle = index_queue.enqueue(index_batch_workflow, document_ids=document_ids, force=force)

    return handle.workflow_id


__all__ = [
    "index_document_workflow",
    "index_batch_workflow",
    "enqueue_index_with_priority",
    "enqueue_batch_index",
    "index_queue",
]
