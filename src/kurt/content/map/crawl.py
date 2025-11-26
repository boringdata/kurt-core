"""
Web crawling functionality for Kurt.

This module handles discovering URLs via focused crawling when no sitemap is available.
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
    progress=None,
    task_id=None,
) -> list[str]:
    """
    Crawl a website using trafilatura's focused_crawler.

    This is used as a fallback when no sitemap is found or when explicit
    crawling is requested with --max-depth.

    Args:
        homepage: Starting URL for crawl
        max_depth: Maximum crawl depth (approximate - trafilatura uses max_seen_urls)
        max_pages: Maximum number of pages to discover
        allow_external: If True, follow external links (outside domain)
        include_patterns: Include URL patterns (glob)
        exclude_patterns: Exclude URL patterns (glob)
        progress: Optional progress object for status updates
        task_id: Optional task ID for progress updates

    Returns:
        List of discovered URLs (strings)

    Note:
        - Trafilatura's focused_crawler doesn't have explicit depth control,
          so we use max_seen_urls as a proxy for depth
        - The crawler automatically respects robots.txt
        - Navigation pages (archives, categories) are prioritized
    """
    # Convert max_depth to max_seen_urls
    # Depth 1 = ~10 URLs, Depth 2 = ~50 URLs, Depth 3+ = ~100+ URLs
    depth_to_urls = {
        1: 10,
        2: 50,
        3: 100,
    }
    max_seen_urls = depth_to_urls.get(max_depth, max_depth * 50) if max_depth else 100
    max_seen_urls = min(max_seen_urls, max_pages)  # Respect max_pages limit

    if progress and task_id is not None:
        progress.update(
            task_id,
            description=f"Crawling website (max depth: {max_depth}, max pages: {max_pages})...",
        )

    logger.info(f"Crawling {homepage} with max_seen_urls={max_seen_urls} (depth={max_depth})")

    # Run focused crawler
    # Note: trafilatura's focused_crawler is blocking and doesn't provide progress callbacks
    # We'll show status before and after
    to_visit, known_links = focused_crawler(
        homepage=homepage,
        max_seen_urls=max_seen_urls,
        max_known_urls=max_pages,
    )

    # Show crawl completion
    if progress and task_id is not None:
        progress.update(
            task_id,
            description=f"Crawl complete - discovered {len(known_links)} URLs, filtering...",
        )

    # Convert to list
    all_urls = list(known_links)

    # Filter external links if not allowed
    if not allow_external:
        if progress and task_id is not None:
            progress.update(
                task_id, description=f"Filtering external URLs from {len(all_urls)} discovered..."
            )

        homepage_domain = urlparse(homepage).netloc
        filtered_urls = []
        for url in all_urls:
            url_domain = urlparse(url).netloc
            if url_domain == homepage_domain:
                filtered_urls.append(url)
        all_urls = filtered_urls
        logger.info(f"Filtered to {len(all_urls)} internal URLs (allow_external=False)")

    # Apply include/exclude patterns
    if include_patterns:
        if progress and task_id is not None:
            progress.update(
                task_id, description=f"Applying include patterns to {len(all_urls)} URLs..."
            )

        filtered = []
        for url in all_urls:
            if any(fnmatch(url, pattern) for pattern in include_patterns):
                filtered.append(url)
        all_urls = filtered
        logger.info(f"Applied include patterns: {len(all_urls)} URLs match")

    if exclude_patterns:
        if progress and task_id is not None:
            progress.update(
                task_id, description=f"Applying exclude patterns to {len(all_urls)} URLs..."
            )

        filtered = []
        for url in all_urls:
            if not any(fnmatch(url, pattern) for pattern in exclude_patterns):
                filtered.append(url)
        all_urls = filtered
        logger.info(f"Applied exclude patterns: {len(all_urls)} URLs remain")

    # Apply final limit
    if len(all_urls) > max_pages:
        all_urls = all_urls[:max_pages]
        logger.info(f"Limited to {max_pages} URLs")

    if progress and task_id is not None:
        progress.update(task_id, description=f"Crawl discovered {len(all_urls)} URLs")

    logger.info(f"Crawling discovered {len(all_urls)} URLs")
    return all_urls
