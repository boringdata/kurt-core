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


def extract_field_value(doc: dict, field_path: str) -> any:
    """
    Extract field value from document using path notation.

    Platform-agnostic field extraction supporting nested paths.
    Works across all CMS platforms (Sanity, Contentful, WordPress, etc.).

    Supports:
    - Simple fields: "title"
    - Nested fields: "slug.current", "category.name", "author.profile.displayName"
    - References: "author->name" (Sanity-specific, resolves reference fields)
    - Arrays: "tags[]"
    - Array of references: "categories[]->title" (Sanity-specific)

    Args:
        doc: Document dictionary from CMS
        field_path: Path to field using dot notation

    Returns:
        Field value or None if not found

    Example:
        >>> doc = {"slug": {"current": "my-article"}, "author": {"name": "Jane"}}
        >>> extract_field_value(doc, "slug.current")
        "my-article"
        >>> extract_field_value(doc, "author.name")
        "Jane"
    """
    if not field_path:
        return None

    # Handle reference resolution (Sanity-specific)
    if "->" in field_path:
        base_path, ref_field = field_path.split("->", 1)
        base_value = extract_field_value(doc, base_path)

        if not base_value:
            return None

        # Handle array of references
        if isinstance(base_value, list):
            return [
                item.get(ref_field)
                for item in base_value
                if isinstance(item, dict) and ref_field in item
            ]
        # Handle single reference
        elif isinstance(base_value, dict):
            return base_value.get(ref_field)
        else:
            return None

    # Handle array notation
    if field_path.endswith("[]"):
        base_path = field_path[:-2]
        value = extract_field_value(doc, base_path)
        return value if isinstance(value, list) else []

    # Handle nested fields with dot notation
    parts = field_path.split(".")
    current = doc

    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None

    return current


def build_document_url(
    doc: dict, content_type: str, base_url: str, content_type_mappings: dict
) -> str | None:
    """
    Build public document URL using CMS schema url_config.

    Platform-agnostic URL building that works across all CMS platforms.
    Uses url_config from content_type_mappings to determine URL structure.

    Supports three url_config types:
    1. static: Fixed path prefix for all documents
       Example: {"type": "static", "path_prefix": "/blog/"}
       Result: https://example.com/blog/my-slug

    2. conditional: Path prefix depends on a document field value
       Example: {"type": "conditional", "field": "category", "mappings": {"news": "/news/", "default": "/posts/"}}
       Result: https://example.com/news/my-slug (if category="news")

    3. None/missing: Use slug directly (legacy behavior)
       Result: https://example.com/my-slug

    Args:
        doc: Full document dictionary from CMS
        content_type: CMS content type/schema name
        base_url: Website base URL (e.g., "https://example.com")
        content_type_mappings: CMS schema configuration with url_config

    Returns:
        Full public URL or None if slug/base_url missing

    Example:
        >>> doc = {"slug": {"current": "my-post"}, "category": "news"}
        >>> mappings = {
        ...     "article": {
        ...         "slug_field": "slug.current",
        ...         "url_config": {
        ...             "type": "conditional",
        ...             "field": "category",
        ...             "mappings": {"news": "/news/", "default": "/blog/"}
        ...         }
        ...     }
        ... }
        >>> build_document_url(doc, "article", "https://example.com", mappings)
        "https://example.com/news/my-post"
    """
    from urllib.parse import urljoin

    if not base_url:
        return None

    # Get schema config
    schema_config = content_type_mappings.get(content_type, {})
    slug_field = schema_config.get("slug_field", "slug")
    url_config = schema_config.get("url_config", {})

    # Extract slug from document
    slug_value = extract_field_value(doc, slug_field)

    # Handle CMS-specific slug objects (e.g., Sanity: {"_type": "slug", "current": "actual-slug"})
    if isinstance(slug_value, dict) and "current" in slug_value:
        slug_value = slug_value["current"]

    if not slug_value or not isinstance(slug_value, str):
        return None

    # No url_config - use slug directly (legacy behavior)
    if not url_config:
        return urljoin(base_url, slug_value)

    config_type = url_config.get("type", "static")

    if config_type == "static":
        # Simple prefix
        path_prefix = url_config.get("path_prefix", "/")
        full_path = f"{path_prefix.rstrip('/')}/{slug_value}"
        return urljoin(base_url, full_path)

    elif config_type == "conditional":
        # Conditional based on field value
        field_path = url_config.get("field")
        mappings = url_config.get("mappings", {})

        if not field_path:
            # Missing field config - fall back to direct slug
            return urljoin(base_url, slug_value)

        # Extract field value from document (supports nested paths)
        field_value = extract_field_value(doc, field_path)

        # Look up path prefix (with fallback to "default")
        path_prefix = mappings.get(str(field_value), mappings.get("default", "/"))
        full_path = f"{path_prefix.rstrip('/')}/{slug_value}"
        return urljoin(base_url, full_path)

    # Unknown config type - fall back to direct slug
    return urljoin(base_url, slug_value)
