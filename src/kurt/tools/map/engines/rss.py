"""RSS feed-based content mapping engine."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx

from kurt.tools.map.core import BaseMapper, MapperResult
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


def discover_from_rss_impl(
    source_url: str,
    *,
    timeout: float = 30.0,
    max_urls: int = 1000,
    include_pattern: Optional[str] = None,
    exclude_pattern: Optional[str] = None,
) -> tuple[list[str], list[str]]:
    """
    Discover URLs from RSS/Atom feeds.

    Args:
        source_url: URL to the RSS/Atom feed or page to discover feeds from
        timeout: HTTP request timeout
        max_urls: Maximum URLs to return
        include_pattern: Regex pattern for URLs to include
        exclude_pattern: Regex pattern for URLs to exclude

    Returns:
        Tuple of (discovered URLs, error messages)
    """
    import re

    parsed = urlparse(source_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    feed_urls: list[str] = []
    errors: list[str] = []

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        # First, try to detect if source_url is itself a feed or a page with feed links
        try:
            response = client.get(source_url)
            if response.status_code != 200:
                errors.append(f"Failed to fetch {source_url}: HTTP {response.status_code}")
                return [], errors

            content_type = response.headers.get("content-type", "").lower()

            # Check if this is directly a feed
            if any(ct in content_type for ct in ["xml", "rss", "atom"]):
                feed_urls.append(source_url)
            elif "html" in content_type:
                # Look for feed links in HTML
                html = response.text
                # Look for RSS/Atom link tags
                link_pattern = re.compile(
                    r'<link[^>]+type=["\']application/(rss|atom)\+xml["\'][^>]*href=["\']([^"\']+)["\']',
                    re.IGNORECASE,
                )
                matches = link_pattern.findall(html)
                for _, href in matches:
                    feed_url = urljoin(source_url, href)
                    if feed_url not in feed_urls:
                        feed_urls.append(feed_url)

                # Also try common feed paths
                common_paths = ["/feed", "/feed.xml", "/rss", "/rss.xml", "/atom.xml", "/feed/atom"]
                for path in common_paths:
                    url = f"{base}{path}"
                    if url not in feed_urls:
                        feed_urls.append(url)
            else:
                # Try treating source_url as a feed anyway
                feed_urls.append(source_url)

        except httpx.RequestError as e:
            errors.append(f"Failed to fetch {source_url}: {e}")
            return [], errors

        # Now process each feed URL
        all_urls: list[str] = []
        seen_urls: set[str] = set()

        for feed_url in feed_urls:
            if len(all_urls) >= max_urls:
                break

            try:
                if feed_url != source_url:
                    response = client.get(feed_url)
                    if response.status_code != 200:
                        continue

                # Parse the feed
                try:
                    root = ET.fromstring(response.content)
                except ET.ParseError:
                    continue

                # Handle RSS 2.0 format
                for item in root.findall(".//item"):
                    if len(all_urls) >= max_urls:
                        break
                    link = item.find("link")
                    if link is not None and link.text:
                        item_url = normalize_url(link.text.strip())
                        if item_url and item_url not in seen_urls:
                            seen_urls.add(item_url)
                            all_urls.append(item_url)

                # Handle Atom format
                atom_ns = {"atom": "http://www.w3.org/2005/Atom"}
                for entry in root.findall(".//atom:entry", atom_ns):
                    if len(all_urls) >= max_urls:
                        break
                    link = entry.find("atom:link[@rel='alternate']", atom_ns)
                    if link is None:
                        link = entry.find("atom:link", atom_ns)
                    if link is not None:
                        href = link.get("href")
                        if href:
                            item_url = normalize_url(href.strip())
                            if item_url and item_url not in seen_urls:
                                seen_urls.add(item_url)
                                all_urls.append(item_url)

                # Also check for entries without namespace (some Atom feeds)
                for entry in root.findall(".//entry"):
                    if len(all_urls) >= max_urls:
                        break
                    link = entry.find("link[@rel='alternate']")
                    if link is None:
                        link = entry.find("link")
                    if link is not None:
                        href = link.get("href")
                        if href:
                            item_url = normalize_url(href.strip())
                            if item_url and item_url not in seen_urls:
                                seen_urls.add(item_url)
                                all_urls.append(item_url)

                if all_urls:
                    # Successfully found URLs from this feed
                    break

            except Exception as e:
                errors.append(f"Failed to process feed {feed_url}: {e}")
                continue

    if not all_urls:
        errors.append(f"No feed entries found for {source_url}")
        return [], errors

    # Apply filters
    if include_pattern:
        pattern = re.compile(include_pattern)
        all_urls = [url for url in all_urls if pattern.search(url)]

    if exclude_pattern:
        pattern = re.compile(exclude_pattern)
        all_urls = [url for url in all_urls if not pattern.search(url)]

    return all_urls[:max_urls], errors


class RssEngine(BaseMapper):
    """Maps content by discovering and parsing RSS/Atom feeds.

    Supports:
    - RSS 2.0 feeds
    - Atom feeds
    - Auto-discovery of feed URLs from HTML pages
    - Common feed path detection

    Usage:
        engine = RssEngine()
        result = engine.map("https://example.com/blog")
        print(result.urls)
    """

    name = "rss"
    version = "1.0.0"
    url_patterns = ["*/feed", "*/feed.xml", "*/rss", "*/rss.xml", "*.xml"]
    requires_env: list[str] = []

    from kurt.tools.map.providers.rss.config import RssProviderConfig
    ConfigModel = RssProviderConfig

    def map(
        self,
        source: str,
        doc_type: DocType = DocType.DOC,
    ) -> MapperResult:
        """Map URLs from RSS feeds.

        Args:
            source: URL to discover feeds from
            doc_type: Type of documents to map

        Returns:
            MapperResult with discovered URLs from feed entries
        """
        urls, errors = discover_from_rss_impl(
            source,
            timeout=self.config.timeout,
            max_urls=self.config.max_urls,
            include_pattern=self.config.include_pattern,
            exclude_pattern=self.config.exclude_pattern,
        )

        return MapperResult(
            urls=urls,
            count=len(urls),
            errors=errors,
            metadata={
                "engine": "rss",
                "source": source,
                "doc_type": doc_type.value,
            },
        )


# Backwards compatibility alias
RssMapper = RssEngine
