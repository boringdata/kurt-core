"""Configuration for TwitterAPI fetch provider."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TwitterApiProviderConfig(BaseModel):
    """Configuration for TwitterAPI.io provider.

    Requires TWITTERAPI_API_KEY environment variable.
    """

    timeout: float = Field(
        default=30.0,
        gt=0,
        description="Request timeout in seconds",
    )
    max_tweets: int = Field(
        default=20,
        ge=1,
        description="Maximum tweets to fetch for user timelines",
    )
    include_replies: bool = Field(
        default=False,
        description="Include replies in user timeline",
    )
