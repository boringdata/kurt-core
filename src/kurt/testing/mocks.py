"""
Mock factories for external providers in E2E tests.

These factories create realistic mock responses for external APIs,
allowing tests to run without making actual API calls while still
testing real data flow through the system.

Usage:
    @patch("httpx.get")
    def test_map_url(mock_get, cli_runner, tmp_project):
        mock_get.return_value = mock_httpx_response(
            json={"urls": ["https://example.com/1", "https://example.com/2"]}
        )
        # ... run test
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock, Mock

# =============================================================================
# HTTP Response Mocks
# =============================================================================


@dataclass
class MockHttpxResponse:
    """Mock httpx.Response object."""

    status_code: int = 200
    _json: dict[str, Any] | None = None
    _text: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    url: str = "https://example.com"

    def json(self) -> dict[str, Any]:
        if self._json is not None:
            return self._json
        raise ValueError("No JSON content")

    @property
    def text(self) -> str:
        if self._text is not None:
            return self._text
        if self._json is not None:
            import json

            return json.dumps(self._json)
        return ""

    @property
    def content(self) -> bytes:
        return self.text.encode("utf-8")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


def mock_httpx_response(
    status: int = 200,
    json: dict[str, Any] | None = None,
    text: str | None = None,
    headers: dict[str, str] | None = None,
    url: str = "https://example.com",
) -> MockHttpxResponse:
    """
    Create a mock httpx.Response.

    Args:
        status: HTTP status code
        json: JSON response body (dict)
        text: Text response body
        headers: Response headers
        url: Request URL

    Returns:
        MockHttpxResponse that can be used as return_value for httpx mocks

    Example:
        @patch("httpx.get")
        def test_fetch(mock_get):
            mock_get.return_value = mock_httpx_response(
                json={"data": "test"}
            )
    """
    return MockHttpxResponse(
        status_code=status,
        _json=json,
        _text=text,
        headers=headers or {},
        url=url,
    )


def mock_httpx_error(error_type: str = "connection") -> Mock:
    """
    Create a mock that raises an httpx error.

    Args:
        error_type: Type of error ("connection", "timeout", "http")

    Returns:
        Mock configured to raise appropriate exception
    """
    import httpx

    mock = Mock()
    if error_type == "connection":
        mock.side_effect = httpx.ConnectError("Connection refused")
    elif error_type == "timeout":
        mock.side_effect = httpx.TimeoutException("Request timed out")
    elif error_type == "http":
        mock.side_effect = httpx.HTTPStatusError(
            "404 Not Found",
            request=Mock(),
            response=mock_httpx_response(status=404),
        )
    return mock


# =============================================================================
# Sitemap and RSS Mocks
# =============================================================================


def mock_sitemap_response(urls: list[str], lastmod: str | None = None) -> MockHttpxResponse:
    """
    Create a mock sitemap XML response.

    Args:
        urls: List of URLs to include in sitemap
        lastmod: Optional last modified date for all URLs

    Returns:
        MockHttpxResponse with sitemap XML

    Example:
        mock_get.return_value = mock_sitemap_response([
            "https://example.com/page1",
            "https://example.com/page2",
        ])
    """
    lastmod_xml = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
    url_entries = "\n".join(
        f"""<url>
    <loc>{url}</loc>
    {lastmod_xml}
</url>"""
        for url in urls
    )

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{url_entries}
</urlset>"""

    return mock_httpx_response(
        text=xml,
        headers={"content-type": "application/xml"},
    )


def mock_sitemap_index_response(sitemap_urls: list[str]) -> MockHttpxResponse:
    """
    Create a mock sitemap index XML response.

    Args:
        sitemap_urls: List of child sitemap URLs

    Returns:
        MockHttpxResponse with sitemap index XML
    """
    sitemap_entries = "\n".join(
        f"""<sitemap>
    <loc>{url}</loc>
</sitemap>"""
        for url in sitemap_urls
    )

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{sitemap_entries}
</sitemapindex>"""

    return mock_httpx_response(
        text=xml,
        headers={"content-type": "application/xml"},
    )


def mock_rss_response(entries: list[dict[str, str]]) -> MockHttpxResponse:
    """
    Create a mock RSS feed response.

    Args:
        entries: List of dicts with "title", "link", "description" keys

    Returns:
        MockHttpxResponse with RSS XML

    Example:
        mock_get.return_value = mock_rss_response([
            {"title": "Post 1", "link": "https://example.com/1", "description": "..."},
        ])
    """
    item_entries = "\n".join(
        f"""<item>
    <title>{entry.get("title", "Untitled")}</title>
    <link>{entry.get("link", "")}</link>
    <description>{entry.get("description", "")}</description>
</item>"""
        for entry in entries
    )

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <description>Test RSS Feed</description>
    {item_entries}
</channel>
</rss>"""

    return mock_httpx_response(
        text=xml,
        headers={"content-type": "application/rss+xml"},
    )


# =============================================================================
# Trafilatura Mocks
# =============================================================================


def mock_trafilatura_extract(content: str, metadata: dict[str, Any] | None = None) -> MagicMock:
    """
    Create a mock for trafilatura.extract().

    Args:
        content: Extracted content to return
        metadata: Optional metadata dict

    Returns:
        MagicMock configured for trafilatura.extract

    Example:
        @patch("trafilatura.extract")
        def test_fetch(mock_extract):
            mock_extract.return_value = mock_trafilatura_extract("Page content")
    """
    mock = MagicMock()
    mock.return_value = content

    if metadata:
        mock.metadata = metadata

    return mock


def mock_trafilatura_fetch_url(html: str | None = None) -> str | None:
    """
    Create a return value for trafilatura.fetch_url().

    Args:
        html: HTML content to return, or None for fetch failure

    Returns:
        HTML string or None
    """
    return html


# =============================================================================
# Perplexity API Mocks
# =============================================================================


def mock_perplexity_response(
    answer: str,
    citations: list[dict[str, str]] | None = None,
    model: str = "llama-3.1-sonar-small-128k-online",
) -> MockHttpxResponse:
    """
    Create a mock Perplexity API response.

    Args:
        answer: The AI-generated answer
        citations: List of citation dicts with "url" and "title" keys
        model: Model name to include in response

    Returns:
        MockHttpxResponse mimicking Perplexity API

    Example:
        mock_client.post.return_value = mock_perplexity_response(
            answer="The answer is...",
            citations=[{"url": "https://source.com", "title": "Source"}]
        )
    """
    citations = citations or []

    response_json = {
        "id": "test-id",
        "model": model,
        "object": "chat.completion",
        "created": 1234567890,
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": answer,
                },
                "delta": {"role": "assistant", "content": ""},
            }
        ],
        "citations": citations,
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 200,
            "total_tokens": 300,
        },
    }

    return mock_httpx_response(json=response_json)


# =============================================================================
# Reddit API Mocks
# =============================================================================


def mock_reddit_posts(posts: list[dict[str, Any]]) -> MockHttpxResponse:
    """
    Create a mock Reddit API response.

    Args:
        posts: List of post dicts with keys: title, score, num_comments, url, selftext

    Returns:
        MockHttpxResponse mimicking Reddit API

    Example:
        mock_get.return_value = mock_reddit_posts([
            {"title": "Test Post", "score": 100, "num_comments": 50},
        ])
    """
    children = []
    for post in posts:
        children.append(
            {
                "kind": "t3",
                "data": {
                    "title": post.get("title", "Untitled"),
                    "score": post.get("score", 0),
                    "num_comments": post.get("num_comments", 0),
                    "url": post.get("url", "https://reddit.com/r/test"),
                    "selftext": post.get("selftext", ""),
                    "created_utc": post.get("created_utc", 1234567890),
                    "author": post.get("author", "test_user"),
                    "subreddit": post.get("subreddit", "test"),
                    "permalink": post.get("permalink", "/r/test/comments/123/test/"),
                    "id": post.get("id", "abc123"),
                },
            }
        )

    return mock_httpx_response(
        json={
            "kind": "Listing",
            "data": {
                "children": children,
                "after": None,
                "before": None,
            },
        }
    )


# =============================================================================
# HackerNews API Mocks
# =============================================================================


def mock_hackernews_top_stories(story_ids: list[int]) -> MockHttpxResponse:
    """
    Create a mock HackerNews top stories response.

    Args:
        story_ids: List of story IDs

    Returns:
        MockHttpxResponse with story ID list
    """
    return mock_httpx_response(json=story_ids)


def mock_hackernews_story(
    story_id: int,
    title: str,
    score: int = 100,
    url: str | None = None,
    **kwargs: Any,
) -> MockHttpxResponse:
    """
    Create a mock HackerNews story item response.

    Args:
        story_id: Story ID
        title: Story title
        score: Story score
        url: External URL (None for Ask HN posts)
        **kwargs: Additional fields

    Returns:
        MockHttpxResponse for single story
    """
    story = {
        "id": story_id,
        "type": "story",
        "title": title,
        "score": score,
        "by": kwargs.get("by", "test_user"),
        "time": kwargs.get("time", 1234567890),
        "descendants": kwargs.get("descendants", 10),
        "kids": kwargs.get("kids", []),
    }

    if url:
        story["url"] = url

    return mock_httpx_response(json=story)


# =============================================================================
# Apify API Mocks
# =============================================================================


def mock_apify_actor_run(
    results: list[dict[str, Any]], status: str = "SUCCEEDED"
) -> dict[str, Any]:
    """
    Create a mock Apify actor run response structure.

    Args:
        results: List of result items
        status: Run status

    Returns:
        Dict mimicking Apify run response
    """
    return {
        "status": status,
        "data": {
            "id": "test-run-id",
            "status": status,
            "startedAt": "2024-01-01T00:00:00.000Z",
            "finishedAt": "2024-01-01T00:01:00.000Z",
            "exitCode": 0 if status == "SUCCEEDED" else 1,
        },
    }


def mock_apify_dataset_items(items: list[dict[str, Any]]) -> MockHttpxResponse:
    """
    Create a mock Apify dataset items response.

    Args:
        items: List of result items

    Returns:
        MockHttpxResponse with dataset items
    """
    return mock_httpx_response(json=items)


def mock_apify_twitter_profile(
    username: str,
    display_name: str,
    followers: int = 1000,
    bio: str = "Test bio",
) -> dict[str, Any]:
    """
    Create a mock Twitter profile from Apify scraper.

    Args:
        username: Twitter username
        display_name: Display name
        followers: Follower count
        bio: Profile bio

    Returns:
        Dict mimicking Apify Twitter profile data
    """
    return {
        "username": username,
        "displayName": display_name,
        "followersCount": followers,
        "followingCount": 500,
        "bio": bio,
        "url": f"https://twitter.com/{username}",
        "profileImageUrl": f"https://pbs.twimg.com/{username}",
        "verified": False,
        "tweets": [],
    }


def mock_apify_twitter_post(
    tweet_id: str,
    text: str,
    username: str = "test_user",
    likes: int = 100,
    retweets: int = 10,
) -> dict[str, Any]:
    """
    Create a mock Twitter post from Apify scraper.

    Args:
        tweet_id: Tweet ID
        text: Tweet text
        username: Author username
        likes: Like count
        retweets: Retweet count

    Returns:
        Dict mimicking Apify Twitter post data
    """
    return {
        "id": tweet_id,
        "text": text,
        "author": {
            "username": username,
            "displayName": f"Test {username}",
        },
        "likeCount": likes,
        "retweetCount": retweets,
        "replyCount": 5,
        "createdAt": "2024-01-01T12:00:00.000Z",
        "url": f"https://twitter.com/{username}/status/{tweet_id}",
    }


# =============================================================================
# PostHog API Mocks
# =============================================================================


def mock_posthog_events(events: list[dict[str, Any]]) -> MockHttpxResponse:
    """
    Create a mock PostHog events API response.

    Args:
        events: List of event dicts

    Returns:
        MockHttpxResponse with PostHog events
    """
    return mock_httpx_response(
        json={
            "results": events,
            "next": None,
        }
    )


def mock_posthog_insights(insights: list[dict[str, Any]]) -> MockHttpxResponse:
    """
    Create a mock PostHog insights API response.

    Args:
        insights: List of insight result dicts

    Returns:
        MockHttpxResponse with PostHog insights
    """
    return mock_httpx_response(
        json={
            "results": insights,
        }
    )


# =============================================================================
# Feedparser Mocks
# =============================================================================


def mock_feedparser_parse(entries: list[dict[str, str]]) -> MagicMock:
    """
    Create a mock feedparser.parse() result.

    Args:
        entries: List of entry dicts with title, link, summary keys

    Returns:
        MagicMock mimicking feedparser FeedParserDict

    Example:
        @patch("feedparser.parse")
        def test_rss(mock_parse):
            mock_parse.return_value = mock_feedparser_parse([
                {"title": "Entry 1", "link": "https://example.com/1"},
            ])
    """
    mock_feed = MagicMock()
    mock_feed.feed.title = "Test Feed"
    mock_feed.feed.link = "https://example.com"

    mock_entries = []
    for entry in entries:
        mock_entry = MagicMock()
        mock_entry.title = entry.get("title", "Untitled")
        mock_entry.link = entry.get("link", "")
        mock_entry.summary = entry.get("summary", entry.get("description", ""))
        mock_entry.published = entry.get("published", "2024-01-01")
        mock_entry.get = lambda key, default=None, e=entry: e.get(key, default)
        mock_entries.append(mock_entry)

    mock_feed.entries = mock_entries
    mock_feed.bozo = False  # No parse errors

    return mock_feed


# =============================================================================
# HTML Content Mocks
# =============================================================================


def mock_html_page(
    title: str = "Test Page",
    content: str = "Page content here.",
    links: list[str] | None = None,
) -> str:
    """
    Create a mock HTML page.

    Args:
        title: Page title
        content: Main content
        links: List of URLs to include as links

    Returns:
        HTML string
    """
    links = links or []
    link_html = "\n".join(f'<a href="{url}">{url}</a>' for url in links)

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
</head>
<body>
    <h1>{title}</h1>
    <main>
        <p>{content}</p>
    </main>
    <nav>
        {link_html}
    </nav>
</body>
</html>"""


__all__ = [
    # HTTP mocks
    "MockHttpxResponse",
    "mock_httpx_response",
    "mock_httpx_error",
    # Sitemap/RSS mocks
    "mock_sitemap_response",
    "mock_sitemap_index_response",
    "mock_rss_response",
    # Trafilatura mocks
    "mock_trafilatura_extract",
    "mock_trafilatura_fetch_url",
    # Perplexity mocks
    "mock_perplexity_response",
    # Reddit mocks
    "mock_reddit_posts",
    # HackerNews mocks
    "mock_hackernews_top_stories",
    "mock_hackernews_story",
    # Apify mocks
    "mock_apify_actor_run",
    "mock_apify_dataset_items",
    "mock_apify_twitter_profile",
    "mock_apify_twitter_post",
    # PostHog mocks
    "mock_posthog_events",
    "mock_posthog_insights",
    # Feedparser mocks
    "mock_feedparser_parse",
    # HTML mocks
    "mock_html_page",
]
