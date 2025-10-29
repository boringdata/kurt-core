"""Add content workflow - orchestrates discover, fetch, and index."""

import asyncio
from collections import defaultdict
from urllib.parse import urlparse

from sqlmodel import select

from kurt.db.database import get_session
from kurt.db.models import Document, IngestionStatus
from kurt.ingestion.fetch import add_document, fetch_document, fetch_documents_batch
from kurt.ingestion.index import batch_extract_document_metadata
from kurt.ingestion.map import map_sitemap

# Configuration
BATCH_THRESHOLD = 20  # Confirmation threshold for large batches


def is_single_page_url(url: str) -> bool:
    """
    Determine if URL points to a single page or a domain/section.

    Single page indicators:
    - Has path beyond root (e.g., /blog/my-post)
    - Path doesn't end with / (unless it's a specific page)
    - Not just domain.com or domain.com/

    Returns True if single page, False if likely multi-page source.
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    # Empty path or just a section (like /blog/) = multi-page
    if not path or path.endswith("/"):
        return False

    # Has meaningful path segments = likely single page
    # Exception: common index patterns like /blog, /docs might be multi-page
    common_index_patterns = ["blog", "docs", "documentation", "articles", "posts", "news", "guides"]
    path_parts = path.split("/")

    # If it's just one segment and matches index pattern, treat as multi-page
    if len(path_parts) == 1 and path_parts[0].lower() in common_index_patterns:
        return False

    # Otherwise, assume single page
    return True


def group_urls_by_path_prefix(urls: list[dict]) -> dict[str, int]:
    """
    Group URLs by their first path segment for display.

    Args:
        urls: List of document dicts with 'url' key

    Returns:
        Dict mapping path prefix to count
    """
    path_groups = defaultdict(int)
    for doc in urls:
        parsed = urlparse(doc["url"])
        path_parts = parsed.path.strip("/").split("/")
        prefix = "/" + path_parts[0] if path_parts and path_parts[0] else "/"
        path_groups[prefix] += 1
    return dict(path_groups)


def add_single_page(
    url: str,
    *,
    fetch: bool = True,
    index: bool = True,
    fetch_engine: str = None,
) -> dict:
    """
    Add a single page to Kurt.

    Args:
        url: URL to add
        fetch: Whether to fetch content
        index: Whether to index content
        fetch_engine: Optional fetch engine override ('firecrawl' or 'trafilatura')

    Returns:
        Dict with keys: doc_id, created, fetched, indexed
    """
    # Check if already exists
    session = get_session()
    stmt = select(Document).where(Document.source_url == url)
    existing_doc = session.exec(stmt).first()

    if existing_doc:
        doc_id = str(existing_doc.id)
        created = False
        needs_fetch = existing_doc.ingestion_status == IngestionStatus.NOT_FETCHED
        needs_index = not existing_doc.indexed_with_hash
    else:
        # Create document
        doc_id = add_document(url)
        created = True
        needs_fetch = True
        needs_index = True

    result = {
        "doc_id": doc_id,
        "created": created,
        "fetched": False,
        "indexed": False,
    }

    # Fetch if needed
    if needs_fetch and fetch:
        fetch_result = fetch_document(doc_id, fetch_engine=fetch_engine)
        result["fetched"] = True
        result["fetch_result"] = fetch_result

    # Index if needed
    if needs_index and index and fetch:  # Can only index if fetched
        index_result = asyncio.run(
            batch_extract_document_metadata([str(doc_id)], max_concurrent=1, force=False)
        )
        if index_result["succeeded"] > 0:
            result["indexed"] = True
            result["index_result"] = index_result["results"][0]

    return result


def add_multiple_pages(
    url: str,
    *,
    url_contains: str = None,
    url_starts_with: str = None,
    limit: int = None,
    fetch: bool = True,
    index: bool = True,
    max_concurrent: int = 5,
    discover_dates: bool = False,
    max_blogrolls: int = 10,
    fetch_engine: str = None,
) -> dict:
    """
    Add multiple pages from a site to Kurt.

    Args:
        url: Base URL to discover from
        url_contains: Filter URLs containing this string
        url_starts_with: Filter URLs starting with this prefix
        limit: Maximum number of pages to process
        fetch: Whether to fetch content
        index: Whether to index content
        max_concurrent: Max parallel operations
        discover_dates: Discover publish dates from blogrolls
        max_blogrolls: Max blogroll pages to scrape
        fetch_engine: Optional fetch engine override ('firecrawl' or 'trafilatura')

    Returns:
        Dict with keys: discovered, created, fetched, indexed, docs
    """
    # Discover all URLs from sitemap
    docs = map_sitemap(
        url,
        fetch_all=False,
        limit=None,  # Apply limit after filtering
        discover_blogrolls=discover_dates,
        max_blogrolls=max_blogrolls,
    )

    if not docs:
        return {
            "discovered": 0,
            "created": 0,
            "fetched": 0,
            "indexed": 0,
            "docs": [],
        }

    # Apply filters
    filtered_docs = docs
    if url_contains:
        filtered_docs = [d for d in filtered_docs if url_contains in d["url"]]
    if url_starts_with:
        filtered_docs = [d for d in filtered_docs if d["url"].startswith(url_starts_with)]

    # Apply limit
    if limit:
        filtered_docs = filtered_docs[:limit]

    # Count newly created docs
    created_docs = [d for d in filtered_docs if d.get("created", False)]
    doc_ids_to_fetch = [d["document_id"] for d in created_docs]

    result = {
        "discovered": len(filtered_docs),
        "created": len(created_docs),
        "fetched": 0,
        "indexed": 0,
        "docs": filtered_docs,
        "created_docs": created_docs,
    }

    # Fetch if requested
    if fetch and doc_ids_to_fetch:
        fetch_results = fetch_documents_batch(
            doc_ids_to_fetch, max_concurrent=max_concurrent, fetch_engine=fetch_engine
        )
        successful = [r for r in fetch_results if r["success"]]
        result["fetched"] = len(successful)
        result["fetch_results"] = fetch_results

    # Index if requested
    if index and fetch and doc_ids_to_fetch:
        # Get all documents that need indexing (FETCHED but not indexed)
        session = get_session()
        doc_ids = [d["document_id"] for d in filtered_docs]
        stmt = select(Document).where(
            Document.id.in_(doc_ids),
            Document.ingestion_status == IngestionStatus.FETCHED,
            Document.indexed_with_hash is None,
        )
        docs_to_index = session.exec(stmt).all()

        if docs_to_index:
            index_ids = [str(doc.id) for doc in docs_to_index]
            index_result = asyncio.run(
                batch_extract_document_metadata(
                    index_ids, max_concurrent=max_concurrent, force=False
                )
            )
            result["indexed"] = index_result["succeeded"] - index_result.get("skipped", 0)
            result["index_result"] = index_result

    return result


def should_confirm_batch(num_docs: int, force: bool = False) -> bool:
    """
    Determine if user confirmation is needed for batch operation.

    Args:
        num_docs: Number of documents to process
        force: Skip confirmation if True

    Returns:
        True if confirmation needed, False otherwise
    """
    if force:
        return False
    return num_docs > BATCH_THRESHOLD
