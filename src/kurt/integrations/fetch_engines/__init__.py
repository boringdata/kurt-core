"""Fetch engines - trafilatura, firecrawl, httpx.

These are integrations with external tools/services for fetching web content.
"""

from .firecrawl import fetch_with_firecrawl
from .trafilatura import fetch_with_httpx, fetch_with_trafilatura

__all__ = [
    "fetch_with_trafilatura",
    "fetch_with_httpx",
    "fetch_with_firecrawl",
]
