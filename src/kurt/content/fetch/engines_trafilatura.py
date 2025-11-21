"""Trafilatura-based fetch engines.

This module provides fetch engines that use trafilatura for content extraction:
- trafilatura: Uses trafilatura for both fetching and extraction
- httpx: Uses httpx for fetching, trafilatura for extraction (proxy-friendly)
"""

import trafilatura


def fetch_with_httpx(url: str) -> tuple[str, dict]:
    """
    Fetch content using httpx + trafilatura extraction (bypasses trafilatura's fetch).

    This engine uses httpx for HTTP requests (which respects proxy patching)
    and trafilatura only for HTML extraction/conversion to markdown.

    Args:
        url: URL to fetch

    Returns:
        Tuple of (content_markdown, metadata_dict)

    Raises:
        ValueError: If fetch fails
    """
    import httpx

    # Download content with httpx (respects proxy patches)
    try:
        response = httpx.get(url, follow_redirects=True, timeout=30.0)
        response.raise_for_status()
        downloaded = response.text
    except Exception as e:
        raise ValueError(f"[httpx] Download error: {type(e).__name__}: {str(e)}") from e

    if not downloaded:
        raise ValueError(f"[httpx] Failed to download (no content returned): {url}")

    # Extract metadata using trafilatura (but not for fetching)
    metadata = trafilatura.extract_metadata(
        downloaded,
        default_url=url,
        extensive=True,
    )

    # Extract content as markdown
    content = trafilatura.extract(
        downloaded,
        output_format="markdown",
        include_tables=True,
        include_links=True,
        url=url,
        with_metadata=True,
    )

    if not content:
        raise ValueError(
            f"[httpx] No content extracted (page might be empty or paywall blocked): {url}"
        )

    # Convert trafilatura metadata to dict
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


def fetch_with_trafilatura(url: str) -> tuple[str, dict]:
    """
    Fetch content using Trafilatura.

    Args:
        url: URL to fetch

    Returns:
        Tuple of (content_markdown, metadata_dict)

    Raises:
        ValueError: If fetch fails
    """
    # Download content
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            raise ValueError(f"[Trafilatura] Failed to download (no content returned): {url}")
    except Exception as e:
        raise ValueError(f"[Trafilatura] Download error: {type(e).__name__}: {str(e)}") from e

    # Extract metadata using trafilatura
    metadata = trafilatura.extract_metadata(
        downloaded,
        default_url=url,
        extensive=True,  # More comprehensive metadata extraction
    )

    # Extract content as markdown
    content = trafilatura.extract(
        downloaded,
        output_format="markdown",
        include_tables=True,
        include_links=True,
        url=url,  # Helps with metadata extraction
        with_metadata=True,  # Include metadata in extraction
    )

    if not content:
        raise ValueError(
            f"[Trafilatura] No content extracted (page might be empty or paywall blocked): {url}"
        )

    # Convert trafilatura metadata to dict
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
