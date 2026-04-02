"""
Tests for mock factories.

These tests verify that mock factories create correct mock objects
that can be used in E2E tests.
"""

from __future__ import annotations

import pytest

from kurt.testing import (
    mock_apify_twitter_post,
    mock_apify_twitter_profile,
    mock_feedparser_parse,
    mock_hackernews_story,
    mock_hackernews_top_stories,
    mock_html_page,
    mock_httpx_error,
    mock_httpx_response,
    mock_perplexity_response,
    mock_posthog_events,
    mock_reddit_posts,
    mock_rss_response,
    mock_sitemap_index_response,
    mock_sitemap_response,
    mock_trafilatura_extract,
    mock_trafilatura_fetch_url,
)


class TestMockHttpxResponse:
    """Tests for httpx response mocks."""

    def test_basic_response(self):
        """Test creating a basic mock response."""
        response = mock_httpx_response(status=200)
        assert response.status_code == 200
        assert response.text == ""

    def test_json_response(self):
        """Test creating a mock response with JSON data."""
        response = mock_httpx_response(json={"key": "value", "count": 42})
        assert response.status_code == 200
        assert response.json() == {"key": "value", "count": 42}
        assert '"key"' in response.text

    def test_text_response(self):
        """Test creating a mock response with text data."""
        response = mock_httpx_response(text="Hello, World!")
        assert response.text == "Hello, World!"
        assert response.content == b"Hello, World!"

    def test_error_response(self):
        """Test creating an error response."""
        response = mock_httpx_response(status=404)
        assert response.status_code == 404
        with pytest.raises(Exception, match="HTTP 404"):
            response.raise_for_status()

    def test_headers(self):
        """Test custom headers."""
        response = mock_httpx_response(headers={"content-type": "application/json"})
        assert response.headers["content-type"] == "application/json"

    def test_mock_httpx_error_connection(self):
        """Test connection error mock."""
        import httpx

        mock = mock_httpx_error("connection")
        with pytest.raises(httpx.ConnectError):
            mock()

    def test_mock_httpx_error_timeout(self):
        """Test timeout error mock."""
        import httpx

        mock = mock_httpx_error("timeout")
        with pytest.raises(httpx.TimeoutException):
            mock()


class TestSitemapMocks:
    """Tests for sitemap mock factories."""

    def test_sitemap_response(self):
        """Test creating a sitemap XML response."""
        response = mock_sitemap_response(
            [
                "https://example.com/page1",
                "https://example.com/page2",
            ]
        )
        assert response.status_code == 200
        assert "https://example.com/page1" in response.text
        assert "https://example.com/page2" in response.text
        assert "<urlset" in response.text
        assert response.headers["content-type"] == "application/xml"

    def test_sitemap_with_lastmod(self):
        """Test sitemap with lastmod dates."""
        response = mock_sitemap_response(["https://example.com/page1"], lastmod="2024-01-15")
        assert "<lastmod>2024-01-15</lastmod>" in response.text

    def test_sitemap_index_response(self):
        """Test creating a sitemap index response."""
        response = mock_sitemap_index_response(
            [
                "https://example.com/sitemap1.xml",
                "https://example.com/sitemap2.xml",
            ]
        )
        assert "<sitemapindex" in response.text
        assert "https://example.com/sitemap1.xml" in response.text


class TestRssMocks:
    """Tests for RSS mock factories."""

    def test_rss_response(self):
        """Test creating an RSS feed response."""
        response = mock_rss_response(
            [
                {"title": "Post 1", "link": "https://example.com/1", "description": "First"},
                {"title": "Post 2", "link": "https://example.com/2", "description": "Second"},
            ]
        )
        assert response.status_code == 200
        assert "<rss" in response.text
        assert "Post 1" in response.text
        assert "https://example.com/1" in response.text
        assert response.headers["content-type"] == "application/rss+xml"


class TestTrafilaturaMocks:
    """Tests for trafilatura mock factories."""

    def test_trafilatura_extract(self):
        """Test mock trafilatura extract."""
        mock = mock_trafilatura_extract("Extracted content here")
        assert mock.return_value == "Extracted content here"

    def test_trafilatura_fetch_url_success(self):
        """Test trafilatura fetch returning HTML."""
        result = mock_trafilatura_fetch_url("<html><body>Test</body></html>")
        assert "<html>" in result

    def test_trafilatura_fetch_url_failure(self):
        """Test trafilatura fetch returning None."""
        result = mock_trafilatura_fetch_url(None)
        assert result is None


class TestPerplexityMocks:
    """Tests for Perplexity API mocks."""

    def test_perplexity_response(self):
        """Test creating a Perplexity API response."""
        response = mock_perplexity_response(
            answer="The answer to your question is...",
            citations=[
                {"url": "https://source1.com", "title": "Source 1"},
                {"url": "https://source2.com", "title": "Source 2"},
            ],
        )
        assert response.status_code == 200
        data = response.json()
        assert "choices" in data
        assert data["choices"][0]["message"]["content"] == "The answer to your question is..."
        assert len(data["citations"]) == 2


class TestRedditMocks:
    """Tests for Reddit API mocks."""

    def test_reddit_posts(self):
        """Test creating Reddit API response."""
        response = mock_reddit_posts(
            [
                {"title": "Test Post", "score": 100, "num_comments": 50},
                {"title": "Another Post", "score": 200, "num_comments": 75},
            ]
        )
        assert response.status_code == 200
        data = response.json()
        assert data["kind"] == "Listing"
        assert len(data["data"]["children"]) == 2
        assert data["data"]["children"][0]["data"]["title"] == "Test Post"
        assert data["data"]["children"][0]["data"]["score"] == 100


class TestHackerNewsMocks:
    """Tests for HackerNews API mocks."""

    def test_hackernews_top_stories(self):
        """Test HackerNews top stories response."""
        response = mock_hackernews_top_stories([12345, 67890, 11111])
        data = response.json()
        assert data == [12345, 67890, 11111]

    def test_hackernews_story(self):
        """Test HackerNews story item response."""
        response = mock_hackernews_story(
            story_id=12345,
            title="Test Story",
            score=150,
            url="https://example.com/story",
        )
        data = response.json()
        assert data["id"] == 12345
        assert data["title"] == "Test Story"
        assert data["score"] == 150
        assert data["url"] == "https://example.com/story"


class TestApifyMocks:
    """Tests for Apify API mocks."""

    def test_apify_twitter_profile(self):
        """Test Twitter profile mock."""
        profile = mock_apify_twitter_profile(
            username="testuser",
            display_name="Test User",
            followers=1000,
            bio="Test bio here",
        )
        assert profile["username"] == "testuser"
        assert profile["displayName"] == "Test User"
        assert profile["followersCount"] == 1000
        assert profile["bio"] == "Test bio here"

    def test_apify_twitter_post(self):
        """Test Twitter post mock."""
        post = mock_apify_twitter_post(
            tweet_id="123456",
            text="This is a test tweet",
            username="testuser",
            likes=100,
            retweets=20,
        )
        assert post["id"] == "123456"
        assert post["text"] == "This is a test tweet"
        assert post["likeCount"] == 100
        assert post["retweetCount"] == 20


class TestPostHogMocks:
    """Tests for PostHog API mocks."""

    def test_posthog_events(self):
        """Test PostHog events response."""
        response = mock_posthog_events(
            [
                {"event": "pageview", "properties": {"$current_url": "/page1"}},
                {"event": "click", "properties": {"element": "button"}},
            ]
        )
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 2
        assert data["results"][0]["event"] == "pageview"


class TestFeedparserMocks:
    """Tests for feedparser mocks."""

    def test_feedparser_parse(self):
        """Test feedparser mock."""
        result = mock_feedparser_parse(
            [
                {"title": "Entry 1", "link": "https://example.com/1", "summary": "Summary 1"},
                {"title": "Entry 2", "link": "https://example.com/2", "summary": "Summary 2"},
            ]
        )
        assert len(result.entries) == 2
        assert result.entries[0].title == "Entry 1"
        assert result.entries[0].link == "https://example.com/1"
        assert not result.bozo  # No parse errors


class TestHtmlMocks:
    """Tests for HTML page mocks."""

    def test_html_page_basic(self):
        """Test basic HTML page mock."""
        html = mock_html_page(
            title="Test Page",
            content="Hello World",
        )
        assert "<title>Test Page</title>" in html
        assert "<h1>Test Page</h1>" in html
        assert "Hello World" in html

    def test_html_page_with_links(self):
        """Test HTML page with links."""
        html = mock_html_page(
            title="Links Page",
            content="Content here",
            links=[
                "https://example.com/1",
                "https://example.com/2",
            ],
        )
        assert 'href="https://example.com/1"' in html
        assert 'href="https://example.com/2"' in html
