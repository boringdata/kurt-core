from __future__ import annotations

from pydantic import BaseModel, Field


class FetchConfig(BaseModel):
    """Configuration for fetch step."""

    document_ids: list[str] = Field(
        default_factory=list,
        description="List of document IDs to fetch",
    )
    fetch_engine: str = Field(
        default="trafilatura",
        description="Fetch engine: trafilatura, httpx, firecrawl",
    )
    embedding_max_chars: int = Field(
        default=1000,
        ge=100,
        le=5000,
        description="Maximum characters for embedding generation",
    )
    dry_run: bool = Field(default=False)
