"""Utility functions for content mapping."""

from typing import Optional
from urllib.parse import urljoin, urlparse


def normalize_url(url: str) -> str:
    """Normalize a URL for consistent matching.

    Args:
        url: URL to normalize

    Returns:
        Normalized URL
    """
    # Remove trailing slashes, lowercase domain
    parsed = urlparse(url)
    normalized = f"{parsed.scheme}://{parsed.netloc.lower()}{parsed.path}"
    if parsed.query:
        normalized += f"?{parsed.query}"
    if parsed.fragment:
        normalized += f"#{parsed.fragment}"
    return normalized


def is_internal_url(base_url: str, check_url: str) -> bool:
    """Check if a URL is internal to a domain.

    Args:
        base_url: Base/source URL
        check_url: URL to check

    Returns:
        True if URL is internal, False otherwise
    """
    base_domain = urlparse(base_url).netloc.lower()
    check_domain = urlparse(check_url).netloc.lower()
    return base_domain == check_domain


def extract_domain(url: str) -> str:
    """Extract domain from URL.

    Args:
        url: URL to extract from

    Returns:
        Domain name
    """
    parsed = urlparse(url)
    return parsed.netloc.lower()


def should_include_url(
    url: str,
    include_pattern: Optional[str] = None,
    exclude_pattern: Optional[str] = None,
) -> bool:
    """Check if URL matches inclusion criteria.

    Args:
        url: URL to check
        include_pattern: Regex pattern for inclusion
        exclude_pattern: Regex pattern for exclusion

    Returns:
        True if URL should be included, False otherwise
    """
    import re

    if exclude_pattern:
        if re.search(exclude_pattern, url):
            return False

    if include_pattern:
        return bool(re.search(include_pattern, url))

    return True


def relative_to_absolute_url(base: str, relative: str) -> Optional[str]:
    """Convert relative URL to absolute.

    Args:
        base: Base URL
        relative: Relative URL

    Returns:
        Absolute URL or None if invalid
    """
    try:
        absolute = urljoin(base, relative)
        # Validate that result is a proper URL
        parsed = urlparse(absolute)
        if parsed.scheme in ("http", "https"):
            return absolute
    except Exception:
        pass

    return None


def get_url_depth(base_url: str, target_url: str) -> int:
    """Calculate depth of target URL relative to base.

    Args:
        base_url: Base URL
        target_url: Target URL

    Returns:
        Depth level (0 for same path, 1+ for deeper)
    """
    base_path = urlparse(base_url).path
    target_path = urlparse(target_url).path

    # Count path segments
    base_segments = [s for s in base_path.split("/") if s]
    target_segments = [s for s in target_path.split("/") if s]

    if not target_segments:
        return 0

    if not base_segments:
        return len(target_segments)

    # Find common prefix
    common = 0
    for b, t in zip(base_segments, target_segments):
        if b == t:
            common += 1
        else:
            break

    return len(target_segments) - common
