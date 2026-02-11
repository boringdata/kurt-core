"""Scaffold templates for new tools and providers.

Generates Python source files from string templates. Uses simple str.format()
rather than Jinja2 to avoid adding a dependency for simple scaffolding.
"""

from __future__ import annotations


def _capitalize(name: str) -> str:
    """Convert snake_case or kebab-case name to PascalCase."""
    return "".join(word.capitalize() for word in name.replace("-", "_").split("_"))


def render_tool_py(name: str, description: str = "") -> str:
    """Render tool.py scaffold."""
    cls = _capitalize(name)
    desc = description or f"{cls} tool"
    return f'''"""{desc}."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from kurt.tools.core import (
    ProgressCallback,
    ProviderRegistry,
    Tool,
    ToolContext,
    ToolResult,
)


class {cls}Input(BaseModel):
    """Input for the {name} tool."""

    source: str = Field(description="Source to process")
    provider: str | None = Field(default=None, description="Explicit provider name")


class {cls}Output(BaseModel):
    """Output from the {name} tool."""

    data: dict = Field(default_factory=dict, description="Processed data")
    metadata: dict = Field(default_factory=dict, description="Processing metadata")


class {cls}Tool(Tool[{cls}Input, {cls}Output]):
    """{desc}."""

    name = "{name}"
    description = "{desc}"
    default_provider = "default"
    InputModel = {cls}Input
    OutputModel = {cls}Output

    async def run(
        self,
        params: {cls}Input,
        context: ToolContext,
        on_progress: ProgressCallback | None = None,
    ) -> ToolResult:
        """Execute the {name} tool."""
        registry = ProviderRegistry()
        registry.discover()

        provider_name = registry.resolve_provider(
            tool_name=self.name,
            provider_name=params.provider,
            url=params.source,
            default_provider=self.default_provider,
        )

        if provider_name is None:
            result = ToolResult(success=False)
            result.add_error("provider_not_found", "No matching provider found")
            return result

        provider = registry.get_provider_checked(self.name, provider_name)

        self.emit_progress(
            on_progress,
            substep="{name}",
            status="running",
            message=f"Processing with {{provider_name}}",
        )

        process_result = provider.process(params.source)

        self.emit_progress(
            on_progress,
            substep="{name}",
            status="completed",
            message="Processing complete",
        )

        result = ToolResult(
            success=process_result.success,
            data=[process_result.model_dump()],
        )

        if process_result.error:
            result.add_error("process_error", process_result.error)

        return result
'''


def render_base_py(name: str) -> str:
    """Render base.py scaffold (provider interface)."""
    cls = _capitalize(name)
    return f'''"""Base class for {name} providers (reference only).

This file defines the interface contract for {name} providers.
Providers loaded by ProviderRegistry must be self-contained
(no relative imports) because they are loaded via importlib.

Providers should define their own Result model locally.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class {cls}Result(BaseModel):
    """Result from a {name} operation."""

    data: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    success: bool = True
    error: str | None = None


class Base{cls}(ABC):
    """Base class for {name} providers.

    Subclasses should set class-level metadata attributes:

        class My{cls}(Base{cls}):
            name = "my-{name}"
            version = "1.0.0"
            url_patterns = ["*.txt"]
            requires_env = ["MY_API_KEY"]

            def process(self, source: str) -> {cls}Result:
                ...
    """

    name: str = ""
    version: str = "1.0.0"
    url_patterns: list[str] = []
    requires_env: list[str] = []

    def validate_requirements(self) -> list[str]:
        """Check if required environment variables are set."""
        import os

        return [var for var in self.requires_env if not os.environ.get(var)]

    @abstractmethod
    def process(self, source: str) -> {cls}Result:
        """Process content from a file path or raw string.

        Args:
            source: File path or raw content string.

        Returns:
            {cls}Result with processed data and metadata.
        """
        pass
'''


def render_init_py(name: str) -> str:
    """Render __init__.py scaffold."""
    cls = _capitalize(name)
    return f'''"""{cls} tool for Kurt."""

from kurt.tools.{name}.tool import {cls}Input, {cls}Output, {cls}Tool

__all__ = ["{cls}Tool", "{cls}Input", "{cls}Output"]
'''


def render_provider_py(tool_name: str, provider_name: str) -> str:
    """Render provider.py scaffold."""
    tool_cls = _capitalize(tool_name)
    provider_cls = _capitalize(provider_name)
    return f'''"""{provider_cls} provider for {tool_name}.

NOTE: Providers loaded by ProviderRegistry must be self-contained.
They cannot use relative imports because they are loaded via
importlib.util.spec_from_file_location (no package context).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class {tool_cls}Result(BaseModel):
    """Result from a {tool_name} operation."""

    data: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    success: bool = True
    error: str | None = None


class {provider_cls}{tool_cls}(object):
    """Provider for {tool_name} tool.

    Attributes set here are used by ProviderRegistry for discovery:
    - name: Unique provider identifier
    - version: Semver version string
    - url_patterns: fnmatch patterns for auto-selection
    - requires_env: Environment variables that must be set
    """

    name = "{provider_name}"
    version = "1.0.0"
    url_patterns: list[str] = []
    requires_env: list[str] = []

    def process(self, source: str) -> {tool_cls}Result:
        """Process the source.

        Args:
            source: File path or raw content.

        Returns:
            {tool_cls}Result with processed data.
        """
        # TODO: Implement your logic here
        return {tool_cls}Result(
            data={{"source": source}},
            success=True,
        )
'''


def render_provider_config_py(tool_name: str, provider_name: str) -> str:
    """Render provider config.py scaffold."""
    tool_cls = _capitalize(tool_name)
    provider_cls = _capitalize(provider_name)
    return f'''"""Configuration for {provider_name} {tool_name} provider."""

from __future__ import annotations

from pydantic import BaseModel, Field


class {provider_cls}{tool_cls}ProviderConfig(BaseModel):
    """Configuration for {provider_name} provider."""

    timeout: float = Field(
        default=30.0,
        gt=0,
        description="Request timeout in seconds",
    )
'''
