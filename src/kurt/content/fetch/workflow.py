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

from dbos import DBOS

from kurt.content.document import (
    resolve_or_create_document,
    save_document_content_and_metadata,
)
from kurt.content.embeddings import generate_document_embedding
from kurt.content.fetch import (
    DocumentFetchFilters,
    _get_fetch_engine,
    extract_document_links,
    fetch_batch_from_cms,
    fetch_from_cms,
    fetch_from_web,
)
from kurt.content.fetch.engines_firecrawl import fetch_with_firecrawl

logger = logging.getLogger(__name__)


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
        except Exception as mark_err:
            logger.debug(f"Could not mark document as error: {mark_err}")
        return {"identifier": str(identifier), "status": "ERROR", "error": str(e)}


@DBOS.step()
def batch_fetch_content_step(
    doc_infos: list[dict[str, Any]],
    fetch_engine: str | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Batch fetch content from multiple sources using appropriate batch APIs.

    Groups documents by source type and uses:
    - CMS batch API for CMS documents (grouped by platform/instance)
    - Firecrawl batch API for web documents (when using firecrawl engine)

    Args:
        doc_infos: List of resolved document info dicts (from resolve_document_step)
        fetch_engine: Optional engine override

    Returns:
        Dict mapping document_id to fetch result dict with content, metadata, etc.
        For failures, includes "error" key with Exception
    """
    from collections import defaultdict

    results = {}
    engine = _get_fetch_engine(override=fetch_engine)

    # Separate CMS and web documents
    cms_groups = defaultdict(list)  # (platform, instance) -> [doc_info, ...]
    web_docs = []

    for doc_info in doc_infos:
        doc_id = doc_info["id"]

        if (
            doc_info.get("cms_platform")
            and doc_info.get("cms_instance")
            and doc_info.get("cms_document_id")
        ):
            # CMS document
            key = (doc_info["cms_platform"], doc_info["cms_instance"])
            cms_groups[key].append(doc_info)
        else:
            # Web document
            web_docs.append(doc_info)

    # Process CMS documents using batch API
    for (platform, instance), group_docs in cms_groups.items():
        cms_doc_ids = [d["cms_document_id"] for d in group_docs]
        discovery_urls = {
            d["cms_document_id"]: d.get("discovery_url")
            for d in group_docs
            if d.get("discovery_url")
        }

        logger.info(f"[Batch] Fetching {len(cms_doc_ids)} CMS docs from {platform}/{instance}")

        try:
            batch_results = fetch_batch_from_cms(platform, instance, cms_doc_ids, discovery_urls)

            for doc_info in group_docs:
                doc_id = doc_info["id"]
                cms_doc_id = doc_info["cms_document_id"]

                result = batch_results.get(cms_doc_id)
                if isinstance(result, Exception):
                    results[doc_id] = {"error": result}
                else:
                    content, metadata, public_url = result
                    results[doc_id] = {
                        "content": content,
                        "metadata": metadata,
                        "content_length": len(content),
                        "public_url": public_url,
                    }
        except Exception as e:
            logger.error(f"[Batch] CMS batch fetch failed for {platform}/{instance}: {e}")
            for doc_info in group_docs:
                results[doc_info["id"]] = {"error": e}

    # Process web documents - use Firecrawl batch if engine is firecrawl and multiple docs
    if web_docs:
        if engine == "firecrawl" and len(web_docs) > 1:
            logger.info(f"[Batch] Fetching {len(web_docs)} web docs with Firecrawl batch API")

            urls = [d["source_url"] for d in web_docs]
            url_to_doc = {d["source_url"]: d for d in web_docs}

            try:
                batch_results = fetch_with_firecrawl(urls)

                for url, result in batch_results.items():
                    doc_info = url_to_doc[url]
                    doc_id = doc_info["id"]

                    if isinstance(result, Exception):
                        results[doc_id] = {"error": result}
                    else:
                        content, metadata = result
                        results[doc_id] = {
                            "content": content,
                            "metadata": metadata,
                            "content_length": len(content),
                            "public_url": None,
                        }
            except Exception as e:
                logger.error(f"[Batch] Firecrawl batch fetch failed: {e}")
                for doc_info in web_docs:
                    results[doc_info["id"]] = {"error": e}
        else:
            # Fetch individually (trafilatura/httpx don't have batch APIs)
            for doc_info in web_docs:
                doc_id = doc_info["id"]
                try:
                    content, metadata = fetch_from_web(doc_info["source_url"], engine)
                    results[doc_id] = {
                        "content": content,
                        "metadata": metadata,
                        "content_length": len(content),
                        "public_url": None,
                    }
                except Exception as e:
                    results[doc_id] = {"error": e}

    logger.info(
        f"[Batch] Fetch complete: {sum(1 for r in results.values() if 'error' not in r)}/{len(results)} successful"
    )

    return results


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
        # BATCH: Optimized batch fetching using batch APIs
        total = len(id_list)

        # Step 1: Batch start
        DBOS.set_event("batch_total", total)
        DBOS.set_event("batch_status", "processing")

        # Step 2: Resolve all documents first (needed for grouping)
        import time
        from datetime import datetime

        loop = asyncio.get_event_loop()

        logger.info(f"[Batch Workflow] Resolving {total} documents...")
        resolve_start = time.time()
        doc_infos = await asyncio.gather(
            *[
                loop.run_in_executor(None, lambda i=identifier: resolve_document_step(i))
                for identifier in id_list
            ]
        )
        resolve_duration = time.time() - resolve_start
        logger.info(f"[Batch Workflow] Resolved {total} documents in {resolve_duration:.2f}s")

        # Step 3: Batch fetch content using appropriate batch APIs
        logger.info("[Batch Workflow] Batch fetching content...")
        fetch_start = time.time()
        fetch_results = await loop.run_in_executor(
            None, lambda: batch_fetch_content_step(doc_infos, fetch_engine)
        )
        fetch_duration = time.time() - fetch_start
        successful_fetches = sum(1 for r in fetch_results.values() if "error" not in r)
        logger.info(
            f"[Batch Workflow] Batch fetch complete: {successful_fetches}/{total} successful in {fetch_duration:.2f}s"
        )

        # Step 4: Process each document (embed, save, links) in parallel
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_fetched_document(doc_info: dict, index: int) -> dict[str, Any]:
            """Process already-fetched document: embed, save, extract links."""
            key = f"doc_{index}"
            doc_id = doc_info["id"]
            start_time = time.time()

            # Get fetch result from batch fetch
            fetch_result = fetch_results.get(doc_id)

            async with semaphore:
                try:
                    # Check if fetch failed
                    if "error" in fetch_result:
                        error = fetch_result["error"]
                        logger.error(f"[{doc_id}] Fetch failed: {error}")
                        await loop.run_in_executor(
                            None, lambda: mark_document_error_transaction(doc_id, str(error))
                        )
                        return {"document_id": doc_id, "status": "ERROR", "error": str(error)}

                    # Get fetched content
                    content = fetch_result["content"]
                    metadata = fetch_result["metadata"]

                    DBOS.write_stream(
                        f"{key}_progress",
                        {
                            "status": "fetched",
                            "document_id": doc_id,
                            "timestamp": datetime.now().isoformat(),
                        },
                    )

                    # Step 1: Embed
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
                    await loop.run_in_executor(
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
                    DBOS.write_stream(
                        f"{key}_progress",
                        {
                            "status": "error",
                            "error": error_msg,
                            "timestamp": datetime.now().isoformat(),
                        },
                    )

                    # Try to mark document as error if we have doc_id
                    if doc_id:
                        try:
                            await loop.run_in_executor(
                                None, lambda: mark_document_error_transaction(doc_id, error_msg)
                            )
                        except Exception as mark_err:
                            logger.debug(f"Could not mark document {doc_id} as error: {mark_err}")

                    return {"document_id": doc_id, "status": "ERROR", "error": error_msg}

                finally:
                    # ALWAYS close stream in finally block to ensure deterministic behavior
                    DBOS.close_stream(f"{key}_progress")

        # Process all documents in parallel
        results = await asyncio.gather(
            *[process_fetched_document(doc_info, i) for i, doc_info in enumerate(doc_infos)]
        )

        # Step 5: Batch completion
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
    # Batch step
    "batch_fetch_content_step",
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
]
