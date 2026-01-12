"""Signals workflow steps."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from dbos import DBOS

from kurt.db import managed_session
from kurt.integrations.research.monitoring import (
    FeedAdapter,
    HackerNewsAdapter,
    RedditAdapter,
    Signal,
)

from .config import SignalsConfig
from .models import MonitoringSignal


def serialize_signals(signals: list[Signal]) -> list[dict[str, Any]]:
    """Serialize Signal objects for DBOS step return."""
    return [s.to_dict() for s in signals]


@DBOS.step(name="fetch_signals")
def fetch_signals_step(config_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Fetch signals from a source (Reddit/HN/RSS).

    Args:
        config_dict: SignalsConfig as dict

    Returns:
        Dict with signals data
    """
    config = SignalsConfig.model_validate(config_dict)

    signals = []
    keywords = config.get_keywords_list()

    if config.source == "reddit":
        adapter = RedditAdapter()
        subreddits = config.get_subreddits_list()

        if len(subreddits) > 1:
            signals = adapter.get_multi_subreddit_posts(
                subreddits=subreddits,
                timeframe=config.timeframe,
                sort=config.sort,
                limit=config.limit,
                keywords=keywords or None,
                min_score=config.min_score,
            )
        elif subreddits:
            signals = adapter.get_subreddit_posts(
                subreddit=subreddits[0],
                timeframe=config.timeframe,
                sort=config.sort,
                limit=config.limit,
                keywords=keywords or None,
                min_score=config.min_score,
            )

    elif config.source == "hackernews":
        adapter = HackerNewsAdapter()
        # Map timeframe to hours for get_recent
        timeframe_hours = {
            "hour": 1,
            "day": 24,
            "week": 168,
            "month": 720,
        }
        hours = timeframe_hours.get(config.timeframe, 24)

        signals = adapter.get_recent(
            hours=hours,
            keywords=keywords or None,
            min_score=config.min_score,
        )
        # Limit results
        signals = signals[: config.limit]

    elif config.source == "feeds":
        if not config.feed_url:
            raise ValueError("feed_url is required for feeds source")

        adapter = FeedAdapter()
        signals = adapter.get_feed_entries(
            feed_url=config.feed_url,
            keywords=keywords or None,
            limit=config.limit,
        )

    else:
        raise ValueError(f"Unknown signal source: {config.source}")

    # Stream progress
    total = len(signals)
    DBOS.set_event("stage_total", total)
    for idx, signal in enumerate(signals):
        DBOS.set_event("stage_current", idx + 1)
        DBOS.write_stream(
            "progress",
            {
                "step": "fetch_signals",
                "idx": idx,
                "total": total,
                "title": signal.title[:50],
                "source": signal.source,
                "timestamp": time.time(),
            },
        )

    return {
        "source": config.source,
        "signals": serialize_signals(signals),
        "total": total,
        "dry_run": config.dry_run,
    }


@DBOS.transaction()
def persist_signals(
    signals: list[dict[str, Any]],
    source: str,
) -> dict[str, int]:
    """
    Persist signals to database.

    Args:
        signals: List of serialized Signal dicts
        source: Source name (reddit, hackernews, feeds)

    Returns:
        Dict with inserted/updated counts
    """
    with managed_session() as session:
        inserted = 0
        updated = 0

        for signal_dict in signals:
            signal_id = signal_dict["signal_id"]

            # Check existing
            existing = (
                session.query(MonitoringSignal)
                .filter(MonitoringSignal.signal_id == signal_id)
                .first()
            )

            # Parse timestamp as string for storage
            timestamp_str = None
            if signal_dict.get("timestamp"):
                ts = signal_dict["timestamp"]
                if isinstance(ts, str):
                    timestamp_str = ts
                elif isinstance(ts, datetime):
                    timestamp_str = ts.isoformat()

            if existing:
                # Update scores (they can change)
                existing.score = signal_dict.get("score", 0)
                existing.comment_count = signal_dict.get("comment_count", 0)
                updated += 1
            else:
                # Insert new
                signal = MonitoringSignal(
                    signal_id=signal_id,
                    source=source,
                    title=signal_dict["title"],
                    url=signal_dict["url"],
                    snippet=signal_dict.get("snippet"),
                    author=signal_dict.get("author"),
                    score=signal_dict.get("score", 0),
                    comment_count=signal_dict.get("comment_count", 0),
                    subreddit=signal_dict.get("subreddit"),
                    domain=signal_dict.get("domain"),
                    keywords_json=signal_dict.get("keywords", []),
                    signal_timestamp=timestamp_str,
                )
                session.add(signal)
                inserted += 1

        return {"inserted": inserted, "updated": updated}
