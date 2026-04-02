"""Configuration for CMS map provider."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CmsProviderConfig(BaseModel):
    """Configuration for CMS content discovery provider.

    Discovers content from CMS platforms (Sanity, etc.).
    """

    platform: Optional[str] = Field(
        default=None,
        description="CMS platform: sanity",
    )
    instance: Optional[str] = Field(
        default=None,
        description="CMS instance identifier",
    )
    content_type: Optional[str] = Field(
        default=None,
        description="Filter by content type",
    )
    status: Optional[str] = Field(
        default=None,
        description="Filter by status: published, draft",
    )
    max_urls: int = Field(
        default=1000,
        ge=1,
        description="Maximum items to collect",
    )
