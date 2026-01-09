"""
Data models for research monitoring signals.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class Signal:
    """A signal from a monitoring source (Reddit, HN, RSS, etc.)."""

    # Identification
    signal_id: str  # Unique ID (e.g., "reddit_abc123")
    source: str  # "reddit", "hackernews", "rss"

    # Content
    title: str
    url: str
    snippet: Optional[str] = None

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    author: Optional[str] = None

    # Scoring
    score: int = 0  # Upvotes/points
    comment_count: int = 0

    # Context
    keywords: list[str] = field(default_factory=list)
    subreddit: Optional[str] = None  # For Reddit
    domain: Optional[str] = None  # For RSS feeds

    # Project association (optional)
    project: Optional[str] = None

    @property
    def relevance_score(self) -> float:
        """
        Calculate simple relevance score.

        Normalized combination of score and comments.
        """
        # Simple scoring: weighted sum
        # Score carries more weight than comments
        normalized_score = min(self.score / 100.0, 1.0)  # Cap at 100
        normalized_comments = min(self.comment_count / 50.0, 1.0)  # Cap at 50

        return (normalized_score * 0.7) + (normalized_comments * 0.3)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert datetime to ISO string
        if isinstance(data.get("timestamp"), datetime):
            data["timestamp"] = data["timestamp"].isoformat()
        # Add calculated relevance score
        data["relevance_score"] = self.relevance_score
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Signal:
        """Create Signal from dictionary."""
        # Parse timestamp if string
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        # Remove relevance_score if present (it's calculated)
        data.pop("relevance_score", None)
        return cls(**data)

    def matches_keywords(self, keywords: list[str]) -> bool:
        """Check if signal matches any of the given keywords."""
        if not keywords:
            return True

        text = f"{self.title} {self.snippet or ''}".lower()
        return any(keyword.lower() in text for keyword in keywords)
