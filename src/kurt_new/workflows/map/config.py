from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class MapConfig(BaseModel):
    """Configuration for mapping/discovery step."""

    source_url: Optional[str] = Field(default=None, description="URL to discover from")
    source_folder: Optional[str] = Field(default=None, description="Local folder path")
    cms_platform: Optional[str] = Field(default=None, description="CMS platform name")
    cms_instance: Optional[str] = Field(default=None, description="CMS instance name")

    discovery_method: str = Field(default="auto", description="auto, sitemap, crawl, folder, cms")
    max_depth: Optional[int] = Field(default=None, ge=1, le=5)
    max_pages: int = Field(default=1000, ge=1, le=10000)

    include_patterns: Optional[str] = Field(
        default=None, description="Comma-separated glob patterns"
    )
    exclude_patterns: Optional[str] = Field(
        default=None, description="Comma-separated glob patterns"
    )

    allow_external: bool = Field(default=False)
    include_blogrolls: bool = Field(default=False)
    dry_run: bool = Field(default=False)
