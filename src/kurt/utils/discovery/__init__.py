"""Discovery utilities - sitemap, crawl, folder, and CMS discovery.

Pure functions for discovering content from various sources.
"""

from .cms import discover_cms_documents
from .crawl import crawl_website
from .folder import discover_folder_files
from .orchestrator import (
    batch_create_documents,
    discover_from_cms,
    discover_from_folder,
    discover_from_url,
)
from .sitemap import discover_sitemap_urls

__all__ = [
    # Low-level discovery
    "discover_sitemap_urls",
    "crawl_website",
    "discover_folder_files",
    "discover_cms_documents",
    # High-level orchestration
    "discover_from_url",
    "discover_from_folder",
    "discover_from_cms",
    "batch_create_documents",
]
