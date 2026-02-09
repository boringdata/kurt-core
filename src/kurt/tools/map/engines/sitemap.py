"""Sitemap-based content mapping engine."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Optional
from urllib.parse import urlparse

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


def discover_from_sitemap_impl(
    base_url: str,
    *,
    sitemap_path: Optional[str] = None,
    timeout: float = 30.0,
    max_urls: int = 1000,
    include_pattern: Optional[str] = None,
    exclude_pattern: Optional[str] = None,
) -> tuple[list[str], list[str]]:
    """
    Discover URLs from sitemap.xml.

    Args:
        base_url: Base URL of the website
        sitemap_path: Custom sitemap path (e.g., '/custom-sitemap.xml')
        timeout: HTTP request timeout
        max_urls: Maximum URLs to return
        include_pattern: Regex pattern for URLs to include
        exclude_pattern: Regex pattern for URLs to exclude

    Returns:
        Tuple of (discovered URLs, error messages)
    """
    import re

    parsed = urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    sitemap_urls: list[str] = []
    errors: list[str] = []

    # If custom sitemap path provided, use it first
    if sitemap_path:
        custom_url = f"{base}{sitemap_path}" if sitemap_path.startswith("/") else sitemap_path
        sitemap_urls.append(custom_url)
    else:
        # Try robots.txt for sitemap location
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.get(f"{base}/robots.txt")
                if response.status_code == 200:
                    for line in response.text.split("\n"):
                        if line.lower().startswith("sitemap:"):
                            sitemap_url = line.split(":", 1)[1].strip()
                            sitemap_urls.append(sitemap_url)
        except Exception:
            pass

        # Add common sitemap paths as fallback
        common_paths = ["/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml"]
        for path in common_paths:
            url = f"{base}{path}"
            if url not in sitemap_urls:
                sitemap_urls.append(url)

    all_urls: list[str] = []
    seen_urls: set[str] = set()

    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for sitemap_url in sitemap_urls:
            if len(all_urls) >= max_urls:
                break

            try:
                response = client.get(sitemap_url)
                if response.status_code != 200:
                    continue

                root = ET.fromstring(response.content)

                # Check for sitemap index
                sitemaps = root.findall(".//sm:sitemap", ns)
                if sitemaps:
                    # Process child sitemaps
                    for sitemap in sitemaps:
                        if len(all_urls) >= max_urls:
                            break
                        loc = sitemap.find("sm:loc", ns)
                        if loc is None or not loc.text:
                            continue
                        child_sitemap_url = loc.text.strip()
                        try:
                            child_response = client.get(child_sitemap_url)
                            if child_response.status_code == 200:
                                child_root = ET.fromstring(child_response.content)
                                urls = child_root.findall(".//sm:url", ns)
                                for url_elem in urls:
                                    if len(all_urls) >= max_urls:
                                        break
                                    loc_elem = url_elem.find("sm:loc", ns)
                                    if loc_elem is not None and loc_elem.text:
                                        page_url = normalize_url(loc_elem.text.strip())
                                        if page_url not in seen_urls:
                                            seen_urls.add(page_url)
                                            all_urls.append(page_url)
                        except Exception as e:
                            errors.append(f"Failed to fetch child sitemap {child_sitemap_url}: {e}")
                            continue
                else:
                    # Process URLs directly
                    urls = root.findall(".//sm:url", ns)
                    for url_elem in urls:
                        if len(all_urls) >= max_urls:
                            break
                        loc_elem = url_elem.find("sm:loc", ns)
                        if loc_elem is not None and loc_elem.text:
                            page_url = normalize_url(loc_elem.text.strip())
                            if page_url not in seen_urls:
                                seen_urls.add(page_url)
                                all_urls.append(page_url)

                if all_urls:
                    # Successfully found URLs from this sitemap
                    break

            except ET.ParseError as e:
                errors.append(f"Failed to parse sitemap {sitemap_url}: {e}")
                continue
            except httpx.RequestError as e:
                errors.append(f"Failed to fetch sitemap {sitemap_url}: {e}")
                continue

    if not all_urls:
        errors.append(f"No sitemap found for {base_url}")
        return [], errors

    # Apply filters
    if include_pattern:
        pattern = re.compile(include_pattern)
        all_urls = [url for url in all_urls if pattern.search(url)]

    if exclude_pattern:
        pattern = re.compile(exclude_pattern)
        all_urls = [url for url in all_urls if not pattern.search(url)]

    return all_urls[:max_urls], errors


class SitemapEngine(BaseMapper):
    """Maps content by discovering and parsing sitemaps.xml.

    Supports:
    - Standard sitemap.xml files
    - Sitemap index files (sitemap_index.xml)
    - Custom sitemap paths
    - robots.txt sitemap discovery

    Usage:
        engine = SitemapEngine()
        result = engine.map("https://example.com")
        print(result.urls)
    """

    name = "sitemap"
    version = "1.0.0"
    url_patterns = ["*/sitemap.xml", "*/sitemap*.xml"]
    requires_env: list[str] = []

    def map(
        self,
        source: str,
        doc_type: DocType = DocType.DOC,
    ) -> MapperResult:
        """Map URLs from sitemap.

        Args:
            source: Base URL to discover sitemap from
            doc_type: Type of documents to map

        Returns:
            MapperResult with discovered URLs
        """
        urls, errors = discover_from_sitemap_impl(
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
                "engine": "sitemap",
                "source": source,
                "doc_type": doc_type.value,
            },
        )


# Backwards compatibility alias
SitemapMapper = SitemapEngine
