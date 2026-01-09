from __future__ import annotations

from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from kurt_new.db.models import TenantMixin, TimestampMixin


class MapStatus(str, Enum):
    """Status for mapped documents."""

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


class MapDocument(TimestampMixin, TenantMixin, SQLModel, table=True):
    """Persisted mapping results for discovered sources."""

    __tablename__ = "map_documents"

    document_id: str = Field(primary_key=True)
    source_url: str = Field(default="")
    source_type: str = Field(default="url")
    discovery_method: str = Field(default="")
    discovery_url: Optional[str] = Field(default=None)
    status: MapStatus = Field(default=MapStatus.SUCCESS)
    is_new: bool = Field(default=True)
    title: Optional[str] = Field(default=None)
    content_hash: Optional[str] = Field(default=None, index=True)
    error: Optional[str] = Field(default=None)
    metadata_json: Optional[dict] = Field(sa_column=Column(JSON), default=None)
