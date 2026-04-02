"""Markdown AST parse provider.

Parses markdown into a structural summary (headings, code blocks, links).
Uses only the Python standard library — no external dependencies.

NOTE: Providers loaded by the ProviderRegistry must be self-contained.
They cannot use relative imports because the ProviderRegistry loads
them via importlib.util.spec_from_file_location (no package context).
"""

import re
from pathlib import Path

from pydantic import BaseModel, Field


class ParseResult(BaseModel):
    """Result from a parse operation."""

    data: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    success: bool = True
    error: str | None = None


class MarkdownAstParser:
    """Parse markdown content into a structural summary.

    Provider metadata attributes are required for ProviderRegistry discovery:
    - name: unique identifier
    - version: semver version
    - url_patterns: fnmatch patterns for auto-selection
    - requires_env: required environment variables
    """

    name = "markdown-ast"
    version = "1.0.0"
    url_patterns = ["*.md", "*.markdown"]
    requires_env: list[str] = []

    def parse(self, source: str) -> ParseResult:
        """Parse markdown into heading structure and content statistics.

        Args:
            source: File path or raw markdown content.

        Returns:
            ParseResult with heading tree and content stats.
        """
        content = source
        path = Path(source)
        if path.exists() and path.is_file():
            content = path.read_text(encoding="utf-8")

        headings = []
        code_blocks = 0
        link_count = 0
        in_code_block = False

        for line in content.split("\n"):
            stripped = line.strip()

            # Track fenced code blocks
            if stripped.startswith("```"):
                if in_code_block:
                    in_code_block = False
                else:
                    in_code_block = True
                    code_blocks += 1
                continue

            if in_code_block:
                continue

            # Extract headings
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
            if heading_match:
                level = len(heading_match.group(1))
                text = heading_match.group(2).strip()
                headings.append({"level": level, "text": text})

            # Count links
            link_count += len(re.findall(r"\[([^\]]+)\]\([^)]+\)", stripped))

        lines = content.split("\n")
        word_count = len(content.split())

        return ParseResult(
            data={
                "headings": headings,
                "heading_count": len(headings),
            },
            metadata={
                "line_count": len(lines),
                "word_count": word_count,
                "code_block_count": code_blocks,
                "link_count": link_count,
                "source": source,
            },
        )
