"""
Web crawling functionality.

Discovers URLs via focused crawling when no sitemap is available.
"""

import logging
from fnmatch import fnmatch
from urllib.parse import urlparse

from trafilatura.spider import focused_crawler

logger = logging.getLogger(__name__)


def crawl_website(
    homepage: str,
    max_depth: int = 2,
    max_pages: int = 100,
    allow_external: bool = False,
    include_patterns: tuple = (),
    exclude_patterns: tuple = (),
) -> list[str]:
    """
    Crawl a website using trafilatura's focused_crawler.

    This is used as a fallback when no sitemap is found.

    Args:
        homepage: Starting URL for crawl
        max_depth: Maximum crawl depth (approximate - uses max_seen_urls)
        max_pages: Maximum number of pages to discover
        allow_external: If True, follow external links
        include_patterns: Include URL patterns (glob)
        exclude_patterns: Exclude URL patterns (glob)

    Returns:
        List of discovered URLs (strings)

    Note:
        - Trafilatura's focused_crawler doesn't have explicit depth control
        - The crawler automatically respects robots.txt
    """
    # Convert max_depth to max_seen_urls
    depth_to_urls = {1: 10, 2: 50, 3: 100}
    max_seen_urls = depth_to_urls.get(max_depth, max_depth * 50) if max_depth else 100
    max_seen_urls = min(max_seen_urls, max_pages)

    logger.info(f"Crawling {homepage} with max_seen_urls={max_seen_urls} (depth={max_depth})")

    # Run focused crawler
    to_visit, known_links = focused_crawler(
        homepage=homepage,
        max_seen_urls=max_seen_urls,
        max_known_urls=max_pages,
    )

    # Convert to list
    all_urls = list(known_links)

    # Filter external links if not allowed
    if not allow_external:
        homepage_domain = urlparse(homepage).netloc
        all_urls = [url for url in all_urls if urlparse(url).netloc == homepage_domain]
        logger.info(f"Filtered to {len(all_urls)} internal URLs")

    # Apply include patterns
    if include_patterns:
        all_urls = [url for url in all_urls if any(fnmatch(url, p) for p in include_patterns)]
        logger.info(f"Applied include patterns: {len(all_urls)} URLs match")

    # Apply exclude patterns
    if exclude_patterns:
        all_urls = [url for url in all_urls if not any(fnmatch(url, p) for p in exclude_patterns)]
        logger.info(f"Applied exclude patterns: {len(all_urls)} URLs remain")

    # Apply final limit
    if len(all_urls) > max_pages:
        all_urls = all_urls[:max_pages]
        logger.info(f"Limited to {max_pages} URLs")

    logger.info(f"Crawling discovered {len(all_urls)} URLs")
    return all_urls
