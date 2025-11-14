"""CMS utility functions for detection and parsing."""

import re


def detect_cms_from_url(url: str) -> tuple[str | None, dict]:
    """
    Detect CMS platform from URL patterns.

    Supports:
    - Sanity Studio URLs: *.sanity.studio/*
    - Contentful URLs: app.contentful.com/*
    - WordPress URLs: */wp-admin/*

    Args:
        url: URL string to analyze

    Returns:
        Tuple of (platform, metadata_dict):
            - platform: "sanity", "contentful", "wordpress", or None
            - metadata: Extracted info (document_id, space_id, etc.)

    Example:
        >>> detect_cms_from_url("https://myproject.sanity.studio/desk/article;abc123")
        ("sanity", {"document_id": "abc123", "project_hint": "myproject"})

        >>> detect_cms_from_url("https://example.com/blog")
        (None, {})
    """
    # Sanity Studio URLs
    if ".sanity.studio" in url:
        # Extract project name and document ID if possible
        project_match = re.search(r"([^.]+)\.sanity\.studio", url)
        doc_match = re.search(r";([a-zA-Z0-9-]+)", url)

        return "sanity", {
            "project_hint": project_match.group(1) if project_match else None,
            "document_id": doc_match.group(1) if doc_match else None,
        }

    # Contentful URLs
    if "app.contentful.com" in url:
        # Extract space ID and entry ID
        space_match = re.search(r"spaces/([^/]+)", url)
        entry_match = re.search(r"entries/([^/]+)", url)

        return "contentful", {
            "space_id": space_match.group(1) if space_match else None,
            "entry_id": entry_match.group(1) if entry_match else None,
        }

    # WordPress admin URLs
    if "/wp-admin/" in url or "/wp-content/" in url:
        post_match = re.search(r"post=(\d+)", url)

        return "wordpress", {
            "post_id": post_match.group(1) if post_match else None,
        }

    return None, {}


def is_cms_mention(text: str) -> tuple[bool, str | None]:
    """
    Detect CMS mentions in natural language.

    Args:
        text: User input text

    Returns:
        Tuple of (is_cms, platform):
            - is_cms: True if CMS mentioned
            - platform: Detected platform or None

    Example:
        >>> is_cms_mention("Can you fetch this from my Sanity CMS?")
        (True, "sanity")

        >>> is_cms_mention("Grab the article from our CMS")
        (True, None)

        >>> is_cms_mention("Check the website for details")
        (False, None)
    """
    text_lower = text.lower()

    # Platform-specific mentions
    if "sanity" in text_lower:
        return True, "sanity"
    if "contentful" in text_lower:
        return True, "contentful"
    if "wordpress" in text_lower or "wp" in text_lower:
        return True, "wordpress"

    # Generic CMS mentions
    cms_keywords = ["cms", "content management", "content system"]
    if any(keyword in text_lower for keyword in cms_keywords):
        return True, None

    return False, None


def parse_cms_source_url(source_url: str) -> dict | None:
    """
    Parse CMS source URL format: platform/instance/schema/slug

    Args:
        source_url: Source URL string

    Returns:
        Dict with parsed components or None if not valid CMS format

    Example:
        >>> parse_cms_source_url("sanity/prod/article/vibe-coding-guide")
        {"platform": "sanity", "instance": "prod", "schema": "article", "slug": "vibe-coding-guide"}

        >>> parse_cms_source_url("https://example.com/page")
        None
    """
    # Skip if it's a web URL
    if source_url.startswith(("http://", "https://")):
        return None

    # Assume CMS format: platform/instance/schema/slug
    parts = source_url.split("/", 3)
    if len(parts) == 4:
        return {
            "platform": parts[0],
            "instance": parts[1],
            "schema": parts[2],
            "slug": parts[3],
        }

    # Also support legacy 3-part format for backward compatibility
    if len(parts) == 3:
        return {"platform": parts[0], "instance": parts[1], "schema": None, "slug": parts[2]}

    return None
