"""Composio fetch provider for Twitter/X content.

Zero-cost Twitter search via Composio API (20k free calls/month).
Based on xBenJamminx/x-research-skill.

API: https://composio.dev
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import httpx

from kurt.tools.fetch.core.base import BaseFetcher, FetcherConfig, FetchResult
from kurt.tools.fetch.providers.composio.config import ComposioProviderConfig


def _get_composio_credentials() -> tuple[Optional[str], Optional[str]]:
    """Get Composio API key and connection ID from environment or Vault.

    Returns:
        Tuple of (api_key, connection_id) or (None, None) if not configured
    """
    api_key = os.getenv("COMPOSIO_API_KEY")
    connection_id = os.getenv("COMPOSIO_CONNECTION_ID")

    if api_key and connection_id:
        return api_key, connection_id

    # Try Vault
    try:
        for field, env_val in [("api_key", api_key), ("connection_id", connection_id)]:
            if env_val:
                continue
            result = subprocess.run(
                ["vault", "kv", "get", "-field=" + field, "secret/agent/composio"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                if field == "api_key":
                    api_key = result.stdout.strip()
                else:
                    connection_id = result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return api_key, connection_id


class ComposioFetcher(BaseFetcher):
    """Fetches Twitter/X content via Composio API.

    Composio provides zero-cost Twitter search (20k API calls/month on free tier).

    Supports:
    - Tweet URLs: Fetch individual tweet content
    - Profile URLs: Fetch user's recent tweets
    - Search queries: Search recent tweets (last 7 days)

    Usage:
        config = ComposioProviderConfig()
        fetcher = ComposioFetcher(config)
        result = fetcher.fetch("https://x.com/username")
        result = fetcher.fetch("https://twitter.com/user/status/123456")
    """

    name = "composio"
    version = "1.0.0"
    url_patterns = ["*twitter.com/*", "*x.com/*"]
    requires_env = ["COMPOSIO_API_KEY", "COMPOSIO_CONNECTION_ID"]

    ConfigModel = ComposioProviderConfig

    BASE_URL = "https://backend.composio.dev/api"

    def __init__(self, config: Optional[FetcherConfig] = None):
        """Initialize Composio fetcher.

        Args:
            config: Fetcher configuration
        """
        if config is None:
            config = FetcherConfig()
        super().__init__(config)

        self._api_key, self._connection_id = _get_composio_credentials()

        # Provider-specific config
        if isinstance(config, ComposioProviderConfig):
            self._provider_config = config
        else:
            self._provider_config = ComposioProviderConfig()

        # Setup cache directory
        self._cache_dir = Path(".kurt") / "cache" / "composio"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_ttl = timedelta(hours=self._provider_config.cache_ttl_hours)

    def fetch(self, url: str) -> FetchResult:
        """Fetch content from Twitter/X URL via Composio.

        Args:
            url: Twitter/X URL (tweet or profile)

        Returns:
            FetchResult with extracted content in markdown format
        """
        if not self._api_key or not self._connection_id:
            return FetchResult(
                content="",
                metadata={"engine": "composio"},
                success=False,
                error="[Composio] Credentials not configured. Set COMPOSIO_API_KEY and COMPOSIO_CONNECTION_ID.",
            )

        try:
            # Detect URL type
            tweet_id = self._extract_tweet_id(url)
            username = self._extract_username(url)

            if tweet_id:
                return self._fetch_tweet(tweet_id, url)
            elif username:
                return self._fetch_profile(username, url)
            else:
                return FetchResult(
                    content="",
                    metadata={"engine": "composio", "url": url},
                    success=False,
                    error=f"[Composio] Could not parse Twitter URL: {url}",
                )

        except httpx.HTTPStatusError as e:
            error = self._map_http_error(e)
            return FetchResult(
                content="",
                metadata={"engine": "composio", "url": url},
                success=False,
                error=error,
            )
        except httpx.RequestError as e:
            return FetchResult(
                content="",
                metadata={"engine": "composio", "url": url},
                success=False,
                error=f"[Composio] Request error: {type(e).__name__}: {e}",
            )

    def _execute_action(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a Composio action.

        Args:
            action: Action name (e.g., TWITTER_RECENT_SEARCH)
            params: Action parameters

        Returns:
            API response data
        """
        url = f"{self.BASE_URL}/v2/actions/{action}/execute"
        body = {
            "connectedAccountId": self._connection_id,
            "input": params,
        }

        with httpx.Client(timeout=self.config.timeout) as client:
            response = client.post(
                url,
                json=body,
                headers={
                    "x-api-key": self._api_key,
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            result = response.json()

        if result.get("error"):
            raise httpx.HTTPStatusError(
                f"Composio action error: {result['error']}",
                request=response.request,
                response=response,
            )

        return result.get("data", result)

    def _search_tweets(
        self,
        query: str,
        max_results: int = 100,
        sort_order: str = "relevancy",
    ) -> list[dict[str, Any]]:
        """Search recent tweets via Composio.

        Args:
            query: Twitter search query
            max_results: Maximum results (10-100)
            sort_order: "relevancy" or "recency"

        Returns:
            List of tweet data dictionaries
        """
        params = {
            "query": query,
            "max_results": min(100, max(10, max_results)),
            "sort_order": sort_order,
            "tweet__fields": ["created_at", "public_metrics", "author_id", "conversation_id", "entities"],
            "expansions": ["author_id"],
            "user__fields": ["username", "name", "public_metrics", "description"],
        }

        result = self._execute_action("TWITTER_RECENT_SEARCH", params)
        return self._parse_tweets(result)

    def _parse_tweets(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse raw API response into normalized tweet data.

        Args:
            raw: Raw Composio API response

        Returns:
            List of normalized tweet dictionaries
        """
        data = raw.get("data", raw)
        tweets_raw = data.get("data", []) if isinstance(data, dict) else data
        if not isinstance(tweets_raw, list):
            tweets_raw = []

        # Build user lookup from includes
        users: dict[str, Any] = {}
        includes = raw.get("includes", {})
        if isinstance(data, dict):
            includes = data.get("includes", includes)
        for u in includes.get("users", []):
            users[u.get("id", "")] = u

        tweets = []
        for t in tweets_raw:
            user = users.get(t.get("author_id", ""), {})
            m = t.get("public_metrics", {})

            tweets.append({
                "id": t.get("id", ""),
                "text": t.get("text", ""),
                "author_id": t.get("author_id", ""),
                "username": user.get("username", "unknown"),
                "name": user.get("name", "Unknown"),
                "created_at": t.get("created_at", ""),
                "conversation_id": t.get("conversation_id", t.get("id", "")),
                "metrics": {
                    "likes": m.get("like_count", 0),
                    "retweets": m.get("retweet_count", 0),
                    "replies": m.get("reply_count", 0),
                    "quotes": m.get("quote_count", 0),
                    "impressions": m.get("impression_count", 0),
                    "bookmarks": m.get("bookmark_count", 0),
                },
                "url": f"https://x.com/{user.get('username', 'unknown')}/status/{t.get('id', '')}",
            })

        return tweets

    def _fetch_tweet(self, tweet_id: str, original_url: str) -> FetchResult:
        """Fetch a single tweet by searching for its conversation.

        Args:
            tweet_id: Tweet ID
            original_url: Original URL for metadata

        Returns:
            FetchResult with tweet content
        """
        # Search for the specific tweet
        tweets = self._search_tweets(tweet_id, max_results=10)

        # Find the exact tweet
        tweet = next((t for t in tweets if t["id"] == tweet_id), None)
        if not tweet and tweets:
            tweet = tweets[0]  # Fallback to first result

        if not tweet:
            return FetchResult(
                content="",
                metadata={"engine": "composio", "url": original_url, "tweet_id": tweet_id},
                success=False,
                error=f"[Composio] Tweet not found: {tweet_id}",
            )

        content = self._format_tweet(tweet)

        return FetchResult(
            content=content,
            metadata={
                "engine": "composio",
                "url": original_url,
                "tweet_id": tweet_id,
                "author": tweet.get("username"),
                "created_at": tweet.get("created_at"),
                "like_count": tweet["metrics"]["likes"],
                "retweet_count": tweet["metrics"]["retweets"],
                "reply_count": tweet["metrics"]["replies"],
                "impression_count": tweet["metrics"]["impressions"],
                "fetched_at": datetime.now().isoformat(),
            },
            success=True,
        )

    def _fetch_profile(self, username: str, original_url: str) -> FetchResult:
        """Fetch user's recent tweets.

        Args:
            username: Twitter username
            original_url: Original URL for metadata

        Returns:
            FetchResult with profile tweets
        """
        query = f"from:{username} -is:retweet -is:reply"
        tweets = self._search_tweets(query, max_results=self._provider_config.max_results, sort_order="recency")

        if not tweets:
            return FetchResult(
                content="",
                metadata={"engine": "composio", "url": original_url, "username": username},
                success=False,
                error=f"[Composio] No tweets found for user: {username}",
            )

        content = self._format_profile(username, tweets)

        return FetchResult(
            content=content,
            metadata={
                "engine": "composio",
                "url": original_url,
                "username": username,
                "tweets_fetched": len(tweets),
                "fetched_at": datetime.now().isoformat(),
            },
            success=True,
        )

    def _extract_tweet_id(self, url: str) -> Optional[str]:
        """Extract tweet ID from URL."""
        match = re.search(r"(?:twitter\.com|x\.com)/\w+/status/(\d+)", url, re.IGNORECASE)
        return match.group(1) if match else None

    def _extract_username(self, url: str) -> Optional[str]:
        """Extract username from profile URL."""
        match = re.search(
            r"(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+)(?:/(?:$|with_replies|media|likes))?$",
            url,
            re.IGNORECASE,
        )
        if match:
            username = match.group(1)
            if username.lower() not in {"home", "explore", "notifications", "messages", "i", "settings"}:
                return username
        return None

    def _format_tweet(self, tweet: dict[str, Any]) -> str:
        """Format a tweet as markdown."""
        lines = []

        lines.append(f"# Tweet by {tweet['name']} (@{tweet['username']})")
        lines.append("")

        if tweet.get("created_at"):
            lines.append(f"**Date:** {tweet['created_at']}")
        lines.append(f"**URL:** {tweet['url']}")
        lines.append("")

        lines.append(tweet.get("text", ""))
        lines.append("")

        m = tweet["metrics"]
        stats = []
        if m["likes"]:
            stats.append(f"{m['likes']:,} likes")
        if m["retweets"]:
            stats.append(f"{m['retweets']:,} retweets")
        if m["replies"]:
            stats.append(f"{m['replies']:,} replies")
        if m["impressions"]:
            stats.append(f"{m['impressions']:,} views")

        if stats:
            lines.append("**Engagement:** " + " · ".join(stats))
            lines.append("")

        return "\n".join(lines)

    def _format_profile(self, username: str, tweets: list[dict[str, Any]]) -> str:
        """Format user profile and tweets as markdown."""
        lines = []

        name = tweets[0]["name"] if tweets else username
        lines.append(f"# @{username} ({name})")
        lines.append("")
        lines.append(f"**Recent tweets:** {len(tweets)}")
        lines.append("")
        lines.append("---")
        lines.append("")

        for i, tweet in enumerate(tweets[:20], 1):
            text = tweet.get("text", "")
            if len(text) > 500:
                text = text[:500] + "..."

            created = tweet.get("created_at", "")[:10] if tweet.get("created_at") else ""
            m = tweet["metrics"]

            lines.append(f"### {i}. {created}")
            lines.append(text)
            lines.append(f"❤️ {m['likes']} · 🔄 {m['retweets']} · 👁️ {m['impressions']:,}")
            lines.append(f"[View tweet]({tweet['url']})")
            lines.append("")

        return "\n".join(lines)

    def _map_http_error(self, e: httpx.HTTPStatusError) -> str:
        """Map HTTP status codes to user-friendly error messages."""
        status_code = e.response.status_code
        if status_code == 401:
            return "[Composio] Invalid API key"
        elif status_code == 403:
            return "[Composio] Access forbidden - check connection ID"
        elif status_code == 429:
            return "[Composio] Rate limit exceeded"
        elif status_code == 404:
            return "[Composio] Resource not found"
        else:
            return f"[Composio] API error ({status_code}): {e}"


# Alias for backward compatibility
ComposioEngine = ComposioFetcher
