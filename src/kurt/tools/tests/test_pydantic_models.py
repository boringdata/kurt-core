"""Tests for Pydantic models (Phase 3)."""

import pytest
from datetime import datetime

from kurt.tools.map.core.models import (
    DocMetadata,
    DocContent,
    ProfileMetadata,
    ProfileContent,
    PostMetadata,
    PostContent,
)


class TestDocMetadata:
    """Test DocMetadata model."""

    def test_doc_metadata_required_fields(self):
        """Test required fields."""
        meta = DocMetadata(url="https://example.com")
        assert meta.url == "https://example.com"
        assert meta.depth == 0

    def test_doc_metadata_full(self):
        """Test with all fields."""
        meta = DocMetadata(
            url="https://example.com/page",
            title="Example Page",
            description="A test page",
            language="en",
            discovered_from="https://example.com",
            depth=2,
        )
        assert meta.title == "Example Page"
        assert meta.depth == 2

    def test_doc_metadata_depth_validation(self):
        """Test depth validation."""
        with pytest.raises(ValueError):
            DocMetadata(url="https://example.com", depth=-1)


class TestDocContent:
    """Test DocContent model."""

    def test_doc_content_basic(self):
        """Test basic document content."""
        content = DocContent(
            url="https://example.com",
            content_text="Sample content text",
        )
        assert content.word_count == 0
        assert content.links == []

    def test_doc_content_with_links(self):
        """Test document with links."""
        content = DocContent(
            url="https://example.com",
            content_text="Content with links",
            links=["https://example.com/page1", "https://example.com/page2"],
            word_count=3,
        )
        assert len(content.links) == 2
        assert content.word_count == 3

    def test_doc_content_with_html(self):
        """Test document with HTML."""
        content = DocContent(
            url="https://example.com",
            content_text="Text",
            content_html="<p>Text</p>",
            content_path="content/page.md",
        )
        assert content.content_html is not None
        assert content.content_path == "content/page.md"


class TestProfileMetadata:
    """Test ProfileMetadata model."""

    def test_profile_metadata_required(self):
        """Test required fields."""
        meta = ProfileMetadata(
            platform="twitter",
            username="testuser",
            url="https://twitter.com/testuser",
        )
        assert meta.platform == "twitter"
        assert meta.username == "testuser"

    def test_profile_metadata_full(self):
        """Test with all fields."""
        meta = ProfileMetadata(
            platform="linkedin",
            username="john.doe",
            display_name="John Doe",
            bio="Software engineer",
            url="https://linkedin.com/in/john.doe",
            verified=True,
            avatar_url="https://example.com/avatar.jpg",
        )
        assert meta.verified is True
        assert meta.avatar_url is not None


class TestProfileContent:
    """Test ProfileContent model."""

    def test_profile_content_basic(self):
        """Test basic profile content."""
        content = ProfileContent(
            url="https://twitter.com/testuser",
            platform="twitter",
            username="testuser",
        )
        assert content.followers_count == 0
        assert content.verified is False

    def test_profile_content_with_metrics(self):
        """Test profile with metrics."""
        content = ProfileContent(
            url="https://linkedin.com/in/john",
            platform="linkedin",
            username="john",
            display_name="John",
            followers_count=1500,
            following_count=300,
            posts_count=50,
            verified=True,
        )
        assert content.followers_count == 1500
        assert content.posts_count == 50

    def test_profile_content_timestamps(self):
        """Test profile with timestamps."""
        joined = datetime(2020, 1, 15)
        content = ProfileContent(
            url="https://twitter.com/user",
            platform="twitter",
            username="user",
            joined_date=joined,
        )
        assert content.joined_date == joined

    def test_profile_content_metadata(self):
        """Test profile with raw metadata."""
        metadata = {"connections": 5000, "api_version": "v2"}
        content = ProfileContent(
            url="https://linkedin.com/in/user",
            platform="linkedin",
            username="user",
            raw_metadata=metadata,
        )
        assert content.raw_metadata == metadata


class TestPostMetadata:
    """Test PostMetadata model."""

    def test_post_metadata_required(self):
        """Test required fields."""
        pub_date = datetime(2024, 1, 29, 10, 30)
        meta = PostMetadata(
            platform="twitter",
            post_id="1234567890",
            published_at=pub_date,
            url="https://twitter.com/user/status/1234567890",
        )
        assert meta.post_id == "1234567890"
        assert meta.published_at == pub_date

    def test_post_metadata_with_profile(self):
        """Test post metadata with author profile."""
        meta = PostMetadata(
            platform="twitter",
            post_id="post_123",
            profile_id="user_456",
            published_at=datetime.now(),
            url="https://twitter.com/user/status/post_123",
        )
        assert meta.profile_id == "user_456"


class TestPostContent:
    """Test PostContent model."""

    def test_post_content_basic(self):
        """Test basic post content."""
        post = PostContent(
            url="https://twitter.com/user/status/123",
            platform="twitter",
            post_id="123",
            published_at=datetime.now(),
        )
        assert post.likes_count == 0
        assert post.content_text == ""

    def test_post_content_with_text(self):
        """Test post with text content."""
        post = PostContent(
            url="https://twitter.com/user/status/123",
            platform="twitter",
            post_id="123",
            author_name="Test User",
            author_username="testuser",
            content_text="This is a test post",
            published_at=datetime.now(),
        )
        assert post.content_text == "This is a test post"
        assert post.author_name == "Test User"

    def test_post_content_with_engagement(self):
        """Test post with engagement metrics."""
        post = PostContent(
            url="https://twitter.com/user/status/123",
            platform="twitter",
            post_id="123",
            content_text="Popular post",
            likes_count=5000,
            shares_count=1000,
            comments_count=500,
            replies_count=200,
            published_at=datetime.now(),
        )
        assert post.likes_count == 5000
        assert post.shares_count == 1000

    def test_post_content_with_media(self):
        """Test post with media."""
        post = PostContent(
            url="https://twitter.com/user/status/123",
            platform="twitter",
            post_id="123",
            content_text="Post with images",
            media_urls=["https://example.com/img1.jpg", "https://example.com/img2.jpg"],
            published_at=datetime.now(),
        )
        assert len(post.media_urls) == 2

    def test_post_content_with_tags(self):
        """Test post with hashtags and mentions."""
        post = PostContent(
            url="https://twitter.com/user/status/123",
            platform="twitter",
            post_id="123",
            content_text="Post with #hashtag @mention",
            hashtags=["hashtag", "trending"],
            mentions=["mention"],
            published_at=datetime.now(),
        )
        assert len(post.hashtags) == 2
        assert "mention" in post.mentions

    def test_post_content_with_timestamps(self):
        """Test post with publication and edit timestamps."""
        pub = datetime(2024, 1, 29, 10, 0)
        edited = datetime(2024, 1, 29, 11, 0)
        post = PostContent(
            url="https://twitter.com/user/status/123",
            platform="twitter",
            post_id="123",
            content_text="Edited post",
            published_at=pub,
            edited_at=edited,
        )
        assert post.published_at == pub
        assert post.edited_at == edited

    def test_post_content_full(self):
        """Test post with all fields."""
        pub = datetime(2024, 1, 29, 10, 0)
        post = PostContent(
            url="https://linkedin.com/feed/update/123",
            platform="linkedin",
            post_id="123",
            profile_id="user_456",
            author_name="John Doe",
            author_username="john.doe",
            content_text="Career announcement",
            content_html="<p>Career announcement</p>",
            media_urls=["https://example.com/img.jpg"],
            likes_count=250,
            shares_count=45,
            comments_count=32,
            replies_count=10,
            published_at=pub,
            hashtags=["hiring", "startup"],
            mentions=["company"],
            raw_metadata={"engagement_rate": 0.85},
        )
        assert post.platform == "linkedin"
        assert post.likes_count == 250
        assert len(post.hashtags) == 2


class TestModelValidation:
    """Test model validation."""

    def test_doc_metadata_invalid_depth(self):
        """Test invalid depth validation."""
        with pytest.raises(ValueError):
            DocMetadata(url="https://example.com", depth=-5)

    def test_profile_content_invalid_counts(self):
        """Test invalid count validation."""
        with pytest.raises(ValueError):
            ProfileContent(
                url="https://twitter.com/user",
                platform="twitter",
                username="user",
                followers_count=-1,
            )

    def test_post_content_invalid_counts(self):
        """Test post invalid count validation."""
        with pytest.raises(ValueError):
            PostContent(
                url="https://twitter.com/user/status/123",
                platform="twitter",
                post_id="123",
                likes_count=-10,
                published_at=datetime.now(),
            )


class TestModelSerialization:
    """Test model serialization."""

    def test_profile_content_to_dict(self):
        """Test converting profile to dict."""
        content = ProfileContent(
            url="https://twitter.com/user",
            platform="twitter",
            username="user",
            display_name="User Name",
        )
        data = content.model_dump()
        assert data["platform"] == "twitter"
        assert data["display_name"] == "User Name"

    def test_post_content_json_serializable(self):
        """Test post content is JSON serializable."""
        post = PostContent(
            url="https://twitter.com/user/status/123",
            platform="twitter",
            post_id="123",
            content_text="Test",
            published_at=datetime(2024, 1, 29, 10, 0),
        )
        json_str = post.model_dump_json()
        assert "twitter" in json_str
        assert "Test" in json_str
