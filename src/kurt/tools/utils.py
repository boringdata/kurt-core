"""
Shared utility functions for all tools.

Provides canonical URL handling and document ID generation.
CRITICAL: All tools MUST use these functions for consistent deduplication.
"""

from __future__ import annotations

import hashlib


def canonicalize_url(source: str) -> str:
    """
    Canonicalize a source URL/path for consistent hashing.

    IMPORTANT: This MUST be used for both document_id and url_hash
    to ensure consistency. Using different normalization leads to
    duplicates or silent overwrites.

    Normalization rules:
    - Strip whitespace
    - Lowercase
    - Remove trailing slashes from URLs

    Args:
        source: URL, file path, or CMS identifier

    Returns:
        Canonicalized string
    """
    normalized = source.strip().lower()
    if normalized.startswith(("http://", "https://")):
        normalized = normalized.rstrip("/")
    return normalized


def make_document_id(source: str) -> str:
    """
    Generate canonical document_id from any source.

    Works for:
    - URLs: https://example.com/path
    - Files: /path/to/file.md or file:///path
    - CMS: cms://notion/page_id

    Args:
        source: URL, file path, or CMS identifier

    Returns:
        12-char hex string (SHA256 prefix)

    Example:
        >>> make_document_id("https://example.com/Page")
        'a1b2c3d4e5f6'
        >>> make_document_id("https://example.com/page")  # Same after canonicalization
        'a1b2c3d4e5f6'
    """
    canonical = canonicalize_url(source)
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]


def make_url_hash(source: str) -> str:
    """
    Generate url_hash for UNIQUE constraint in document_registry.

    MUST use same canonicalization as document_id to prevent:
    - Duplicate documents from URL variants (case, trailing slash)
    - Silent overwrites from ON DUPLICATE KEY UPDATE

    Args:
        source: URL, file path, or CMS identifier

    Returns:
        64-char hex string (full SHA256)

    Example:
        >>> make_url_hash("https://example.com/Page")
        'a1b2c3d4e5f6...'  # Full 64 chars
        >>> make_url_hash("https://example.com/page")  # Same!
        'a1b2c3d4e5f6...'
    """
    canonical = canonicalize_url(source)
    return hashlib.sha256(canonical.encode()).hexdigest()
