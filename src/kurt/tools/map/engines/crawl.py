"""Web crawl-based content mapping engine."""

from __future__ import annotations

from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx

from kurt.tools.map.core import BaseMapper, MapperConfig, MapperResult
from kurt.tools.map.models import DocType


def normalize_url(url: str) -> str:
    """Normalize URL for consistent comparison."""
    if not url:
        return ""
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/") if parsed.path != "/" else "/"
    if parsed.query:
        return f"{scheme}://{host}{path}?{parsed.query}"
    return f"{scheme}://{host}{path}"


class LinkExtractor(HTMLParser):
    """Extract links from HTML content."""

    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            for name, value in attrs:
                if name == "href" and value:
                    self.links.append(value)


def check_robots_txt(
    client: httpx.Client,
    base_url: str,
    timeout: float = 10.0,
) -> set[str]:
    """
    Fetch and parse robots.txt to get disallowed paths.

    Args:
        client: HTTP client
        base_url: Base URL of the website
        timeout: Request timeout

    Returns:
        Set of disallowed URL prefixes
    """
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    disallowed: set[str] = set()

    try:
        response = client.get(robots_url, timeout=timeout)
        if response.status_code == 200:
            current_applies = False

            for line in response.text.split("\n"):
                line = line.strip().lower()
                if line.startswith("user-agent:"):
                    agent = line.split(":", 1)[1].strip()
                    current_applies = agent == "*" or agent == "claude"
                elif line.startswith("disallow:") and current_applies:
                    path = line.split(":", 1)[1].strip()
                    if path:
                        disallowed.add(path)
    except Exception:
        pass

    return disallowed


def is_blocked_by_robots(url: str, disallowed: set[str]) -> bool:
    """Check if a URL is blocked by robots.txt rules."""
    if not disallowed:
        return False

    parsed = urlparse(url)
    path = parsed.path or "/"

    for pattern in disallowed:
        if pattern.endswith("*"):
            if path.startswith(pattern[:-1]):
                return True
        elif path.startswith(pattern):
            return True

    return False


def discover_from_crawl_impl(
    start_url: str,
    *,
    max_depth: int = 3,
    max_urls: int = 1000,
    timeout: float = 30.0,
    include_pattern: Optional[str] = None,
    exclude_pattern: Optional[str] = None,
    follow_external: bool = False,
    respect_robots: bool = True,
) -> tuple[list[str], list[str]]:
    """
    Discover URLs by recursive web crawling.

    Args:
        start_url: Starting URL for crawl
        max_depth: Maximum crawl depth
        max_urls: Maximum URLs to discover
        timeout: HTTP request timeout
        include_pattern: Regex pattern for URLs to include
        exclude_pattern: Regex pattern for URLs to exclude
        follow_external: Allow crawling to external domains
        respect_robots: Respect robots.txt disallow rules

    Returns:
        Tuple of (discovered URLs, error messages)
    """
    import re

    parsed_start = urlparse(start_url)
    base_domain = parsed_start.netloc

    errors: list[str] = []

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        # Check robots.txt
        disallowed: set[str] = set()
        if respect_robots:
            disallowed = check_robots_txt(client, start_url, timeout)

        seen: set[str] = set()
        urls: list[str] = []
        queue: list[tuple[str, int]] = [(normalize_url(start_url), 0)]
        seen.add(normalize_url(start_url))

        while queue and len(urls) < max_urls:
            current_url, depth = queue.pop(0)

            # Check robots.txt
            if respect_robots and is_blocked_by_robots(current_url, disallowed):
                continue

            try:
                response = client.get(current_url)
                if response.status_code >= 400:
                    errors.append(f"HTTP {response.status_code}: {current_url}")
                    continue

                # Add to discovered URLs
                urls.append(current_url)

                # Don't crawl deeper if at max depth
                if depth >= max_depth:
                    continue

                # Extract links from HTML
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type:
                    continue

                try:
                    extractor = LinkExtractor()
                    extractor.feed(response.text)

                    for link in extractor.links:
                        # Skip non-http links
                        if link.startswith(("#", "javascript:", "mailto:", "tel:")):
                            continue

                        # Resolve relative URLs
                        full_url = urljoin(current_url, link)
                        normalized = normalize_url(full_url)

                        # Skip external links (unless follow_external is True)
                        parsed = urlparse(normalized)
                        if not follow_external and parsed.netloc != base_domain:
                            continue

                        # Skip if already seen
                        if normalized in seen:
                            continue

                        # Apply filters
                        if include_pattern:
                            pattern = re.compile(include_pattern)
                            if not pattern.search(normalized):
                                continue

                        if exclude_pattern:
                            pattern = re.compile(exclude_pattern)
                            if pattern.search(normalized):
                                continue

                        seen.add(normalized)
                        queue.append((normalized, depth + 1))

                except Exception as e:
                    errors.append(f"Failed to parse links from {current_url}: {e}")
                    continue

            except httpx.RequestError as e:
                errors.append(f"Failed to fetch {current_url}: {e}")
                continue
            except Exception as e:
                errors.append(f"Unexpected error crawling {current_url}: {e}")
                continue

    if not urls:
        # If we couldn't crawl anything, at least include the start URL
        urls = [normalize_url(start_url)]
        errors.append(f"Crawl yielded no results, including start URL only")

    return urls[:max_urls], errors


class CrawlEngine(BaseMapper):
    """Maps content by crawling and following links.

    Supports:
    - Recursive link following with configurable depth
    - robots.txt respect
    - Include/exclude patterns
    - External domain handling

    Usage:
        config = MapperConfig(max_depth=2, max_urls=100)
        engine = CrawlEngine(config=config)
        result = engine.map("https://example.com")
        print(result.urls)
    """

    def map(
        self,
        source: str,
        doc_type: DocType = DocType.DOC,
    ) -> MapperResult:
        """Map URLs by crawling.

        Args:
            source: Base URL to start crawling from
            doc_type: Type of documents to map

        Returns:
            MapperResult with discovered URLs
        """
        urls, errors = discover_from_crawl_impl(
            source,
            max_depth=self.config.max_depth,
            max_urls=self.config.max_urls,
            timeout=self.config.timeout,
            include_pattern=self.config.include_pattern,
            exclude_pattern=self.config.exclude_pattern,
            follow_external=self.config.follow_external,
        )

        return MapperResult(
            urls=urls,
            count=len(urls),
            errors=errors,
            metadata={
                "engine": "crawl",
                "source": source,
                "doc_type": doc_type.value,
                "max_depth": self.config.max_depth,
            },
        )


# Backwards compatibility alias
CrawlMapper = CrawlEngine
