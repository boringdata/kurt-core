"""URL utility functions."""

from typing import Optional
from urllib.parse import urlparse


def is_single_page_url(url: str) -> bool:
    """
    Determine if URL points to a single page or a domain/section.

    Single page indicators:
    - Has path beyond root (e.g., /blog/my-post)
    - Path doesn't end with / (unless it's a specific page)
    - Not just domain.com or domain.com/

    Returns True if single page, False if likely multi-page source.

    Example:
        >>> is_single_page_url("https://example.com/blog/my-post")
        True
        >>> is_single_page_url("https://example.com/blog/")
        False
        >>> is_single_page_url("https://example.com")
        False
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    # Empty path or just a section (like /blog/) = multi-page
    if not path or path.endswith("/"):
        return False

    # Has meaningful path segments = likely single page
    # Exception: common index patterns like /blog, /docs might be multi-page
    common_index_patterns = ["blog", "docs", "documentation", "articles", "posts", "news", "guides"]
    path_parts = path.split("/")

    # If it's just one segment and matches index pattern, treat as multi-page
    if len(path_parts) == 1 and path_parts[0].lower() in common_index_patterns:
        return False

    # Otherwise, assume single page
    return True


def get_url_depth(url: Optional[str]) -> int:
    """
    Calculate the depth of a URL based on path segments.

    The depth is the number of path segments after the domain.
    Root or domain-only URLs have depth 0.

    Args:
        url: URL string to analyze (can be None)

    Returns:
        Integer representing the depth (0 if url is None)

    Example:
        >>> get_url_depth("https://example.com")
        0
        >>> get_url_depth("https://example.com/")
        0
        >>> get_url_depth("https://example.com/docs")
        1
        >>> get_url_depth("https://example.com/docs/guide")
        2
        >>> get_url_depth("https://example.com/docs/guide/intro")
        3
        >>> get_url_depth(None)
        0
    """
    if not url:
        return 0

    parsed = urlparse(url)
    path = parsed.path.strip("/")

    # Empty path = root = depth 0
    if not path:
        return 0

    # Count path segments
    segments = [s for s in path.split("/") if s]
    return len(segments)


# Removed unused functions:
# - group_urls_by_path_prefix: Defined and tested but never used in production code
# - normalize_url: Duplicate of normalize_url in ingestion/map.py (which is actively used)
