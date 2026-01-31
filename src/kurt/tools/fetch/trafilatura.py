"""Trafilatura fetch provider."""

from __future__ import annotations

import trafilatura

from .models import FetchResult
from .utils import extract_with_trafilatura


def fetch_with_trafilatura(url: str) -> FetchResult:
    """
    Fetch content using Trafilatura (free, local extraction).

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
            raise ValueError(f"[Trafilatura] No content from: {url}")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"[Trafilatura] Download error: {type(e).__name__}: {str(e)}") from e

    return extract_with_trafilatura(downloaded, url)
