"""Tests for Phase 1 database schema models."""

import pytest
from datetime import datetime

from kurt.tools.map.models import DocType as MapDocType
from kurt.tools.map.models import MapDocument, MapStatus
from kurt.tools.fetch.models import DocType as FetchDocType
from kurt.tools.fetch.models import FetchDocument, FetchStatus, Profile, Post


class TestMapDocument:
    """Test MapDocument model with new columns."""

    def test_map_document_creation_with_defaults(self):
        """Test creating MapDocument with default values."""
        doc = MapDocument(
            document_id="test_123",
            source_url="https://example.com",
        )
        assert doc.document_id == "test_123"
        assert doc.source_url == "https://example.com"
        assert doc.doc_type == MapDocType.DOC
        assert doc.platform is None
        assert doc.status == MapStatus.SUCCESS

    def test_map_document_with_doc_type_profile(self):
        """Test MapDocument with profile type."""
        doc = MapDocument(
            document_id="profile_123",
            source_url="https://twitter.com/example",
            doc_type=MapDocType.PROFILE,
            platform="twitter",
        )
        assert doc.doc_type == MapDocType.PROFILE
        assert doc.platform == "twitter"

    def test_map_document_with_doc_type_posts(self):
        """Test MapDocument with posts type."""
        doc = MapDocument(
            document_id="posts_123",
            source_url="https://linkedin.com/posts/example",
            doc_type=MapDocType.POSTS,
            platform="linkedin",
        )
        assert doc.doc_type == MapDocType.POSTS
        assert doc.platform == "linkedin"

    def test_map_document_doc_type_enum_values(self):
        """Test MapDocType enum values."""
        assert MapDocType.DOC.value == "doc"
        assert MapDocType.PROFILE.value == "profile"
        assert MapDocType.POSTS.value == "posts"

    def test_map_document_with_metadata(self):
        """Test MapDocument with metadata."""
        metadata = {"discovered_links": 42, "depth": 2}
        doc = MapDocument(
            document_id="test_123",
            source_url="https://example.com",
            metadata_json=metadata,
        )
        assert doc.metadata_json == metadata


class TestFetchDocument:
    """Test FetchDocument model with new columns."""

    def test_fetch_document_creation_with_defaults(self):
        """Test creating FetchDocument with default values."""
        doc = FetchDocument(
            document_id="test_123",
        )
        assert doc.document_id == "test_123"
        assert doc.doc_type == FetchDocType.DOC
        assert doc.platform is None
        assert doc.status == FetchStatus.PENDING

    def test_fetch_document_with_doc_type_profile(self):
        """Test FetchDocument with profile type."""
        doc = FetchDocument(
            document_id="profile_123",
            doc_type=FetchDocType.PROFILE,
            platform="twitter",
            status=FetchStatus.SUCCESS,
        )
        assert doc.doc_type == FetchDocType.PROFILE
        assert doc.platform == "twitter"

    def test_fetch_document_with_doc_type_posts(self):
        """Test FetchDocument with posts type."""
        doc = FetchDocument(
            document_id="posts_123",
            doc_type=FetchDocType.POSTS,
            platform="linkedin",
        )
        assert doc.doc_type == FetchDocType.POSTS
        assert doc.platform == "linkedin"

    def test_fetch_document_doc_type_enum_values(self):
        """Test FetchDocType enum values."""
        assert FetchDocType.DOC.value == "doc"
        assert FetchDocType.PROFILE.value == "profile"
        assert FetchDocType.POSTS.value == "posts"

    def test_fetch_document_with_content(self):
        """Test FetchDocument with content info."""
        doc = FetchDocument(
            document_id="test_123",
            content_length=5000,
            content_hash="abc123",
            content_path="content/test.md",
            fetch_engine="trafilatura",
        )
        assert doc.content_length == 5000
        assert doc.content_hash == "abc123"
        assert doc.content_path == "content/test.md"
        assert doc.fetch_engine == "trafilatura"


class TestProfile:
    """Test Profile model."""

    def test_profile_creation_with_defaults(self):
        """Test creating Profile with defaults."""
        profile = Profile(
            platform="twitter",
            platform_id="123456",
            username="testuser",
        )
        assert profile.platform == "twitter"
        assert profile.platform_id == "123456"
        assert profile.username == "testuser"
        assert profile.followers_count == 0
        assert profile.following_count == 0
        assert profile.verified is False

    def test_profile_full_creation(self):
        """Test creating Profile with all fields."""
        profile = Profile(
            platform="linkedin",
            platform_id="abc123",
            username="john.doe",
            display_name="John Doe",
            bio="Software engineer",
            followers_count=1500,
            following_count=300,
            posts_count=45,
            profile_url="https://linkedin.com/in/john.doe",
            avatar_url="https://example.com/avatar.jpg",
            verified=True,
            raw_metadata={"connections": 5000},
        )
        assert profile.platform == "linkedin"
        assert profile.display_name == "John Doe"
        assert profile.bio == "Software engineer"
        assert profile.followers_count == 1500
        assert profile.verified is True
        assert profile.raw_metadata == {"connections": 5000}

    def test_profile_twitter_example(self):
        """Test Profile with Twitter data."""
        profile = Profile(
            platform="twitter",
            platform_id="987654321",
            username="techstartup",
            display_name="Tech Startup Inc",
            followers_count=50000,
            posts_count=1200,
            verified=True,
        )
        assert profile.platform == "twitter"
        assert profile.followers_count == 50000
        assert profile.verified is True

    def test_profile_metadata_json(self):
        """Test Profile raw metadata field."""
        metadata = {
            "last_updated": "2024-01-29",
            "data_source": "apify",
            "api_version": "v2",
        }
        profile = Profile(
            platform="twitter",
            platform_id="123",
            username="user",
            raw_metadata=metadata,
        )
        assert profile.raw_metadata == metadata


class TestPost:
    """Test Post model."""

    def test_post_creation_with_defaults(self):
        """Test creating Post with defaults."""
        post = Post(
            platform="twitter",
            platform_id="post_123",
        )
        assert post.platform == "twitter"
        assert post.platform_id == "post_123"
        assert post.likes_count == 0
        assert post.shares_count == 0
        assert post.comments_count == 0

    def test_post_full_creation(self):
        """Test creating Post with all fields."""
        post = Post(
            platform="linkedin",
            platform_id="post_456",
            profile_id=1,
            content_text="Check out our new product!",
            content_html="<p>Check out our new product!</p>",
            media_urls=["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
            likes_count=250,
            shares_count=45,
            comments_count=32,
            published_at="2024-01-29T10:30:00Z",
            raw_metadata={"engagement_rate": 0.85},
        )
        assert post.platform == "linkedin"
        assert post.profile_id == 1
        assert post.content_text == "Check out our new product!"
        assert post.likes_count == 250
        assert post.shares_count == 45
        assert len(post.media_urls) == 2

    def test_post_twitter_example(self):
        """Test Post with Twitter data."""
        post = Post(
            platform="twitter",
            platform_id="1234567890",
            profile_id=2,
            content_text="Excited to announce our Series A funding!",
            likes_count=5000,
            comments_count=800,
            shares_count=2100,
            published_at="2024-01-28T15:45:00Z",
        )
        assert post.platform == "twitter"
        assert post.likes_count == 5000
        assert post.comments_count == 800

    def test_post_with_media(self):
        """Test Post with media URLs."""
        media = [
            "https://pbs.twimg.com/media/example1.jpg",
            "https://pbs.twimg.com/media/example2.jpg",
        ]
        post = Post(
            platform="twitter",
            platform_id="post_789",
            content_text="Multi-media post",
            media_urls=media,
        )
        assert post.media_urls == media
        assert len(post.media_urls) == 2

    def test_post_metadata(self):
        """Test Post raw metadata field."""
        metadata = {
            "reply_count": 100,
            "retweet_count": 500,
            "language": "en",
        }
        post = Post(
            platform="twitter",
            platform_id="post_123",
            raw_metadata=metadata,
        )
        assert post.raw_metadata == metadata


class TestModelIntegration:
    """Test integration between related models."""

    def test_map_and_fetch_doc_types_match(self):
        """Test that doc types are consistent across models."""
        map_doc_types = {MapDocType.DOC, MapDocType.PROFILE, MapDocType.POSTS}
        fetch_doc_types = {FetchDocType.DOC, FetchDocType.PROFILE, FetchDocType.POSTS}

        # Should have same values
        map_values = {dt.value for dt in map_doc_types}
        fetch_values = {dt.value for dt in fetch_doc_types}
        assert map_values == fetch_values

    def test_profile_post_relationship(self):
        """Test Profile-Post relationship (profile_id FK)."""
        profile = Profile(
            platform="twitter",
            platform_id="user_123",
            username="testuser",
        )

        post = Post(
            platform="twitter",
            platform_id="post_456",
            profile_id=profile.id,  # Would be set by DB
            content_text="Test post",
        )

        # profile_id can reference profiles.id
        assert post.profile_id == profile.id

    def test_multi_platform_documents(self):
        """Test creating documents for multiple platforms."""
        platforms = ["twitter", "linkedin", "instagram"]

        for platform in platforms:
            map_doc = MapDocument(
                document_id=f"{platform}_map_1",
                source_url=f"https://{platform}.com/example",
                platform=platform,
                doc_type=MapDocType.PROFILE,
            )
            assert map_doc.platform == platform

            fetch_doc = FetchDocument(
                document_id=f"{platform}_fetch_1",
                platform=platform,
                doc_type=FetchDocType.PROFILE,
            )
            assert fetch_doc.platform == platform
