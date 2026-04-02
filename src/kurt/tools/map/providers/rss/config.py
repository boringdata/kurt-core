"""Configuration for RSS map provider."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RssProviderConfig(BaseModel):
    """Configuration for RSS/Atom feed discovery provider.

    Discovers URLs from RSS 2.0 and Atom feeds.
    """

    timeout: float = Field(
        default=30.0,
        gt=0,
        description="Request timeout in seconds",
    )
    max_urls: int = Field(
        default=1000,
        ge=1,
        description="Maximum URLs to collect",
    )
    include_pattern: Optional[str] = Field(
        default=None,
        description="Regex pattern to include URLs",
    )
    exclude_pattern: Optional[str] = Field(
        default=None,
        description="Regex pattern to exclude URLs",
    )
