"""Trafilatura fetch provider."""

from __future__ import annotations

import trafilatura

from .utils import extract_with_trafilatura


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
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            raise ValueError(f"[Trafilatura] Failed to download (no content returned): {url}")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"[Trafilatura] Download error: {type(e).__name__}: {str(e)}") from e

    try:
        return extract_with_trafilatura(downloaded, url)
    except ValueError as e:
        raise ValueError(f"[Trafilatura] {e}") from e
