"""Analytics utility functions."""

from urllib.parse import urlparse


def normalize_url_for_analytics(url: str) -> str:
    """
    Normalize URL for analytics matching.

    Removes:
    - Protocol (https://, http://)
    - www. prefix
    - Trailing slashes
    - Query parameters
    - Fragments

    Args:
        url: Full URL to normalize

    Returns:
        Normalized URL (domain + path)

    Examples:
        >>> normalize_url_for_analytics("https://www.docs.company.com/guides/quickstart/?utm=123#step-1")
        'docs.company.com/guides/quickstart'

        >>> normalize_url_for_analytics("http://docs.company.com/guides/quickstart/")
        'docs.company.com/guides/quickstart'

        >>> normalize_url_for_analytics("https://docs.company.com")
        'docs.company.com'
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
