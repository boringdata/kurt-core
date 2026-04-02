"""Configuration for httpx fetch provider."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HttpxProviderConfig(BaseModel):
    """Configuration for httpx provider.

    Uses httpx library for HTTP requests with content extraction.
    """

    timeout: float = Field(
        default=30.0,
        gt=0,
        description="Request timeout in seconds",
    )
    follow_redirects: bool = Field(
        default=True,
        description="Follow HTTP redirects",
    )
    verify_ssl: bool = Field(
        default=True,
        description="Verify SSL certificates",
    )
    max_content_size: int = Field(
        default=10_485_760,
        gt=0,
        description="Maximum content size in bytes (default 10MB)",
    )
    validate_content_type: bool = Field(
        default=True,
        description="Validate content-type header before extraction",
    )
