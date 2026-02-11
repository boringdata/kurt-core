"""Configuration for crawl map provider."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CrawlProviderConfig(BaseModel):
    """Configuration for web crawl discovery provider.

    BFS-based crawler that follows links within a domain.
    """

    max_depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum crawl depth",
    )
    max_urls: int = Field(
        default=1000,
        ge=1,
        description="Maximum URLs to collect",
    )
    timeout: float = Field(
        default=30.0,
        gt=0,
        description="Request timeout in seconds",
    )
    follow_external: bool = Field(
        default=False,
        description="Follow links to external domains",
    )
    respect_robots: bool = Field(
        default=True,
        description="Respect robots.txt directives",
    )
    include_pattern: Optional[str] = Field(
        default=None,
        description="Regex pattern to include URLs",
    )
    exclude_pattern: Optional[str] = Field(
        default=None,
        description="Regex pattern to exclude URLs",
    )
