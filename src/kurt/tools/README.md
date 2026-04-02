# Kurt Tools: Map and Fetch Framework

High-performance content discovery and extraction framework supporting multiple content types (documents, social profiles, posts) across various sources and platforms.

## Overview

The Kurt Tools framework provides a modular, extensible architecture for:

- **Mapping**: Discovering content URLs and metadata from websites and social platforms
- **Fetching**: Extracting full content from discovered URLs with platform-specific support
- **Multi-content support**: Documents, social media profiles, and posts
- **Engine abstraction**: Pluggable backends (crawlers, APIs, scrapers)
- **Rate limiting**: Built-in token bucket rate limiting with per-engine isolation
- **Error handling**: Comprehensive error hierarchy with retry strategies

## Architecture

```
┌─────────────────────────────────────────┐
│         CLI Commands                     │
│  (map doc, map profile, fetch posts)     │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│      Subcommands                         │
│  (MapDocSubcommand, FetchDocSubcommand)  │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│   Core Abstractions                      │
│  (BaseMapper, BaseFetcher)               │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│      Engine Implementations              │
│  (Crawl, Sitemap, Apify, Trafilatura)    │
└──────────────────────────────────────────┘
```

## Content Types

### DocType Enum

```python
from kurt.tools.map.models import DocType

DocType.DOC       # Web documents/pages
DocType.PROFILE   # Social media profiles
DocType.POSTS     # Social media posts
```

### Pydantic Models

**Metadata models** (for discovery):
- `DocMetadata` - Document URL with title, description, depth
- `ProfileMetadata` - Profile URL with username, platform, verification
- `PostMetadata` - Post URL with ID, timestamp, platform

**Content models** (for extraction):
- `DocContent` - Full document with text, HTML, word count, links
- `ProfileContent` - Full profile with metrics (followers, posts count)
- `PostContent` - Full post with engagement metrics, hashtags, mentions

## Usage Examples

### Basic Mapping

```python
from kurt.tools.map.subcommands import MapDocSubcommand
from kurt.tools.map.core import BaseMapper, MapperConfig

# Create mapper instance
mapper = MyCustomMapper(MapperConfig(max_urls=100, max_depth=3))

# Discover documents
cmd = MapDocSubcommand(mapper)
docs = cmd.run("https://example.com", depth=3)

for doc in docs:
    print(f"Found: {doc.url}")
    print(f"  Title: {doc.title}")
    print(f"  Depth: {doc.depth}")
```

### Profile Discovery

```python
from kurt.tools.map.subcommands import MapProfileSubcommand

cmd = MapProfileSubcommand(mapper)

# Search on Twitter
profiles = cmd.run("AI engineer", platform="twitter", limit=50)

# Search on LinkedIn
profiles = cmd.run("data scientist", platform="linkedin", limit=25)

# Multi-platform
for platform in ["twitter", "linkedin", "instagram"]:
    profiles = cmd.run("developer", platform=platform)
```

### Content Extraction

```python
from kurt.tools.fetch.subcommands import FetchDocSubcommand
from kurt.tools.fetch.core import BaseFetcher

fetcher = MyCustomFetcher()
cmd = FetchDocSubcommand(fetcher)

# Fetch documents
docs = cmd.run([
    "https://example.com/page1",
    "https://example.com/page2",
])

for doc in docs:
    print(f"Title: {doc.title}")
    print(f"Words: {doc.word_count}")
    print(f"Links: {len(doc.links)}")
```

### Platform-Specific Content

```python
from kurt.tools.fetch.subcommands import (
    FetchProfileSubcommand,
    FetchPostsSubcommand,
)

# Fetch Twitter profiles
profile_fetcher = FetchProfileSubcommand(fetcher)
profiles = profile_fetcher.run(
    ["https://twitter.com/user1", "https://twitter.com/user2"],
    platform="twitter"
)

for profile in profiles:
    print(f"@{profile.username}: {profile.followers_count} followers")

# Fetch Twitter posts
post_fetcher = FetchPostsSubcommand(fetcher)
posts = post_fetcher.run(
    ["https://twitter.com/user/status/123"],
    platform="twitter"
)

for post in posts:
    print(f"Likes: {post.likes_count}, Replies: {post.replies_count}")
```

## Creating Custom Engines

### Mapping Engine

```python
from kurt.tools.map.core import BaseMapper, MapperConfig, MapperResult
from kurt.tools.map.models import DocType

class CustomMapper(BaseMapper):
    """Custom content discovery engine."""

    def map(self, source: str, doc_type: DocType = DocType.DOC) -> MapperResult:
        """Discover content from source."""
        urls = []
        errors = []

        try:
            if doc_type == DocType.DOC:
                urls = self._discover_documents(source)
            elif doc_type == DocType.PROFILE:
                urls = self._discover_profiles(source)
            elif doc_type == DocType.POSTS:
                urls = self._discover_posts(source)
        except Exception as e:
            errors.append(str(e))

        return MapperResult(
            urls=urls[:self.config.max_urls],
            count=len(urls),
            errors=errors,
        )

    def _discover_documents(self, source: str) -> list[str]:
        # Implementation here
        pass

    def _discover_profiles(self, source: str) -> list[str]:
        # Implementation here
        pass

    def _discover_posts(self, source: str) -> list[str]:
        # Implementation here
        pass
```

### Fetching Engine

```python
from kurt.tools.fetch.core import BaseFetcher, FetcherConfig, FetchResult

class CustomFetcher(BaseFetcher):
    """Custom content extraction engine."""

    def fetch(self, url: str) -> FetchResult:
        """Extract content from URL."""
        try:
            content = self._extract_content(url)
            html = self._extract_html(url)

            return FetchResult(
                content=content,
                content_html=html,
                metadata={"url": url},
                success=True,
            )
        except Exception as e:
            return FetchResult(
                content="",
                error=str(e),
                success=False,
            )

    def _extract_content(self, url: str) -> str:
        # Implementation here
        pass

    def _extract_html(self, url: str) -> str:
        # Implementation here
        pass
```

## Rate Limiting

Built-in token bucket rate limiting with per-engine configuration:

```python
from kurt.tools.rate_limit import RateLimiter, RateLimitConfig

limiter = RateLimiter()

# Configure rate limit for engine
config = RateLimitConfig(
    tokens_per_second=5,
    bucket_size=50,
)
limiter.configure_engine("apify", config)

# Acquire tokens before making request
with limiter.rate_limited("apify", cost=1):
    # Make request here
    pass
```

## Error Handling

```python
from kurt.tools.errors import (
    EngineError,
    RateLimitError,
    TimeoutError,
    AuthError,
    ContentError,
)

try:
    results = cmd.run(urls)
except RateLimitError:
    # Handle rate limiting with backoff
    pass
except AuthError:
    # Handle authentication failure
    pass
except TimeoutError:
    # Handle timeout with retry
    pass
except ContentError:
    # Handle content extraction failure
    pass
```

## Configuration

Map/fetch configuration can be passed during initialization:

```python
from kurt.tools.map.core import MapperConfig
from kurt.tools.fetch.core import FetcherConfig

# Mapper configuration
mapper_config = MapperConfig(
    max_depth=5,                    # Crawl depth limit
    max_urls=1000,                  # Maximum URLs to discover
    timeout=30,                     # Request timeout (seconds)
    follow_external=False,          # Follow external links
    include_pattern=r".*blog.*",    # URL inclusion regex
    exclude_pattern=r".*admin.*",   # URL exclusion regex
)

# Fetcher configuration
fetcher_config = FetcherConfig(
    timeout=30,                     # Request timeout (seconds)
    max_retries=3,                  # Retry attempts
    verify_ssl=True,                # SSL verification
    user_agent="Kurt/1.0",          # Custom user agent
)
```

## Testing

The framework includes comprehensive test suites:

**Unit Tests:**
```bash
pytest src/kurt/tools/tests/test_schema_models.py      # Database models
pytest src/kurt/tools/tests/test_pydantic_models.py    # Content type models
pytest src/kurt/tools/tests/test_rate_limit.py         # Rate limiting
pytest src/kurt/tools/tests/test_subcommands.py        # Subcommands
```

**Integration Tests:**
```bash
pytest src/kurt/tools/tests/test_integration_e2e.py    # E2E workflows
pytest src/kurt/tools/tests/test_map_engines.py        # Engine integration
```

**Running All Tests:**
```bash
pytest src/kurt/tools/tests/ -v
```

## Command Line Interface

### Map Commands

```bash
# Discover documents from a website
kurt tools map doc https://example.com --depth 3 --engine crawl

# Search for profiles
kurt tools map profile "AI engineer" --platform twitter --limit 50
kurt tools map profile "data scientist" --platform linkedin --limit 25

# Discover posts
kurt tools map posts "machine learning" --limit 100 --since 2024-01-01
```

### Fetch Commands

```bash
# Fetch document content
kurt tools fetch doc https://example.com/page1 https://example.com/page2

# Fetch profile details
kurt tools fetch profile https://twitter.com/user1 --platform twitter

# Fetch post content
kurt tools fetch posts https://twitter.com/user/status/123 --platform twitter
```

### Backward Compatibility

Deprecated commands still work with warnings:

```bash
# These commands still work but show deprecation warnings
kurt tools map discover https://example.com
kurt tools fetch content https://example.com/page
```

## Performance Optimization

### Parallel Processing

Map/fetch operations support parallel execution:

```python
# Configure mapper for parallel crawling
config = MapperConfig(
    max_urls=500,
    max_depth=5,
    follow_external=True,
)

# Fetch supports parallel downloads
results = fetcher.fetch_batch(urls, concurrency=10)
```

### Caching

Implement response caching in custom engines:

```python
class CachedFetcher(BaseFetcher):
    def __init__(self, config: Optional[FetcherConfig] = None):
        super().__init__(config)
        self.cache = {}

    def fetch(self, url: str) -> FetchResult:
        if url in self.cache:
            return self.cache[url]

        result = self._fetch_uncached(url)
        self.cache[url] = result
        return result
```

## API Keys and Credentials

Manage API keys through environment variables or config:

```python
# Environment variables (highest priority)
export APIFY_KEY="your-key"
export FIRECRAWL_KEY="your-key"
export TAVILY_KEY="your-key"

# Or configure in kurt.config
INTEGRATIONS:
  APIFY:
    KEY: "your-key"
    REQUEST_TIMEOUT: 60
  FIRECRAWL:
    KEY: "your-key"
```

Access in code:

```python
from kurt.tools.api_keys import global_key_manager

api_key = global_key_manager.get("apify")
if not api_key:
    raise AuthError("Apify API key not configured")
```

## Monitoring and Debugging

Enable logging for debugging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("kurt.tools")
```

Track progress with status events:

```python
# Custom mapper that emits progress
class ProgressMapper(BaseMapper):
    def map(self, source: str, doc_type: DocType) -> MapperResult:
        total = self.config.max_urls
        for i in range(total):
            # Process item
            progress = (i + 1) / total
            print(f"Progress: {progress*100:.1f}%")
```

## Contributing

To add new engines or features:

1. **Create new engine** inheriting from `BaseMapper` or `BaseFetcher`
2. **Implement abstract methods** (`map()` or `fetch()`)
3. **Add tests** in `tests/` directory
4. **Update documentation** in this README
5. **Submit pull request** with examples

## License

Same as Kurt project.
