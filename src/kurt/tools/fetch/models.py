from __future__ import annotations

from enum import Enum
from typing import Optional, Protocol

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from kurt.db.models import EmbeddingMixin, TenantMixin, TimestampMixin

# Type alias for fetch results
FetchResult = tuple[str, dict]  # (content_markdown, metadata_dict)
BatchFetchResult = dict[str, FetchResult | Exception]  # URL -> result or error


class BatchFetcher(Protocol):
    """Protocol for batch fetch engines."""

    def __call__(self, urls: list[str]) -> BatchFetchResult:
        """Batch fetch multiple URLs.

        Args:
            urls: List of URLs to fetch

        Returns:
            Dict mapping URL -> (content, metadata) or Exception for failures
        """
        ...


class FetchStatus(str, Enum):
    """Status for fetched documents."""

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


class DocType(str, Enum):
    """Type of document being fetched."""

    DOC = "doc"
    PROFILE = "profile"
    POSTS = "posts"


class FetchDocument(EmbeddingMixin, TimestampMixin, TenantMixin, SQLModel, table=True):
    """Persisted fetch results for documents."""

    __tablename__ = "fetch_documents"

    document_id: str = Field(primary_key=True)

    # Document type
    doc_type: DocType = Field(default=DocType.DOC, index=True)
    platform: Optional[str] = Field(default=None, index=True)

    # Status
    status: FetchStatus = Field(default=FetchStatus.PENDING)

    # Content info
    content_length: int = Field(default=0)
    content_hash: Optional[str] = Field(default=None)
    content_path: Optional[str] = Field(default=None)  # Relative path to markdown file

    # Fetch info
    fetch_engine: Optional[str] = Field(default=None)
    public_url: Optional[str] = Field(default=None)

    # Error tracking
    error: Optional[str] = Field(default=None)

    # Metadata
    metadata_json: Optional[dict] = Field(sa_column=Column(JSON), default=None)


class Profile(TimestampMixin, TenantMixin, SQLModel, table=True):
    """Social media profile metadata."""

    __tablename__ = "profiles"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Profile identity
    platform: str = Field(index=True)  # twitter, linkedin, etc.
    platform_id: str = Field(unique=True, index=True)  # Platform-specific ID
    username: str = Field(index=True)
    display_name: Optional[str] = Field(default=None)

    # Profile info
    bio: Optional[str] = Field(default=None)
    followers_count: int = Field(default=0)
    following_count: int = Field(default=0)
    posts_count: int = Field(default=0)

    # Profile URLs and assets
    profile_url: Optional[str] = Field(default=None, unique=True)
    avatar_url: Optional[str] = Field(default=None)
    verified: bool = Field(default=False)

    # Raw metadata
    raw_metadata: Optional[dict] = Field(sa_column=Column(JSON), default=None)


class Post(TimestampMixin, TenantMixin, SQLModel, table=True):
    """Social media post metadata."""

    __tablename__ = "posts"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Post identity
    platform: str = Field(index=True)  # twitter, linkedin, etc.
    platform_id: str = Field(unique=True, index=True)  # Platform-specific post ID
    profile_id: Optional[int] = Field(default=None, foreign_key="profiles.id", index=True)

    # Post content
    content_text: Optional[str] = Field(default=None)
    content_html: Optional[str] = Field(default=None)
    media_urls: Optional[list[str]] = Field(sa_column=Column(JSON), default=None)

    # Engagement metrics
    likes_count: int = Field(default=0)
    shares_count: int = Field(default=0)
    comments_count: int = Field(default=0)

    # Post timing
    published_at: Optional[str] = Field(default=None, index=True)

    # Raw metadata
    raw_metadata: Optional[dict] = Field(sa_column=Column(JSON), default=None)
