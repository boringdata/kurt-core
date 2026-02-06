"""CMS discovery helper - thin wrapper around engines/cms.py.

This module provides backward compatibility for existing code using
discover_from_cms(). New code should use CmsEngine from engines/cms.py.
"""

from __future__ import annotations


def discover_from_cms(
    platform: str,
    instance: str,
    *,
    content_type: str | None = None,
    status: str | None = None,
    limit: int | None = None,
) -> dict:
    """Discover documents from a CMS platform without persisting them.

    This is a backward-compatible wrapper around the canonical implementation
    in engines/cms.py. New code should use CmsEngine directly.

    Args:
        platform: CMS platform name (e.g., "sanity")
        instance: CMS instance identifier
        content_type: Filter by content type
        status: Filter by document status
        limit: Maximum number of documents to return

    Returns:
        Dict with discovered documents and metadata
    """
    from kurt.tools.map.engines.cms import discover_from_cms_impl

    return discover_from_cms_impl(
        platform=platform,
        instance=instance,
        content_type=content_type,
        status=status,
        limit=limit,
    )
