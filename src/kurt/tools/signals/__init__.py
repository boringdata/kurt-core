"""
SignalsTool - Social monitoring tool for Kurt workflows.

Fetches signals from Reddit, HackerNews, and RSS/Atom feeds.
Thin wrapper around kurt.integrations.research.monitoring.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from kurt.tools.base import ProgressCallback, Tool, ToolContext, ToolResult
from kurt.tools.registry import register_tool

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models
# ============================================================================


class SignalInput(BaseModel):
    """Input parameters for the Signals tool."""

    source: Literal["reddit", "hackernews", "feeds"] = Field(
        ...,
        description="Signal source: reddit, hackernews, or feeds",
    )

    # Reddit options
    subreddit: str | None = Field(
        default=None,
        description="Subreddit(s) to monitor (comma or + separated)",
    )

    # Feeds options
    feed_url: str | None = Field(
        default=None,
        description="RSS/Atom feed URL (required for feeds source)",
    )

    # Common filters
    keywords: str | None = Field(
        default=None,
        description="Keywords to filter (comma-separated)",
    )

    timeframe: Literal["hour", "day", "week", "month"] = Field(
        default="day",
        description="Time filter for results",
    )

    min_score: int = Field(
        default=0,
        ge=0,
        description="Minimum score threshold",
    )

    limit: int = Field(
        default=25,
        ge=1,
        le=100,
        description="Maximum number of results",
    )

    # Reddit-specific
    sort: Literal["hot", "new", "top", "rising"] = Field(
        default="hot",
        description="Sort order for Reddit",
    )

    dry_run: bool = Field(
        default=False,
        description="Preview mode - don't persist to database",
    )


class SignalOutput(BaseModel):
    """Output for a single signal."""

    signal_id: str = Field(..., description="Unique signal identifier")
    source: str = Field(..., description="Source platform (reddit, hackernews, feeds)")
    title: str = Field(..., description="Signal title/headline")
    url: str = Field(..., description="Signal URL")
    snippet: str | None = Field(default=None, description="Content snippet/summary")
    author: str | None = Field(default=None, description="Author/poster")
    score: int = Field(default=0, description="Upvotes/score")
    comment_count: int = Field(default=0, description="Number of comments")
    subreddit: str | None = Field(default=None, description="Subreddit (Reddit only)")
    domain: str | None = Field(default=None, description="Link domain")
    keywords: list[str] = Field(default_factory=list, description="Matched keywords")
    timestamp: str | None = Field(default=None, description="Signal timestamp (ISO format)")


# ============================================================================
# Helper Functions
# ============================================================================


def _parse_keywords(keywords: str | None) -> list[str]:
    """Parse comma-separated keywords into list."""
    if not keywords:
        return []
    return [k.strip() for k in keywords.split(",") if k.strip()]


def _parse_subreddits(subreddit: str | None) -> list[str]:
    """Parse subreddit string into list (supports comma or + separator)."""
    if not subreddit:
        return []
    # Support both comma and + separators
    if "+" in subreddit:
        return [s.strip() for s in subreddit.split("+") if s.strip()]
    return [s.strip() for s in subreddit.split(",") if s.strip()]


# ============================================================================
# SignalsTool Implementation
# ============================================================================


@register_tool
class SignalsTool(Tool[SignalInput, SignalOutput]):
    """
    Fetch signals from social platforms and feeds.

    Substeps:
    - fetch_signals: Fetch from source (Reddit/HN/RSS)

    Sources:
    - reddit: Fetch posts from subreddit(s)
    - hackernews: Fetch recent stories from HN
    - feeds: Fetch entries from RSS/Atom feed
    """

    name = "signals"
    description = "Fetch signals from Reddit, HackerNews, or RSS feeds"
    InputModel = SignalInput
    OutputModel = SignalOutput

    async def run(
        self,
        params: SignalInput,
        context: ToolContext,
        on_progress: ProgressCallback | None = None,
    ) -> ToolResult:
        """
        Execute the signals tool.

        Args:
            params: Signal parameters (source, filters, etc.)
            context: Execution context
            on_progress: Optional progress callback

        Returns:
            ToolResult with fetched signals
        """
        from kurt.integrations.research.monitoring import (
            FeedAdapter,
            HackerNewsAdapter,
            RedditAdapter,
            Signal,
        )

        # ----------------------------------------------------------------
        # Substep: fetch_signals
        # ----------------------------------------------------------------
        self.emit_progress(
            on_progress,
            substep="fetch_signals",
            status="running",
            current=0,
            total=params.limit,
            message=f"Fetching signals from {params.source}",
        )

        keywords = _parse_keywords(params.keywords)
        signals: list[Signal] = []

        try:
            if params.source == "reddit":
                adapter = RedditAdapter()
                subreddits = _parse_subreddits(params.subreddit)

                if not subreddits:
                    tool_result = ToolResult(success=False)
                    tool_result.add_error(
                        error_type="missing_subreddit",
                        message="subreddit is required for reddit source",
                    )
                    return tool_result

                if len(subreddits) > 1:
                    signals = adapter.get_multi_subreddit_posts(
                        subreddits=subreddits,
                        timeframe=params.timeframe,
                        sort=params.sort,
                        limit=params.limit,
                        keywords=keywords or None,
                        min_score=params.min_score,
                    )
                else:
                    signals = adapter.get_subreddit_posts(
                        subreddit=subreddits[0],
                        timeframe=params.timeframe,
                        sort=params.sort,
                        limit=params.limit,
                        keywords=keywords or None,
                        min_score=params.min_score,
                    )

            elif params.source == "hackernews":
                adapter = HackerNewsAdapter()
                # Map timeframe to hours
                timeframe_hours = {
                    "hour": 1,
                    "day": 24,
                    "week": 168,
                    "month": 720,
                }
                hours = timeframe_hours.get(params.timeframe, 24)

                signals = adapter.get_recent(
                    hours=hours,
                    keywords=keywords or None,
                    min_score=params.min_score,
                )
                # Limit results
                signals = signals[: params.limit]

            elif params.source == "feeds":
                if not params.feed_url:
                    tool_result = ToolResult(success=False)
                    tool_result.add_error(
                        error_type="missing_feed_url",
                        message="feed_url is required for feeds source",
                    )
                    return tool_result

                adapter = FeedAdapter()
                signals = adapter.get_feed_entries(
                    feed_url=params.feed_url,
                    keywords=keywords or None,
                    limit=params.limit,
                )

            else:
                tool_result = ToolResult(success=False)
                tool_result.add_error(
                    error_type="invalid_source",
                    message=f"Unknown signal source: {params.source}",
                )
                return tool_result

        except Exception as e:
            logger.error(f"Failed to fetch signals: {e}")
            self.emit_progress(
                on_progress,
                substep="fetch_signals",
                status="failed",
                message=str(e),
            )
            tool_result = ToolResult(success=False)
            tool_result.add_error(
                error_type="fetch_failed",
                message=str(e),
            )
            return tool_result

        # Emit progress for each signal
        total = len(signals)
        for idx, signal in enumerate(signals):
            self.emit_progress(
                on_progress,
                substep="fetch_signals",
                status="progress",
                current=idx + 1,
                total=total,
                message=f"Fetched {idx + 1}/{total} signals",
                metadata={
                    "signal_id": signal.signal_id,
                    "title": signal.title[:50] if signal.title else "",
                },
            )

        self.emit_progress(
            on_progress,
            substep="fetch_signals",
            status="completed",
            current=total,
            total=total,
            message=f"Fetched {total} signal(s) from {params.source}",
        )

        # Build output data
        output_data = []
        for signal in signals:
            signal_dict = signal.to_dict()
            # Convert timestamp to ISO string if datetime
            if isinstance(signal_dict.get("timestamp"), datetime):
                signal_dict["timestamp"] = signal_dict["timestamp"].isoformat()

            output_data.append({
                "signal_id": signal_dict["signal_id"],
                "source": signal_dict["source"],
                "title": signal_dict["title"],
                "url": signal_dict["url"],
                "snippet": signal_dict.get("snippet"),
                "author": signal_dict.get("author"),
                "score": signal_dict.get("score", 0),
                "comment_count": signal_dict.get("comment_count", 0),
                "subreddit": signal_dict.get("subreddit"),
                "domain": signal_dict.get("domain"),
                "keywords": signal_dict.get("keywords", []),
                "timestamp": signal_dict.get("timestamp"),
            })

        # Build result
        tool_result = ToolResult(
            success=True,
            data=output_data,
        )

        tool_result.add_substep(
            name="fetch_signals",
            status="completed",
            current=total,
            total=total,
        )

        return tool_result


__all__ = [
    "SignalsTool",
    "SignalInput",
    "SignalOutput",
]
