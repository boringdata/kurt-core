"""Configuration for Apify map provider."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ApifyMapProviderConfig(BaseModel):
    """Configuration for Apify social media mapping provider.

    Requires APIFY_API_KEY environment variable.
    Supports Twitter/X, LinkedIn, Threads, and Substack.
    """

    platform: Optional[str] = Field(
        default=None,
        description="Social platform: twitter, linkedin, threads, substack",
    )
    apify_actor: Optional[str] = Field(
        default=None,
        description="Override Apify actor ID",
    )
    max_items: int = Field(
        default=50,
        ge=1,
        description="Maximum items to discover",
    )
    max_urls: int = Field(
        default=1000,
        ge=1,
        description="Maximum URLs to collect",
    )
