"""URL utility functions.

This module provides centralized URL parsing and normalization utilities.
Different normalization strategies exist for different purposes:

1. normalize_url_for_deduplication: Removes query params & anchors (prevents duplicate documents)
2. normalize_url_for_matching: Lowercase + strip trailing slash (fuzzy matching in clusters)
3. normalize_url_for_analytics: Full normalization including www and protocol (analytics matching)
"""

from typing import Optional
from urllib.parse import urlparse, urlunparse

# ============================================================================
# URL Analysis Functions
# ============================================================================


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


# ============================================================================
# URL Normalization Functions
# ============================================================================


def normalize_url_for_deduplication(url: str) -> str:
    """
    Normalize URL for deduplication by removing query params and anchors.

    This prevents creating duplicate documents for URLs that only differ
    by query parameters or anchor fragments.

    Use case: URL discovery, sitemap parsing, preventing duplicate documents

    Args:
        url: URL to normalize

    Returns:
        Normalized URL without query parameters or anchors

    Example:
        >>> normalize_url_for_deduplication("https://example.com/blog?page=1#latest")
        'https://example.com/blog'
        >>> normalize_url_for_deduplication("https://example.com/blog")
        'https://example.com/blog'
    """
    parsed = urlparse(url)
    # Remove fragment (anchor) and query string
    normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
    return normalized


def normalize_url_for_matching(url: str) -> str:
    """
    Normalize URL for fuzzy matching by lowercasing and stripping trailing slash.

    Use case: Cluster matching, finding similar URLs across different sources

    Args:
        url: URL to normalize

    Returns:
        Normalized URL (lowercase, no trailing slash)

    Example:
        >>> normalize_url_for_matching("https://Example.com/Blog/")
        'https://example.com/blog'
        >>> normalize_url_for_matching("HTTPS://EXAMPLE.COM/BLOG")
        'https://example.com/blog'
    """
    if not url:
        return ""

    # Lowercase for case-insensitive matching
    normalized = url.lower()

    # Strip trailing slash (unless it's root path)
    if normalized.endswith("/") and len(normalized) > 1:
        parsed = urlparse(normalized)
        if parsed.path != "/":
            normalized = normalized.rstrip("/")

    return normalized


def normalize_url_for_analytics(url: str) -> str:
    """
    Normalize URL for analytics matching (removes protocol, www, params).

    This aggressive normalization is used to match URLs from analytics
    platforms (like PostHog) with documents in the database, regardless
    of protocol or www prefix differences.

    Use case: Analytics integration, tracking URL matching

    Args:
        url: Full URL to normalize

    Returns:
        Normalized URL (domain + path only, no protocol/www/params)

    Example:
        >>> normalize_url_for_analytics("https://www.docs.company.com/guides/quickstart/?utm=123#step-1")
        'docs.company.com/guides/quickstart'
        >>> normalize_url_for_analytics("http://docs.company.com/guides/quickstart/")
        'docs.company.com/guides/quickstart'
        >>> normalize_url_for_analytics("https://www.example.com")
        'example.com'
    """
    if not url:
        return ""

    parsed = urlparse(url)

    # Remove www. from domain
    domain = parsed.netloc.replace("www.", "")

    # Remove trailing slash from path (unless it's root)
    path = parsed.path.rstrip("/") if parsed.path != "/" else ""

    # Combine domain + path (ignore query params and fragments)
    normalized = f"{domain}{path}"

    return normalized


# ============================================================================
# Domain Utilities
# ============================================================================


def strip_www_prefix(domain: str) -> str:
    """
    Strip 'www.' prefix from domain for consistency.

    This ensures www.example.com and example.com map to the same location.

    Args:
        domain: Domain string (may or may not have www prefix)

    Returns:
        Domain without www prefix

    Example:
        >>> strip_www_prefix("www.example.com")
        'example.com'
        >>> strip_www_prefix("example.com")
        'example.com'
        >>> strip_www_prefix("www.subdomain.example.com")
        'subdomain.example.com'
    """
    if domain.startswith("www."):
        return domain[4:]  # Remove "www."
    return domain


def get_domain_from_url(url: str, strip_www: bool = True) -> str:
    """
    Extract domain (netloc) from URL.

    Args:
        url: Full URL
        strip_www: If True, remove www. prefix (default: True)

    Returns:
        Domain string

    Example:
        >>> get_domain_from_url("https://www.example.com/path/to/page")
        'example.com'
        >>> get_domain_from_url("https://www.example.com/path/to/page", strip_www=False)
        'www.example.com'
        >>> get_domain_from_url("https://subdomain.example.com:8080/path")
        'subdomain.example.com:8080'
    """
    parsed = urlparse(url)
    domain = parsed.netloc or "unknown"

    if strip_www:
        return strip_www_prefix(domain)

    return domain
