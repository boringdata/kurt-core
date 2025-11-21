"""
Pure fetching business logic for document content.

This module provides business logic for fetching content from sources.
NO DATABASE OPERATIONS - pure Network I/O and CMS integration.

Pattern:
- Business logic (pure): Fetch content from web/CMS sources
- Workflow (DB ops): Orchestrate fetching with DB operations in workflows/fetch.py
"""

import logging

from kurt.content.fetch.engines_firecrawl import fetch_with_firecrawl
from kurt.content.fetch.engines_trafilatura import fetch_with_httpx, fetch_with_trafilatura
from kurt.content.paths import parse_source_identifier

logger = logging.getLogger(__name__)


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
        metadata_dict = {
            "title": cms_document.title,
            "author": cms_document.author,
            "date": cms_document.published_date,
            "description": cms_document.metadata.get("description")
            if cms_document.metadata
            else None,
        }

        return cms_document.content, metadata_dict, public_url

    except Exception as e:
        raise ValueError(
            f"Failed to fetch from {platform}/{instance} (cms_document_id: {cms_document_id}): {e}"
        )


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
    "fetch_from_web",
]
