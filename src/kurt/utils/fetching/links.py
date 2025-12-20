"""
Pure link extraction logic for document content.

This module provides business logic for extracting links from markdown content.
NO DATABASE OPERATIONS - pure regex parsing and URL resolution.

Pattern:
- Business logic (pure): Extract and resolve links from markdown
- Workflow (DB ops): Save links to database in workflows/fetch.py
"""

import logging
import re
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


def extract_document_links(
    content: str, source_url: str, base_url: str | None = None
) -> list[dict]:
    """
    Extract internal document links from markdown content.

    Pure function - uses regex to find markdown links and resolve relative URLs.
    NO database operations - workflows handle saving links.

    Only returns internal links (same domain). Claude interprets anchor_text
    to understand relationship types (prerequisites, related, examples).

    Args:
        content: Markdown content to extract links from
        source_url: Source URL of the document (for resolving relative links)
        base_url: Optional base URL for CMS documents (e.g., "https://technically.dev")
                  Used for domain matching when source_url is a CMS path like "sanity/prod/article/slug"

    Returns:
        List of dicts with:
            - url: Resolved absolute URL
            - anchor_text: Link text (max 500 chars)

    Example:
        >>> content = "See [Getting Started](./getting-started) for details."
        >>> extract_document_links(content, "https://example.com/docs/intro")
        [{'url': 'https://example.com/docs/getting-started', 'anchor_text': 'Getting Started'}]

        >>> # CMS document example
        >>> content = "See [Context Windows](https://technically.dev/universe/context-windows)."
        >>> extract_document_links(content, "sanity/prod/article/my-post", base_url="https://technically.dev")
        [{'url': 'https://technically.dev/universe/context-windows', 'anchor_text': 'Context Windows'}]
    """
    # Regex for markdown links: [text](url)
    # Matches: [anchor text](url) or [anchor text](url "title")
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^\)]+?)(?:\s+['\"]([^'\"]+)['\"])?\)")

    links = []

    # Determine which URL to use for domain matching
    # For CMS documents (source_url like "sanity/prod/article/slug"), use base_url
    # For web documents (source_url like "https://example.com/page"), use source_url
    if base_url and not source_url.startswith(("http://", "https://")):
        # CMS document - use base_url for domain matching
        domain_url = base_url
    else:
        # Web document - use source_url
        domain_url = source_url

    parsed_source = urlparse(domain_url)

    for match in link_pattern.finditer(content):
        anchor_text = match.group(1).strip()
        link_url = match.group(2).strip()

        # Skip non-HTTP links (anchors, mailto, etc.)
        if link_url.startswith("#") or link_url.startswith("mailto:"):
            continue

        # Skip image links (sanity-image-*)
        if link_url.startswith("sanity-image"):
            continue

        # Resolve relative URLs
        if not link_url.startswith(("http://", "https://")):
            # Relative URL - resolve against domain URL
            absolute_url = urljoin(domain_url, link_url)
        else:
            absolute_url = link_url

        # Only include links from the same domain (internal links)
        parsed_link = urlparse(absolute_url)
        if parsed_link.netloc != parsed_source.netloc:
            continue

        links.append(
            {
                "url": absolute_url,
                "anchor_text": anchor_text[:500],  # Truncate to max length
            }
        )

    return links


__all__ = [
    "extract_document_links",
]
