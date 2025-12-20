"""Fetching utilities - web fetching wrapper and link extraction.

Pure functions for fetching content and extracting links.
"""

from .config import get_fetch_engine
from .links import extract_document_links
from .web import fetch_from_web

__all__ = [
    "fetch_from_web",
    "extract_document_links",
    "get_fetch_engine",
]
