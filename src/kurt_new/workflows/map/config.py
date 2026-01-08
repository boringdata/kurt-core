"""
Map workflow configuration.

Config values can be set in kurt.config with MAP.* prefix:

    MAP.MAX_PAGES=500
    MAP.MAX_DEPTH=3
    MAP.DRY_RUN=true
    MAP.DISCOVERY_METHOD=sitemap

Usage:
    # Load from config file
    config = MapConfig.from_config("map")

    # Or instantiate directly
    config = MapConfig(max_pages=500, dry_run=True)

    # Or merge: config file + overrides
    config = MapConfig.from_config("map", max_pages=500)
"""

from __future__ import annotations

from typing import Optional

from kurt_new.config import ConfigParam, StepConfig


class MapConfig(StepConfig):
    """Configuration for mapping/discovery workflow.

    Loaded from kurt.config with MAP.* prefix.
    """

    # Source specification (one of these should be set)
    source_url: Optional[str] = ConfigParam(default=None, description="URL to discover from")
    source_folder: Optional[str] = ConfigParam(default=None, description="Local folder path")
    cms_platform: Optional[str] = ConfigParam(default=None, description="CMS platform name")
    cms_instance: Optional[str] = ConfigParam(default=None, description="CMS instance name")

    # Discovery settings
    discovery_method: str = ConfigParam(
        default="auto", description="Discovery method: auto, sitemap, crawl, folder, cms"
    )
    sitemap_path: Optional[str] = ConfigParam(
        default=None, description="Override sitemap location (e.g., /custom-sitemap.xml)"
    )
    max_depth: Optional[int] = ConfigParam(default=None, ge=1, le=5, description="Max crawl depth")
    max_pages: int = ConfigParam(default=1000, ge=1, le=10000, description="Max pages to discover")

    # Filtering
    include_patterns: Optional[str] = ConfigParam(
        default=None, description="Comma-separated glob patterns to include"
    )
    exclude_patterns: Optional[str] = ConfigParam(
        default=None, description="Comma-separated glob patterns to exclude"
    )

    # Behavior
    allow_external: bool = ConfigParam(default=False, description="Allow external URLs")
    include_blogrolls: bool = ConfigParam(default=False, description="Include blogroll links")
    dry_run: bool = ConfigParam(default=False, description="Dry run mode")
