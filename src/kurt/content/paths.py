"""Content path utilities.

This module provides path-related utilities for content storage that can be used
across different commands (fetch, index, map).
"""

from pathlib import Path
from urllib.parse import urlparse

from kurt.config.base import KurtConfig
from kurt.utils.url_utils import get_domain_from_url


def parse_source_identifier(source_url: str) -> tuple[str, dict]:
    """
    Parse source identifier to determine if it's a web URL or CMS identifier.

    Distinguishes between:
    - Web URLs: http:// or https:// prefixed URLs
    - CMS identifiers: platform/instance/schema/slug format

    Note: This is different from utils.source_detection.detect_source_type(),
    which distinguishes between URLs, files, and directories.

    Args:
        source_url: Source URL or CMS identifier string

    Returns:
        Tuple of (source_type, parsed_data):
            - source_type: 'web' or 'cms'
            - parsed_data: For web: {'url': url}, For CMS: {'platform': ..., 'instance': ..., 'schema': ..., 'slug': ...}

    Example:
        >>> parse_source_identifier("https://example.com/page")
        ('web', {'url': 'https://example.com/page'})

        >>> parse_source_identifier("sanity/prod/article/vibe-coding-guide")
        ('cms', {'platform': 'sanity', 'instance': 'prod', 'schema': 'article', 'slug': 'vibe-coding-guide'})
    """
    if source_url.startswith(("http://", "https://")):
        return "web", {"url": source_url}

    # Assume CMS format: platform/instance/schema/slug
    parts = source_url.split("/", 3)
    if len(parts) == 4:
        return "cms", {
            "platform": parts[0],
            "instance": parts[1],
            "schema": parts[2],
            "slug": parts[3],
        }

    # Also support legacy 3-part format for backward compatibility
    if len(parts) == 3:
        return "cms", {"platform": parts[0], "instance": parts[1], "schema": None, "slug": parts[2]}

    raise ValueError(
        f"Invalid source URL format: {source_url}. "
        f"Expected either http(s):// URL or platform/instance/schema/slug format"
    )


def create_cms_content_path(platform: str, instance: str, doc_id: str, config: KurtConfig) -> Path:
    """
    Create filesystem path for CMS content.

    Args:
        platform: CMS platform name (sanity, contentful, etc)
        instance: Instance name (prod, staging, etc)
        doc_id: Document ID
        config: Kurt configuration

    Returns:
        Path object for content file

    Example:
        >>> create_cms_content_path("sanity", "prod", "abc-123", config)
        Path("sources/cms/sanity/prod/abc-123.md")
    """
    source_base = config.get_absolute_sources_path()
    content_path = source_base / "cms" / platform / instance / f"{doc_id}.md"
    return content_path


def create_content_path(url: str, config: KurtConfig) -> Path:
    """
    Create filesystem path for storing web content.

    Format: {source_path}/{domain}/{subdomain}/{path}/page_name.md

    Uses centralized get_domain_from_url() to ensure consistent domain
    extraction and www-stripping across the codebase.

    Example:
        url: https://docs.example.com/guide/getting-started
        → sources/docs.example.com/guide/getting-started.md

        url: https://example.com/
        → sources/example.com/index.md

        url: https://www.example.com/
        → sources/example.com/index.md (www stripped for consistency)
    """
    # Get domain using centralized utility (automatically strips www)
    domain = get_domain_from_url(url, strip_www=True)

    # Get path components
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    # If empty path, use 'index'
    if not path:
        path = "index"

    # If path ends with /, append 'index'
    if path.endswith("/"):
        path = path + "index"

    # Add .md extension if not present
    if not path.endswith(".md"):
        path = path + ".md"

    # Build full path: source_path/domain/path
    source_base = config.get_absolute_sources_path()
    content_path = source_base / domain / path

    return content_path
