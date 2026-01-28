"""
Map tool - Content source discovery.

Provides:
- MapTool: Tool class for discovering URLs, files, CMS entries
- MapInput, MapOutput: Pydantic models for tool IO
- MapDocument, MapStatus: Database models
- MapConfig: Configuration for map operations
- Discovery methods: sitemap, crawl, folder scan, CMS adapters
- URL normalization utilities
"""

from .config import MapConfig
from .models import MapDocument, MapStatus
from .tool import (
    SAFE_CHARS,
    MapInput,
    MapOutput,
    MapTool,
    check_robots_txt,
    discover_from_cms,
    discover_from_crawl,
    discover_from_folder,
    discover_from_sitemap,
    filter_items,
    is_blocked_by_robots,
    make_document_id,
    normalize_url,
)

__all__ = [
    # Tool class
    "MapTool",
    # Pydantic models
    "MapConfig",
    "MapInput",
    "MapOutput",
    # Database models
    "MapDocument",
    "MapStatus",
    # Discovery functions
    "discover_from_sitemap",
    "discover_from_crawl",
    "discover_from_folder",
    "discover_from_cms",
    # Utility functions
    "normalize_url",
    "make_document_id",
    "filter_items",
    "check_robots_txt",
    "is_blocked_by_robots",
    # Constants
    "SAFE_CHARS",
]
