"""Database models for batch embedding storage."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel

from kurt.db.models import EmbeddingMixin, TenantMixin, TimestampMixin


class BatchEmbeddingStatus(str, Enum):
    """Status for batch embedding operations."""

    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


class BatchEmbeddingRecord(EmbeddingMixin, TimestampMixin, TenantMixin, SQLModel, table=True):
    """Persisted embeddings linked to documents."""

    __tablename__ = "batch_embedding_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: str = Field(index=True)
    workflow_id: Optional[str] = Field(default=None, index=True)

    # Model info
    model: str = Field(default="text-embedding-3-small")
    provider: str = Field(default="openai")
    vector_size: int = Field(default=0)

    # Status
    status: BatchEmbeddingStatus = Field(default=BatchEmbeddingStatus.SUCCESS)

    # Source text info
    text_hash: Optional[str] = Field(default=None, index=True)
    text_length: int = Field(default=0)

    # Error tracking
    error: Optional[str] = Field(default=None)
