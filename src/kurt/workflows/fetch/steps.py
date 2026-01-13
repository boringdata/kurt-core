from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from dbos import DBOS, Queue

from kurt.core import embedding_to_bytes, generate_embeddings
from kurt.core.tracking import QueueStepTracker, log_item, step_log
from kurt.db import managed_session
from kurt.integrations.cms import fetch_from_cms

from .config import FetchConfig
from .fetch_file import fetch_from_file
from .fetch_web import fetch_from_web
from .models import BatchFetchResult, FetchDocument, FetchStatus
from .utils import load_document_content, save_content_file

logger = logging.getLogger(__name__)

# Queue for parallel URL fetching (trafilatura/httpx)
fetch_url_queue = Queue("fetch_url_queue", concurrency=5)


@DBOS.step(name="fetch_single_url")
def fetch_single_url_step(
    url: str,
    fetch_engine: str,
    parent_workflow_id: str | None = None,
    parent_step_name: str | None = None,
    document_id: str | None = None,
) -> dict[str, Any]:
    """Fetch a single URL using specified engine.

    This step is enqueued by the workflow for parallel execution.
    Used for trafilatura/httpx which don't have native batch APIs.

    Args:
        url: URL to fetch
        fetch_engine: Engine to use (trafilatura or httpx)
        parent_workflow_id: Parent workflow ID for linking in UI
        parent_step_name: Parent step name for grouping in UI

    Returns:
        Dict with url, content, metadata, or error
    """
    from .fetch_httpx import fetch_with_httpx
    from .fetch_trafilatura import fetch_with_trafilatura

    # Store parent workflow ID for UI linking
    if parent_workflow_id:
        try:
            DBOS.set_event("parent_workflow_id", parent_workflow_id)
        except Exception:
            pass
    if parent_step_name:
        try:
            DBOS.set_event("parent_step_name", parent_step_name)
        except Exception:
            pass

    tracker = QueueStepTracker("fetch_single_url", total=1)
    tracker.start(f"Fetching URL using {fetch_engine}")

    try:
        if fetch_engine == "httpx":
            content, metadata = fetch_with_httpx(url)
        else:
            content, metadata = fetch_with_trafilatura(url)

        tracker.item_success(0, url, metadata={"content_length": len(content) if content else 0})
        tracker.end()

        return {
            "url": url,
            "content": content,
            "metadata": metadata,
            "error": None,
        }
    except Exception as e:
        error_msg = str(e)
        tracker.item_error(0, url, error=error_msg)
        tracker.end()
        return {
            "url": url,
            "content": None,
            "metadata": None,
            "error": error_msg,
        }


@DBOS.step(name="fetch_url_batch")
def fetch_url_batch_step(
    urls: list[str],
    fetch_engine: str,
    parent_workflow_id: str | None = None,
    parent_step_name: str | None = None,
    document_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Fetch a batch of URLs using native batch API.

    This step is enqueued by the workflow for parallel execution.
    Used for tavily/firecrawl which have native batch APIs.

    Args:
        urls: List of URLs to fetch in this batch
        fetch_engine: Engine to use (tavily or firecrawl)
        parent_workflow_id: Parent workflow ID for linking in UI
        parent_step_name: Parent step name for grouping in UI

    Returns:
        Dict with results mapping url -> (content, metadata) or error
    """
    # Store parent workflow ID for UI linking
    if parent_workflow_id:
        try:
            DBOS.set_event("parent_workflow_id", parent_workflow_id)
        except Exception:
            pass
    if parent_step_name:
        try:
            DBOS.set_event("parent_step_name", parent_step_name)
        except Exception:
            pass

    tracker = QueueStepTracker("fetch_url_batch", total=len(urls))
    tracker.start(f"Fetching {len(urls)} URL(s) using {fetch_engine}")

    try:
        results = fetch_from_web(urls, fetch_engine)
    except Exception as e:
        error_msg = str(e)
        for idx, url in enumerate(urls):
            tracker.item_error(idx, url, error=error_msg)
        tracker.end()
        return {"results": {url: e for url in urls}, "error": error_msg}

    for idx, url in enumerate(urls):
        result = results.get(url)
        if isinstance(result, Exception) or result is None:
            error_msg = str(result) if result else "No result"
            tracker.item_error(idx, url, error=error_msg)
            continue
        content, _metadata = result
        tracker.item_success(idx, url, metadata={"content_length": len(content) if content else 0})

    tracker.end()
    return {"results": results, "error": None}


def fetch_urls_parallel(docs: list[dict[str, Any]], config: FetchConfig) -> list[dict[str, Any]]:
    """Fetch URLs in parallel using DBOS Queue.

    Must be called from a workflow (not from a step) because Queue.enqueue()
    is forbidden inside steps.

    Strategy:
    - trafilatura/httpx: One task per URL (no native batch)
    - tavily: Batches of 20 URLs (API limit)
    - firecrawl: Batches based on config.batch_size

    Args:
        docs: List of document dicts with source_url
        config: Fetch configuration

    Returns:
        List of result dicts with content/error
    """
    if not docs:
        return []

    total = len(docs)

    # Use QueueStepTracker for progress tracking
    tracker = QueueStepTracker("fetch_documents", total=total)
    tracker.start(f"Fetching {total} document(s) using {config.fetch_engine}")

    # Get parent workflow ID to link queue tasks in UI
    try:
        parent_workflow_id = DBOS.workflow_id
    except Exception:
        parent_workflow_id = None

    # Build URL to doc mapping
    url_to_doc: dict[str, dict[str, Any]] = {}
    for doc in docs:
        url = doc.get("source_url")
        if url:
            url_to_doc[url] = doc

    urls = list(url_to_doc.keys())
    handles: list[tuple[list[str], Any]] = []  # (urls_in_batch, handle)

    if config.fetch_engine in ("tavily", "firecrawl"):
        # Batch mode: group URLs into batches
        batch_size = config.batch_size or 20
        if config.fetch_engine == "tavily":
            batch_size = min(batch_size, 20)  # Tavily API limit

        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i : i + batch_size]
            batch_doc_ids = []
            for url in batch_urls:
                doc_id = url_to_doc.get(url, {}).get("document_id")
                batch_doc_ids.append(str(doc_id) if doc_id is not None else None)
            handle = fetch_url_queue.enqueue(
                fetch_url_batch_step,
                batch_urls,
                config.fetch_engine,
                parent_workflow_id,
                "fetch_documents",
                batch_doc_ids,
            )
            handles.append((batch_urls, handle))
    else:
        # Single URL mode: one task per URL
        for url in urls:
            doc_id = url_to_doc.get(url, {}).get("document_id")
            handle = fetch_url_queue.enqueue(
                fetch_single_url_step,
                url,
                config.fetch_engine,
                parent_workflow_id,
                "fetch_documents",
                str(doc_id) if doc_id is not None else None,
            )
            handles.append(([url], handle))

    # Collect results
    rows: list[dict[str, Any]] = []
    processed = 0

    for batch_urls, handle in handles:
        result = handle.get_result()

        if config.fetch_engine in ("tavily", "firecrawl"):
            # Batch result: result["results"] is a dict mapping url -> (content, metadata) or Exception
            batch_results = result.get("results", {})
            for url in batch_urls:
                doc = url_to_doc.get(url)
                if not doc:
                    continue
                doc_id = doc.get("document_id")
                url_result = batch_results.get(url)

                if isinstance(url_result, Exception) or url_result is None:
                    error_msg = str(url_result) if url_result else "No result"
                    logger.error(f"Failed to fetch {doc_id}: {error_msg}")
                    rows.append(
                        {
                            "document_id": str(doc_id),
                            "source_url": url,
                            "status": FetchStatus.ERROR,
                            "content": None,
                            "content_length": 0,
                            "content_hash": None,
                            "fetch_engine": config.fetch_engine,
                            "public_url": None,
                            "metadata_json": None,
                            "error": error_msg,
                        }
                    )
                    tracker.item_error(processed, str(doc_id), error=error_msg)
                else:
                    content, metadata = url_result
                    logger.info(f"Fetched {doc_id}: {len(content)} chars")
                    rows.append(
                        {
                            "document_id": str(doc_id),
                            "source_url": url,
                            "status": FetchStatus.SUCCESS,
                            "content": content,
                            "content_length": len(content),
                            "content_hash": metadata.get("fingerprint") if metadata else None,
                            "fetch_engine": config.fetch_engine,
                            "public_url": None,
                            "metadata_json": metadata,
                            "error": None,
                        }
                    )
                    tracker.item_success(
                        processed, str(doc_id), metadata={"content_length": len(content)}
                    )
                processed += 1
        else:
            # Single URL result
            url = batch_urls[0]
            doc = url_to_doc.get(url)
            if not doc:
                continue
            doc_id = doc.get("document_id")

            if result.get("error"):
                logger.error(f"Failed to fetch {doc_id}: {result['error']}")
                rows.append(
                    {
                        "document_id": str(doc_id),
                        "source_url": url,
                        "status": FetchStatus.ERROR,
                        "content": None,
                        "content_length": 0,
                        "content_hash": None,
                        "fetch_engine": config.fetch_engine,
                        "public_url": None,
                        "metadata_json": None,
                        "error": result["error"],
                    }
                )
                tracker.item_error(processed, str(doc_id), error=result["error"])
            else:
                content = result["content"]
                metadata = result.get("metadata", {})
                logger.info(f"Fetched {doc_id}: {len(content)} chars")
                rows.append(
                    {
                        "document_id": str(doc_id),
                        "source_url": url,
                        "status": FetchStatus.SUCCESS,
                        "content": content,
                        "content_length": len(content),
                        "content_hash": metadata.get("fingerprint") if metadata else None,
                        "fetch_engine": config.fetch_engine,
                        "public_url": None,
                        "metadata_json": metadata,
                        "error": None,
                    }
                )
                tracker.item_success(
                    processed, str(doc_id), metadata={"content_length": len(content)}
                )
            processed += 1

    tracker.end()
    return rows


def _fetch_single_document(doc: dict[str, Any], config: FetchConfig) -> dict[str, Any]:
    """Fetch a single document and return result dict."""
    doc_id = doc.get("document_id")
    source_url = doc.get("source_url")
    source_type = doc.get("source_type", "url")
    metadata_json = doc.get("metadata_json", {})

    try:
        # Fetch content based on source type
        public_url = None
        if source_type == "cms":
            # CMS documents have platform/instance/cms_id in metadata
            cms_platform = metadata_json.get("cms_platform")
            cms_instance = metadata_json.get("cms_instance")
            cms_document_id = metadata_json.get("cms_id") or metadata_json.get("cms_document_id")

            if cms_platform and cms_instance and cms_document_id:
                content, metadata, public_url = fetch_from_cms(
                    platform=cms_platform,
                    instance=cms_instance,
                    cms_document_id=cms_document_id,
                    discovery_url=doc.get("discovery_url"),
                )
            else:
                raise ValueError(f"CMS document missing platform/instance/cms_id: {doc_id}")
        elif source_type == "file":
            # Local file sources
            content, metadata = fetch_from_file(source_url)
        else:
            # Web URL sources - fetch_from_web returns BatchFetchResult
            results = fetch_from_web([source_url], config.fetch_engine)
            if source_url not in results:
                raise ValueError(f"No result for: {source_url}")
            result = results[source_url]
            if isinstance(result, Exception):
                raise result
            content, metadata = result

        logger.info(f"Fetched {doc_id}: {len(content)} chars")

        return {
            "document_id": str(doc_id),
            "source_url": source_url,
            "status": FetchStatus.SUCCESS,
            "content": content,
            "content_length": len(content),
            "content_hash": metadata.get("fingerprint"),
            "fetch_engine": config.fetch_engine,
            "public_url": public_url,
            "metadata_json": metadata,
            "error": None,
        }

    except Exception as e:
        logger.error(f"Failed to fetch {doc_id}: {e}")
        return {
            "document_id": str(doc_id),
            "source_url": source_url,
            "status": FetchStatus.ERROR,
            "content": None,
            "content_length": 0,
            "content_hash": None,
            "fetch_engine": config.fetch_engine,
            "public_url": None,
            "metadata_json": None,
            "error": str(e),
        }


def _fetch_batch_web_documents(
    docs: list[dict[str, Any]], config: FetchConfig
) -> list[dict[str, Any]]:
    """Fetch multiple web documents using batch API when available.

    Args:
        docs: List of document dicts (all must be source_type="url")
        config: Fetch configuration

    Returns:
        List of result dicts
    """
    if not docs:
        return []

    # Build URL to doc mapping
    url_to_doc: dict[str, dict[str, Any]] = {}
    for doc in docs:
        url = doc.get("source_url")
        if url:
            url_to_doc[url] = doc

    urls = list(url_to_doc.keys())

    # Determine batch size (tavily max=20, firecrawl unlimited)
    batch_size = config.batch_size
    if config.fetch_engine == "tavily":
        # Tavily API limit is 20 - cap user-provided value
        batch_size = min(batch_size or 20, 20)
    elif batch_size is None:
        batch_size = len(urls)  # No batching for other engines

    # Batch fetch URLs in chunks
    batch_results: BatchFetchResult = {}
    for i in range(0, len(urls), batch_size):
        batch_urls = urls[i : i + batch_size]
        results = fetch_from_web(batch_urls, config.fetch_engine)
        batch_results.update(results)

    # Convert batch results to row format
    rows: list[dict[str, Any]] = []
    for url, result in batch_results.items():
        doc = url_to_doc.get(url)
        if not doc:
            continue

        doc_id = doc.get("document_id")

        if isinstance(result, Exception):
            logger.error(f"Failed to fetch {doc_id}: {result}")
            rows.append(
                {
                    "document_id": str(doc_id),
                    "source_url": url,
                    "status": FetchStatus.ERROR,
                    "content": None,
                    "content_length": 0,
                    "content_hash": None,
                    "fetch_engine": config.fetch_engine,
                    "public_url": None,
                    "metadata_json": None,
                    "error": str(result),
                }
            )
        else:
            content, metadata = result
            logger.info(f"Fetched {doc_id}: {len(content)} chars")
            rows.append(
                {
                    "document_id": str(doc_id),
                    "source_url": url,
                    "status": FetchStatus.SUCCESS,
                    "content": content,
                    "content_length": len(content),
                    "content_hash": metadata.get("fingerprint"),
                    "fetch_engine": config.fetch_engine,
                    "public_url": None,
                    "metadata_json": metadata,
                    "error": None,
                }
            )

    return rows


@DBOS.step(name="generate_embeddings")
def embedding_step(rows: list[dict[str, Any]], config_dict: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate embeddings for fetched documents.

    This step runs AFTER save_content_step, so content is loaded from files.
    """
    config = FetchConfig.model_validate(config_dict)

    # Filter to only successfully fetched documents with content_path
    # Compare both enum and string values (status may be serialized)
    fetchable = [
        r
        for r in rows
        if r.get("status") in (FetchStatus.SUCCESS, FetchStatus.SUCCESS.value)
        and r.get("content_path")
    ]

    if not fetchable:
        step_log("No documents to embed", step_name="generate_embeddings")
        for row in rows:
            row["embedding"] = None
        return rows

    step_log(
        f"Generating embeddings for {len(fetchable)} document(s)", step_name="generate_embeddings"
    )

    # Load content from files and truncate for embedding
    texts = []
    doc_ids = []
    for r in fetchable:
        content = load_document_content(r["content_path"])
        if content:
            texts.append(content[: config.embedding_max_chars])
            doc_ids.append(r["document_id"])

    if not texts:
        for row in rows:
            row["embedding"] = None
        return rows

    # Process in batches
    all_embeddings: list[bytes] = []
    for i in range(0, len(texts), config.embedding_batch_size):
        batch_texts = texts[i : i + config.embedding_batch_size]
        batch_embeddings = generate_embeddings(batch_texts, module_name="FETCH")
        all_embeddings.extend([embedding_to_bytes(e) for e in batch_embeddings])

    # Map embeddings back to rows
    embedding_map = dict(zip(doc_ids, all_embeddings))
    for row in rows:
        row["embedding"] = embedding_map.get(row["document_id"])

    return rows


@DBOS.step(name="save_content")
def save_content_step(
    rows: list[dict[str, Any]], config_dict: dict[str, Any]
) -> list[dict[str, Any]]:
    """Save fetched content to files and add content_path to rows.

    Args:
        rows: List of fetch result dicts with 'content' field
        config_dict: FetchConfig as dict

    Returns:
        Same rows with 'content_path' added and 'content' removed
    """
    config = FetchConfig.model_validate(config_dict)

    if config.dry_run:
        # In dry run, don't save files but keep content for inspection
        step_log("Dry run: skipping content save", step_name="save_content")
        for row in rows:
            row["content_path"] = None
        return rows

    saved_count = sum(
        1
        for r in rows
        if r.get("status") in (FetchStatus.SUCCESS, FetchStatus.SUCCESS.value) and r.get("content")
    )
    step_log(f"Saving content for {saved_count} document(s)", step_name="save_content")

    for row in rows:
        # Compare both enum and string values (status may be serialized)
        is_success = row.get("status") in (FetchStatus.SUCCESS, FetchStatus.SUCCESS.value)
        if is_success and row.get("content"):
            try:
                source_url = row.get("source_url")
                content_path = save_content_file(row["document_id"], row["content"], source_url)
                row["content_path"] = content_path
                logger.info(f"Saved content for {row['document_id']} to {content_path}")
            except Exception as e:
                logger.error(f"Failed to save content for {row['document_id']}: {e}")
                row["content_path"] = None
        else:
            row["content_path"] = None

        # Remove content from row to avoid storing in DB
        row.pop("content", None)

    return rows


@DBOS.step(name="fetch_documents")
def fetch_step(docs: list[dict[str, Any]], config_dict: dict[str, Any]) -> dict[str, Any]:
    """Fetch content for documents.

    Uses batch fetching for web URLs when the engine supports it (tavily, firecrawl).
    Falls back to sequential fetching for file/cms sources or unsupported engines.

    Args:
        docs: List of dicts with:
            - document_id: str (required)
            - source_url: str (required)
            - source_type: str ("url" | "file" | "cms")
            - discovery_url: Optional[str]
            - metadata_json: Optional[dict]
        config_dict: FetchConfig as dict

    Returns:
        Dict with total, documents_fetched, documents_failed, rows, etc.
    """
    config = FetchConfig.model_validate(config_dict)

    if not docs:
        logger.warning("No documents provided")
        return {
            "total": 0,
            "documents_fetched": 0,
            "documents_failed": 0,
            "rows_written": 0,
            "rows_updated": 0,
            "rows": [],
            "dry_run": config.dry_run,
        }

    total = len(docs)

    logger.info(f"Fetching {total} documents (engine: {config.fetch_engine})")
    step_log(
        f"Fetching {total} document(s) using {config.fetch_engine}",
        step_name="fetch_documents",
    )

    # Emit observability events
    DBOS.set_event("fetch_engine", config.fetch_engine)
    DBOS.set_event("stage_total", total)

    # Separate docs by source type
    web_docs: list[dict[str, Any]] = []
    non_web_docs: list[dict[str, Any]] = []

    for doc in docs:
        source_type = doc.get("source_type", "url")
        if source_type == "url":
            web_docs.append(doc)
        else:
            non_web_docs.append(doc)

    # Emit source type counts for observability
    DBOS.set_event("web_docs_count", len(web_docs))
    DBOS.set_event("non_web_docs_count", len(non_web_docs))

    rows: list[dict[str, Any]] = []
    processed = 0

    # Process web docs using batch API (handles both native batch and sequential fallback)
    if web_docs:
        batch_rows = _fetch_batch_web_documents(web_docs, config)
        rows.extend(batch_rows)

        # Update progress for each document
        for row in batch_rows:
            processed += 1
            DBOS.set_event("stage_current", processed)
            is_success = row["status"] == FetchStatus.SUCCESS
            progress_event = {
                "step": "fetch_documents",
                "idx": processed - 1,
                "total": total,
                "status": "success" if is_success else "error",
                "engine": config.fetch_engine,
                "document_id": row.get("document_id"),
                "content_length": row.get("content_length", 0),
                "timestamp": time.time(),
            }
            if not is_success and row.get("error"):
                progress_event["error"] = row["error"]
            DBOS.write_stream("progress", progress_event)
            log_item(
                str(row.get("document_id", "")),
                status="success" if is_success else "error",
                message=row.get("error") if not is_success else row.get("source_url", ""),
                counter=(processed, total),
                step_name="fetch_documents",
            )

    # Process non-web docs (file, cms) sequentially - no batch support
    for doc in non_web_docs:
        row = _fetch_single_document(doc, config)
        rows.append(row)
        processed += 1
        DBOS.set_event("stage_current", processed)
        is_success = row["status"] == FetchStatus.SUCCESS
        source_type = doc.get("source_type", "url")
        progress_event = {
            "step": "fetch_documents",
            "idx": processed - 1,
            "total": total,
            "status": "success" if is_success else "error",
            "source_type": source_type,
            "document_id": row.get("document_id"),
            "content_length": row.get("content_length", 0),
            "timestamp": time.time(),
        }
        if not is_success and row.get("error"):
            progress_event["error"] = row["error"]
        DBOS.write_stream("progress", progress_event)
        log_item(
            str(row.get("document_id", "")),
            status="success" if is_success else "error",
            message=row.get("error") if not is_success else row.get("source_url", ""),
            counter=(processed, total),
            step_name="fetch_documents",
        )

    fetched = sum(1 for row in rows if row["status"] == FetchStatus.SUCCESS)
    failed = sum(1 for row in rows if row["status"] == FetchStatus.ERROR)

    logger.info(f"Fetch complete: {fetched} successful, {failed} failed")
    step_log(
        f"Fetch complete: {fetched} successful, {failed} failed",
        step_name="fetch_documents",
    )

    return {
        "total": total,
        "documents_fetched": fetched,
        "documents_failed": failed,
        "rows": _serialize_rows(rows),
        "dry_run": config.dry_run,
    }


def _serialize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Serialize rows for JSON output."""
    return [
        {
            **r,
            "status": r["status"].value
            if isinstance(r.get("status"), FetchStatus)
            else r.get("status"),
        }
        for r in rows
    ]


@DBOS.transaction()
def persist_fetch_documents(rows: list[dict[str, Any]]) -> dict[str, int]:
    """Persist fetch results in a durable transaction."""
    # Fields that are in the row dict but not in FetchDocument model
    # source_url is used for save_content_file path generation but not stored in fetch_documents
    non_model_fields = {"source_url", "content"}

    with managed_session() as session:
        inserted = 0
        updated = 0
        for row in rows:
            # Filter out non-model fields before persisting
            db_row = {k: v for k, v in row.items() if k not in non_model_fields}
            existing_row = session.get(FetchDocument, row["document_id"])
            if existing_row:
                for key, value in db_row.items():
                    setattr(existing_row, key, value)
                existing_row.updated_at = datetime.utcnow()
                updated += 1
            else:
                session.add(FetchDocument(**db_row))
                inserted += 1
        return {"rows_written": inserted, "rows_updated": updated}
