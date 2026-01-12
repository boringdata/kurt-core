"""Shared utilities for fetch providers."""

from __future__ import annotations

import hashlib

import trafilatura

from kurt.config import load_config


def extract_with_trafilatura(html: str, url: str) -> tuple[str, dict]:
    """
    Extract content and metadata from HTML using trafilatura.

    Args:
        html: Raw HTML content
        url: Source URL (for metadata extraction)

    Returns:
        Tuple of (markdown_content, metadata_dict)

    Raises:
        ValueError: If no content extracted
    """
    metadata = trafilatura.extract_metadata(
        html,
        default_url=url,
        extensive=True,
    )

    content = trafilatura.extract(
        html,
        output_format="markdown",
        include_tables=True,
        include_links=True,
        url=url,
        with_metadata=True,
    )

    if not content:
        raise ValueError(f"No content extracted (page might be empty or paywall blocked): {url}")

    metadata_dict = {}
    if metadata:
        metadata_dict = {
            "title": metadata.title,
            "author": metadata.author,
            "date": metadata.date,
            "description": metadata.description,
            "fingerprint": metadata.fingerprint,
        }

    return content, metadata_dict


def generate_content_path(document_id: str, source_url: str | None = None) -> str:
    """
    Generate a relative path for storing document content.

    If source_url is provided, creates a human-readable path based on the URL:
        domain.com/path/to/page.md

    Otherwise falls back to hash-based path:
        ab/cd/document_id.md

    Args:
        document_id: Unique document identifier (fallback)
        source_url: Optional source URL for readable path

    Returns:
        Relative path like "domain.com/path/to/page.md" or "ab/cd/doc_id.md"
    """
    if source_url:
        return _url_to_path(source_url)

    # Fallback: hash-based path for non-URL sources
    hash_hex = hashlib.md5(document_id.encode()).hexdigest()
    prefix1 = hash_hex[:2]
    prefix2 = hash_hex[2:4]

    # Sanitize document_id for filename (replace problematic chars)
    safe_id = document_id.replace("/", "_").replace(":", "_").replace("?", "_")
    # Truncate if too long (keep last 100 chars which are usually more unique)
    if len(safe_id) > 100:
        safe_id = safe_id[-100:]

    return f"{prefix1}/{prefix2}/{safe_id}.md"


def _url_to_path(url: str) -> str:
    """
    Convert a URL to a filesystem-safe path.

    Examples:
        https://example.com/blog/post  -> example.com/blog/post.md
        https://sub.domain.com/a/b/c   -> sub.domain.com/a/b/c.md
        https://example.com/           -> example.com/index.md
        https://example.com/page?q=1   -> example.com/page.md

    Args:
        url: Source URL

    Returns:
        Relative path like "domain.com/path/to/page.md"
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    domain = parsed.netloc or "unknown"
    path = parsed.path.strip("/")

    # Handle empty path (root URL)
    if not path:
        path = "index"

    # Remove file extension if present (we'll add .md)
    if path.endswith(".html") or path.endswith(".htm"):
        path = path.rsplit(".", 1)[0]

    # Sanitize path components
    safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/.")
    sanitized_path = "".join(c if c in safe_chars else "_" for c in path)

    # Collapse multiple underscores
    while "__" in sanitized_path:
        sanitized_path = sanitized_path.replace("__", "_")

    # Remove trailing underscores from path segments
    sanitized_path = "/".join(seg.strip("_") for seg in sanitized_path.split("/") if seg.strip("_"))

    # Handle edge case of empty path after sanitization
    if not sanitized_path:
        sanitized_path = "index"

    return f"{domain}/{sanitized_path}.md"


def save_content_file(document_id: str, content: str, source_url: str | None = None) -> str:
    """
    Save document content to a markdown file.

    Args:
        document_id: Unique document identifier
        content: Markdown content to save
        source_url: Optional source URL for human-readable path

    Returns:
        Relative path where content was saved
    """
    config = load_config()
    sources_dir = config.get_absolute_sources_path()

    relative_path = generate_content_path(document_id, source_url)
    full_path = sources_dir / relative_path

    # Ensure directory exists
    full_path.parent.mkdir(parents=True, exist_ok=True)

    # Write content
    full_path.write_text(content, encoding="utf-8")

    return relative_path


def load_document_content(content_path: str) -> str | None:
    """
    Load document content from file.

    Args:
        content_path: Relative path to content file (from sources directory)

    Returns:
        Content string, or None if file doesn't exist
    """
    config = load_config()
    sources_dir = config.get_absolute_sources_path()

    full_path = sources_dir / content_path

    if not full_path.exists():
        return None

    return full_path.read_text(encoding="utf-8")
