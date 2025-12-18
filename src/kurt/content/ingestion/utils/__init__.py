"""Fetch utilities - web/CMS fetching, link extraction, and discovery."""

from .cms import fetch_batch_from_cms, fetch_from_cms
from .links import extract_document_links

# Discovery utilities
from .map import (
    batch_create_documents,
    discover_from_cms,
    discover_from_folder,
    discover_from_url,
)
from .web import fetch_from_web

__all__ = [
    # Fetch utilities
    "fetch_from_web",
    "fetch_from_cms",
    "fetch_batch_from_cms",
    "extract_document_links",
    # Discovery utilities
    "discover_from_url",
    "discover_from_folder",
    "discover_from_cms",
    "batch_create_documents",
]
