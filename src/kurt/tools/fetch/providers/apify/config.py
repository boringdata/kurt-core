"""Configuration for Apify fetch provider."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ApifyFetchProviderConfig(BaseModel):
    """Configuration for Apify social media fetch provider.

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
    content_type: Optional[str] = Field(
        default=None,
        description="Content type: auto, doc, profile, post",
    )
    max_items: int = Field(
        default=20,
        ge=1,
        description="Maximum items to fetch",
    )
