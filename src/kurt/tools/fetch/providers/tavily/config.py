"""Configuration for Tavily fetch provider."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TavilyProviderConfig(BaseModel):
    """Configuration for Tavily API provider.

    Requires TAVILY_API_KEY environment variable.
    """

    timeout: float = Field(
        default=30.0,
        gt=0,
        description="Base request timeout in seconds",
    )
    batch_size: int = Field(
        default=20,
        ge=1,
        le=20,
        description="Maximum URLs per batch request",
    )
    extract_depth: str = Field(
        default="advanced",
        description="Extraction depth: basic or advanced",
    )
    include_images: bool = Field(
        default=True,
        description="Include image URLs in extracted content",
    )
