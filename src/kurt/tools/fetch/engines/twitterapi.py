"""TwitterAPI.io content fetching engine for Twitter/X.

Uses the TwitterAPI.io service (https://twitterapi.io) to extract content
from Twitter/X profiles and tweets. Pay-as-you-go pricing with no subscription.

API Documentation: https://docs.twitterapi.io/
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from datetime import datetime
from typing import Any, Optional

import httpx

from kurt.tools.fetch.core.base import BaseFetcher, FetcherConfig, FetchResult


def _get_api_key() -> Optional[str]:
    """Get TwitterAPI.io API key from environment or Vault.

    Returns:
        API key string or None if not configured
    """
    # First try environment variable
    api_key = os.getenv("TWITTERAPI_API_KEY")
    if api_key:
        return api_key

    # Try Vault
    try:
        result = subprocess.run(
            ["vault", "kv", "get", "-field=api_key", "secret/agent/twitterapi"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return None


class TwitterApiFetcherConfig(FetcherConfig):
    """Configuration for TwitterAPI.io fetcher.

    Attributes:
        api_key: TwitterAPI.io API key (uses TWITTERAPI_API_KEY env var or Vault)
        max_tweets: Maximum tweets to fetch for profile URLs (default 20)
        include_replies: Include replies in user tweets (default False)
    """

    api_key: Optional[str] = None
    max_tweets: int = 20
    include_replies: bool = False


class TwitterApiFetcher(BaseFetcher):
    """Fetches content from Twitter/X using TwitterAPI.io.

    Supports:
    - Tweet URLs: Fetch individual tweet content
    - Profile URLs: Fetch user profile and recent tweets

    Pricing (pay-as-you-go):
    - Tweets: $0.15 per 1,000 tweets
    - Profiles: $0.18 per 1,000 users

    Usage:
        config = TwitterApiFetcherConfig()
        fetcher = TwitterApiFetcher(config)
        result = fetcher.fetch("https://twitter.com/username")
        result = fetcher.fetch("https://x.com/user/status/123456")
    """

    BASE_URL = "https://api.twitterapi.io"

    def __init__(self, config: Optional[FetcherConfig] = None):
        """Initialize TwitterAPI.io fetcher.

        Args:
            config: Fetcher configuration (TwitterApiFetcherConfig for full control)
        """
        # Convert base FetcherConfig to TwitterApiFetcherConfig if needed
        if config is None:
            config = TwitterApiFetcherConfig()
        elif not isinstance(config, TwitterApiFetcherConfig):
            config = TwitterApiFetcherConfig(**config.model_dump())

        super().__init__(config)
        self._config: TwitterApiFetcherConfig = self.config  # type: ignore

        # Get API key from config, environment, or Vault
        self._api_key = self._config.api_key or _get_api_key()

    def fetch(self, url: str) -> FetchResult:
        """Fetch content from Twitter/X URL.

        Args:
            url: Twitter/X URL (tweet or profile)

        Returns:
            FetchResult with extracted content in markdown format
        """
        if not self._api_key:
            return FetchResult(
                content="",
                metadata={"engine": "twitterapi"},
                success=False,
                error="[TwitterAPI] API key not configured. Set TWITTERAPI_API_KEY or add to Vault.",
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
                    metadata={"engine": "twitterapi", "url": url},
                    success=False,
                    error=f"[TwitterAPI] Could not parse Twitter URL: {url}",
                )

        except httpx.HTTPStatusError as e:
            error = self._map_http_error(e)
            return FetchResult(
                content="",
                metadata={"engine": "twitterapi", "url": url},
                success=False,
                error=error,
            )
        except httpx.RequestError as e:
            return FetchResult(
                content="",
                metadata={"engine": "twitterapi", "url": url},
                success=False,
                error=f"[TwitterAPI] Request error: {type(e).__name__}: {e}",
            )

    def _fetch_tweet(self, tweet_id: str, original_url: str) -> FetchResult:
        """Fetch a single tweet by ID.

        Args:
            tweet_id: Tweet ID
            original_url: Original URL for metadata

        Returns:
            FetchResult with tweet content
        """
        endpoint = f"{self.BASE_URL}/twitter/tweets"
        params = {"tweet_ids": tweet_id}

        with httpx.Client(timeout=self.config.timeout) as client:
            response = client.get(
                endpoint,
                params=params,
                headers={"X-API-Key": self._api_key},
            )
            response.raise_for_status()
            data = response.json()

        tweets = data.get("tweets", [])
        if not tweets:
            return FetchResult(
                content="",
                metadata={"engine": "twitterapi", "url": original_url, "tweet_id": tweet_id},
                success=False,
                error=f"[TwitterAPI] Tweet not found: {tweet_id}",
            )

        tweet = tweets[0]
        content = self._format_tweet(tweet)

        return FetchResult(
            content=content,
            metadata={
                "engine": "twitterapi",
                "url": original_url,
                "tweet_id": tweet_id,
                "author": tweet.get("author", {}).get("userName"),
                "created_at": tweet.get("createdAt"),
                "like_count": self._safe_int(tweet.get("likeCount")),
                "retweet_count": self._safe_int(tweet.get("retweetCount")),
                "reply_count": self._safe_int(tweet.get("replyCount")),
                "view_count": self._safe_int(tweet.get("viewCount")),
                "fetched_at": datetime.now().isoformat(),
            },
            success=True,
        )

    def _fetch_profile(self, username: str, original_url: str) -> FetchResult:
        """Fetch user profile and recent tweets.

        Args:
            username: Twitter username
            original_url: Original URL for metadata

        Returns:
            FetchResult with profile and tweets content
        """
        # Fetch user info
        user_endpoint = f"{self.BASE_URL}/twitter/user/info"
        user_params = {"userName": username}

        with httpx.Client(timeout=self.config.timeout) as client:
            user_response = client.get(
                user_endpoint,
                params=user_params,
                headers={"X-API-Key": self._api_key},
            )
            user_response.raise_for_status()
            user_data = user_response.json()

        user = user_data.get("data", {})
        if not user or user.get("unavailable"):
            return FetchResult(
                content="",
                metadata={"engine": "twitterapi", "url": original_url, "username": username},
                success=False,
                error=f"[TwitterAPI] User not found or unavailable: {username}",
            )

        # Rate limit: free tier allows 1 request per 5 seconds
        time.sleep(5.5)

        # Fetch recent tweets
        tweets_endpoint = f"{self.BASE_URL}/twitter/user/last_tweets"
        tweets_params = {
            "userName": username,
            "cursor": "",
            "includeReplies": str(self._config.include_replies).lower(),
        }

        with httpx.Client(timeout=self.config.timeout) as client:
            tweets_response = client.get(
                tweets_endpoint,
                params=tweets_params,
                headers={"X-API-Key": self._api_key},
            )
            tweets_response.raise_for_status()
            tweets_data = tweets_response.json()

        # Note: /user/last_tweets returns tweets under data.tweets
        tweets = tweets_data.get("data", {}).get("tweets", [])

        # Format content
        content = self._format_profile(user, tweets)

        return FetchResult(
            content=content,
            metadata={
                "engine": "twitterapi",
                "url": original_url,
                "username": username,
                "user_id": user.get("id"),
                "followers": user.get("followers", 0),
                "following": user.get("following", 0),
                "tweet_count": user.get("statusesCount", 0),
                "tweets_fetched": len(tweets),
                "is_verified": user.get("isBlueVerified", False),
                "fetched_at": datetime.now().isoformat(),
            },
            success=True,
        )

    def _extract_tweet_id(self, url: str) -> Optional[str]:
        """Extract tweet ID from URL.

        Args:
            url: Twitter URL

        Returns:
            Tweet ID or None
        """
        # Match: twitter.com/user/status/123 or x.com/user/status/123
        match = re.search(r"(?:twitter\.com|x\.com)/\w+/status/(\d+)", url, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _extract_username(self, url: str) -> Optional[str]:
        """Extract username from profile URL.

        Args:
            url: Twitter URL

        Returns:
            Username or None
        """
        # Match profile URL: twitter.com/username or x.com/username
        # Exclude special paths like /status/, /i/, /settings, etc.
        match = re.search(
            r"(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+)(?:/(?:$|with_replies|media|likes))?$",
            url,
            re.IGNORECASE,
        )
        if match:
            username = match.group(1)
            # Exclude reserved paths
            if username.lower() not in {"home", "explore", "notifications", "messages", "i", "settings"}:
                return username
        return None

    def _format_tweet(self, tweet: dict[str, Any]) -> str:
        """Format a tweet as markdown.

        Args:
            tweet: Tweet data from API

        Returns:
            Formatted markdown string
        """
        lines = []
        author = tweet.get("author", {})

        # Header with author info
        author_name = author.get("name", "Unknown")
        author_username = author.get("userName", "unknown")
        verified = " ✓" if author.get("isBlueVerified") else ""

        lines.append(f"# Tweet by {author_name} (@{author_username}){verified}")
        lines.append("")

        # Tweet metadata
        if tweet.get("createdAt"):
            lines.append(f"**Date:** {tweet['createdAt']}")
        if tweet.get("url"):
            lines.append(f"**URL:** {tweet['url']}")
        lines.append("")

        # Tweet content
        if tweet.get("text"):
            lines.append(tweet["text"])
            lines.append("")

        # Engagement stats (note: some fields can be arrays, so we normalize)
        stats = []
        like_count = self._safe_int(tweet.get("likeCount"))
        retweet_count = self._safe_int(tweet.get("retweetCount"))
        reply_count = self._safe_int(tweet.get("replyCount"))
        view_count = self._safe_int(tweet.get("viewCount"))

        if like_count:
            stats.append(f"{like_count:,} likes")
        if retweet_count:
            stats.append(f"{retweet_count:,} retweets")
        if reply_count:
            stats.append(f"{reply_count:,} replies")
        if view_count:
            stats.append(f"{view_count:,} views")

        if stats:
            lines.append("**Engagement:** " + " · ".join(stats))
            lines.append("")

        # Quoted tweet
        if tweet.get("quoted_tweet"):
            lines.append("---")
            lines.append("**Quoted tweet:**")
            lines.append(self._format_tweet_brief(tweet["quoted_tweet"]))
            lines.append("")

        return "\n".join(lines)

    def _format_tweet_brief(self, tweet: dict[str, Any]) -> str:
        """Format a tweet briefly (for quotes/retweets).

        Args:
            tweet: Tweet data

        Returns:
            Brief formatted string
        """
        author = tweet.get("author", {})
        username = author.get("userName", "unknown")
        text = tweet.get("text", "")[:280]
        return f"> @{username}: {text}"

    def _format_profile(self, user: dict[str, Any], tweets: list[dict]) -> str:
        """Format user profile and tweets as markdown.

        Args:
            user: User data from API
            tweets: List of tweet data

        Returns:
            Formatted markdown string
        """
        lines = []

        # Profile header
        name = user.get("name", "Unknown")
        username = user.get("userName", "unknown")
        verified = " ✓" if user.get("isBlueVerified") else ""

        lines.append(f"# {name} (@{username}){verified}")
        lines.append("")

        # Profile info
        if user.get("description"):
            lines.append(user["description"])
            lines.append("")

        if user.get("location"):
            lines.append(f"📍 {user['location']}")
        if user.get("url"):
            lines.append(f"🔗 {user['url']}")
        if user.get("createdAt"):
            lines.append(f"📅 Joined {user['createdAt']}")
        lines.append("")

        # Stats
        stats = []
        if user.get("followers") is not None:
            stats.append(f"**{user['followers']:,}** followers")
        if user.get("following") is not None:
            stats.append(f"**{user['following']:,}** following")
        if user.get("statusesCount") is not None:
            stats.append(f"**{user['statusesCount']:,}** tweets")

        if stats:
            lines.append(" · ".join(stats))
            lines.append("")

        # Recent tweets
        if tweets:
            lines.append("---")
            lines.append("## Recent Tweets")
            lines.append("")

            for i, tweet in enumerate(tweets[: self._config.max_tweets], 1):
                text = tweet.get("text", "")
                created = tweet.get("createdAt", "")
                url = tweet.get("url", "")

                # Truncate long tweets
                if len(text) > 500:
                    text = text[:500] + "..."

                lines.append(f"### {i}. {created}")
                lines.append(text)
                if url:
                    lines.append(f"[View tweet]({url})")
                lines.append("")

        return "\n".join(lines)

    def _safe_int(self, val: Any) -> int:
        """Safely convert API value to int (handles arrays and None)."""
        if isinstance(val, list):
            return val[0] if val else 0
        return val if isinstance(val, int) else 0

    def _map_http_error(self, e: httpx.HTTPStatusError) -> str:
        """Map HTTP status codes to user-friendly error messages."""
        status_code = e.response.status_code
        if status_code == 401:
            return "[TwitterAPI] Invalid API key"
        elif status_code == 403:
            return "[TwitterAPI] Access forbidden"
        elif status_code == 429:
            return "[TwitterAPI] Rate limit exceeded"
        elif status_code == 404:
            return "[TwitterAPI] Resource not found"
        else:
            return f"[TwitterAPI] API error ({status_code}): {e}"


# Alias for backward compatibility
TwitterApiEngine = TwitterApiFetcher
