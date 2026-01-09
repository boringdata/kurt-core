"""Database models for signals workflow."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON
from sqlmodel import Field, SQLModel

from kurt.db.models import TimestampMixin


class MonitoringSignal(TimestampMixin, SQLModel, table=True):
    """Persisted monitoring signal from Reddit/HN/Feeds."""

    __tablename__ = "monitoring_signals"

    id: int | None = Field(default=None, primary_key=True)
    signal_id: str = Field(index=True, unique=True)
    source: str = Field(default="")  # reddit, hackernews, feeds
    title: str = Field(default="")
    url: str = Field(default="")
    snippet: str | None = Field(default=None)
    author: str | None = Field(default=None)
    score: int = Field(default=0)
    comment_count: int = Field(default=0)
    subreddit: str | None = Field(default=None)
    domain: str | None = Field(default=None)
    keywords_json: list[str] = Field(default_factory=list, sa_type=JSON)
    signal_timestamp: str | None = Field(default=None)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "signal_id": self.signal_id,
            "source": self.source,
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "author": self.author,
            "score": self.score,
            "comment_count": self.comment_count,
            "subreddit": self.subreddit,
            "domain": self.domain,
            "keywords": self.keywords_json,
            "timestamp": self.signal_timestamp,
        }
