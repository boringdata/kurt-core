"""Configuration for Composio fetch provider."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ComposioProviderConfig(BaseModel):
    """Configuration for Composio Twitter/X provider.

    Requires:
    - COMPOSIO_API_KEY environment variable
    - COMPOSIO_CONNECTION_ID environment variable (from Composio dashboard)

    Free tier: 20,000 API calls/month.
    """

    timeout: float = Field(
        default=60.0,
        gt=0,
        description="Request timeout in seconds",
    )
    max_results: int = Field(
        default=100,
        ge=10,
        le=100,
        description="Maximum results per search (10-100)",
    )
    cache_ttl_hours: int = Field(
        default=6,
        ge=0,
        description="Cache TTL in hours (0 to disable)",
    )
