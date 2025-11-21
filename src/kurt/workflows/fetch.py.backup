"""
DBOS Workflows for Content Fetching

This module provides durable, resumable workflows for fetching web content.

Key Features:
- Automatic checkpointing after each document fetch
- Resume from last completed step on crash/restart
- Priority queue support for urgent content
- Batch fetching with progress tracking

Workflows:
- fetch_document_workflow: Fetch single document (durable)
- fetch_batch_workflow: Fetch multiple documents with checkpoints
- fetch_and_index_workflow: Fetch + extract metadata (multi-step)
"""

from typing import Any
from uuid import UUID

from dbos import DBOS, Queue, SetEnqueueOptions

from kurt.content.fetch import fetch_document
from kurt.content.indexing import extract_document_metadata

# Create priority-enabled queue for fetch operations
# Concurrency=5 means max 5 concurrent fetch operations
fetch_queue = Queue("fetch_queue", priority_enabled=True, concurrency=5)


@DBOS.step()
def fetch_document_step(identifier: str | UUID, fetch_engine: str | None = None) -> dict[str, Any]:
    """
    Individual fetch step - DBOS checkpoints after completion.

    This step won't re-run if the workflow restarts after this step completes.

    Args:
        identifier: Document UUID or source URL
        fetch_engine: Optional fetch engine ('firecrawl', 'trafilatura', 'httpx')

    Returns:
        dict with fetch results (document_id, title, status, etc.)
    """
    return fetch_document(identifier, fetch_engine=fetch_engine)


@DBOS.step()
def extract_metadata_step(document_id: str, force: bool = False) -> dict[str, Any]:
    """
    Extract metadata step - DBOS checkpoints after completion.

    This expensive LLM operation is protected by checkpoint.
    Won't re-run if workflow crashes after this step completes.

    Args:
        document_id: Document UUID
        force: If True, re-index even if content hasn't changed

    Returns:
        dict with metadata extraction results
    """
    return extract_document_metadata(document_id, force=force)


@DBOS.workflow()
def fetch_document_workflow(
    identifier: str | UUID, fetch_engine: str | None = None, extract_metadata: bool = True
) -> dict[str, Any]:
    """
    Durable workflow for fetching a single document.

    If this crashes, DBOS will automatically resume from the last completed step.

    Steps:
    1. Fetch document content (checkpointed)
    2. Extract metadata (optional, checkpointed, expensive LLM call)

    Args:
        identifier: Document UUID or source URL
        fetch_engine: Optional fetch engine override
        extract_metadata: If True, also extract metadata after fetching

    Returns:
        dict with keys:
            - document_id: str
            - title: str
            - fetch_status: str
            - metadata: dict (if extract_metadata=True)
    """
    # Step 1: Fetch document content
    fetch_result = fetch_document_step(identifier, fetch_engine=fetch_engine)

    result = {
        "document_id": fetch_result.get("document_id"),
        "title": fetch_result.get("title"),
        "fetch_status": fetch_result.get("status"),
    }

    # Step 2: Extract metadata (if requested)
    if extract_metadata and fetch_result.get("status") == "FETCHED":
        doc_id = str(fetch_result["document_id"])
        metadata_result = extract_metadata_step(doc_id)
        result["metadata"] = metadata_result

    return result


@DBOS.workflow()
def fetch_batch_workflow(
    identifiers: list[str | UUID],
    fetch_engine: str | None = None,
    extract_metadata: bool = False,
) -> dict[str, Any]:
    """
    Batch fetch workflow with progress tracking.

    Each document is a separate step - can resume mid-batch if crashed.

    Args:
        identifiers: List of document UUIDs or source URLs
        fetch_engine: Optional fetch engine override
        extract_metadata: If True, also extract metadata for each document

    Returns:
        dict with keys:
            - total: int
            - successful: int
            - failed: int
            - results: list[dict]
    """
    results = []
    total = len(identifiers)
    successful = 0
    failed = 0

    for i, identifier in enumerate(identifiers):
        # Each fetch is checkpointed
        try:
            result = fetch_document_step(identifier, fetch_engine=fetch_engine)

            # Optionally extract metadata
            if extract_metadata and result.get("status") == "FETCHED":
                doc_id = str(result["document_id"])
                metadata = extract_metadata_step(doc_id)
                result["metadata"] = metadata

            results.append(result)

            if result.get("status") == "FETCHED":
                successful += 1
            else:
                failed += 1

        except Exception as e:
            # Log error and continue
            DBOS.logger.error(f"Failed to fetch {identifier}: {e}")
            results.append({"identifier": str(identifier), "status": "ERROR", "error": str(e)})
            failed += 1

        # Progress tracking (logs to DBOS)
        DBOS.logger.info(f"Progress: {i+1}/{total} documents processed")

    return {"total": total, "successful": successful, "failed": failed, "results": results}


@DBOS.workflow()
def fetch_and_index_workflow(
    identifier: str | UUID, fetch_engine: str | None = None
) -> dict[str, Any]:
    """
    Complete fetch + index workflow (fully resumable).

    This is a convenience workflow that always fetches AND indexes.
    Equivalent to fetch_document_workflow with extract_metadata=True.

    Args:
        identifier: Document UUID or source URL
        fetch_engine: Optional fetch engine override

    Returns:
        dict with fetch and metadata results
    """
    return fetch_document_workflow(identifier, fetch_engine=fetch_engine, extract_metadata=True)


# Priority Queue Helper Functions


def enqueue_fetch_with_priority(
    identifiers: list[str | UUID],
    priority: int = 10,
    fetch_engine: str | None = None,
    extract_metadata: bool = False,
) -> list[str]:
    """
    Enqueue fetch jobs with specific priority.

    Priority ranges from 1 (highest) to 2,147,483,647 (lowest).
    Lower number = higher priority.

    Args:
        identifiers: List of document UUIDs or URLs to fetch
        priority: Priority level (1=highest, default=10)
        fetch_engine: Optional fetch engine override
        extract_metadata: If True, also extract metadata

    Returns:
        List of workflow IDs
    """
    workflow_ids = []

    with SetEnqueueOptions(priority=priority):
        for identifier in identifiers:
            handle = fetch_queue.enqueue(
                fetch_document_workflow,
                identifier=identifier,
                fetch_engine=fetch_engine,
                extract_metadata=extract_metadata,
            )
            workflow_ids.append(handle.workflow_id)

    return workflow_ids


def enqueue_batch_fetch(
    identifiers: list[str | UUID],
    fetch_engine: str | None = None,
    extract_metadata: bool = False,
    priority: int = 10,
) -> str:
    """
    Enqueue a batch fetch job (single workflow for all documents).

    This is more efficient than individual workflows when you don't need
    fine-grained priority control per document.

    Args:
        identifiers: List of document UUIDs or URLs
        fetch_engine: Optional fetch engine override
        extract_metadata: If True, also extract metadata
        priority: Priority level (1=highest, default=10)

    Returns:
        Workflow ID
    """
    with SetEnqueueOptions(priority=priority):
        handle = fetch_queue.enqueue(
            fetch_batch_workflow,
            identifiers=identifiers,
            fetch_engine=fetch_engine,
            extract_metadata=extract_metadata,
        )

    return handle.workflow_id


__all__ = [
    "fetch_document_workflow",
    "fetch_batch_workflow",
    "fetch_and_index_workflow",
    "enqueue_fetch_with_priority",
    "enqueue_batch_fetch",
    "fetch_queue",
]
