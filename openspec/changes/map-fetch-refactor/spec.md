# Map/Fetch Refactor - Technical Specification

## Overview

**Goal**: Extend map/fetch tools to support documents, profiles, and posts via subcommands with schema-driven Pydantic models.

**Status**: Draft v1

---

## Architecture

### Current State

```
tools/
├── map/
│   ├── cli.py              # Single command: kurt content map
│   ├── models.py           # MapDocument (pages only)
│   ├── config.py
│   └── utils.py
│
└── fetch/
    ├── cli.py              # Single command: kurt content fetch
    ├── models.py           # FetchDocument (pages only)
    ├── trafilatura.py      # Engine
    ├── firecrawl.py        # Engine
    └── tavily.py           # Engine
```

### Target State

```
tools/
├── map/
│   ├── __init__.py         # Exports, CLI group assembly
│   │
│   ├── core/               # Shared logic
│   │   ├── __init__.py
│   │   ├── base.py         # MapEngine protocol, BaseMapItem
│   │   ├── storage.py      # save_map_items(), query_map_items()
│   │   └── router.py       # URL → engine detection
│   │
│   ├── engines/            # Shared engines
│   │   ├── __init__.py
│   │   ├── sitemap.py      # Sitemap parser
│   │   ├── crawl.py        # Link crawler
│   │   ├── folder.py       # Filesystem discovery
│   │   ├── cms.py          # CMS sync (Sanity, etc.)
│   │   ├── apify.py        # Apify search/enumerate
│   │   └── rss.py          # RSS/Atom feed parser
│   │
│   ├── doc/                # Document mapping
│   │   ├── __init__.py
│   │   ├── cli.py          # kurt map doc ...
│   │   └── model.py        # DocMetadata (Pydantic)
│   │
│   ├── profile/            # Profile mapping
│   │   ├── __init__.py
│   │   ├── cli.py          # kurt map profile ...
│   │   └── model.py        # ProfileMetadata (Pydantic)
│   │
│   └── posts/              # Posts mapping
│       ├── __init__.py
│       ├── cli.py          # kurt map posts ...
│       └── model.py        # PostMetadata (Pydantic)
│
└── fetch/
    ├── __init__.py         # Exports, CLI group assembly
    │
    ├── core/               # Shared logic
    │   ├── __init__.py
    │   ├── base.py         # FetchEngine protocol, BaseFetchItem
    │   ├── storage.py      # save_fetch_items(), query_fetch_items()
    │   └── router.py       # doc → engine selection
    │
    ├── engines/            # Shared engines
    │   ├── __init__.py
    │   ├── trafilatura.py  # Local extraction
    │   ├── httpx_engine.py # HTTP + trafilatura
    │   ├── firecrawl.py    # Firecrawl API
    │   ├── tavily.py       # Tavily API
    │   ├── apify.py        # Apify profile/post scraping
    │   └── rss.py          # RSS content (already fetched)
    │
    ├── doc/                # Document fetching
    │   ├── __init__.py
    │   ├── cli.py          # kurt fetch doc ...
    │   └── model.py        # DocContent (Pydantic)
    │
    ├── profile/            # Profile fetching
    │   ├── __init__.py
    │   ├── cli.py          # kurt fetch profile ...
    │   └── model.py        # ProfileContent (Pydantic)
    │
    └── posts/              # Posts fetching
        ├── __init__.py
        ├── cli.py          # kurt fetch posts ...
        └── model.py        # PostContent (Pydantic)
```

---

## Database Schema Changes

### map_documents (ADD columns)

```sql
-- Phase 1: Add columns with defaults
ALTER TABLE map_documents ADD COLUMN doc_type VARCHAR(20) DEFAULT 'doc';
ALTER TABLE map_documents ADD COLUMN platform VARCHAR(50);

-- Phase 2: Create composite indices (better query performance)
CREATE INDEX idx_map_doc_type_platform ON map_documents(doc_type, platform);
CREATE INDEX idx_map_doc_type_status ON map_documents(doc_type, status);

-- Phase 3: Backfill existing rows based on URL patterns
UPDATE map_documents
SET doc_type = CASE
    WHEN source_url ~ 'twitter\.com/.*/status/' THEN 'post'
    WHEN source_url ~ 'twitter\.com/[^/]+/?$' THEN 'profile'
    WHEN source_url ~ 'x\.com/.*/status/' THEN 'post'
    WHEN source_url ~ 'x\.com/[^/]+/?$' THEN 'profile'
    WHEN source_url ~ 'linkedin\.com/in/' THEN 'profile'
    WHEN source_url ~ 'linkedin\.com/posts/' THEN 'post'
    WHEN source_url ~ '\.substack\.com/p/' THEN 'post'
    WHEN source_url ~ '\.substack\.com/?$' THEN 'profile'
    ELSE 'doc'
END
WHERE doc_type = 'doc';

-- Phase 4: Add composite unique constraint (prevents duplicate URL+type)
ALTER TABLE map_documents
  ADD CONSTRAINT uq_map_url_type UNIQUE(source_url, doc_type);
```

### fetch_documents (ADD columns)

```sql
ALTER TABLE fetch_documents ADD COLUMN doc_type VARCHAR(20) DEFAULT 'doc';
ALTER TABLE fetch_documents ADD COLUMN platform VARCHAR(50);

-- Index for filtering
CREATE INDEX idx_fetch_doc_type ON fetch_documents(doc_type);
CREATE INDEX idx_fetch_platform ON fetch_documents(platform);
```

### Updated SQLModel

```python
# tools/map/models.py
class MapDocument(TimestampMixin, TenantMixin, SQLModel, table=True):
    __tablename__ = "map_documents"

    document_id: str = Field(primary_key=True)
    source_url: str = Field(default="", unique=True)
    source_type: str = Field(default="url")

    # NEW: Content type classification
    doc_type: str = Field(default="doc")      # "doc", "profile", "post"
    platform: str | None = Field(default=None) # "twitter", "linkedin", "substack"

    discovery_method: str = Field(default="")
    discovery_url: str | None = Field(default=None)
    status: MapStatus = Field(default=MapStatus.SUCCESS)
    is_new: bool = Field(default=True)
    title: str | None = Field(default=None)
    content_hash: str | None = Field(default=None, index=True)
    error: str | None = Field(default=None)
    metadata_json: dict | None = Field(sa_column=Column(JSON), default=None)
```

---

## Pydantic Models

### Map Models (Lightweight Discovery)

```python
# tools/map/core/base.py
from pydantic import BaseModel, Field
from datetime import datetime

class BaseMapItem(BaseModel):
    """Base for all mapped items."""
    url: str
    title: str | None = None
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    source_query: str | None = None


# tools/map/doc/model.py
class DocMetadata(BaseMapItem):
    """Metadata for discovered web pages."""
    doc_type: str = "doc"

    discovery_method: str = "sitemap"  # sitemap, crawl, folder, cms
    discovery_url: str | None = None
    content_type: str | None = None
    last_modified: datetime | None = None

    # Field mappings for extraction
    __field_mappings__ = {
        "title": ["title", "og:title", "name"],
        "last_modified": ["lastmod", "last-modified", "modified"],
    }


# tools/map/profile/model.py
class ProfileMetadata(BaseMapItem):
    """Metadata for discovered profiles."""
    doc_type: str = "profile"

    platform: str                      # twitter, linkedin, substack
    username: str
    display_name: str | None = None
    bio_snippet: str | None = None     # Truncated from search
    follower_count: int | None = None  # Sometimes available

    # Classification (user-provided)
    relationship: str | None = None    # competitor, adjacent, collaboration
    tags: list[str] = []

    __field_mappings__ = {
        "username": ["username", "screen_name", "handle", "user"],
        "display_name": ["name", "displayName", "full_name"],
        "follower_count": ["followersCount", "followers_count", "followers"],
        "bio_snippet": ["description", "bio", "summary"],
    }


# tools/map/posts/model.py
class PostMetadata(BaseMapItem):
    """Metadata for discovered posts."""
    doc_type: str = "post"

    platform: str
    author: str
    author_url: str | None = None
    posted_at: datetime | None = None
    preview: str | None = None         # First ~200 chars

    __field_mappings__ = {
        "author": ["author", "username", "user", "creator"],
        "posted_at": ["createdAt", "created_at", "publishedAt", "date"],
        "preview": ["text", "content", "description"],
    }
```

### Fetch Models (Full Content)

```python
# tools/fetch/core/base.py
class BaseFetchItem(BaseModel):
    """Base for all fetched content."""
    url: str
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    fetch_engine: str
    content_hash: str | None = None


# tools/fetch/doc/model.py
class DocContent(BaseFetchItem):
    """Full content for web pages."""
    doc_type: str = "doc"

    title: str | None = None
    content: str                       # Markdown
    content_length: int = 0

    author: str | None = None
    published_at: datetime | None = None
    description: str | None = None
    keywords: list[str] = []


# tools/fetch/profile/model.py
class ProfileContent(BaseFetchItem):
    """Full content for profiles."""
    doc_type: str = "profile"

    platform: str
    username: str
    display_name: str | None = None
    bio: str | None = None             # Full bio

    # Metrics
    follower_count: int | None = None
    following_count: int | None = None
    post_count: int | None = None

    # Extended
    website: str | None = None
    location: str | None = None
    joined_at: datetime | None = None
    verified: bool = False

    # Computed (post-fetch analysis)
    avg_posts_per_month: float | None = None
    top_topics: list[str] = []

    __field_mappings__ = {
        "follower_count": ["followersCount", "followers_count", "followers"],
        "following_count": ["followingCount", "following_count", "following"],
        "post_count": ["statusesCount", "postsCount", "tweetsCount"],
        "bio": ["description", "bio", "about", "summary"],
        "website": ["url", "website", "link"],
        "location": ["location", "geo"],
        "joined_at": ["createdAt", "created_at", "joinedAt"],
        "verified": ["verified", "isVerified", "is_verified"],
    }


# tools/fetch/posts/model.py
class PostContent(BaseFetchItem):
    """Full content for posts."""
    doc_type: str = "post"

    platform: str
    author: str
    author_url: str | None = None

    # Content
    content: str
    posted_at: datetime | None = None

    # Engagement
    score: int = 0                     # likes, upvotes
    comment_count: int = 0
    share_count: int = 0

    # Media
    has_media: bool = False
    media_urls: list[str] = []

    __field_mappings__ = {
        "content": ["text", "content", "body", "postContent"],
        "score": ["likeCount", "likes", "favoriteCount", "reactions"],
        "comment_count": ["replyCount", "replies", "commentCount", "numComments"],
        "share_count": ["retweetCount", "shareCount", "reposts"],
        "posted_at": ["createdAt", "created_at", "publishedAt"],
    }
```

---

## Error Handling Framework

```python
# tools/map/core/errors.py
from enum import Enum
from typing import Optional

class ErrorCategory(Enum):
    """Categorize errors for retry logic."""
    RETRYABLE = "retryable"        # Timeout, 429, 503 - safe to retry
    FATAL = "fatal"                # 401, 403, 404 - don't retry
    PARTIAL = "partial"            # Some items succeeded, some failed
    INVALID_INPUT = "invalid"      # User error - don't retry

class EngineError(Exception):
    """Base for all engine errors with retry metadata."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        retry_after: Optional[float] = None,
        source_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.retry_after = retry_after  # seconds to wait before retry
        self.source_error = source_error

    def is_retryable(self) -> bool:
        return self.category == ErrorCategory.RETRYABLE

class RateLimitError(EngineError):
    """API rate limit exceeded - retryable after delay."""
    def __init__(self, retry_after: float = 60.0):
        super().__init__("Rate limit exceeded", ErrorCategory.RETRYABLE, retry_after)

class InvalidAPIKeyError(EngineError):
    """Invalid or missing API key - fatal."""
    def __init__(self, engine: str):
        super().__init__(f"Invalid API key for {engine}", ErrorCategory.FATAL)

class PartialBatchFailure(EngineError):
    """Some items succeeded, some failed."""
    def __init__(self, succeeded: int, failed: int, failures: dict):
        super().__init__(
            f"Batch partial failure: {succeeded} succeeded, {failed} failed",
            ErrorCategory.PARTIAL,
        )
        self.succeeded = succeeded
        self.failed = failed
        self.failures = failures  # url -> error mapping
```

### Retry Strategy

```python
# tools/map/core/retry.py
import time
from dataclasses import dataclass

@dataclass
class RetryConfig:
    max_retries: int = 3
    backoff_factor: float = 2.0
    initial_delay: float = 1.0

def with_retry(fn, config: RetryConfig = RetryConfig()):
    """Decorator for automatic retry with exponential backoff."""
    def wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(config.max_retries):
            try:
                return fn(*args, **kwargs)
            except EngineError as e:
                last_error = e
                if not e.is_retryable():
                    raise
                if attempt >= config.max_retries - 1:
                    raise
                delay = config.initial_delay * (config.backoff_factor ** attempt)
                if e.retry_after:
                    delay = max(delay, e.retry_after)
                time.sleep(delay)
        raise last_error
    return wrapper
```

---

## Engine Protocols

```python
# tools/map/core/base.py
from typing import Protocol, runtime_checkable

@runtime_checkable
class MapEngine(Protocol):
    """Protocol for map engines."""

    name: str

    def discover(
        self,
        source: str,
        doc_type: str,
        **kwargs
    ) -> list[BaseMapItem]:
        """Discover items from source."""
        ...

    def supports(self, doc_type: str, platform: str | None) -> bool:
        """Check if engine supports this doc_type/platform combo."""
        ...


# tools/fetch/core/base.py
@runtime_checkable
class FetchEngine(Protocol):
    """Protocol for fetch engines."""

    name: str

    def fetch(
        self,
        url: str,
        doc_type: str,
        **kwargs
    ) -> BaseFetchItem:
        """Fetch content from URL."""
        ...

    def fetch_batch(
        self,
        urls: list[str],
        doc_type: str,
        **kwargs
    ) -> dict[str, BaseFetchItem | Exception]:
        """Batch fetch multiple URLs."""
        ...

    def supports(self, doc_type: str, platform: str | None) -> bool:
        """Check if engine supports this doc_type/platform combo."""
        ...
```

---

## Engine Implementations

### Apify Map Engine

**IMPORTANT**: ApifyMapEngine wraps the existing ApifyAdapter (from PR #89) and converts
`Signal` objects to the appropriate map/fetch models. This avoids reimplementing Apify logic.

```python
# tools/map/engines/apify.py
from kurt.integrations.research.monitoring import ApifyAdapter
from kurt.integrations.research.monitoring.models import Signal
from ..profile.model import ProfileMetadata
from ..posts.model import PostMetadata
from ..core.errors import EngineError, RateLimitError, InvalidAPIKeyError

class ApifyMapEngine:
    """Map engine using Apify for profile/post discovery."""

    name = "apify"

    def __init__(self):
        from kurt.integrations.research.config import get_source_config
        config = get_source_config("apify")
        self.adapter = ApifyAdapter(config)

    def supports(self, doc_type: str, platform: str | None) -> bool:
        return doc_type in ["profile", "post"] and platform in ["twitter", "linkedin"]

    def discover(
        self,
        source: str,
        doc_type: str,
        platform: str,
        max_results: int = 100,
        **kwargs
    ) -> list[BaseMapItem]:
        if doc_type == "profile":
            return self._discover_profiles(source, platform, max_results, **kwargs)
        elif doc_type == "post":
            return self._discover_posts(source, platform, max_results, **kwargs)
        raise ValueError(f"Unsupported doc_type: {doc_type}")

    def _discover_profiles(
        self,
        query: str,
        platform: str,
        max_results: int,
        **kwargs
    ) -> list[ProfileMetadata]:
        """Search for profiles via Apify.

        NOTE: Uses existing ApifyAdapter methods which return Signal objects,
        then converts to ProfileMetadata. This ensures we reuse the adapter's
        field mappings and actor registry.
        """
        try:
            # Use adapter's existing search methods
            if platform == "twitter":
                signals = self.adapter.search_twitter(query, max_items=max_results)
            elif platform == "linkedin":
                signals = self.adapter.search_linkedin(query, max_items=max_results)
            else:
                raise ValueError(f"Unsupported platform: {platform}")

            # Convert Signal -> ProfileMetadata
            return [self._signal_to_profile(s, platform, query) for s in signals]

        except Exception as e:
            if "401" in str(e) or "Unauthorized" in str(e):
                raise InvalidAPIKeyError("apify")
            if "429" in str(e) or "rate" in str(e).lower():
                raise RateLimitError(60.0)
            raise EngineError(str(e), ErrorCategory.RETRYABLE)

    def _signal_to_profile(
        self,
        signal: Signal,
        platform: str,
        query: str
    ) -> ProfileMetadata:
        """Convert Signal (adapter output) to ProfileMetadata (map output).

        Field mappings:
        - Signal.author -> ProfileMetadata.username
        - Signal.title -> ProfileMetadata.display_name
        - Signal.snippet -> ProfileMetadata.bio_snippet
        - Signal.score -> ProfileMetadata.follower_count (Twitter uses this)
        """
        return ProfileMetadata(
            url=signal.url,
            platform=platform,
            username=signal.author or self._extract_username_from_url(signal.url),
            display_name=signal.title,
            bio_snippet=signal.snippet[:200] if signal.snippet else None,
            follower_count=signal.score if signal.score else None,
            source_query=query,
        )

    def _discover_posts(
        self,
        username: str,
        platform: str,
        max_results: int,
        **kwargs
    ) -> list[PostMetadata]:
        """Enumerate posts from a profile via Apify."""
        signals = self.adapter.scrape_profile(username, platform=platform, max_items=max_results)

        return [
            PostMetadata(
                url=signal.url,
                title=signal.title,
                platform=platform,
                author=signal.author,
                author_url=self._build_profile_url({"username": signal.author}, platform),
                posted_at=signal.timestamp,
                preview=signal.snippet[:200] if signal.snippet else None,
            )
            for signal in signals
        ]


# Actor mapping
PROFILE_SEARCH_ACTORS = {
    "twitter": "apidojo/twitter-search",
    "linkedin": "anchor/linkedin-people-search",
}
```

### Apify Fetch Engine

```python
# tools/fetch/engines/apify.py
class ApifyFetchEngine:
    """Fetch engine using Apify for profile/post content."""

    name = "apify"

    def supports(self, doc_type: str, platform: str | None) -> bool:
        return doc_type in ["profile", "post"] and platform in ["twitter", "linkedin"]

    def fetch(
        self,
        url: str,
        doc_type: str,
        platform: str,
        **kwargs
    ) -> BaseFetchItem:
        if doc_type == "profile":
            return self._fetch_profile(url, platform)
        elif doc_type == "post":
            return self._fetch_post(url, platform)
        raise ValueError(f"Unsupported doc_type: {doc_type}")

    def _fetch_profile(self, url: str, platform: str) -> ProfileContent:
        """Fetch full profile details via Apify."""
        username = extract_username_from_url(url, platform)

        items = self.adapter.run_actor(
            PROFILE_DETAIL_ACTORS[platform],
            {"handles": [username]} if platform == "twitter" else {"profileUrls": [url]}
        )

        item = items[0]
        return ProfileContent(
            url=url,
            fetch_engine="apify",
            platform=platform,
            username=username,
            display_name=item.get("name"),
            bio=item.get("description"),
            follower_count=item.get("followersCount"),
            following_count=item.get("followingCount"),
            post_count=item.get("statusesCount"),
            website=item.get("url"),
            location=item.get("location"),
            verified=item.get("verified", False),
        )


PROFILE_DETAIL_ACTORS = {
    "twitter": "apidojo/twitter-user-scraper",
    "linkedin": "anchor/linkedin-profile-scraper",
}
```

### RSS Engines (Substack)

```python
# tools/map/engines/rss.py
import feedparser

class RSSMapEngine:
    """Map engine for RSS/Atom feeds (Substack, blogs)."""

    name = "rss"

    def supports(self, doc_type: str, platform: str | None) -> bool:
        return doc_type == "post" and platform == "substack"

    def discover(
        self,
        source: str,  # Substack URL or RSS feed URL
        doc_type: str,
        max_results: int = 50,
        **kwargs
    ) -> list[PostMetadata]:
        feed_url = self._get_feed_url(source)
        feed = feedparser.parse(feed_url)

        return [
            PostMetadata(
                url=entry.link,
                title=entry.title,
                platform="substack",
                author=entry.get("author", ""),
                posted_at=self._parse_date(entry.get("published_parsed")),
                preview=entry.get("summary", "")[:200],
            )
            for entry in feed.entries[:max_results]
        ]

    def _get_feed_url(self, url: str) -> str:
        if "/feed" in url:
            return url
        return f"{url.rstrip('/')}/feed"
```

---

## CLI Implementation

### Map CLI Group

```python
# tools/map/__init__.py
import click
from .doc.cli import doc_cmd
from .profile.cli import profile_cmd
from .posts.cli import posts_cmd

@click.group("map")
def map_group():
    """Discover content sources."""
    pass

map_group.add_command(doc_cmd, "doc")
map_group.add_command(profile_cmd, "profile")
map_group.add_command(posts_cmd, "posts")
```

### Map Profile CLI

```python
# tools/map/profile/cli.py
import click
from rich.console import Console

console = Console()

@click.command("profile")
@click.argument("source")
@click.option("--platform", "-p", type=click.Choice(["twitter", "linkedin", "substack"]),
              help="Platform (auto-detected from URL if not specified)")
@click.option("--max", "max_results", default=100, help="Maximum profiles to discover")
@click.option("--relationship", "-r", type=click.Choice(["competitor", "adjacent", "collaboration"]),
              help="Tag profiles with relationship type")
@click.option("--tags", help="Comma-separated tags")
@click.option("--from-file", "from_file", type=click.Path(exists=True),
              help="Read sources from file (one per line)")
@click.option("--dry-run", is_flag=True, help="Preview without saving")
@click.option("--output-format", "output_format", default="table",
              type=click.Choice(["table", "json"]))
def profile_cmd(
    source: str,
    platform: str | None,
    max_results: int,
    relationship: str | None,
    tags: str | None,
    from_file: str | None,
    dry_run: bool,
    output_format: str,
):
    """
    Discover creator/company profiles.

    SOURCE can be:
    - URL: https://twitter.com/username (auto-detects platform)
    - Search query: "AI newsletter" (requires --platform)

    Examples:
        kurt map profile https://twitter.com/elonmusk
        kurt map profile "AI newsletter" --platform twitter --max 50
        kurt map profile --from-file competitors.txt --relationship competitor
    """
    from ..core.router import detect_platform_from_url
    from ..core.storage import save_map_items
    from ..engines import get_map_engine
    from .model import ProfileMetadata

    # Auto-detect platform from URL
    if not platform and source.startswith("http"):
        platform = detect_platform_from_url(source)

    if not platform:
        console.print("[red]Error:[/red] --platform required for search queries")
        raise click.Abort()

    # Get appropriate engine
    engine = get_map_engine("profile", platform)

    # Discover profiles
    console.print(f"[dim]Discovering profiles on {platform}...[/dim]")
    profiles = engine.discover(
        source=source,
        doc_type="profile",
        platform=platform,
        max_results=max_results,
    )

    # Add user-provided metadata
    tag_list = [t.strip() for t in tags.split(",")] if tags else []
    for p in profiles:
        p.relationship = relationship
        p.tags = tag_list

    console.print(f"[green]✓[/green] Found {len(profiles)} profiles")

    if dry_run:
        console.print("[dim]Dry run - not saving[/dim]")
        # Display results
        for p in profiles[:10]:
            console.print(f"  @{p.username} - {p.display_name or 'N/A'}")
        if len(profiles) > 10:
            console.print(f"  ... and {len(profiles) - 10} more")
        return

    # Save to database
    save_map_items(profiles, doc_type="profile", platform=platform)
    console.print(f"[green]✓[/green] Saved {len(profiles)} profiles")
```

### Fetch Profile CLI

```python
# tools/fetch/profile/cli.py
import click
from rich.console import Console

console = Console()

@click.command("profile")
@click.option("--pending", is_flag=True, help="Fetch all pending profiles")
@click.option("--id", "profile_id", help="Fetch specific profile by ID")
@click.option("--platform", "-p", help="Filter by platform")
@click.option("--relationship", "-r", help="Filter by relationship")
@click.option("--dry-run", is_flag=True, help="Preview without saving")
@click.option("--output-format", "output_format", default="table",
              type=click.Choice(["table", "json"]))
def profile_cmd(
    pending: bool,
    profile_id: str | None,
    platform: str | None,
    relationship: str | None,
    dry_run: bool,
    output_format: str,
):
    """
    Fetch full profile details.

    Examples:
        kurt fetch profile --pending
        kurt fetch profile --id twitter:elonmusk
        kurt fetch profile --pending --relationship competitor
    """
    from ..core.storage import query_map_items, save_fetch_items
    from ..engines import get_fetch_engine

    # Query profiles to fetch
    profiles = query_map_items(
        doc_type="profile",
        status="pending" if pending else None,
        platform=platform,
        relationship=relationship,
        ids=[profile_id] if profile_id else None,
    )

    if not profiles:
        console.print("[yellow]No profiles to fetch[/yellow]")
        return

    console.print(f"[dim]Fetching {len(profiles)} profiles...[/dim]")

    results = []
    for profile in profiles:
        engine = get_fetch_engine("profile", profile.platform)
        try:
            content = engine.fetch(
                url=profile.source_url,
                doc_type="profile",
                platform=profile.platform,
            )
            results.append(content)
            console.print(f"  [green]✓[/green] @{profile.username}")
        except Exception as e:
            console.print(f"  [red]✗[/red] @{profile.username}: {e}")

    if dry_run:
        console.print("[dim]Dry run - not saving[/dim]")
        return

    save_fetch_items(results, doc_type="profile")
    console.print(f"[green]✓[/green] Fetched {len(results)} profiles")
```

---

## Engine Router

```python
# tools/map/core/router.py
import re

PLATFORM_PATTERNS = {
    "twitter": [r"twitter\.com", r"x\.com"],
    "linkedin": [r"linkedin\.com/in/", r"linkedin\.com/company/"],
    "substack": [r"\.substack\.com"],
}

def detect_platform_from_url(url: str) -> str | None:
    """Detect platform from URL patterns."""
    for platform, patterns in PLATFORM_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, url):
                return platform
    return None


def detect_doc_type_from_url(url: str) -> str:
    """Detect doc_type from URL patterns."""
    # Twitter
    if re.search(r"twitter\.com/\w+/status/", url) or re.search(r"x\.com/\w+/status/", url):
        return "post"
    if re.search(r"twitter\.com/\w+$", url) or re.search(r"x\.com/\w+$", url):
        return "profile"

    # LinkedIn
    if re.search(r"linkedin\.com/in/", url):
        return "profile"
    if re.search(r"linkedin\.com/posts/", url):
        return "post"

    # Substack
    if re.search(r"\.substack\.com/p/", url):
        return "post"
    if re.search(r"\.substack\.com/?$", url):
        return "profile"

    return "doc"


# tools/map/engines/__init__.py
from .sitemap import SitemapEngine
from .crawl import CrawlEngine
from .apify import ApifyMapEngine
from .rss import RSSMapEngine

ENGINES = {
    "sitemap": SitemapEngine(),
    "crawl": CrawlEngine(),
    "apify": ApifyMapEngine(),
    "rss": RSSMapEngine(),
}

def get_map_engine(doc_type: str, platform: str | None = None) -> MapEngine:
    """Get appropriate engine for doc_type/platform."""
    for engine in ENGINES.values():
        if engine.supports(doc_type, platform):
            return engine
    raise ValueError(f"No engine supports doc_type={doc_type}, platform={platform}")
```

---

## Storage Layer

```python
# tools/map/core/storage.py
from sqlmodel import select
from kurt.db import managed_session
from kurt.tools.map.models import MapDocument, MapStatus

def save_map_items(
    items: list[BaseMapItem],
    doc_type: str,
    platform: str | None = None,
) -> int:
    """Save map items to database."""
    from kurt.tools.core import make_document_id

    saved = 0
    with managed_session() as session:
        for item in items:
            doc_id = make_document_id(item.url)

            # Check if exists
            existing = session.exec(
                select(MapDocument).where(MapDocument.document_id == doc_id)
            ).first()

            if existing:
                continue

            doc = MapDocument(
                document_id=doc_id,
                source_url=item.url,
                source_type="url",
                doc_type=doc_type,
                platform=platform,
                title=item.title,
                discovery_method=getattr(item, "discovery_method", "search"),
                status=MapStatus.SUCCESS,
                is_new=True,
                metadata_json=item.model_dump(exclude={"url", "title"}),
            )
            session.add(doc)
            saved += 1

    return saved


def query_map_items(
    doc_type: str | None = None,
    platform: str | None = None,
    status: str | None = None,
    relationship: str | None = None,
    ids: list[str] | None = None,
    limit: int = 1000,
) -> list[MapDocument]:
    """Query map items from database."""
    with managed_session() as session:
        query = select(MapDocument)

        if doc_type:
            query = query.where(MapDocument.doc_type == doc_type)
        if platform:
            query = query.where(MapDocument.platform == platform)
        if status == "pending":
            query = query.where(MapDocument.status == MapStatus.SUCCESS)
            # TODO: Join with fetch_documents to find unfetched
        if ids:
            query = query.where(MapDocument.document_id.in_(ids))

        query = query.limit(limit)
        return list(session.exec(query).all())
```

---

## CLI Command Tree

```
kurt
├── map
│   ├── doc [source]                    # Web pages (sitemap/crawl/folder/cms)
│   │   ├── --method sitemap|crawl|folder|cms
│   │   ├── --depth <n>
│   │   ├── --include <pattern>
│   │   ├── --exclude <pattern>
│   │   ├── --max <n>
│   │   └── --dry-run
│   │
│   ├── profile <source>                # Creator profiles
│   │   ├── --platform twitter|linkedin|substack
│   │   ├── --max <n>
│   │   ├── --relationship competitor|adjacent|collaboration
│   │   ├── --tags <tags>
│   │   ├── --from-file <path>
│   │   └── --dry-run
│   │
│   └── posts <source>                  # Social posts
│       ├── --platform twitter|linkedin|substack
│       ├── --from-profiles             # Use stored profiles
│       ├── --relationship <rel>        # Filter profiles
│       ├── --max <n>
│       └── --dry-run
│
├── fetch
│   ├── doc                             # Fetch web pages
│   │   ├── --pending
│   │   ├── --engine trafilatura|firecrawl|tavily
│   │   ├── --url <url>
│   │   ├── --refetch
│   │   └── --dry-run
│   │
│   ├── profile                         # Fetch profile details
│   │   ├── --pending
│   │   ├── --id <id>
│   │   ├── --platform <platform>
│   │   ├── --relationship <rel>
│   │   └── --dry-run
│   │
│   └── posts                           # Fetch post content
│       ├── --pending
│       ├── --from-profile <id>
│       ├── --platform <platform>
│       └── --dry-run
│
└── list
    ├── doc [filters]
    ├── profile [filters]
    └── posts [filters]
```

---

## Migration Steps

### Phase 1: Database Changes
```bash
# Add columns to existing tables
alembic revision -m "add_doc_type_platform_columns"
alembic upgrade head
```

### Phase 2: Create Directory Structure
```bash
mkdir -p src/kurt/tools/map/{core,engines,doc,profile,posts}
mkdir -p src/kurt/tools/fetch/{core,engines,doc,profile,posts}
touch src/kurt/tools/map/{core,engines,doc,profile,posts}/__init__.py
touch src/kurt/tools/fetch/{core,engines,doc,profile,posts}/__init__.py
```

### Phase 3: Move Existing Code
```bash
# Move existing map logic to map/doc/
git mv src/kurt/tools/map/cli.py src/kurt/tools/map/doc/cli.py
git mv src/kurt/tools/map/models.py src/kurt/tools/map/models.py  # Keep shared

# Move existing fetch logic to fetch/doc/
git mv src/kurt/tools/fetch/cli.py src/kurt/tools/fetch/doc/cli.py
```

### Phase 4: Implement Core
- `map/core/base.py` - BaseMapItem, MapEngine protocol
- `map/core/storage.py` - save_map_items, query_map_items
- `map/core/router.py` - URL detection
- Same for `fetch/core/`

### Phase 5: Implement Engines
- `map/engines/apify.py` - Profile/post discovery
- `map/engines/rss.py` - RSS feed parsing
- `fetch/engines/apify.py` - Profile/post fetching

### Phase 6: Implement Type Modules
- `map/profile/cli.py`, `map/profile/model.py`
- `map/posts/cli.py`, `map/posts/model.py`
- Same for `fetch/`

### Phase 7: Update CLI Entry Points
```python
# cli/main.py
from kurt.tools.map import map_group
from kurt.tools.fetch import fetch_group

app.add_command(map_group, "map")
app.add_command(fetch_group, "fetch")

# Backward compat aliases
app.add_command(map_group.commands["doc"], "content map")
app.add_command(fetch_group.commands["doc"], "content fetch")
```

### Phase 8: Tests
- Unit tests for each engine
- Integration tests for CLI
- E2E tests with real Apify (optional, requires API key)

---

## Open Questions

1. **Backward compatibility**: Should `kurt content map` still work?
   - Proposal: Yes, alias to `kurt map doc`

2. **Apify costs**: How to handle users without Apify API key?
   - Proposal: Clear error message, point to free RSS for Substack

3. **Rate limiting**: How to handle platform rate limits?
   - Proposal: Built-in delays, configurable via kurt.config

4. **Schema versioning**: How to handle Pydantic model changes?
   - Proposal: Version field in metadata_json, migration scripts

---

## Timeline (Revised after Codex Review)

| Phase | Description | Original | Revised | Notes |
|-------|-------------|----------|---------|-------|
| 0 | Pre-implementation addendum | - | 2-3 days | Security, errors, rate limiting |
| 1 | Database changes + backfill | 1 day | 1 day | Includes data migration |
| 2-3 | Directory structure, move existing | 1 day | 1 day | |
| 4 | Core modules + error handling | 2 days | 3 days | Retry logic, EngineError |
| 5 | Engines (apify, rss) | 2 days | 3-4 days | Signal→Model conversion |
| 6 | Type modules (profile, posts) | 2 days | 2 days | |
| 7 | CLI integration + deprecation | 1 day | 1 day | Backward compat aliases |
| 8 | Tests + documentation | 2 days | 3 days | Extension guide, examples |
| **Total** | | **~11 days** | **~16-18 days** | |

**Key additions from review:**
- Phase 0: Security/error/rate-limiting design before coding
- Phase 4: Error handling framework (EngineError classes, retry logic)
- Phase 5: Signal→ProfileMetadata/PostMetadata conversion layer
- Phase 8: User guide, developer guide, migration docs
