"""Pydantic models for map/fetch content types."""

from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


class DocMetadata(BaseModel):
    """Metadata for document discovery."""

    url: str = Field(..., description="Document URL")
    title: Optional[str] = Field(None, description="Page title")
    description: Optional[str] = Field(None, description="Page description")
    language: Optional[str] = Field(None, description="Content language (e.g., 'en')")
    discovered_from: Optional[str] = Field(None, description="Parent URL where discovered")
    depth: int = Field(0, ge=0, description="Crawl depth from source")


class DocContent(BaseModel):
    """Content extracted from a document."""

    url: str = Field(..., description="Document URL")
    content_text: str = Field(default="", description="Plain text content")
    content_html: Optional[str] = Field(None, description="HTML content")
    content_path: Optional[str] = Field(None, description="Relative file path")
    word_count: int = Field(0, ge=0, description="Number of words in content")
    links: list[str] = Field(default_factory=list, description="URLs found in content")


class ProfileMetadata(BaseModel):
    """Metadata for social media profile discovery."""

    platform: str = Field(..., description="Platform (twitter, linkedin, etc.)")
    username: str = Field(..., description="Profile username")
    display_name: Optional[str] = Field(None, description="Display name")
    bio: Optional[str] = Field(None, description="Profile bio/description")
    url: str = Field(..., description="Profile URL")
    verified: bool = Field(False, description="Verification status")
    avatar_url: Optional[str] = Field(None, description="Avatar image URL")


class ProfileContent(BaseModel):
    """Full profile content extracted from a social platform."""

    url: str = Field(..., description="Profile URL")
    platform: str = Field(..., description="Platform (twitter, linkedin, etc.)")
    username: str = Field(..., description="Username")
    display_name: Optional[str] = Field(None, description="Display name")
    bio: Optional[str] = Field(None, description="Bio/description")
    followers_count: int = Field(0, ge=0, description="Follower count")
    following_count: int = Field(0, ge=0, description="Following count")
    posts_count: int = Field(0, ge=0, description="Total posts")
    verified: bool = Field(False, description="Verification status")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    cover_url: Optional[str] = Field(None, description="Cover image URL")
    location: Optional[str] = Field(None, description="Location")
    website: Optional[str] = Field(None, description="Website URL")
    joined_date: Optional[datetime] = Field(None, description="Account creation date")
    raw_metadata: dict = Field(default_factory=dict, description="Platform-specific data")


class PostMetadata(BaseModel):
    """Metadata for social media post discovery."""

    platform: str = Field(..., description="Platform (twitter, linkedin, etc.)")
    post_id: str = Field(..., description="Platform-specific post ID")
    profile_id: Optional[str] = Field(None, description="Author profile ID")
    published_at: datetime = Field(..., description="Publication datetime")
    url: str = Field(..., description="Post URL")


class PostContent(BaseModel):
    """Full post content extracted from a social platform."""

    url: str = Field(..., description="Post URL")
    platform: str = Field(..., description="Platform (twitter, linkedin, etc.)")
    post_id: str = Field(..., description="Platform-specific post ID")
    profile_id: Optional[str] = Field(None, description="Author profile ID")
    author_name: Optional[str] = Field(None, description="Author display name")
    author_username: Optional[str] = Field(None, description="Author username")
    content_text: str = Field(default="", description="Post text content")
    content_html: Optional[str] = Field(None, description="HTML formatted content")
    media_urls: list[str] = Field(default_factory=list, description="Media URLs (images, videos)")
    likes_count: int = Field(0, ge=0, description="Like/reaction count")
    shares_count: int = Field(0, ge=0, description="Share count")
    comments_count: int = Field(0, ge=0, description="Comment count")
    replies_count: int = Field(0, ge=0, description="Reply count")
    published_at: datetime = Field(..., description="Publication datetime")
    edited_at: Optional[datetime] = Field(None, description="Last edit datetime")
    hashtags: list[str] = Field(default_factory=list, description="Hashtags in post")
    mentions: list[str] = Field(default_factory=list, description="Mentioned usernames")
    raw_metadata: dict = Field(default_factory=dict, description="Platform-specific data")
