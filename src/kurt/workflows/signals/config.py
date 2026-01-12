"""Configuration for signals workflow."""

from __future__ import annotations

from typing import Literal

from kurt.config import ConfigParam, StepConfig


class SignalsConfig(StepConfig):
    """Configuration for signals monitoring workflow."""

    source: Literal["reddit", "hackernews", "feeds"] = ConfigParam(
        description="Signal source: reddit, hackernews, or feeds"
    )

    # Reddit options
    subreddit: str | None = ConfigParam(
        default=None,
        description="Subreddit(s) to monitor (comma or + separated)",
    )

    # Feeds options
    feed_url: str | None = ConfigParam(
        default=None,
        description="RSS/Atom feed URL",
    )

    # Common filters
    keywords: str | None = ConfigParam(
        default=None,
        description="Keywords to filter (comma-separated)",
    )
    timeframe: Literal["hour", "day", "week", "month"] = ConfigParam(
        default="day",
        description="Time filter for results",
    )
    min_score: int = ConfigParam(
        default=0,
        description="Minimum score threshold",
    )
    limit: int = ConfigParam(
        default=25,
        description="Maximum number of results",
    )

    # Reddit-specific
    sort: Literal["hot", "new", "top", "rising"] = ConfigParam(
        default="hot",
        description="Sort order for Reddit",
    )

    # Workflow options
    dry_run: bool = ConfigParam(
        default=False,
        description="Execute but don't persist to database",
    )

    def get_keywords_list(self) -> list[str]:
        """Parse comma-separated keywords into list."""
        if not self.keywords:
            return []
        return [k.strip() for k in self.keywords.split(",") if k.strip()]

    def get_subreddits_list(self) -> list[str]:
        """Parse subreddit string into list (supports comma or + separator)."""
        if not self.subreddit:
            return []
        # Support both comma and + separators
        if "+" in self.subreddit:
            return [s.strip() for s in self.subreddit.split("+") if s.strip()]
        return [s.strip() for s in self.subreddit.split(",") if s.strip()]
