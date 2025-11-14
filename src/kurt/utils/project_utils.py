"""Project metadata utilities.

This module provides utilities for extracting and parsing project metadata
from markdown files (e.g., project.md).
"""

import re
from typing import Optional


def extract_section(content: str, header: str) -> Optional[str]:
    """
    Extract content between markdown headers.

    Finds a markdown header (## Header Name) and returns the first non-empty
    line of content that follows it, stopping at the next header.

    Args:
        content: Full markdown content
        header: Header name (without ##)

    Returns:
        First non-empty line after the header, or None if header not found
        or no content follows it.

    Examples:
        >>> content = "## Goal\\nCreate a documentation site\\n## Other\\nContent"
        >>> extract_section(content, "Goal")
        'Create a documentation site'

        >>> content = "## Goal\\n\\n## Other\\nContent"
        >>> extract_section(content, "Goal")
        None
    """
    # Find the header
    pattern = rf"^## {re.escape(header)}\s*$"
    lines = content.split("\n")

    found = False
    for line in lines:
        if re.match(pattern, line):
            found = True
            continue

        # If we found the header, return the first non-empty line
        if found:
            # Stop if we hit another header
            if line.startswith("##"):
                return None
            # Return first non-empty line
            stripped = line.strip()
            if stripped:
                return stripped

    return None
