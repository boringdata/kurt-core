"""
Map orchestration functionality.

Coordinates URL/content discovery from various sources.
"""

import logging
from fnmatch import fnmatch
from typing import Optional

from sqlmodel import select

from kurt.db.database import get_session
from kurt.db.models import Document, IngestionStatus, SourceType

logger = logging.getLogger(__name__)


def discover_from_url(
    url: str,
    max_depth: Optional[int] = None,
    max_pages: int = 1000,
    allow_external: bool = False,
    include_patterns: tuple = (),
    exclude_patterns: tuple = (),
) -> dict:
    """
    Discover URLs from web source (sitemap or crawl).

    Tries sitemap first, falls back to crawling if sitemap fails.

    Args:
        url: Base URL to discover from
        max_depth: Crawl depth for fallback (None = sitemap only)
        max_pages: Maximum pages to discover
        allow_external: Allow external domain links
        include_patterns: Include URL patterns (glob)
        exclude_patterns: Exclude URL patterns (glob)

    Returns:
        dict with keys: discovered, total, new, existing, method
    """
    from .crawl import crawl_website
    from .sitemap import discover_sitemap_urls

    discovered_urls = []
    discovery_method = "sitemap"

    # Try sitemap first
    try:
        discovered_urls = discover_sitemap_urls(url)
        logger.info(f"Sitemap discovered {len(discovered_urls)} URLs")
    except ValueError as e:
        # Sitemap failed - try crawling if max_depth specified
        if max_depth is not None:
            logger.info(f"Sitemap failed: {e}. Falling back to crawl with max_depth={max_depth}")
            discovered_urls = crawl_website(
                homepage=url,
                max_depth=max_depth,
                max_pages=max_pages,
                allow_external=allow_external,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
            )
            discovery_method = "crawl"
        else:
            # No fallback - use single URL
            logger.info(f"Sitemap failed: {e}. Using single URL.")
            discovered_urls = [url]
            discovery_method = "single_page"

    # Apply filters (sitemap doesn't apply them)
    if discovery_method == "sitemap":
        if include_patterns:
            discovered_urls = [
                u for u in discovered_urls if any(fnmatch(u, p) for p in include_patterns)
            ]
        if exclude_patterns:
            discovered_urls = [
                u for u in discovered_urls if not any(fnmatch(u, p) for p in exclude_patterns)
            ]
        # Apply limit
        if max_pages and len(discovered_urls) > max_pages:
            discovered_urls = discovered_urls[:max_pages]

    # Create documents in database
    docs, new_count = batch_create_documents(
        url_list=discovered_urls,
        discovery_method=discovery_method,
        discovery_url=url,
    )

    # Convert to result format
    results = []
    for doc in docs:
        results.append(
            {
                "doc_id": str(doc.id),
                "url": doc.source_url,
                "title": doc.title,
                "created": doc.ingestion_status == IngestionStatus.NOT_FETCHED,
            }
        )

    return {
        "discovered": results,
        "total": len(results),
        "new": new_count,
        "existing": len(results) - new_count,
        "method": discovery_method,
    }


def discover_from_folder(
    folder_path: str,
    include_patterns: tuple = (),
    exclude_patterns: tuple = (),
) -> dict:
    """
    Discover markdown files from local folder.

    Args:
        folder_path: Path to folder to scan
        include_patterns: Include file patterns (glob)
        exclude_patterns: Exclude file patterns (glob)

    Returns:
        dict with keys: discovered, total, new, existing
    """
    from .folder import discover_folder_files

    results = discover_folder_files(
        folder_path=folder_path,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
    )

    new_count = sum(1 for r in results if r.get("created", False))

    return {
        "discovered": results,
        "total": len(results),
        "new": new_count,
        "existing": len(results) - new_count,
        "method": "folder",
    }


def discover_from_cms(
    platform: str,
    instance: str,
) -> dict:
    """
    Discover documents from CMS platform.

    Args:
        platform: CMS platform name
        instance: CMS instance name

    Returns:
        dict with keys: discovered, total, new, existing
    """
    from .cms_discovery import discover_cms_documents

    results = discover_cms_documents(
        platform=platform,
        instance=instance,
    )

    new_count = sum(1 for r in results if r.get("created", False))

    return {
        "discovered": results,
        "total": len(results),
        "new": new_count,
        "existing": len(results) - new_count,
        "method": "cms",
    }


def batch_create_documents(
    url_list: list[str],
    discovery_method: str,
    discovery_url: str = None,
    batch_size: int = 100,
) -> tuple[list[Document], int]:
    """
    Create document records for discovered URLs.

    Args:
        url_list: List of URLs to create documents for
        discovery_method: How URLs were discovered (sitemap, crawl, etc.)
        discovery_url: Source URL where these URLs were discovered
        batch_size: Number of documents to commit at once

    Returns:
        Tuple of (list of Document objects, count of newly created documents)
    """
    session = get_session()

    # Check which URLs already exist
    existing_urls_stmt = select(Document).where(Document.source_url.in_(url_list))
    existing_docs = list(session.exec(existing_urls_stmt).all())
    existing_urls = {doc.source_url for doc in existing_docs}

    # Create documents for new URLs
    new_urls = [url for url in url_list if url not in existing_urls]
    new_count = 0

    if new_urls:
        docs_to_add = []
        for url in new_urls:
            # Generate title from URL
            title = url.rstrip("/").split("/")[-1] or url

            doc = Document(
                title=title,
                source_type=SourceType.URL,
                source_url=url,
                ingestion_status=IngestionStatus.NOT_FETCHED,
                discovery_method=discovery_method,
                discovery_url=discovery_url,
            )

            session.add(doc)
            docs_to_add.append(doc)

            # Commit in batches
            if len(docs_to_add) >= batch_size:
                session.commit()
                docs_to_add = []

        # Commit any remaining
        if docs_to_add:
            session.commit()

        new_count = len(new_urls)

    # Return all documents
    all_docs_stmt = select(Document).where(Document.source_url.in_(url_list))
    all_docs = list(session.exec(all_docs_stmt).all())

    return all_docs, new_count
