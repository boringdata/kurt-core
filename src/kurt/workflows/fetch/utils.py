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


def generate_content_path(document_id: str) -> str:
    """
    Generate a relative path for storing document content.

    Uses a 2-level hash prefix directory structure to avoid having
    too many files in a single directory.

    Args:
        document_id: Unique document identifier

    Returns:
        Relative path like "ab/cd/document_id.md"
    """
    # Create hash prefix from document_id for directory sharding
    hash_hex = hashlib.md5(document_id.encode()).hexdigest()
    prefix1 = hash_hex[:2]
    prefix2 = hash_hex[2:4]

    # Sanitize document_id for filename (replace problematic chars)
    safe_id = document_id.replace("/", "_").replace(":", "_").replace("?", "_")
    # Truncate if too long (keep last 100 chars which are usually more unique)
    if len(safe_id) > 100:
        safe_id = safe_id[-100:]

    return f"{prefix1}/{prefix2}/{safe_id}.md"


def save_content_file(document_id: str, content: str) -> str:
    """
    Save document content to a markdown file.

    Args:
        document_id: Unique document identifier
        content: Markdown content to save

    Returns:
        Relative path where content was saved
    """
    config = load_config()
    sources_dir = config.get_absolute_sources_path()

    relative_path = generate_content_path(document_id)
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
