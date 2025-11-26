"""
DBOS Workflows for Content Fetching

Main workflow:
- fetch_workflow(): Unified workflow for single or batch fetching (NO indexing)
  - Single: Calls fetch_document_step()
  - Batch: Parallel execution with DBOS events (doc_N_status, batch_status)

Main step:
- fetch_document_step(): Fetch one document (resolve → fetch → embed → save → links)
  - Use this in other workflows or CLI orchestration
"""

import asyncio
import logging
from typing import Any
from uuid import UUID

from dbos import DBOS, Queue

from kurt.content.document import (
    resolve_or_create_document,
    save_document_content_and_metadata,
)
from kurt.content.embeddings import generate_document_embedding
from kurt.content.fetch import (
    DocumentFetchFilters,
    _get_fetch_engine,
    extract_document_links,
    fetch_from_cms,
    fetch_from_web,
)

logger = logging.getLogger(__name__)

# Create priority-enabled queue for fetch operations
# Concurrency=5 means max 5 concurrent fetch operations
fetch_queue = Queue("fetch_queue", priority_enabled=True, concurrency=5)


# ============================================================================
# DBOS Workflow Steps (Granular Checkpointing)
# ============================================================================


@DBOS.step()
def resolve_document_step(identifier: str | UUID) -> dict[str, Any]:
    """Resolve or create document record. Returns dict with id, source_url, cms fields."""
    return resolve_or_create_document(identifier)


@DBOS.step()
def fetch_content_step(
    source_url: str,
    cms_platform: str | None = None,
    cms_instance: str | None = None,
    cms_document_id: str | None = None,
    discovery_url: str | None = None,
    fetch_engine: str | None = None,
) -> dict[str, Any]:
    """Fetch content from source (CMS or web). Returns dict with content, metadata, public_url."""
    # Determine engine to use
    engine = _get_fetch_engine(override=fetch_engine)

    # Call pure business logic (NO DB operations!)
    if cms_platform and cms_instance and cms_document_id:
        # CMS fetch
        content, metadata, public_url = fetch_from_cms(
            platform=cms_platform,
            instance=cms_instance,
            cms_document_id=cms_document_id,
            discovery_url=discovery_url,
        )
    else:
        # Web fetch
        content, metadata = fetch_from_web(source_url=source_url, fetch_engine=engine)
        public_url = None

    return {
        "content": content,
        "metadata": metadata,
        "content_length": len(content),
        "public_url": public_url,
    }


@DBOS.step()
def generate_embedding_step(content: str) -> dict[str, Any]:
    """Generate document embedding (LLM call). Returns dict with embedding, status."""
    try:
        embedding = generate_document_embedding(content)
        embedding_dims = len(embedding) // 4  # bytes to float32 count

        logger.info(f"Generated embedding ({embedding_dims} dimensions)")

        return {
            "embedding": embedding,
            "embedding_dims": embedding_dims,
            "status": "success",
        }
    except Exception as e:
        # Log but don't fail entire workflow
        logger.warning(f"Could not generate embedding: {e}")
        return {
            "embedding": None,
            "embedding_dims": 0,
            "status": "skipped",
            "error": str(e),
        }


@DBOS.step()
def save_document_step(
    doc_id: str,
    content: str,
    metadata: dict,
    embedding: bytes | None,
    public_url: str | None = None,
) -> dict[str, Any]:
    """Save content and metadata to database. Returns dict with save result."""
    result = save_document_content_and_metadata(
        UUID(doc_id), content, metadata, embedding, public_url=public_url
    )

    logger.info(f"Saved document {doc_id} to {result['content_path']}")

    return result


@DBOS.step()
def save_links_step(doc_id: str, links: list[dict]) -> int:
    """Save document links to database. Returns number of links saved."""
    from kurt.content.document import save_document_links

    return save_document_links(UUID(doc_id), links)


@DBOS.transaction()
def mark_document_error_transaction(doc_id: str, error_message: str) -> dict[str, Any]:
    """Mark document as ERROR in database (ACID). Returns dict with error info."""
    from kurt.db.database import get_session
    from kurt.db.models import Document, IngestionStatus

    session = get_session()
    doc = session.get(Document, UUID(doc_id))

    if doc:
        doc.ingestion_status = IngestionStatus.ERROR
        session.add(doc)
        session.commit()

        logger.info(f"Marked document {doc_id} as ERROR: {error_message}")

    return {"document_id": doc_id, "status": "ERROR", "error": error_message}


@DBOS.step()
def extract_links_step(content: str, source_url: str, base_url: str | None = None) -> list[dict]:
    """Extract links from content. Returns list of links (no DB operation)."""
    # Call pure business logic (NO DB operations!)
    return extract_document_links(content, source_url, base_url=base_url)


@DBOS.step()
def extract_metadata_step(document_id: str, force: bool = False) -> dict[str, Any]:
    """Extract metadata from document (LLM call)."""
    from kurt.content.indexing.extract import extract_document_metadata

    # Create callback to publish events
    def publish_activity(activity: str):
        """Publish indexing activity as DBOS event"""
        DBOS.set_event(f"doc_{document_id[:8]}_index_activity", activity)

    return extract_document_metadata(document_id, force=force, activity_callback=publish_activity)


@DBOS.step()
def select_documents_step(filters: DocumentFetchFilters) -> list[dict[str, Any]]:
    """Select documents to fetch based on filters. Returns list of doc info dicts."""
    from kurt.content.fetch.filtering import select_documents_to_fetch

    return select_documents_to_fetch(filters)


# ============================================================================
# Unified Fetch Workflow
# ============================================================================


@DBOS.step()
def fetch_document_step(
    identifier: str | UUID,
    fetch_engine: str | None = None,
) -> dict[str, Any]:
    """
    Fetch one document (ONLY fetching, no indexing).

    Steps:
    1. Resolve document
    2. Fetch content
    3. Generate embedding
    4. Save to database
    5. Extract and save links
    """
    try:
        # Step 1: Resolve
        doc_info = resolve_document_step(identifier)
        doc_id = doc_info["id"]

        # Step 2: Fetch
        fetch_result = fetch_content_step(
            source_url=doc_info["source_url"],
            cms_platform=doc_info.get("cms_platform"),
            cms_instance=doc_info.get("cms_instance"),
            cms_document_id=doc_info.get("cms_document_id"),
            fetch_engine=fetch_engine,
        )
        content = fetch_result["content"]
        metadata = fetch_result["metadata"]

        # Step 3: Embed
        embedding_result = generate_embedding_step(content)

        # Step 4: Save
        save_result = save_document_step(
            doc_id=doc_id,
            content=content,
            metadata=metadata,
            embedding=embedding_result.get("embedding"),
            public_url=fetch_result.get("public_url"),
        )

        # Step 5: Links
        links = extract_links_step(content, doc_info["source_url"])
        links_count = 0
        if links:
            try:
                links_count = save_links_step(doc_id, links)
            except Exception as e:
                logger.warning(f"Links failed: {e}")

        return {
            "document_id": doc_id,
            "status": "FETCHED",
            "content_length": fetch_result["content_length"],
            "content_path": save_result["content_path"],
            "embedding_dims": embedding_result["embedding_dims"],
            "links_extracted": links_count,
            "metadata": metadata,
        }

    except Exception as e:
        logger.error(f"Failed {identifier}: {e}")
        try:
            doc_info = resolve_document_step(identifier)
            mark_document_error_transaction(doc_info["id"], str(e))
        except Exception:
            pass
        return {"identifier": str(identifier), "status": "ERROR", "error": str(e)}


@DBOS.workflow()
async def fetch_workflow(
    identifiers: str | UUID | list[str | UUID],
    fetch_engine: str | None = None,
    max_concurrent: int = 5,
) -> dict[str, Any]:
    """
    One workflow for fetching (NO indexing - CLI orchestrates that).

    Args:
        identifiers: Single ID or list of IDs
        fetch_engine: Optional engine override
        max_concurrent: Parallel limit

    Returns:
        Single: {document_id, status, ...}
        Batch: {total, successful, failed, results: [...]}
    """
    # Normalize to list
    is_batch = isinstance(identifiers, list)
    id_list = identifiers if is_batch else [identifiers]

    if len(id_list) == 1:
        # SINGLE: Call fetch step directly
        result = fetch_document_step(id_list[0], fetch_engine)
        DBOS.set_event("workflow_done", True)  # Signal completion for CLI polling
        return result

    else:
        # BATCH: Parallel gather with events
        total = len(id_list)

        # Step 1: Batch start
        DBOS.set_event("batch_total", total)
        DBOS.set_event("batch_status", "processing")

        # Step 2: Parallel gather
        semaphore = asyncio.Semaphore(max_concurrent)

        async def fetch_with_semaphore(identifier: str | UUID, index: int) -> dict[str, Any]:
            """Fetch one document with semaphore control and streaming progress."""
            import time
            from datetime import datetime

            key = f"doc_{index}"
            loop = asyncio.get_event_loop()
            start_time = time.time()

            async with semaphore:
                try:
                    # Stream: Started
                    DBOS.write_stream(
                        f"{key}_progress",
                        {
                            "status": "started",
                            "identifier": str(identifier),
                            "timestamp": datetime.now().isoformat(),
                        },
                    )

                    # Step 1: Resolve
                    resolve_start = time.time()
                    doc_info = await loop.run_in_executor(
                        None, lambda: resolve_document_step(identifier)
                    )
                    resolve_duration = time.time() - resolve_start
                    doc_id = doc_info["id"]
                    DBOS.write_stream(
                        f"{key}_progress",
                        {
                            "status": "resolved",
                            "document_id": doc_id,
                            "duration_ms": int(resolve_duration * 1000),
                            "timestamp": datetime.now().isoformat(),
                        },
                    )

                    # Step 2: Fetch
                    fetch_start = time.time()
                    fetch_result = await loop.run_in_executor(
                        None,
                        lambda: fetch_content_step(
                            source_url=doc_info["source_url"],
                            cms_platform=doc_info.get("cms_platform"),
                            cms_instance=doc_info.get("cms_instance"),
                            cms_document_id=doc_info.get("cms_document_id"),
                            fetch_engine=fetch_engine,
                        ),
                    )
                    fetch_duration = time.time() - fetch_start
                    content = fetch_result["content"]
                    metadata = fetch_result["metadata"]
                    DBOS.write_stream(
                        f"{key}_progress",
                        {
                            "status": "fetched",
                            "duration_ms": int(fetch_duration * 1000),
                            "timestamp": datetime.now().isoformat(),
                        },
                    )

                    # Step 3: Embed
                    embed_start = time.time()
                    embedding_result = await loop.run_in_executor(
                        None, lambda: generate_embedding_step(content)
                    )
                    embed_duration = time.time() - embed_start
                    DBOS.write_stream(
                        f"{key}_progress",
                        {
                            "status": "embedded",
                            "duration_ms": int(embed_duration * 1000),
                            "timestamp": datetime.now().isoformat(),
                        },
                    )

                    # Step 4: Save
                    save_start = time.time()
                    save_result = await loop.run_in_executor(
                        None,
                        lambda: save_document_step(
                            doc_id=doc_id,
                            content=content,
                            metadata=metadata,
                            embedding=embedding_result.get("embedding"),
                            public_url=fetch_result.get("public_url"),
                        ),
                    )
                    save_duration = time.time() - save_start
                    DBOS.write_stream(
                        f"{key}_progress",
                        {
                            "status": "saved",
                            "duration_ms": int(save_duration * 1000),
                            "timestamp": datetime.now().isoformat(),
                        },
                    )

                    # Step 5: Links
                    links_start = time.time()
                    links = await loop.run_in_executor(
                        None, lambda: extract_links_step(content, doc_info["source_url"])
                    )
                    links_count = 0
                    if links:
                        try:
                            links_count = await loop.run_in_executor(
                                None, lambda: save_links_step(doc_id, links)
                            )
                        except Exception as e:
                            logger.warning(f"Links failed: {e}")
                    links_duration = time.time() - links_start
                    DBOS.write_stream(
                        f"{key}_progress",
                        {
                            "status": "links_extracted",
                            "duration_ms": int(links_duration * 1000),
                            "timestamp": datetime.now().isoformat(),
                        },
                    )

                    # Stream: Completed with total time
                    total_duration = time.time() - start_time
                    DBOS.write_stream(
                        f"{key}_progress",
                        {
                            "status": "completed",
                            "document_id": doc_id,
                            "duration_ms": int(total_duration * 1000),
                            "timestamp": datetime.now().isoformat(),
                        },
                    )
                    DBOS.close_stream(f"{key}_progress")

                    return {
                        "document_id": doc_id,
                        "status": "FETCHED",
                        "metadata": metadata,
                        "content_length": len(content),
                        "links_count": links_count,
                    }

                except Exception as e:
                    # Stream: Error
                    error_msg = str(e)
                    DBOS.write_stream(f"{key}_progress", {"status": "error", "error": error_msg})
                    DBOS.close_stream(f"{key}_progress")

                    # Try to mark document as error if we have doc_id
                    try:
                        if "doc_id" in locals():
                            await loop.run_in_executor(
                                None, lambda: mark_document_error_transaction(doc_id, error_msg)
                            )
                    except Exception:
                        pass

                    return {"identifier": str(identifier), "status": "ERROR", "error": error_msg}

        results = await asyncio.gather(
            *[fetch_with_semaphore(id, i) for i, id in enumerate(id_list)]
        )

        # Step 3: Batch completion
        successful = sum(1 for r in results if r.get("status") == "FETCHED")
        failed = total - successful

        DBOS.set_event("batch_successful", successful)
        DBOS.set_event("batch_failed", failed)
        DBOS.set_event("batch_status", "completed")
        DBOS.set_event("workflow_done", True)  # Signal completion for CLI polling

        return {"total": total, "successful": successful, "failed": failed, "results": results}


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Main workflow
    "fetch_workflow",
    # Helper step
    "fetch_document_step",
    # Granular steps (for custom workflows)
    "select_documents_step",
    "resolve_document_step",
    "fetch_content_step",
    "generate_embedding_step",
    "save_document_step",
    "save_links_step",
    "extract_links_step",
    "extract_metadata_step",
    "mark_document_error_transaction",
    # Queue
    "fetch_queue",
]
