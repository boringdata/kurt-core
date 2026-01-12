"""HTTPX fetch provider (proxy-friendly, uses trafilatura for extraction)."""

from __future__ import annotations

import httpx

from .models import FetchResult
from .utils import extract_with_trafilatura


def fetch_with_httpx(url: str) -> FetchResult:
    """
    Fetch content using httpx + trafilatura extraction (proxy-friendly).

    Args:
        url: URL to fetch

    Returns:
        Tuple of (content_markdown, metadata_dict)

    Raises:
        ValueError: If fetch fails
    """
    try:
        response = httpx.get(url, follow_redirects=True, timeout=30.0)
        response.raise_for_status()
        downloaded = response.text
    except Exception as e:
        raise ValueError(f"[httpx] Download error: {type(e).__name__}: {str(e)}") from e

    if not downloaded:
        raise ValueError(f"[httpx] No content from: {url}")

    return extract_with_trafilatura(downloaded, url)
