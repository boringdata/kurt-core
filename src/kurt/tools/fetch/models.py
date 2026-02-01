from __future__ import annotations

from enum import Enum
from typing import Optional, Protocol

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from kurt.db.models import EmbeddingMixin, TenantMixin, TimestampMixin

# Type alias for fetch results
FetchResult = tuple[str, dict]  # (content_markdown, metadata_dict)
BatchFetchResult = dict[str, FetchResult | Exception]  # URL -> result or error


class BatchFetcher(Protocol):
    """Protocol for batch fetch engines."""

    def __call__(self, urls: list[str]) -> BatchFetchResult:
        """Batch fetch multiple URLs.

        Args:
            urls: List of URLs to fetch

        Returns:
            Dict mapping URL -> (content, metadata) or Exception for failures
        """
        ...


class FetchStatus(str, Enum):
    """Status for fetched documents."""

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


class FetchDocument(EmbeddingMixin, TimestampMixin, TenantMixin, SQLModel, table=True):
    """Persisted fetch results for documents."""

    __tablename__ = "fetch_documents"

    document_id: str = Field(primary_key=True)

    # Status
    status: FetchStatus = Field(default=FetchStatus.PENDING)

    # Content info
    content_length: int = Field(default=0)
    content_hash: Optional[str] = Field(default=None)
    content_path: Optional[str] = Field(default=None)  # Relative path to markdown file

    # Fetch info
    fetch_engine: Optional[str] = Field(default=None)
    public_url: Optional[str] = Field(default=None)

    # Error tracking
    error: Optional[str] = Field(default=None)

    # Metadata
    metadata_json: Optional[dict] = Field(sa_column=Column(JSON), default=None)
