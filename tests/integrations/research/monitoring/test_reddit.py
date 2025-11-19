"""Tests for Reddit monitoring adapter."""

from unittest.mock import Mock, patch

import pytest

from kurt.integrations.research.monitoring.models import Signal
from kurt.integrations.research.monitoring.reddit import RedditAdapter


class TestRedditAdapter:
    """Test Reddit adapter."""

    def test_init(self):
        """Test adapter initialization."""
        adapter = RedditAdapter()
        assert adapter is not None
        assert adapter.BASE_URL == "https://reddit.com"
        assert "User-Agent" in adapter.headers
        assert "Kurt" in adapter.headers["User-Agent"]

    @patch("kurt.integrations.research.monitoring.reddit.requests")
    def test_get_subreddit_posts_basic(self, mock_requests):
        """Test getting subreddit posts without filters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "id": "abc123",
                            "title": "Test Post 1",
                            "permalink": "/r/test/comments/abc123/test_post_1/",
                            "selftext": "This is the post content",
                            "created_utc": 1705320600,
                            "author": "user1",
                            "score": 100,
                            "num_comments": 25,
                        }
                    },
                    {
                        "data": {
                            "id": "def456",
                            "title": "Test Post 2",
                            "permalink": "/r/test/comments/def456/test_post_2/",
                            "created_utc": 1705320700,
                            "author": "user2",
                            "score": 75,
                            "num_comments": 15,
                        }
                    },
                ]
            }
        }

        mock_requests.get.return_value = mock_response

        adapter = RedditAdapter()
        signals = adapter.get_subreddit_posts("test")

        assert len(signals) == 2
        assert all(isinstance(s, Signal) for s in signals)
        assert signals[0].title == "Test Post 1"
        assert signals[0].source == "reddit"
        assert signals[0].signal_id == "reddit_abc123"
        assert signals[0].subreddit == "test"
        assert signals[0].score == 100
        assert signals[0].comment_count == 25

    @patch("kurt.integrations.research.monitoring.reddit.requests")
    def test_get_subreddit_posts_with_keywords(self, mock_requests):
        """Test getting posts with keyword filter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "id": "abc123",
                            "title": "Python Tutorial for Beginners",
                            "permalink": "/r/programming/comments/abc123/",
                            "selftext": "Learn Python basics",
                            "created_utc": 1705320600,
                            "score": 100,
                            "num_comments": 20,
                        }
                    },
                    {
                        "data": {
                            "id": "def456",
                            "title": "JavaScript Framework Guide",
                            "permalink": "/r/programming/comments/def456/",
                            "created_utc": 1705320700,
                            "score": 75,
                            "num_comments": 15,
                        }
                    },
                ]
            }
        }

        mock_requests.get.return_value = mock_response

        adapter = RedditAdapter()
        signals = adapter.get_subreddit_posts("programming", keywords=["Python"])

        # Should only match first post
        assert len(signals) == 1
        assert signals[0].title == "Python Tutorial for Beginners"
        assert "Python" in signals[0].keywords

    @patch("kurt.integrations.research.monitoring.reddit.requests")
    def test_get_subreddit_posts_with_min_score(self, mock_requests):
        """Test getting posts with minimum score filter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "id": "abc",
                            "title": "High Score",
                            "permalink": "/r/test/comments/abc/",
                            "created_utc": 1705320600,
                            "score": 100,
                            "num_comments": 10,
                        }
                    },
                    {
                        "data": {
                            "id": "def",
                            "title": "Medium Score",
                            "permalink": "/r/test/comments/def/",
                            "created_utc": 1705320700,
                            "score": 50,
                            "num_comments": 5,
                        }
                    },
                    {
                        "data": {
                            "id": "ghi",
                            "title": "Low Score",
                            "permalink": "/r/test/comments/ghi/",
                            "created_utc": 1705320800,
                            "score": 5,
                            "num_comments": 2,
                        }
                    },
                ]
            }
        }

        mock_requests.get.return_value = mock_response

        adapter = RedditAdapter()
        signals = adapter.get_subreddit_posts("test", min_score=40)

        # Should only get posts with score >= 40
        assert len(signals) == 2
        assert all(s.score >= 40 for s in signals)

    @patch("kurt.integrations.research.monitoring.reddit.requests")
    def test_get_subreddit_posts_sort_options(self, mock_requests):
        """Test different sort options."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"children": []}}

        mock_requests.get.return_value = mock_response

        adapter = RedditAdapter()

        # Test different sort options
        for sort in ["hot", "new", "top", "rising"]:
            adapter.get_subreddit_posts("test", sort=sort)
            call_args = mock_requests.get.call_args
            assert f"/{sort}.json" in call_args[0][0]

    @patch("kurt.integrations.research.monitoring.reddit.requests")
    def test_get_subreddit_posts_timeframe(self, mock_requests):
        """Test timeframe parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"children": []}}

        mock_requests.get.return_value = mock_response

        adapter = RedditAdapter()
        adapter.get_subreddit_posts("test", timeframe="week")

        call_args = mock_requests.get.call_args
        assert call_args[1]["params"]["t"] == "week"

    @patch("kurt.integrations.research.monitoring.reddit.requests")
    def test_get_subreddit_posts_limit(self, mock_requests):
        """Test limit parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"children": []}}

        mock_requests.get.return_value = mock_response

        adapter = RedditAdapter()
        adapter.get_subreddit_posts("test", limit=50)

        call_args = mock_requests.get.call_args
        assert call_args[1]["params"]["limit"] == 50

    @patch("kurt.integrations.research.monitoring.reddit.requests")
    def test_get_subreddit_posts_limit_caps_at_100(self, mock_requests):
        """Test that limit is capped at 100."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"children": []}}

        mock_requests.get.return_value = mock_response

        adapter = RedditAdapter()
        adapter.get_subreddit_posts("test", limit=200)

        call_args = mock_requests.get.call_args
        assert call_args[1]["params"]["limit"] == 100

    @patch("kurt.integrations.research.monitoring.reddit.requests")
    def test_get_subreddit_posts_request_error(self, mock_requests):
        """Test handling of request errors."""
        import requests as real_requests

        mock_requests.RequestException = real_requests.RequestException
        mock_requests.get.side_effect = real_requests.RequestException("Network error")

        adapter = RedditAdapter()
        with pytest.raises(Exception, match="Failed to fetch Reddit data"):
            adapter.get_subreddit_posts("test")

    @patch("kurt.integrations.research.monitoring.reddit.requests")
    def test_get_multi_subreddit_posts(self, mock_requests):
        """Test getting posts from multiple subreddits."""
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "id": "abc",
                            "title": "Post from r/python",
                            "permalink": "/r/python/comments/abc/",
                            "created_utc": 1705320600,
                            "score": 100,
                            "num_comments": 20,
                        }
                    }
                ]
            }
        }

        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "id": "def",
                            "title": "Post from r/programming",
                            "permalink": "/r/programming/comments/def/",
                            "created_utc": 1705320700,
                            "score": 75,
                            "num_comments": 15,
                        }
                    }
                ]
            }
        }

        mock_requests.get.side_effect = [mock_response1, mock_response2]

        adapter = RedditAdapter()
        signals = adapter.get_multi_subreddit_posts(["python", "programming"])

        assert len(signals) == 2
        # Should be sorted by relevance score
        assert signals[0].score >= signals[1].score

    @patch("kurt.integrations.research.monitoring.reddit.requests")
    def test_get_multi_subreddit_posts_handles_errors(self, mock_requests):
        """Test that errors in one subreddit don't stop others."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "id": "abc",
                            "title": "Successful Post",
                            "permalink": "/r/test/comments/abc/",
                            "created_utc": 1705320600,
                            "score": 50,
                            "num_comments": 10,
                        }
                    }
                ]
            }
        }

        # First fails, second succeeds
        mock_requests.get.side_effect = [Exception("Network error"), mock_response]

        adapter = RedditAdapter()
        signals = adapter.get_multi_subreddit_posts(["failing", "working"])

        # Should still get results from working subreddit
        assert len(signals) == 1
        assert signals[0].title == "Successful Post"

    @patch("kurt.integrations.research.monitoring.reddit.requests")
    def test_search_subreddit_basic(self, mock_requests):
        """Test searching within a subreddit."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "id": "abc123",
                            "title": "Kubernetes Tutorial",
                            "permalink": "/r/devops/comments/abc123/",
                            "selftext": "Learn Kubernetes basics",
                            "created_utc": 1705320600,
                            "score": 150,
                            "num_comments": 45,
                        }
                    }
                ]
            }
        }

        mock_requests.get.return_value = mock_response

        adapter = RedditAdapter()
        signals = adapter.search_subreddit("devops", "Kubernetes")

        assert len(signals) == 1
        assert signals[0].title == "Kubernetes Tutorial"
        assert signals[0].keywords == ["Kubernetes"]

    @patch("kurt.integrations.research.monitoring.reddit.requests")
    def test_search_subreddit_parameters(self, mock_requests):
        """Test search parameters are passed correctly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"children": []}}

        mock_requests.get.return_value = mock_response

        adapter = RedditAdapter()
        adapter.search_subreddit(
            "test",
            "query",
            timeframe="month",
            sort="top",
            limit=50,
        )

        call_args = mock_requests.get.call_args
        params = call_args[1]["params"]

        assert params["q"] == "query"
        assert params["restrict_sr"] == "on"
        assert params["sort"] == "top"
        assert params["t"] == "month"
        assert params["limit"] == 50

    @patch("kurt.integrations.research.monitoring.reddit.requests")
    def test_get_subreddit_posts_keyword_in_snippet(self, mock_requests):
        """Test keyword matching in post snippet."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "id": "abc",
                            "title": "Generic Title",
                            "permalink": "/r/test/comments/abc/",
                            "selftext": "This post is all about Kubernetes deployment",
                            "created_utc": 1705320600,
                            "score": 50,
                            "num_comments": 10,
                        }
                    }
                ]
            }
        }

        mock_requests.get.return_value = mock_response

        adapter = RedditAdapter()
        signals = adapter.get_subreddit_posts("test", keywords=["Kubernetes"])

        assert len(signals) == 1
        assert "Kubernetes" in signals[0].keywords

    @patch("kurt.integrations.research.monitoring.reddit.requests")
    def test_get_subreddit_posts_handles_missing_selftext(self, mock_requests):
        """Test handling posts without selftext (link posts)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "id": "abc",
                            "title": "Link Post",
                            "permalink": "/r/test/comments/abc/",
                            # No selftext
                            "created_utc": 1705320600,
                            "score": 50,
                            "num_comments": 10,
                        }
                    }
                ]
            }
        }

        mock_requests.get.return_value = mock_response

        adapter = RedditAdapter()
        signals = adapter.get_subreddit_posts("test")

        assert len(signals) == 1
        assert signals[0].snippet is None
