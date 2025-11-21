"""
DBOS Workflows for Content Fetching

This module provides durable, resumable workflows for fetching web content.

Key Features:
- Automatic checkpointing after each step (5 steps per document!)
- Resume from last completed step on crash/restart
- Priority queue support for urgent content
- Batch fetching with progress tracking
- Granular checkpointing for expensive operations (HTTP, LLM, DB)

Workflows:
- fetch_document_workflow: Fetch single document with 5 checkpointed steps
- fetch_batch_workflow: Fetch multiple documents with checkpoints
- fetch_and_index_workflow: Fetch + extract metadata (fully checkpointed)

Checkpoint Strategy:
1. Resolve document → Fast DB lookup
2. Fetch content → Network I/O (can timeout/rate-limit)
3. Generate embedding → EXPENSIVE LLM call (~$0.0001)
4. Save to database → Atomic transaction
5. Extract links → Optional, doesn't block

If embedding fails, steps 1-2 don't re-run = cost savings!
"""

from typing import Any
from uuid import UUID

from dbos import DBOS, Queue, SetEnqueueOptions

# Import helper functions from refactored fetch.py
from kurt.content.fetch import (
    extract_and_save_document_links,
    fetch_content_from_source,
    generate_document_embedding,
    resolve_or_create_document,
    save_document_content_and_metadata,
)
from kurt.content.indexing import extract_document_metadata

# Create priority-enabled queue for fetch operations
# Concurrency=5 means max 5 concurrent fetch operations
fetch_queue = Queue("fetch_queue", priority_enabled=True, concurrency=5)


# ============================================================================
# DBOS Workflow Steps (Granular Checkpointing)
# ============================================================================


@DBOS.step()
def resolve_document_step(identifier: str | UUID) -> dict[str, Any]:
    """
    Step 1: Resolve or create document record.

    Fast database lookup - checkpointed to avoid re-creating documents.
    Returns lightweight dict to minimize checkpoint data size.

    Args:
        identifier: Document UUID or source URL

    Returns:
        dict with document info (id, source_url, cms fields)
    """
    return resolve_or_create_document(identifier)


@DBOS.step()
def fetch_content_step(
    source_url: str,
    cms_platform: str | None = None,
    cms_instance: str | None = None,
    cms_document_id: str | None = None,
    fetch_engine: str | None = None,
) -> dict[str, Any]:
    """
    Step 2: Fetch content from source.

    Network I/O - can fail due to timeouts, rate limits, etc.
    Checkpointing means we don't re-fetch on retry!

    Args:
        source_url: Source URL to fetch
        cms_platform: CMS platform (optional)
        cms_instance: CMS instance (optional)
        cms_document_id: CMS document ID (optional)
        fetch_engine: Optional engine override

    Returns:
        dict with content and metadata
    """
    content, metadata = fetch_content_from_source(
        source_url=source_url,
        cms_platform=cms_platform,
        cms_instance=cms_instance,
        cms_document_id=cms_document_id,
        fetch_engine=fetch_engine,
    )

    return {
        "content": content,
        "metadata": metadata,
        "content_length": len(content),
    }


@DBOS.step()
def generate_embedding_step(content: str) -> dict[str, Any]:
    """
    Step 3: Generate document embedding.

    EXPENSIVE LLM CALL (~$0.0001 per call) - critical to checkpoint!
    If this fails, we don't re-fetch content (saves time + money).
    If workflow restarts after this completes, we don't re-generate.

    Args:
        content: Document content

    Returns:
        dict with embedding and status
    """
    try:
        embedding = generate_document_embedding(content)
        embedding_dims = len(embedding) // 4  # bytes to float32 count

        DBOS.logger.info(f"Generated embedding ({embedding_dims} dimensions)")

        return {
            "embedding": embedding,
            "embedding_dims": embedding_dims,
            "status": "success",
        }
    except Exception as e:
        # Log but don't fail entire workflow
        DBOS.logger.warning(f"Could not generate embedding: {e}")
        return {
            "embedding": None,
            "embedding_dims": 0,
            "status": "skipped",
            "error": str(e),
        }


@DBOS.transaction()
def save_document_transaction(
    doc_id: str, content: str, metadata: dict, embedding: bytes | None
) -> dict[str, Any]:
    """
    Step 4: Save content and metadata to database.

    ACID transaction - uses @DBOS.transaction() for proper guarantees.
    File write + database update are atomic and checkpointed.

    Args:
        doc_id: Document UUID (as string)
        content: Markdown content
        metadata: Metadata dict
        embedding: Optional embedding bytes

    Returns:
        dict with save result
    """
    result = save_document_content_and_metadata(UUID(doc_id), content, metadata, embedding)

    DBOS.logger.info(f"Saved document {doc_id} to {result['content_path']}")

    return result


@DBOS.step()
def extract_links_step(doc_id: str, content: str, source_url: str) -> dict[str, Any]:
    """
    Step 5: Extract and save document links.

    Separate step so link extraction failures don't affect document save.
    Optional operation - workflow succeeds even if this fails.

    Args:
        doc_id: Document UUID (as string)
        content: Markdown content
        source_url: Source URL for resolving relative links

    Returns:
        dict with links extraction result
    """
    try:
        links_count = extract_and_save_document_links(UUID(doc_id), content, source_url)

        DBOS.logger.info(f"Extracted {links_count} links for document {doc_id}")

        return {
            "links_extracted": links_count,
            "status": "success",
        }
    except Exception as e:
        DBOS.logger.warning(f"Could not extract links: {e}")
        return {
            "links_extracted": 0,
            "status": "failed",
            "error": str(e),
        }


@DBOS.step()
def extract_metadata_step(document_id: str, force: bool = False) -> dict[str, Any]:
    """
    Step 6: Extract metadata from document.

    EXPENSIVE LLM CALL (~$0.01 per call) - must be checkpointed!
    Used in fetch_and_index_workflow.

    Args:
        document_id: Document UUID
        force: If True, re-index even if content hasn't changed

    Returns:
        dict with metadata extraction results
    """
    return extract_document_metadata(document_id, force=force)


# ============================================================================
# DBOS Workflows (Orchestration with Granular Checkpointing)
# ============================================================================


@DBOS.workflow()
def fetch_document_workflow(
    identifier: str | UUID, fetch_engine: str | None = None
) -> dict[str, Any]:
    """
    Durable workflow for fetching a document.

    Each step is checkpointed - workflow can resume from any step on failure:

    1. Resolve document → Fast DB lookup
    2. Fetch content → Network I/O (can timeout/rate-limit)
    3. Generate embedding → EXPENSIVE LLM call (~$0.0001)
    4. Save to database → Atomic transaction
    5. Extract links → Optional, doesn't block

    Failure Recovery Examples:
    - Network timeout after step 1 → Resume from step 2 (re-fetch)
    - Embedding fails after step 2 → Resume from step 3 (NO re-fetch!)
    - Database error after step 3 → Resume from step 4 (NO re-fetch, NO re-embed!)
    - Link extraction fails → Document still saved, just log warning

    Args:
        identifier: Document UUID or source URL
        fetch_engine: Optional engine override

    Returns:
        dict with complete fetch results
    """
    # Step 1: Resolve document (fast DB lookup - checkpointed)
    DBOS.logger.info(f"Resolving document: {identifier}")
    doc_info = resolve_document_step(identifier)
    doc_id = doc_info["id"]

    # Step 2: Fetch content (network I/O - checkpointed!)
    DBOS.logger.info(f"Fetching content for {doc_id} from {doc_info['source_url']}")
    fetch_result = fetch_content_step(
        source_url=doc_info["source_url"],
        cms_platform=doc_info.get("cms_platform"),
        cms_instance=doc_info.get("cms_instance"),
        cms_document_id=doc_info.get("cms_document_id"),
        fetch_engine=fetch_engine,
    )
    content = fetch_result["content"]
    metadata = fetch_result["metadata"]

    # Step 3: Generate embedding (EXPENSIVE LLM - checkpointed!)
    DBOS.logger.info(f"Generating embedding for {doc_id}")
    embedding_result = generate_embedding_step(content)

    # Step 4: Save to database (transactional - checkpointed!)
    DBOS.logger.info(f"Saving document {doc_id} to database")
    save_result = save_document_transaction(
        doc_id=doc_id,
        content=content,
        metadata=metadata,
        embedding=embedding_result.get("embedding"),
    )

    # Step 5: Extract links (optional - checkpointed!)
    DBOS.logger.info(f"Extracting links for {doc_id}")
    links_result = extract_links_step(doc_id, content, doc_info["source_url"])

    return {
        "document_id": doc_id,
        "status": save_result["status"],
        "content_length": fetch_result["content_length"],
        "content_path": save_result["content_path"],
        "embedding_dims": embedding_result["embedding_dims"],
        "links_extracted": links_result["links_extracted"],
        "metadata": metadata,
    }


@DBOS.workflow()
def fetch_and_index_workflow(
    identifier: str | UUID, fetch_engine: str | None = None
) -> dict[str, Any]:
    """
    Complete fetch + index workflow with proper checkpointing.

    This workflow has meaningful structure with 6 checkpointed steps:

    Steps 1-5: Fetch document (via fetch_document_workflow)
      1. Resolve document
      2. Fetch content (network I/O)
      3. Generate embedding (LLM ~$0.0001)
      4. Save to database (transaction)
      5. Extract links

    Step 6: Extract metadata (EXPENSIVE LLM ~$0.01)

    Key Benefit: If metadata extraction fails, document is already fetched!
    On retry, only step 6 runs (no re-fetch, no re-embed).

    This is a MAJOR improvement over the old implementation where
    metadata failure would re-run the entire fetch.

    Args:
        identifier: Document UUID or source URL
        fetch_engine: Optional fetch engine override

    Returns:
        dict with fetch and metadata results
    """
    # Steps 1-5: Fetch document (checkpointed sub-workflow)
    DBOS.logger.info(f"Starting fetch workflow for {identifier}")
    fetch_result = fetch_document_workflow(identifier, fetch_engine)

    # Step 6: Extract metadata (EXPENSIVE LLM - checkpointed!)
    DBOS.logger.info(f"Extracting metadata for {fetch_result['document_id']}")
    metadata_result = extract_metadata_step(fetch_result["document_id"], force=False)

    return {
        **fetch_result,
        "index_metadata": metadata_result,
        "workflow_status": "completed",
    }


@DBOS.workflow()
def fetch_batch_workflow(
    identifiers: list[str | UUID],
    fetch_engine: str | None = None,
    extract_metadata: bool = False,
) -> dict[str, Any]:
    """
    Batch fetch workflow with progress tracking.

    Each document is fetched using fetch_document_workflow,
    which provides 5 checkpoints per document.

    Can resume mid-batch if crashed.

    Args:
        identifiers: List of document UUIDs or source URLs
        fetch_engine: Optional fetch engine override
        extract_metadata: If True, also extract metadata for each document

    Returns:
        dict with batch results
    """
    results = []
    total = len(identifiers)
    successful = 0
    failed = 0

    for i, identifier in enumerate(identifiers):
        # Each fetch is checkpointed (5 steps per document)
        try:
            if extract_metadata:
                # Use fetch_and_index_workflow (6 checkpoints)
                result = fetch_and_index_workflow(identifier, fetch_engine)
            else:
                # Use fetch_document_workflow (5 checkpoints)
                result = fetch_document_workflow(identifier, fetch_engine)

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


# ============================================================================
# Priority Queue Helper Functions
# ============================================================================


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
            if extract_metadata:
                handle = fetch_queue.enqueue(
                    fetch_and_index_workflow,
                    identifier=identifier,
                    fetch_engine=fetch_engine,
                )
            else:
                handle = fetch_queue.enqueue(
                    fetch_document_workflow,
                    identifier=identifier,
                    fetch_engine=fetch_engine,
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
    # Workflow steps (for direct use if needed)
    "resolve_document_step",
    "fetch_content_step",
    "generate_embedding_step",
    "save_document_transaction",
    "extract_links_step",
    "extract_metadata_step",
    # Main workflows
    "fetch_document_workflow",
    "fetch_and_index_workflow",
    "fetch_batch_workflow",
    # Queue helpers
    "enqueue_fetch_with_priority",
    "enqueue_batch_fetch",
    "fetch_queue",
]
