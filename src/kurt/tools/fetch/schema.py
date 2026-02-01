"""
Pydantic schema for fetch_results table.

Used for VALIDATION ONLY - not DDL generation.
Actual table schema defined in src/kurt/db/schema/fetch_results.sql
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FetchResult(BaseModel):
    """Validation schema for FetchTool output."""

    model_config = ConfigDict(extra="forbid")  # Strict - no extra fields

    document_id: str = Field(description="Document ID (12-char hex) - JOIN key")
    run_id: str = Field(description="Run/batch ID (UUID) for versioning")
    url: str = Field(description="Fetched URL")
    status: str = Field(description="success|error|skipped")
    content_path: str | None = Field(default=None, description="Path to .md file on disk")
    content_hash: str | None = Field(default=None, description="SHA256 of content")
    content_length: int | None = Field(default=None, description="Content length in bytes")
    fetch_engine: str | None = Field(default=None, description="trafilatura|firecrawl|httpx")
    error: str | None = Field(default=None, description="Error message if status=error")
    metadata: dict | None = Field(default=None, description="Additional metadata as JSON")
    # NOTE: created_at NOT included - DB handles it with CURRENT_TIMESTAMP(6)
