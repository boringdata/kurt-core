"""
GIF search integration using Tenor API.

Provides GIF search functionality for Kurt workflows and CLI.
"""

from kurt.integrations.gifgrep.client import (
    GifgrepAPIError,
    GifgrepAuthError,
    GifgrepClient,
    GifgrepError,
    GifgrepRateLimitError,
    GifResult,
    search_gifs,
)

__all__ = [
    "GifgrepClient",
    "GifgrepAPIError",
    "GifgrepAuthError",
    "GifgrepError",
    "GifgrepRateLimitError",
    "GifResult",
    "search_gifs",
]
