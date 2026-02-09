"""Frontmatter parse provider.

Parses YAML frontmatter from markdown files. Demonstrates a provider
with no external dependencies (requires_env is empty).

NOTE: Providers loaded by the ProviderRegistry must be self-contained.
They cannot use relative imports because the ProviderRegistry loads
them via importlib.util.spec_from_file_location (no package context).
"""

from pathlib import Path

from pydantic import BaseModel, Field

# yaml is in the standard library since Python 3
import yaml


class ParseResult(BaseModel):
    """Result from a parse operation."""

    data: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    success: bool = True
    error: str | None = None


class FrontmatterParser:
    """Parse YAML frontmatter from markdown files.

    Provider metadata attributes are required for ProviderRegistry discovery:
    - name: unique identifier
    - version: semver version
    - url_patterns: fnmatch patterns for auto-selection
    - requires_env: required environment variables
    """

    name = "frontmatter"
    version = "1.0.0"
    url_patterns = ["*.md", "*.markdown", "*.mdx"]
    requires_env: list[str] = []

    def parse(self, source: str) -> ParseResult:
        """Parse YAML frontmatter from a file or raw markdown string.

        Args:
            source: File path or raw markdown content.

        Returns:
            ParseResult with frontmatter data and body metadata.
        """
        content = source
        path = Path(source)
        if path.exists() and path.is_file():
            content = path.read_text(encoding="utf-8")

        if not content.startswith("---"):
            return ParseResult(
                data={},
                metadata={"has_frontmatter": False, "source": source},
            )

        end = content.find("---", 3)
        if end == -1:
            return ParseResult(
                success=False,
                error="Unclosed frontmatter block (missing closing '---')",
            )

        try:
            frontmatter = yaml.safe_load(content[3:end])
            body = content[end + 3 :].strip()

            return ParseResult(
                data=frontmatter or {},
                metadata={
                    "has_frontmatter": True,
                    "body_length": len(body),
                    "source": source,
                },
            )
        except yaml.YAMLError as e:
            return ParseResult(success=False, error=f"YAML parse error: {e}")
