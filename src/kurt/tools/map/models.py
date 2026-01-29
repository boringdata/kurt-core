from __future__ import annotations

from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel

from kurt.db.models import TenantMixin, TimestampMixin


class DocType(str, Enum):
    """Type of document being mapped."""

    DOC = "doc"
    PROFILE = "profile"
    POSTS = "posts"


class MapStatus(str, Enum):
    """Status for mapped documents."""

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


class MapDocument(TimestampMixin, TenantMixin, SQLModel, table=True):
    """Persisted mapping results for discovered sources."""

    __tablename__ = "map_documents"

    document_id: str = Field(primary_key=True)
    source_url: str = Field(default="", index=True)
    source_type: str = Field(default="url")
    doc_type: DocType = Field(default=DocType.DOC, index=True)
    platform: Optional[str] = Field(default=None, index=True)
    discovery_method: str = Field(default="")
    discovery_url: Optional[str] = Field(default=None)
    status: MapStatus = Field(default=MapStatus.SUCCESS)
    is_new: bool = Field(default=True)
    title: Optional[str] = Field(default=None)
    content_hash: Optional[str] = Field(default=None, index=True)
    error: Optional[str] = Field(default=None)
    metadata_json: Optional[dict] = Field(sa_column=Column(JSON), default=None)

    __table_args__ = (
        UniqueConstraint("source_url", "doc_type", name="unique_source_doctype"),
    )
