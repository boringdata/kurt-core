"""Base class for parse providers (reference only).

This file defines the interface contract for parse providers.
It is NOT imported by providers at runtime — the ProviderRegistry
discovers providers by class attributes, not inheritance.

Providers define their own ParseResult locally because the registry
loads provider.py files via importlib (no package context available).

This file serves as documentation and as a local development aid
for IDE type checking when developing providers as a Python package.

Follows the same metadata pattern as Kurt's BaseFetcher and BaseMapper:
- name: Unique provider identifier
- version: Semver version string
- url_patterns: fnmatch patterns for auto-selection (e.g., "*.md")
- requires_env: Environment variables that must be set
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class ParseResult(BaseModel):
    """Result from a parse operation."""

    data: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    success: bool = True
    error: str | None = None


class BaseParser(ABC):
    """Base class for parse providers.

    Subclasses should set the class-level metadata attributes for
    provider discovery and validation:

        class MyParser(BaseParser):
            name = "my-parser"
            version = "1.0.0"
            url_patterns = ["*.csv"]
            requires_env = ["MY_API_KEY"]

            def parse(self, source: str) -> ParseResult:
                ...
    """

    # Provider metadata — same interface as BaseFetcher/BaseMapper
    name: str = ""
    version: str = "1.0.0"
    url_patterns: list[str] = []
    requires_env: list[str] = []

    def validate_requirements(self) -> list[str]:
        """Check if all required environment variables are set.

        Returns:
            List of missing environment variable names. Empty if all present.
        """
        import os

        return [var for var in self.requires_env if not os.environ.get(var)]

    @abstractmethod
    def parse(self, source: str) -> ParseResult:
        """Parse content from a file path or raw string.

        Args:
            source: File path or raw content string.

        Returns:
            ParseResult with parsed data and metadata.
        """
        pass
