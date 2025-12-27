"""Tests for HackerNews monitoring adapter."""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from kurt.integrations.research.monitoring.hackernews import HackerNewsAdapter
from kurt.integrations.research.monitoring.models import Signal


class TestHackerNewsAdapter:
    """Test HackerNews adapter."""

    def test_init(self):
        """Test adapter initialization."""
        adapter = HackerNewsAdapter()
        assert adapter is not None
        assert adapter.ALGOLIA_URL == "https://hn.algolia.com/api/v1"
        assert adapter.FIREBASE_URL == "https://hacker-news.firebaseio.com/v0"

    @patch("kurt.integrations.research.monitoring.hackernews.requests")
    def test_get_top_stories_basic(self, mock_requests):
        """Test getting top stories without filters."""
        # Mock story IDs response
        mock_ids_response = Mock()
        mock_ids_response.status_code = 200
        mock_ids_response.json.return_value = [123, 456, 789]

        # Mock individual story responses
        mock_story_response = Mock()
        mock_story_response.status_code = 200
        mock_story_response.json.side_effect = [
            {
                "id": 123,
                "type": "story",
                "title": "Test Story 1",
                "url": "https://example.com/1",
                "text": "Story description",
                "time": 1705320600,
                "by": "user1",
                "score": 100,
                "descendants": 50,
            },
            {
                "id": 456,
                "type": "story",
                "title": "Test Story 2",
                "url": "https://example.com/2",
                "time": 1705320700,
                "by": "user2",
                "score": 75,
                "descendants": 30,
            },
            {
                "id": 789,
                "type": "story",
                "title": "Test Story 3",
                "url": "https://example.com/3",
                "time": 1705320800,
                "by": "user3",
                "score": 50,
                "descendants": 20,
            },
        ]

        mock_requests.get.side_effect = [
            mock_ids_response,
            mock_story_response,
            mock_story_response,
            mock_story_response,
        ]

        adapter = HackerNewsAdapter()
        signals = adapter.get_top_stories(limit=3)

        assert len(signals) == 3
        assert all(isinstance(s, Signal) for s in signals)
        assert signals[0].title == "Test Story 1"
        assert signals[0].source == "hackernews"
        assert signals[0].signal_id == "hn_123"
        assert signals[0].score == 100
        assert signals[0].comment_count == 50

    @patch("kurt.integrations.research.monitoring.hackernews.requests")
    def test_get_top_stories_with_keywords(self, mock_requests):
        """Test getting top stories with keyword filter."""
        mock_ids_response = Mock()
        mock_ids_response.status_code = 200
        mock_ids_response.json.return_value = [123, 456]

        mock_story_response = Mock()
        mock_story_response.status_code = 200
        mock_story_response.json.side_effect = [
            {
                "id": 123,
                "type": "story",
                "title": "Python Tutorial for Beginners",
                "url": "https://example.com/python",
                "time": 1705320600,
                "by": "user1",
                "score": 100,
                "descendants": 25,
            },
            {
                "id": 456,
                "type": "story",
                "title": "JavaScript Framework Comparison",
                "url": "https://example.com/js",
                "time": 1705320700,
                "by": "user2",
                "score": 75,
                "descendants": 15,
            },
        ]

        mock_requests.get.side_effect = [
            mock_ids_response,
            mock_story_response,
            mock_story_response,
        ]

        adapter = HackerNewsAdapter()
        signals = adapter.get_top_stories(limit=2, keywords=["Python"])

        # Should only match first story
        assert len(signals) == 1
        assert signals[0].title == "Python Tutorial for Beginners"
        assert "Python" in signals[0].keywords

    @patch("kurt.integrations.research.monitoring.hackernews.requests")
    def test_get_top_stories_with_min_score(self, mock_requests):
        """Test getting top stories with minimum score filter."""
        mock_ids_response = Mock()
        mock_ids_response.status_code = 200
        mock_ids_response.json.return_value = [123, 456, 789]

        mock_story_response = Mock()
        mock_story_response.status_code = 200
        mock_story_response.json.side_effect = [
            {
                "id": 123,
                "type": "story",
                "title": "High Score",
                "url": "https://example.com/1",
                "time": 1705320600,
                "score": 100,
                "descendants": 10,
            },
            {
                "id": 456,
                "type": "story",
                "title": "Medium Score",
                "url": "https://example.com/2",
                "time": 1705320700,
                "score": 50,
                "descendants": 5,
            },
            {
                "id": 789,
                "type": "story",
                "title": "Low Score",
                "url": "https://example.com/3",
                "time": 1705320800,
                "score": 10,
                "descendants": 2,
            },
        ]

        mock_requests.get.side_effect = [
            mock_ids_response,
            mock_story_response,
            mock_story_response,
            mock_story_response,
        ]

        adapter = HackerNewsAdapter()
        signals = adapter.get_top_stories(limit=3, min_score=40)

        # Should only get stories with score >= 40
        assert len(signals) == 2
        assert signals[0].score >= 40
        assert signals[1].score >= 40

    @patch("kurt.integrations.research.monitoring.hackernews.requests")
    def test_get_top_stories_skips_non_stories(self, mock_requests):
        """Test that non-story items are skipped."""
        mock_ids_response = Mock()
        mock_ids_response.status_code = 200
        mock_ids_response.json.return_value = [123, 456]

        mock_story_response = Mock()
        mock_story_response.status_code = 200
        mock_story_response.json.side_effect = [
            {"id": 123, "type": "comment", "title": "This is a comment"},  # Should skip
            {
                "id": 456,
                "type": "story",
                "title": "Real Story",
                "url": "https://example.com",
                "time": 1705320700,
                "score": 50,
                "descendants": 10,
            },
        ]

        mock_requests.get.side_effect = [
            mock_ids_response,
            mock_story_response,
            mock_story_response,
        ]

        adapter = HackerNewsAdapter()
        signals = adapter.get_top_stories(limit=2)

        assert len(signals) == 1
        assert signals[0].title == "Real Story"

    @patch("kurt.integrations.research.monitoring.hackernews.requests")
    def test_get_top_stories_handles_missing_url(self, mock_requests):
        """Test that stories without URL use HN link."""
        mock_ids_response = Mock()
        mock_ids_response.status_code = 200
        mock_ids_response.json.return_value = [123]

        mock_story_response = Mock()
        mock_story_response.status_code = 200
        mock_story_response.json.return_value = {
            "id": 123,
            "type": "story",
            "title": "Ask HN: Question",
            # No URL - should use HN link
            "time": 1705320600,
            "score": 50,
            "descendants": 25,
        }

        mock_requests.get.side_effect = [mock_ids_response, mock_story_response]

        adapter = HackerNewsAdapter()
        signals = adapter.get_top_stories(limit=1)

        assert len(signals) == 1
        assert signals[0].url == "https://news.ycombinator.com/item?id=123"

    @patch("kurt.integrations.research.monitoring.hackernews.requests")
    def test_search_basic(self, mock_requests):
        """Test basic search functionality."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": [
                {
                    "objectID": "12345",
                    "title": "Kubernetes Tutorial",
                    "url": "https://example.com/k8s",
                    "story_text": "Learn Kubernetes from scratch",
                    "created_at_i": 1705320600,
                    "author": "user1",
                    "points": 150,
                    "num_comments": 45,
                },
                {
                    "objectID": "67890",
                    "title": "Docker vs Kubernetes",
                    "url": "https://example.com/docker-k8s",
                    "created_at_i": 1705320700,
                    "author": "user2",
                    "points": 100,
                    "num_comments": 30,
                },
            ]
        }

        mock_requests.get.return_value = mock_response

        adapter = HackerNewsAdapter()
        signals = adapter.search("Kubernetes")

        assert len(signals) == 2
        assert signals[0].title == "Kubernetes Tutorial"
        assert signals[0].source == "hackernews"
        assert signals[0].signal_id == "hn_12345"
        assert signals[0].keywords == ["Kubernetes"]

    @patch("kurt.integrations.research.monitoring.hackernews.requests")
    def test_search_with_timeframe(self, mock_requests):
        """Test search with time filter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"hits": []}

        mock_requests.get.return_value = mock_response

        adapter = HackerNewsAdapter()
        adapter.search("test", timeframe="day")

        # Verify time filter was applied
        call_args = mock_requests.get.call_args
        assert "numericFilters" in call_args[1]["params"]
        assert "created_at_i>" in call_args[1]["params"]["numericFilters"]

    @patch("kurt.integrations.research.monitoring.hackernews.requests")
    def test_search_sort_by_date(self, mock_requests):
        """Test search with date sorting."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"hits": []}

        mock_requests.get.return_value = mock_response

        adapter = HackerNewsAdapter()
        adapter.search("test", sort="date")

        # Should use search_by_date endpoint
        call_args = mock_requests.get.call_args
        assert "search_by_date" in call_args[0][0]

    @patch("kurt.integrations.research.monitoring.hackernews.requests")
    def test_search_with_min_score(self, mock_requests):
        """Test search with minimum score filter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": [
                {
                    "objectID": "123",
                    "title": "High Score",
                    "url": "https://example.com/1",
                    "created_at_i": 1705320600,
                    "points": 100,
                    "num_comments": 20,
                },
                {
                    "objectID": "456",
                    "title": "Low Score",
                    "url": "https://example.com/2",
                    "created_at_i": 1705320700,
                    "points": 5,
                    "num_comments": 2,
                },
            ]
        }

        mock_requests.get.return_value = mock_response

        adapter = HackerNewsAdapter()
        signals = adapter.search("test", min_score=50)

        # Should only return high-scoring story
        assert len(signals) == 1
        assert signals[0].score >= 50

    @patch("kurt.integrations.research.monitoring.hackernews.requests")
    def test_search_request_error(self, mock_requests):
        """Test handling of request errors."""
        import requests as real_requests

        mock_requests.RequestException = real_requests.RequestException
        mock_requests.get.side_effect = real_requests.RequestException("Network error")

        adapter = HackerNewsAdapter()
        with pytest.raises(Exception, match="Failed to search Hacker News"):
            adapter.search("test")

    @patch("kurt.integrations.research.monitoring.hackernews.requests")
    def test_get_recent_basic(self, mock_requests):
        """Test getting recent stories."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": [
                {
                    "objectID": "123",
                    "title": "Recent Story",
                    "url": "https://example.com/recent",
                    "created_at_i": int(datetime.now().timestamp()),
                    "points": 50,
                    "num_comments": 15,
                }
            ]
        }

        mock_requests.get.return_value = mock_response

        adapter = HackerNewsAdapter()
        signals = adapter.get_recent(hours=24, min_score=10)

        assert len(signals) == 1
        assert signals[0].title == "Recent Story"

    @patch("kurt.integrations.research.monitoring.hackernews.requests")
    def test_get_recent_with_keywords(self, mock_requests):
        """Test getting recent stories with keyword filter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": [
                {
                    "objectID": "123",
                    "title": "Python Tutorial",
                    "url": "https://example.com/1",
                    "created_at_i": int(datetime.now().timestamp()),
                    "points": 50,
                    "num_comments": 10,
                },
                {
                    "objectID": "456",
                    "title": "JavaScript Guide",
                    "url": "https://example.com/2",
                    "created_at_i": int(datetime.now().timestamp()),
                    "points": 40,
                    "num_comments": 8,
                },
            ]
        }

        mock_requests.get.return_value = mock_response

        adapter = HackerNewsAdapter()
        signals = adapter.get_recent(hours=24, keywords=["Python"], min_score=10)

        # Should only match Python story
        assert len(signals) == 1
        assert signals[0].title == "Python Tutorial"
        assert "Python" in signals[0].keywords

    @patch("kurt.integrations.research.monitoring.hackernews.requests")
    def test_get_recent_sorted_by_relevance(self, mock_requests):
        """Test that results are sorted by relevance score."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": [
                {
                    "objectID": "123",
                    "title": "Low Engagement",
                    "url": "https://example.com/1",
                    "created_at_i": int(datetime.now().timestamp()),
                    "points": 10,
                    "num_comments": 2,
                },
                {
                    "objectID": "456",
                    "title": "High Engagement",
                    "url": "https://example.com/2",
                    "created_at_i": int(datetime.now().timestamp()),
                    "points": 100,
                    "num_comments": 50,
                },
            ]
        }

        mock_requests.get.return_value = mock_response

        adapter = HackerNewsAdapter()
        signals = adapter.get_recent(hours=24, min_score=10)

        # Should be sorted by relevance (high engagement first)
        assert len(signals) == 2
        assert signals[0].title == "High Engagement"
        assert signals[1].title == "Low Engagement"
