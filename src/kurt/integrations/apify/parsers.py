"""
Field mapping and parsing utilities for Apify actor outputs.

Provides flexible extraction of data from various actor response formats.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable


@dataclass
class FieldMapping:
    """
    Maps actor output fields to standardized fields.

    Each field can be:
    - A string: direct field name lookup
    - A list of strings: try each in order, use first non-null
    - A callable: function(item) -> value for complex extraction

    Supports dot notation for nested fields (e.g., "author.name").
    """

    text: str | list[str] | Callable[[dict], str] = field(
        default_factory=lambda: ["text", "content", "title", "postContent", "description", "body"]
    )
    url: str | list[str] | Callable[[dict], str] = field(
        default_factory=lambda: ["url", "postUrl", "link", "profileUrl", "canonicalUrl"]
    )
    id: str | list[str] | Callable[[dict], str] = field(
        default_factory=lambda: ["id", "postId", "objectID", "tweetId", "slug"]
    )
    score: str | list[str] | Callable[[dict], int] = field(
        default_factory=lambda: ["likeCount", "likes", "numLikes", "reactions", "favoriteCount"]
    )
    comments: str | list[str] | Callable[[dict], int] = field(
        default_factory=lambda: ["replyCount", "replies", "commentCount", "numComments"]
    )
    author: str | list[str] | Callable[[dict], str] = field(
        default_factory=lambda: ["author", "username", "authorName", "user", "author.name"]
    )
    timestamp: str | list[str] | Callable[[dict], str] = field(
        default_factory=lambda: ["createdAt", "created_at", "publishedAt", "postedAt", "date", "post_date"]
    )
    title: str | list[str] | Callable[[dict], str] = field(
        default_factory=lambda: ["title", "headline", "name"]
    )


def get_nested(item: dict[str, Any], field_name: str) -> Any:
    """
    Get a possibly nested field value (supports dot notation).

    Args:
        item: Dict to extract from
        field_name: Field name, optionally with dots for nesting (e.g., "author.name")

    Returns:
        Field value or None if not found
    """
    if "." in field_name:
        parts = field_name.split(".")
        value = item
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value
    return item.get(field_name)


def extract_field(
    item: dict[str, Any],
    field_spec: str | list[str] | Callable[[dict], Any],
) -> Any:
    """
    Extract a field value using the field specification.

    Args:
        item: Dict to extract from
        field_spec: Field specification - string, list of strings, or callable

    Returns:
        Extracted value or None
    """
    if callable(field_spec):
        try:
            return field_spec(item)
        except Exception:
            return None
    elif isinstance(field_spec, list):
        for field_name in field_spec:
            value = get_nested(item, field_name)
            if value is not None:
                return value
        return None
    else:
        return get_nested(item, field_spec)


def parse_date(date_str: str | None) -> datetime:
    """
    Parse ISO date string with fallback to now.

    Args:
        date_str: ISO 8601 date string or None

    Returns:
        Parsed datetime or current time as fallback
    """
    if not date_str:
        return datetime.now()
    try:
        if isinstance(date_str, str):
            # Handle Z suffix and various ISO formats
            clean = date_str.replace("Z", "+00:00")
            return datetime.fromisoformat(clean)
        return datetime.now()
    except (ValueError, TypeError):
        return datetime.now()


def extract_author(item: dict[str, Any], mapping: FieldMapping) -> str | None:
    """
    Extract author from item, handling nested author objects.

    Args:
        item: Dict to extract from
        mapping: Field mapping configuration

    Returns:
        Author name string or None
    """
    author_value = extract_field(item, mapping.author)
    if isinstance(author_value, dict):
        return author_value.get("username") or author_value.get("name")
    return author_value


def extract_title(item: dict[str, Any], mapping: FieldMapping, max_length: int = 200) -> str:
    """
    Extract title from item, falling back to truncated text/url.

    Args:
        item: Dict to extract from
        mapping: Field mapping configuration
        max_length: Maximum title length

    Returns:
        Title string
    """
    # Try explicit title field first
    title = extract_field(item, mapping.title)
    if title:
        return str(title)[:max_length]

    # Fall back to first line of text
    text = extract_field(item, mapping.text)
    if text:
        first_line = str(text).split("\n")[0]
        return first_line[:max_length]

    # Fall back to URL
    url = extract_field(item, mapping.url)
    if url:
        return str(url)[:max_length]

    return "Untitled"


@dataclass
class ParsedItem:
    """Standardized parsed item from any Apify actor."""

    id: str
    text: str
    url: str
    title: str
    author: str | None
    timestamp: datetime
    score: int
    comment_count: int
    source: str
    raw: dict[str, Any]


def parse_item(
    item: dict[str, Any],
    source: str,
    mapping: FieldMapping | None = None,
) -> ParsedItem | None:
    """
    Parse a single actor result item into standardized format.

    Args:
        item: Raw item from actor
        source: Source platform name (e.g., "twitter")
        mapping: Field mapping (uses defaults if None)

    Returns:
        ParsedItem or None if item is invalid
    """
    mapping = mapping or FieldMapping()

    text = extract_field(item, mapping.text) or ""
    url = extract_field(item, mapping.url) or ""

    if not text and not url:
        return None

    # Extract ID with fallback to hash
    item_id = extract_field(item, mapping.id)
    if not item_id:
        import hashlib
        item_id = hashlib.md5(f"{url}{text[:100]}".encode()).hexdigest()[:12]

    return ParsedItem(
        id=str(item_id),
        text=str(text),
        url=str(url),
        title=extract_title(item, mapping),
        author=extract_author(item, mapping),
        timestamp=parse_date(extract_field(item, mapping.timestamp)),
        score=int(extract_field(item, mapping.score) or 0),
        comment_count=int(extract_field(item, mapping.comments) or 0),
        source=source,
        raw=item,
    )


def parse_items(
    items: list[dict[str, Any]],
    source: str,
    mapping: FieldMapping | None = None,
) -> list[ParsedItem]:
    """
    Parse multiple actor result items.

    Args:
        items: Raw items from actor
        source: Source platform name
        mapping: Field mapping (uses defaults if None)

    Returns:
        List of parsed items (invalid items are skipped)
    """
    results = []
    for item in items:
        try:
            parsed = parse_item(item, source, mapping)
            if parsed:
                results.append(parsed)
        except Exception:
            continue
    return results
