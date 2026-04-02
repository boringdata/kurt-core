"""Configuration for trafilatura fetch provider."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TrafilaturaProviderConfig(BaseModel):
    """Configuration for Trafilatura provider.

    Trafilatura is a local extraction library with no API key required.
    """

    include_comments: bool = Field(
        default=False,
        description="Include comments in extracted content",
    )
    include_tables: bool = Field(
        default=True,
        description="Include tables in extracted content",
    )
    favor_precision: bool = Field(
        default=True,
        description="Favor precision over recall in extraction",
    )
    output_format: str = Field(
        default="markdown",
        description="Output format: markdown, txt, html",
    )
