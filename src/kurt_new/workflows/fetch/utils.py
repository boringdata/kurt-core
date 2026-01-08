"""Shared utilities for fetch providers."""

from __future__ import annotations

import trafilatura


def extract_with_trafilatura(html: str, url: str) -> tuple[str, dict]:
    """
    Extract content and metadata from HTML using trafilatura.

    Args:
        html: Raw HTML content
        url: Source URL (for metadata extraction)

    Returns:
        Tuple of (markdown_content, metadata_dict)

    Raises:
        ValueError: If no content extracted
    """
    metadata = trafilatura.extract_metadata(
        html,
        default_url=url,
        extensive=True,
    )

    content = trafilatura.extract(
        html,
        output_format="markdown",
        include_tables=True,
        include_links=True,
        url=url,
        with_metadata=True,
    )

    if not content:
        raise ValueError(f"No content extracted (page might be empty or paywall blocked): {url}")

    metadata_dict = {}
    if metadata:
        metadata_dict = {
            "title": metadata.title,
            "author": metadata.author,
            "date": metadata.date,
            "description": metadata.description,
            "fingerprint": metadata.fingerprint,
        }

    return content, metadata_dict
