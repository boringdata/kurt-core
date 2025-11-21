"""
DBOS Workflows for Content Fetching

Durable, resumable workflows with automatic checkpointing:
- fetch_document_workflow: Fetch single document (5 checkpoints)
- fetch_batch_workflow: Fetch multiple documents with progress tracking
- fetch_and_index_workflow: Fetch + metadata extraction (6 checkpoints)
"""

from typing import Any
from uuid import UUID

from dbos import DBOS, Queue, SetEnqueueOptions

# Import helper functions from their proper modules
from kurt.content.document import (
    add_documents_for_files,
    add_documents_for_urls,
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
from kurt.content.filtering import resolve_ids_to_uuids

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
    """Save content and metadata to database (ACID). Returns dict with save result."""
    result = save_document_content_and_metadata(UUID(doc_id), content, metadata, embedding)

    DBOS.logger.info(f"Saved document {doc_id} to {result['content_path']}")

    return result


@DBOS.transaction()
def save_links_transaction(doc_id: str, links: list[dict]) -> int:
    """Save document links to database (ACID). Returns number of links saved."""
    from sqlmodel import select

    from kurt.db.database import get_session
    from kurt.db.models import DocumentLink

    session = get_session()
    doc_uuid = UUID(doc_id)

    # Delete existing links for this document (on refetch)
    existing_links = session.exec(
        select(DocumentLink).where(DocumentLink.source_document_id == doc_uuid)
    ).all()
    for link in existing_links:
        session.delete(link)

    # Find which target URLs exist in database
    target_urls = [link["url"] for link in links]
    if not target_urls:
        session.commit()
        return 0

    # Resolve URLs to document IDs (calls helper from document.py - NO logic here!)
    from kurt.content.document import resolve_urls_to_doc_ids

    url_to_doc_id = resolve_urls_to_doc_ids(target_urls)

    # Create links for URLs that have matching documents
    saved_count = 0
    for link in links:
        target_url = link["url"]
        if target_url in url_to_doc_id:
            document_link = DocumentLink(
                source_document_id=doc_uuid,
                target_document_id=url_to_doc_id[target_url],
                anchor_text=link["anchor_text"],
            )
            session.add(document_link)
            saved_count += 1

    session.commit()
    return saved_count


@DBOS.step()
def extract_links_step(
    doc_id: str, content: str, source_url: str, base_url: str | None = None
) -> dict[str, Any]:
    """Extract and save document links. Returns dict with links_extracted, status."""
    try:
        # Call pure business logic (NO DB operations!)
        links = extract_document_links(content, source_url, base_url=base_url)

        # Save to database (DB operation in transaction)
        links_count = save_links_transaction(doc_id, links)

        DBOS.logger.info(f"Extracted {len(links)} links, saved {links_count} for document {doc_id}")

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
    """Extract metadata from document (LLM call). Calls indexing workflow."""
    from kurt.content.indexing.workflow_index import index_document_workflow

    return index_document_workflow(document_id, force=force)


@DBOS.step()
def select_documents_step(filters: DocumentFetchFilters) -> list[dict[str, Any]]:
    """Select documents to fetch based on filters. Returns list of doc info dicts."""
    from kurt.content.filtering import apply_glob_filters, build_document_query
    from kurt.db.database import get_session

    session = get_session()

    # Step 1: Create documents for URLs (calls document.py helper - DB operation)
    if filters.url_list:
        DBOS.logger.info(f"Creating documents for {len(filters.url_list)} URLs")
        add_documents_for_urls(filters.url_list)

    # Step 2: Create documents for files (calls document.py helper - DB operation)
    if filters.file_list:
        DBOS.logger.info(f"Creating documents for {len(filters.file_list)} files")
        add_documents_for_files(filters.file_list)

    # Step 3: Resolve IDs to UUIDs (calls filtering.py helper)
    id_uuids = []
    if filters.id_list:
        DBOS.logger.info(f"Resolving {len(filters.id_list)} IDs to UUIDs")
        id_uuids = resolve_ids_to_uuids(filters.id_list)

    # Step 4: Build query (calls filtering.py helper - NO logic here!)
    stmt = build_document_query(
        id_uuids=id_uuids,
        with_status=filters.with_status,
        refetch=filters.refetch,
        in_cluster=filters.in_cluster,
        with_content_type=filters.with_content_type,
        limit=filters.limit,
    )

    # Execute query (DB operation)
    docs = list(session.exec(stmt).all())

    # Step 5: Apply glob filters (calls filtering.py helper - NO logic here!)
    filtered_docs = apply_glob_filters(
        docs,
        include_pattern=filters.include_pattern,
        exclude_pattern=filters.exclude_pattern,
    )

    # Convert to lightweight dicts for checkpoint
    doc_infos = []
    for doc in filtered_docs:
        doc_infos.append(
            {
                "id": str(doc.id),
                "source_url": doc.source_url,
                "cms_platform": doc.cms_platform,
                "cms_instance": doc.cms_instance,
                "cms_document_id": doc.cms_document_id,
                "discovery_url": doc.discovery_url,
            }
        )

    DBOS.logger.info(f"Selected {len(doc_infos)} documents to fetch")

    return doc_infos


# ============================================================================
# DBOS Workflows (Orchestration with Granular Checkpointing)
# ============================================================================


@DBOS.workflow()
def fetch_document_workflow(
    identifier: str | UUID, fetch_engine: str | None = None
) -> dict[str, Any]:
    """Fetch document with 5 checkpointed steps. Returns dict with fetch results."""
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
    """Fetch document and extract metadata with 6 checkpointed steps."""
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
    """Batch fetch workflow with progress tracking and checkpoints per document."""
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
    """Enqueue fetch jobs with priority (1=highest). Returns workflow IDs."""
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
    """Enqueue batch fetch job as single workflow. Returns workflow ID."""
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
    "select_documents_step",
    "resolve_document_step",
    "fetch_content_step",
    "generate_embedding_step",
    "save_document_transaction",
    "save_links_transaction",
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
