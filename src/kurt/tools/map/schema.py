"""
Pydantic schema for map_results table.

Used for VALIDATION ONLY - not DDL generation.
Actual table schema defined in src/kurt/db/schema/map_results.sql
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class MapResult(BaseModel):
    """Validation schema for MapTool output."""

    model_config = ConfigDict(extra="forbid")  # Strict - no extra fields

    document_id: str = Field(description="Document ID (12-char hex) - JOIN key")
    run_id: str = Field(description="Run/batch ID (UUID) for versioning")
    url: str = Field(description="Original URL (not canonicalized)")
    source_type: str = Field(default="url", description="url|file|cms")
    discovery_method: str = Field(description="crawl|sitemap|folder|cms")
    discovery_url: str | None = Field(default=None, description="URL where this was discovered")
    title: str | None = Field(default=None, description="Page title if available")
    status: str = Field(default="success", description="success|error|skipped")
    error: str | None = Field(default=None, description="Error message if status=error")
    metadata: dict | None = Field(default=None, description="Additional metadata as JSON")
    # NOTE: created_at NOT included - DB handles it with CURRENT_TIMESTAMP(6)
