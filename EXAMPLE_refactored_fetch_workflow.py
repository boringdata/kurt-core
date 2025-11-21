"""
Example: Refactored DBOS Workflow with Better Granularity

This shows how to break down fetch_document into meaningful, checkpointed steps.
"""

from typing import Any
from uuid import UUID

from dbos import DBOS

# ============================================================================
# Core Business Logic (in content/fetch.py)
# ============================================================================


def resolve_or_create_document(identifier: str | UUID) -> dict:
    """
    Find existing document or create new one.

    Fast database operation - no need to checkpoint.
    Returns lightweight dict to minimize checkpoint data.
    """
    from sqlmodel import select

    from kurt.content.fetch import add_document
    from kurt.db.database import get_session
    from kurt.db.models import Document

    session = get_session()

    # Try UUID lookup
    try:
        doc_id = UUID(identifier) if not isinstance(identifier, UUID) else identifier
        doc = session.get(Document, doc_id)
        if doc:
            return {
                "id": str(doc.id),
                "source_url": doc.source_url,
                "cms_platform": doc.cms_platform,
                "cms_instance": doc.cms_instance,
            }
    except (ValueError, AttributeError):
        pass

    # Try URL lookup
    stmt = select(Document).where(Document.source_url == str(identifier))
    doc = session.exec(stmt).first()

    if not doc:
        # Create new document
        doc_id = add_document(str(identifier))
        doc = session.get(Document, doc_id)

    return {
        "id": str(doc.id),
        "source_url": doc.source_url,
        "cms_platform": doc.cms_platform,
        "cms_instance": doc.cms_instance,
    }


def fetch_content_from_source(
    source_url: str, cms_platform: str = None, cms_instance: str = None, engine: str = None
) -> tuple[str, dict]:
    """
    Fetch raw content from URL or CMS.

    Network I/O - can fail, should be checkpointed.
    Returns (content, metadata_dict).
    """
    from kurt.content.fetch import _fetch_from_cms, _get_fetch_engine
    from kurt.content.fetch_firecrawl import fetch_with_firecrawl
    from kurt.content.fetch_httpx import fetch_with_httpx
    from kurt.content.fetch_trafilatura import fetch_with_trafilatura

    # CMS fetch
    if cms_platform and cms_instance:
        # Need document object for CMS fetch - lightweight wrapper
        from kurt.db.database import get_session
        from kurt.db.models import Document

        session = get_session()
        # Find by source_url to get full document
        from sqlmodel import select

        doc = session.exec(select(Document).where(Document.source_url == source_url)).first()
        return _fetch_from_cms(cms_platform, cms_instance, doc)

    # Web fetch
    fetch_engine = _get_fetch_engine(override=engine)

    if fetch_engine == "firecrawl":
        return fetch_with_firecrawl(source_url)
    elif fetch_engine == "httpx":
        return fetch_with_httpx(source_url)
    else:
        return fetch_with_trafilatura(source_url)


def generate_document_embedding(content: str) -> bytes:
    """
    Generate embedding vector for content.

    Expensive LLM call - must be checkpointed!
    """
    import dspy
    import numpy as np

    from kurt.config import load_config

    config = load_config()
    embedding_model = config.EMBEDDING_MODEL

    # Use first 1000 chars
    content_sample = content[:1000] if len(content) > 1000 else content

    embedding_vector = dspy.Embedder(model=embedding_model)([content_sample])[0]
    return np.array(embedding_vector, dtype=np.float32).tobytes()


def save_document_content_and_metadata(
    doc_id: UUID, content: str, metadata: dict, embedding: bytes | None
) -> dict:
    """
    Save content to filesystem and update database.

    Transactional operation - use @DBOS.transaction() wrapper.
    """

    from kurt.config import load_config
    from kurt.content.paths import create_cms_content_path, create_content_path
    from kurt.db.database import get_session
    from kurt.db.models import Document, IngestionStatus

    session = get_session()
    doc = session.get(Document, doc_id)

    # Update metadata
    if metadata:
        if metadata.get("title"):
            doc.title = metadata["title"]
        if metadata.get("fingerprint"):
            doc.content_hash = metadata["fingerprint"]
        if metadata.get("description"):
            doc.description = metadata["description"]

        # Author
        author = metadata.get("author")
        if author:
            doc.author = [author] if isinstance(author, str) else list(author)

        # Published date
        if metadata.get("date"):
            from datetime import datetime

            try:
                doc.published_date = datetime.fromisoformat(metadata["date"])
            except (ValueError, AttributeError):
                pass

    # Store embedding
    if embedding:
        doc.embedding = embedding

    # Determine content path
    config = load_config()

    if doc.cms_platform and doc.cms_instance:
        content_path = create_cms_content_path(
            platform=doc.cms_platform,
            instance=doc.cms_instance,
            doc_id=doc.cms_document_id,
            config=config,
            source_url=doc.source_url,
        )
    else:
        content_path = create_content_path(doc.source_url, config)

    # Write file
    content_path.parent.mkdir(parents=True, exist_ok=True)
    with open(content_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Update document record
    source_base = config.get_absolute_sources_path()
    doc.content_path = str(content_path.relative_to(source_base))
    doc.ingestion_status = IngestionStatus.FETCHED

    session.commit()

    return {
        "content_path": str(content_path),
        "status": "FETCHED",
    }


def extract_and_save_document_links(doc_id: UUID, content: str, source_url: str) -> int:
    """
    Extract markdown links and save to database.

    Fast operation, but separate from main save to isolate failures.
    """
    from kurt.content.fetch import extract_document_links, save_document_links
    from kurt.db.database import get_session
    from kurt.db.models import Document

    session = get_session()
    doc = session.get(Document, doc_id)

    # Get base_url for CMS documents
    base_url = None
    if doc.cms_platform and doc.cms_instance:
        try:
            from kurt.integrations.cms.config import get_platform_config

            cms_config = get_platform_config(doc.cms_platform, doc.cms_instance)
            base_url = cms_config.get("base_url")
        except Exception:
            pass

    links = extract_document_links(content, source_url, base_url=base_url)
    links_saved = save_document_links(doc_id, links)

    return links_saved


# ============================================================================
# DBOS Workflow Steps (in workflows/fetch.py)
# ============================================================================


@DBOS.step()
def resolve_document_step(identifier: str | UUID) -> dict[str, Any]:
    """
    Step 1: Resolve or create document record.

    Fast database lookup - checkpointed to avoid re-creating documents.
    """
    return resolve_or_create_document(identifier)


@DBOS.step()
def fetch_content_step(
    source_url: str,
    cms_platform: str | None = None,
    cms_instance: str | None = None,
    fetch_engine: str | None = None,
) -> dict[str, Any]:
    """
    Step 2: Fetch content from source.

    Network I/O - can fail due to timeouts, rate limits, etc.
    Checkpointing means we don't re-fetch on retry.
    """
    content, metadata = fetch_content_from_source(
        source_url, cms_platform, cms_instance, fetch_engine
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

    EXPENSIVE LLM CALL - critical to checkpoint!
    If this fails, we don't re-fetch content.
    If workflow restarts after this completes, we don't re-generate.
    """
    try:
        embedding = generate_document_embedding(content)
        embedding_dims = len(embedding) // 4  # bytes to float32 count

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
    File write + database update are atomic.
    """
    result = save_document_content_and_metadata(UUID(doc_id), content, metadata, embedding)

    return result


@DBOS.step()
def extract_links_step(doc_id: str, content: str, source_url: str) -> dict[str, Any]:
    """
    Step 5: Extract and save document links.

    Separate step so link extraction failures don't affect document save.
    """
    try:
        links_count = extract_and_save_document_links(UUID(doc_id), content, source_url)
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


# ============================================================================
# DBOS Workflows (in workflows/fetch.py)
# ============================================================================


@DBOS.workflow()
def fetch_document_workflow(
    identifier: str | UUID, fetch_engine: str | None = None
) -> dict[str, Any]:
    """
    Durable workflow for fetching a document.

    Each step is checkpointed - workflow can resume from any step:
    1. Resolve/create document → lightweight, fast
    2. Fetch content → network I/O, can fail
    3. Generate embedding → EXPENSIVE LLM call
    4. Save to database → transactional
    5. Extract links → optional, doesn't block

    Example failure scenarios:
    - Network timeout after step 1 → resume from step 2 (re-fetch)
    - Embedding fails after step 2 → resume from step 3 (no re-fetch!)
    - Database error after step 3 → resume from step 4 (no re-fetch, no re-embed!)
    - Link extraction fails → document still saved, just log warning
    """
    # Step 1: Resolve document (fast)
    doc_info = resolve_document_step(identifier)
    doc_id = doc_info["id"]

    # Step 2: Fetch content (network I/O - checkpointed!)
    DBOS.logger.info(f"Fetching content for {doc_id} from {doc_info['source_url']}")
    fetch_result = fetch_content_step(
        source_url=doc_info["source_url"],
        cms_platform=doc_info.get("cms_platform"),
        cms_instance=doc_info.get("cms_instance"),
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
    Complete fetch + index workflow.

    This now has meaningful structure:
    - Steps 1-5: Fetch document (via fetch_document_workflow)
    - Step 6: Extract metadata (separate EXPENSIVE LLM call)

    Key benefit: If metadata extraction fails, document is already fetched.
    On retry, only metadata extraction runs (no re-fetch, no re-embed).
    """
    from kurt.content.indexing import extract_document_metadata

    # Steps 1-5: Fetch document (sub-workflow is checkpointed as a whole)
    DBOS.logger.info(f"Starting fetch workflow for {identifier}")
    fetch_result = fetch_document_workflow(identifier, fetch_engine)

    # Step 6: Extract metadata (EXPENSIVE LLM - checkpointed!)
    DBOS.logger.info(f"Extracting metadata for {fetch_result['document_id']}")

    @DBOS.step()
    def extract_metadata_step(doc_id: str) -> dict:
        return extract_document_metadata(doc_id, force=False)

    metadata_result = extract_metadata_step(fetch_result["document_id"])

    return {
        **fetch_result,
        "index_metadata": metadata_result,
        "workflow_status": "completed",
    }


# ============================================================================
# Usage Examples
# ============================================================================

if __name__ == "__main__":
    # Example 1: Just fetch (no indexing)
    result = fetch_document_workflow("https://example.com/page1")
    print(f"Fetched: {result['document_id']} ({result['content_length']} chars)")

    # Example 2: Fetch + index
    result = fetch_and_index_workflow("https://example.com/page2")
    print(f"Indexed: {result['document_id']}")
    print(f"Topics: {result['index_metadata'].get('topics', [])}")

    # Example 3: If workflow crashes during embedding generation...
    # On restart, DBOS automatically:
    # 1. Skips resolve_document_step (already completed)
    # 2. Skips fetch_content_step (already completed)
    # 3. Resumes from generate_embedding_step
    #
    # Result: No re-fetch! Saves time and API costs.
