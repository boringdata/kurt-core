"""Research workflow database models."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from kurt.db.models import TimestampMixin


class ResearchStatus(str, Enum):
    """Status of a research document."""

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


class ResearchDocument(TimestampMixin, SQLModel, table=True):
    """Saved research result from Perplexity queries."""

    __tablename__ = "research_documents"

    id: str = Field(primary_key=True)
    query: str = Field(default="")
    answer: str = Field(default="")

    # Source info
    source: str = Field(default="perplexity")
    model: Optional[str] = Field(default=None)

    # Metadata
    citations_json: Optional[dict] = Field(sa_column=Column(JSON), default=None)
    response_time_seconds: Optional[float] = Field(default=None)

    # Status
    status: str = Field(default=ResearchStatus.SUCCESS.value)
    error: Optional[str] = Field(default=None)

    # File storage
    content_path: Optional[str] = Field(default=None)

    def __repr__(self) -> str:
        return f"<ResearchDocument(id={self.id}, query={self.query[:50]}...)>"
