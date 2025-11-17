"""Tests for monitoring Signal model."""

from datetime import datetime

from kurt.integrations.research.monitoring.models import Signal


class TestSignal:
    """Test Signal model."""

    def test_signal_init_minimal(self):
        """Test Signal initialization with minimal fields."""
        signal = Signal(
            signal_id="test-123",
            source="reddit",
            title="Test Signal",
            url="https://example.com/test",
        )

        assert signal.signal_id == "test-123"
        assert signal.source == "reddit"
        assert signal.title == "Test Signal"
        assert signal.url == "https://example.com/test"
        assert signal.snippet is None
        assert signal.author is None
        assert signal.score == 0
        assert signal.comment_count == 0
        assert signal.keywords == []
        assert isinstance(signal.timestamp, datetime)

    def test_signal_init_full(self):
        """Test Signal initialization with all fields."""
        timestamp = datetime(2024, 1, 15, 10, 30)
        signal = Signal(
            signal_id="hn_12345",
            source="hackernews",
            title="New AI Tool Released",
            url="https://example.com/ai-tool",
            snippet="This is a description of the new AI tool",
            timestamp=timestamp,
            author="johndoe",
            score=150,
            comment_count=42,
            keywords=["AI", "tool"],
            subreddit="programming",
            domain="example.com",
            project="my-project",
        )

        assert signal.signal_id == "hn_12345"
        assert signal.source == "hackernews"
        assert signal.title == "New AI Tool Released"
        assert signal.url == "https://example.com/ai-tool"
        assert signal.snippet == "This is a description of the new AI tool"
        assert signal.timestamp == timestamp
        assert signal.author == "johndoe"
        assert signal.score == 150
        assert signal.comment_count == 42
        assert signal.keywords == ["AI", "tool"]
        assert signal.subreddit == "programming"
        assert signal.domain == "example.com"
        assert signal.project == "my-project"

    def test_relevance_score_high(self):
        """Test relevance score calculation for high-scoring signal."""
        signal = Signal(
            signal_id="test",
            source="reddit",
            title="Popular Post",
            url="https://example.com",
            score=100,
            comment_count=50,
        )

        # Score normalized to 1.0 (100/100), comments to 1.0 (50/50)
        # (1.0 * 0.7) + (1.0 * 0.3) = 1.0
        assert signal.relevance_score == 1.0

    def test_relevance_score_medium(self):
        """Test relevance score for medium engagement."""
        signal = Signal(
            signal_id="test",
            source="reddit",
            title="Medium Post",
            url="https://example.com",
            score=50,
            comment_count=25,
        )

        # Score: 50/100 = 0.5, Comments: 25/50 = 0.5
        # (0.5 * 0.7) + (0.5 * 0.3) = 0.5
        assert signal.relevance_score == 0.5

    def test_relevance_score_low(self):
        """Test relevance score for low engagement."""
        signal = Signal(
            signal_id="test",
            source="reddit",
            title="Low Post",
            url="https://example.com",
            score=0,
            comment_count=0,
        )

        assert signal.relevance_score == 0.0

    def test_relevance_score_caps_at_one(self):
        """Test that relevance score caps at 1.0 even with very high values."""
        signal = Signal(
            signal_id="test",
            source="reddit",
            title="Viral Post",
            url="https://example.com",
            score=1000,  # Way above cap
            comment_count=500,  # Way above cap
        )

        assert signal.relevance_score == 1.0

    def test_to_dict(self):
        """Test converting signal to dictionary."""
        timestamp = datetime(2024, 1, 15, 10, 30)
        signal = Signal(
            signal_id="test-123",
            source="reddit",
            title="Test Post",
            url="https://example.com",
            timestamp=timestamp,
            score=50,
            comment_count=10,
            keywords=["test"],
        )

        data = signal.to_dict()

        assert data["signal_id"] == "test-123"
        assert data["source"] == "reddit"
        assert data["title"] == "Test Post"
        assert data["url"] == "https://example.com"
        assert data["timestamp"] == "2024-01-15T10:30:00"
        assert data["score"] == 50
        assert data["comment_count"] == 10
        assert data["keywords"] == ["test"]
        assert "relevance_score" in data
        assert isinstance(data["relevance_score"], float)

    def test_from_dict(self):
        """Test creating signal from dictionary."""
        data = {
            "signal_id": "test-456",
            "source": "hackernews",
            "title": "Test Story",
            "url": "https://example.com",
            "timestamp": "2024-01-15T10:30:00",
            "score": 75,
            "comment_count": 20,
            "keywords": ["test"],
            "relevance_score": 0.65,  # Should be ignored
        }

        signal = Signal.from_dict(data)

        assert signal.signal_id == "test-456"
        assert signal.source == "hackernews"
        assert signal.title == "Test Story"
        assert signal.url == "https://example.com"
        assert isinstance(signal.timestamp, datetime)
        assert signal.score == 75
        assert signal.comment_count == 20
        assert signal.keywords == ["test"]

    def test_matches_keywords_single_match(self):
        """Test keyword matching with single keyword."""
        signal = Signal(
            signal_id="test",
            source="reddit",
            title="Building an AI Tool",
            url="https://example.com",
        )

        assert signal.matches_keywords(["AI"])
        assert signal.matches_keywords(["tool"])
        assert signal.matches_keywords(["building"])

    def test_matches_keywords_multiple_match(self):
        """Test keyword matching with multiple keywords."""
        signal = Signal(
            signal_id="test",
            source="reddit",
            title="Python Data Engineering",
            url="https://example.com",
            snippet="Learn about data pipelines with Python",
        )

        assert signal.matches_keywords(["Python", "Engineering"])
        assert signal.matches_keywords(["data"])
        assert signal.matches_keywords(["pipelines"])

    def test_matches_keywords_no_match(self):
        """Test keyword matching with no matches."""
        signal = Signal(
            signal_id="test",
            source="reddit",
            title="JavaScript Tutorial",
            url="https://example.com",
        )

        assert not signal.matches_keywords(["Python"])
        assert not signal.matches_keywords(["Rust", "Go"])

    def test_matches_keywords_empty_list(self):
        """Test that empty keyword list matches everything."""
        signal = Signal(
            signal_id="test",
            source="reddit",
            title="Any Title",
            url="https://example.com",
        )

        assert signal.matches_keywords([])
        assert signal.matches_keywords(None)

    def test_matches_keywords_case_insensitive(self):
        """Test that keyword matching is case-insensitive."""
        signal = Signal(
            signal_id="test",
            source="reddit",
            title="Python Programming",
            url="https://example.com",
        )

        assert signal.matches_keywords(["python"])
        assert signal.matches_keywords(["PYTHON"])
        assert signal.matches_keywords(["PyThOn"])

    def test_matches_keywords_in_snippet(self):
        """Test keyword matching in snippet."""
        signal = Signal(
            signal_id="test",
            source="reddit",
            title="Interesting Post",
            url="https://example.com",
            snippet="This is about Kubernetes deployment strategies",
        )

        assert signal.matches_keywords(["Kubernetes"])
        assert signal.matches_keywords(["deployment"])
        assert not signal.matches_keywords(["Docker"])

    def test_roundtrip_serialization(self):
        """Test that to_dict/from_dict roundtrip works correctly."""
        original = Signal(
            signal_id="test-789",
            source="reddit",
            title="Test Post",
            url="https://example.com",
            snippet="Test snippet",
            timestamp=datetime(2024, 1, 15, 10, 30),
            author="testuser",
            score=100,
            comment_count=25,
            keywords=["test", "example"],
            subreddit="testing",
        )

        # Convert to dict and back
        data = original.to_dict()
        restored = Signal.from_dict(data)

        # Compare key fields
        assert restored.signal_id == original.signal_id
        assert restored.source == original.source
        assert restored.title == original.title
        assert restored.url == original.url
        assert restored.snippet == original.snippet
        assert restored.author == original.author
        assert restored.score == original.score
        assert restored.comment_count == original.comment_count
        assert restored.keywords == original.keywords
        assert restored.subreddit == original.subreddit
