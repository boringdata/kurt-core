"""
Utility functions for map module.

This module contains map-specific database operations that extend the basic CRUD
operations in document.py with discovery metadata tracking.
"""

from sqlmodel import select

from kurt.db.database import get_session
from kurt.db.models import Document, IngestionStatus, SourceType


def batch_create_discovered_documents(
    url_list: list[str],
    discovery_method: str,
    discovery_url: str = None,
    batch_size: int = 100,
) -> tuple[list[Document], int]:
    """
    Create document records for discovered URLs with discovery metadata.

    This is map-specific and tracks how/where URLs were discovered.
    For simple document creation without discovery tracking, use
    add_documents_for_urls() from document.py.

    Args:
        url_list: List of URLs to create documents for
        discovery_method: How URLs were discovered (sitemap, crawl, blogroll, etc.)
        discovery_url: Optional source URL where these URLs were discovered
        batch_size: Number of documents to commit at once (default: 100)

    Returns:
        Tuple of (list of Document objects, count of newly created documents)

    Example:
        >>> from kurt.content.map.db import batch_create_discovered_documents
        >>>
        >>> # Sitemap discovery
        >>> docs, new_count = batch_create_discovered_documents(
        ...     url_list=["https://example.com/page1", "https://example.com/page2"],
        ...     discovery_method="sitemap",
        ...     discovery_url="https://example.com/sitemap.xml"
        ... )
        >>>
        >>> # Crawl discovery
        >>> docs, new_count = batch_create_discovered_documents(
        ...     url_list=crawled_urls,
        ...     discovery_method="crawl",
        ...     discovery_url="https://example.com"
        ... )
    """
    session = get_session()

    # Check which URLs already exist (using IN for efficiency)
    existing_urls_stmt = select(Document).where(Document.source_url.in_(url_list))
    existing_docs = list(session.exec(existing_urls_stmt).all())
    existing_urls = {doc.source_url for doc in existing_docs}

    # Create documents for new URLs with batch commits
    new_urls = [url for url in url_list if url not in existing_urls]
    new_count = 0

    if new_urls:
        # Batch creation for performance
        docs_to_add = []
        for url in new_urls:
            # Generate title from URL
            title = url.rstrip("/").split("/")[-1] or url

            # Create document with discovery metadata
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

    # Return all documents (existing + newly created)
    all_docs_stmt = select(Document).where(Document.source_url.in_(url_list))
    all_docs = list(session.exec(all_docs_stmt).all())

    return all_docs, new_count
