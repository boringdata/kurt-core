"""
Pure fetching business logic for document content.

This module provides business logic for fetching content from sources.
NO DATABASE OPERATIONS - pure Network I/O and CMS integration.

Pattern:
- Business logic (pure): Fetch content from web/CMS sources
- Workflow (DB ops): Orchestrate fetching with DB operations in workflows/fetch.py
"""

import logging
from typing import Any, Optional

from kurt.content.fetch.engines_firecrawl import fetch_with_firecrawl
from kurt.content.fetch.engines_trafilatura import fetch_with_httpx, fetch_with_trafilatura
from kurt.content.paths import parse_source_identifier

logger = logging.getLogger(__name__)


def _build_metadata_dict(
    title: Optional[str] = None,
    author: Optional[str] = None,
    date: Optional[str] = None,
    description: Optional[str] = None,
) -> dict[str, Any]:
    """Build a standardized metadata dictionary."""
    return {
        "title": title,
        "author": author,
        "date": date,
        "description": description,
    }


def fetch_from_cms(
    platform: str,
    instance: str,
    cms_document_id: str,
    discovery_url: str = None,
) -> tuple[str, dict, str]:
    """
    Fetch content from CMS using appropriate adapter.

    Pure business logic - calls CMS API, no DB operations.
    Workflows call this function and handle DB operations separately.

    Args:
        platform: CMS platform name
        instance: Instance name
        cms_document_id: CMS document ID to fetch
        discovery_url: Optional public URL (returned if provided)

    Returns:
        Tuple of (markdown_content, metadata_dict, public_url)

    Raises:
        ValueError: If CMS fetch fails or cms_document_id is missing

    Example:
        >>> content, metadata, url = fetch_from_cms(
        ...     "sanity", "prod", "article-123"
        ... )
        >>> # Returns: ("# Title\n\nContent...", {"title": "...", ...}, "https://...")
    """
    from kurt.integrations.cms import get_adapter
    from kurt.integrations.cms.config import get_platform_config

    # Validate cms_document_id is present
    if not cms_document_id:
        raise ValueError(
            f"cms_document_id is required to fetch from CMS. "
            f"Platform: {platform}, Instance: {instance}"
        )

    try:
        # Get CMS adapter
        cms_config = get_platform_config(platform, instance)
        adapter = get_adapter(platform, cms_config)

        # Fetch document using CMS document ID (not the slug)
        cms_document = adapter.fetch(cms_document_id)

        # Get public URL from CMS document (for link matching)
        # (CMS documents use source_url like "sanity/prod/article/slug"
        #  but discovery_url stores the actual public URL like "https://technically.dev/posts/slug")
        public_url = cms_document.url or discovery_url

        # Extract metadata
        metadata_dict = _build_metadata_dict(
            title=cms_document.title,
            author=cms_document.author,
            date=cms_document.published_date,
            description=cms_document.metadata.get("description") if cms_document.metadata else None,
        )

        return cms_document.content, metadata_dict, public_url

    except Exception as e:
        raise ValueError(
            f"Failed to fetch from {platform}/{instance} (cms_document_id: {cms_document_id}): {e}"
        )


def fetch_batch_from_cms(
    platform: str,
    instance: str,
    cms_document_ids: list[str],
    discovery_urls: dict[str, str] | None = None,
) -> dict[str, tuple[str, dict, str] | Exception]:
    """
    Fetch multiple CMS documents in a single batch API call.

    This is more efficient than individual fetches as it uses the CMS adapter's
    batch API, reducing the number of network requests.

    Pure business logic - calls CMS API, no DB operations.

    Args:
        platform: CMS platform name
        instance: Instance name
        cms_document_ids: List of CMS document IDs to fetch
        discovery_urls: Optional dict mapping cms_document_id to public URL

    Returns:
        Dict mapping cms_document_id to either:
            - (content_markdown, metadata_dict, public_url) on success
            - Exception on failure

    Example:
        >>> results = fetch_batch_from_cms(
        ...     "sanity", "prod", ["article-1", "article-2"]
        ... )
        >>> for doc_id, result in results.items():
        ...     if isinstance(result, Exception):
        ...         print(f"Failed {doc_id}: {result}")
        ...     else:
        ...         content, metadata, url = result
        ...         print(f"Success {doc_id}: {len(content)} chars")
    """
    from kurt.integrations.cms import get_adapter
    from kurt.integrations.cms.config import get_platform_config

    if not cms_document_ids:
        return {}

    discovery_urls = discovery_urls or {}
    results = {}

    try:
        # Get CMS adapter
        cms_config = get_platform_config(platform, instance)
        adapter = get_adapter(platform, cms_config)

        logger.info(
            f"[CMS Batch] Fetching {len(cms_document_ids)} documents from {platform}/{instance}"
        )

        # Fetch all documents in one batch API call
        cms_documents = adapter.fetch_batch(cms_document_ids)

        # Create lookup by CMS document ID
        cms_docs_by_id = {cms_doc.id: cms_doc for cms_doc in cms_documents}

        # Process each requested document
        for cms_doc_id in cms_document_ids:
            try:
                cms_document = cms_docs_by_id.get(cms_doc_id)
                if not cms_document:
                    raise ValueError(f"Document {cms_doc_id} not returned from CMS batch fetch")

                # Get public URL
                public_url = cms_document.url or discovery_urls.get(cms_doc_id)

                # Extract metadata
                metadata_dict = _build_metadata_dict(
                    title=cms_document.title,
                    author=cms_document.author,
                    date=cms_document.published_date,
                    description=cms_document.metadata.get("description")
                    if cms_document.metadata
                    else None,
                )

                results[cms_doc_id] = (cms_document.content, metadata_dict, public_url)
                logger.debug(
                    f"[CMS Batch] ✓ Fetched {cms_doc_id} ({len(cms_document.content)} chars)"
                )

            except Exception as e:
                error = ValueError(f"[CMS Batch] Failed to process {cms_doc_id}: {e}")
                results[cms_doc_id] = error
                logger.warning(f"[CMS Batch] ✗ Failed {cms_doc_id}: {e}")

    except Exception as e:
        # If batch fetch fails entirely, mark all as failed
        logger.error(f"[CMS Batch] Batch fetch failed: {type(e).__name__}: {str(e)}")
        for cms_doc_id in cms_document_ids:
            if cms_doc_id not in results:
                results[cms_doc_id] = ValueError(f"[CMS Batch] Batch error: {str(e)}")

    logger.info(
        f"[CMS Batch] Complete: {sum(1 for r in results.values() if not isinstance(r, Exception))}/{len(results)} successful"
    )

    return results


def fetch_from_web(source_url: str, fetch_engine: str) -> tuple[str, dict]:
    """
    Fetch content from web URL using specified engine.

    Pure business logic - Network I/O only, no DB operations.
    Workflows call this function and handle DB operations separately.

    Args:
        source_url: Web URL to fetch
        fetch_engine: Engine to use ('firecrawl', 'trafilatura', 'httpx')

    Returns:
        Tuple of (markdown_content, metadata_dict)

    Raises:
        ValueError: If URL looks like CMS pattern or fetch fails

    Example:
        >>> content, metadata = fetch_from_web(
        ...     "https://example.com/page1", "firecrawl"
        ... )
        >>> # Returns: ("# Title\n\nContent...", {"title": "...", ...})
    """
    # Check if it looks like a CMS URL pattern (legacy check)
    source_type, parsed_data = parse_source_identifier(source_url)

    if source_type == "cms":
        raise ValueError(
            f"CMS URL pattern detected but missing platform/instance fields. "
            f"URL: {source_url}. Please recreate this document using 'kurt content map cms'."
        )

    # Standard web fetch
    if fetch_engine == "firecrawl":
        return fetch_with_firecrawl(source_url)
    elif fetch_engine == "httpx":
        return fetch_with_httpx(source_url)
    else:
        return fetch_with_trafilatura(source_url)


__all__ = [
    "fetch_from_cms",
    "fetch_batch_from_cms",
    "fetch_from_web",
]
