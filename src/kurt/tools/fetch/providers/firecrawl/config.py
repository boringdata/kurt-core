"""Configuration for Firecrawl fetch provider."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FirecrawlProviderConfig(BaseModel):
    """Configuration for Firecrawl API provider.

    Requires FIRECRAWL_API_KEY environment variable.
    """

    timeout: float = Field(
        default=30.0,
        gt=0,
        description="Request timeout in seconds",
    )
    formats: list[str] = Field(
        default=["markdown", "html"],
        description="Output formats to request",
    )
    poll_interval: int = Field(
        default=2,
        ge=1,
        description="Seconds between status checks for async jobs",
    )
