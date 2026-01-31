"""
Document lifecycle models.

Includes:
- DocumentIdRegistry: Central document ID registry (SQLModel table)
- DocumentView: Virtual view aggregated from workflow tables (dataclass, not persisted)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from kurt.db.models import TenantMixin, TimestampMixin
from kurt.tools.fetch.models import FetchStatus
from kurt.tools.map.models import MapStatus

# =============================================================================
# SQLModel Table
# =============================================================================


class DocumentIdRegistry(TimestampMixin, TenantMixin, SQLModel, table=True):
    """Central document ID registry.

    Maps URLs to stable document IDs. Used as the primary key registry
    that other workflow tables (map_documents, fetch_documents) reference.

    The document_id is typically a 12-character hex string from URL hash,
    matching the format used in map_documents and fetch_documents tables.
    """

    __tablename__ = "document_id_registry"
    __table_args__ = (
        Index("idx_registry_url", "url"),
        Index("idx_registry_url_hash", "url_hash", unique=True),
    )

    document_id: str = Field(primary_key=True)
    url: str = Field(max_length=2048)
    url_hash: str = Field(max_length=64, index=True)
    source_type: str = Field(default="url", max_length=20)


# =============================================================================
# Virtual View (Dataclass)
# =============================================================================


@dataclass
class DocumentView:
    """Virtual view of a document across all workflow stages.

    This is NOT a database table - it's computed by joining workflow tables.
    Each workflow (map, fetch, index, ...) maintains its own table,
    and DocumentView provides a unified lens to see the full lifecycle.
    """

    # Identity
    document_id: str
    source_url: str
    source_type: str = "url"

    # From map_documents
    map_status: Optional[MapStatus] = None
    discovery_method: Optional[str] = None
    discovery_url: Optional[str] = None
    is_new: bool = True
    discovered_at: Optional[datetime] = None

    # From fetch_documents
    fetch_status: Optional[FetchStatus] = None
    fetch_engine: Optional[str] = None
    content_length: Optional[int] = None
    content_hash: Optional[str] = None
    public_url: Optional[str] = None
    fetched_at: Optional[datetime] = None

    # Common
    title: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None

    # Tenant info
    user_id: Optional[str] = None
    workspace_id: Optional[str] = None

    @property
    def current_stage(self) -> str:
        """Determine the furthest stage this document has reached."""
        if self.fetch_status == FetchStatus.SUCCESS:
            return "fetched"
        if self.fetch_status == FetchStatus.PENDING:
            return "fetching"
        if self.map_status:
            return "mapped"
        return "unknown"

    @property
    def has_error(self) -> bool:
        """Check if document has error in any stage."""
        return self.map_status == MapStatus.ERROR or self.fetch_status == FetchStatus.ERROR

    @property
    def is_fetchable(self) -> bool:
        """Check if document is ready to be fetched."""
        return self.map_status == MapStatus.SUCCESS and self.fetch_status in (
            None,
            FetchStatus.PENDING,
            FetchStatus.ERROR,
        )

    @property
    def is_fetched(self) -> bool:
        """Check if document has been successfully fetched."""
        return self.fetch_status == FetchStatus.SUCCESS
