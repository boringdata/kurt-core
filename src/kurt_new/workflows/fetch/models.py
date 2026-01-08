from __future__ import annotations

from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from kurt_new.db.models import TenantMixin, TimestampMixin


class FetchStatus(str, Enum):
    """Status for fetched documents."""

    PENDING = "PENDING"
    FETCHED = "FETCHED"
    ERROR = "ERROR"


class FetchDocument(TimestampMixin, TenantMixin, SQLModel, table=True):
    """Persisted fetch results for documents."""

    __tablename__ = "fetch_documents"

    document_id: str = Field(primary_key=True)

    # Status
    status: FetchStatus = Field(default=FetchStatus.PENDING)

    # Content info
    content_length: int = Field(default=0)
    content_hash: Optional[str] = Field(default=None)
    content_path: Optional[str] = Field(default=None)

    # Embedding info
    embedding_dims: int = Field(default=0)

    # Links info
    links_extracted: int = Field(default=0)

    # Fetch info
    fetch_engine: Optional[str] = Field(default=None)
    public_url: Optional[str] = Field(default=None)

    # Error tracking
    error: Optional[str] = Field(default=None)

    # Metadata
    metadata_json: Optional[dict] = Field(sa_column=Column(JSON), default=None)
