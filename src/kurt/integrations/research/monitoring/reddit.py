"""
Reddit monitoring adapter.

Uses Reddit's JSON API (no authentication required for public content).
"""

from datetime import datetime
from typing import List, Optional

import requests

from kurt.integrations.research.monitoring.models import Signal


class RedditAdapter:
    """Adapter for monitoring Reddit posts and discussions."""

    BASE_URL = "https://reddit.com"

    def __init__(self):
        """Initialize Reddit adapter."""
        # Set user agent to avoid rate limiting
        self.headers = {"User-Agent": "Kurt/1.0 (Research monitoring tool)"}

    def get_subreddit_posts(
        self,
        subreddit: str,
        timeframe: str = "day",
        sort: str = "hot",
        limit: int = 25,
        keywords: Optional[List[str]] = None,
        min_score: int = 0,
    ) -> List[Signal]:
        """
        Get posts from a subreddit.

        Args:
            subreddit: Subreddit name (e.g., "dataengineering")
            timeframe: Time filter ("hour", "day", "week", "month", "year", "all")
            sort: Sort order ("hot", "new", "top", "rising")
            limit: Maximum posts to fetch (max 100)
            keywords: Optional keyword filter
            min_score: Minimum score threshold

        Returns:
            List of Signal objects
        """
        # Build URL
        url = f"{self.BASE_URL}/r/{subreddit}/{sort}.json"

        params = {
            "limit": min(limit, 100),
            "t": timeframe,  # Time filter (for "top" sort)
        }

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            signals = []
            for post in data.get("data", {}).get("children", []):
                post_data = post.get("data", {})

                # Skip if below score threshold
                if post_data.get("score", 0) < min_score:
                    continue

                # Create signal
                signal = Signal(
                    signal_id=f"reddit_{post_data.get('id')}",
                    source="reddit",
                    title=post_data.get("title", ""),
                    url=f"https://reddit.com{post_data.get('permalink', '')}",
                    snippet=post_data.get("selftext", "")[:500]
                    if post_data.get("selftext")
                    else None,
                    timestamp=datetime.fromtimestamp(post_data.get("created_utc", 0)),
                    author=post_data.get("author"),
                    score=post_data.get("score", 0),
                    comment_count=post_data.get("num_comments", 0),
                    subreddit=subreddit,
                    keywords=[],
                )

                # Filter by keywords if provided
                if keywords and not signal.matches_keywords(keywords):
                    continue

                # Track which keywords matched
                if keywords:
                    signal.keywords = [
                        kw
                        for kw in keywords
                        if kw.lower() in signal.title.lower()
                        or (signal.snippet and kw.lower() in signal.snippet.lower())
                    ]

                signals.append(signal)

            return signals

        except requests.RequestException as e:
            raise Exception(f"Failed to fetch Reddit data: {e}")

    def get_multi_subreddit_posts(self, subreddits: List[str], **kwargs) -> List[Signal]:
        """
        Get posts from multiple subreddits.

        Args:
            subreddits: List of subreddit names
            **kwargs: Additional arguments passed to get_subreddit_posts

        Returns:
            Combined list of Signal objects
        """
        all_signals = []
        for subreddit in subreddits:
            try:
                signals = self.get_subreddit_posts(subreddit, **kwargs)
                all_signals.extend(signals)
            except Exception as e:
                print(f"Warning: Failed to fetch from r/{subreddit}: {e}")
                continue

        # Sort by relevance score
        all_signals.sort(key=lambda s: s.relevance_score, reverse=True)
        return all_signals

    def search_subreddit(
        self,
        subreddit: str,
        query: str,
        timeframe: str = "week",
        sort: str = "relevance",
        limit: int = 25,
    ) -> List[Signal]:
        """
        Search within a subreddit.

        Args:
            subreddit: Subreddit to search
            query: Search query
            timeframe: Time filter
            sort: Sort order ("relevance", "hot", "top", "new")
            limit: Maximum results

        Returns:
            List of Signal objects
        """
        url = f"{self.BASE_URL}/r/{subreddit}/search.json"

        params = {
            "q": query,
            "restrict_sr": "on",  # Restrict to this subreddit
            "sort": sort,
            "t": timeframe,
            "limit": min(limit, 100),
        }

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            signals = []
            for post in data.get("data", {}).get("children", []):
                post_data = post.get("data", {})

                signal = Signal(
                    signal_id=f"reddit_{post_data.get('id')}",
                    source="reddit",
                    title=post_data.get("title", ""),
                    url=f"https://reddit.com{post_data.get('permalink', '')}",
                    snippet=post_data.get("selftext", "")[:500]
                    if post_data.get("selftext")
                    else None,
                    timestamp=datetime.fromtimestamp(post_data.get("created_utc", 0)),
                    author=post_data.get("author"),
                    score=post_data.get("score", 0),
                    comment_count=post_data.get("num_comments", 0),
                    subreddit=subreddit,
                    keywords=[query],
                )

                signals.append(signal)

            return signals

        except requests.RequestException as e:
            raise Exception(f"Failed to search Reddit: {e}")
