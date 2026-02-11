"""ParseTool — custom tool demonstrating the Kurt provider system.

This tool parses files into structured data. It shows how to:
- Define input/output schemas with Pydantic
- Set a default_provider for fallback resolution
- Use the ProviderRegistry inside a tool's run() method
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from kurt.tools.core import (
    ProgressCallback,
    ProviderRegistry,
    Tool,
    ToolContext,
    ToolResult,
)


class ParseInput(BaseModel):
    """Input for the parse tool."""

    source: str = Field(description="File path or raw content to parse")
    provider: str | None = Field(default=None, description="Explicit provider name")


class ParseOutput(BaseModel):
    """Output from the parse tool."""

    data: dict = Field(default_factory=dict, description="Parsed structured data")
    metadata: dict = Field(default_factory=dict, description="Parse metadata")


class ParseTool(Tool[ParseInput, ParseOutput]):
    """Parse files into structured data.

    Demonstrates:
    - Tool with input/output models
    - Provider resolution via the registry
    - Progress event emission
    """

    name = "parse"
    description = "Parse files into structured data"
    default_provider = "frontmatter"
    InputModel = ParseInput
    OutputModel = ParseOutput

    async def run(
        self,
        params: ParseInput,
        context: ToolContext,
        on_progress: ProgressCallback | None = None,
    ) -> ToolResult:
        """Execute the parse tool.

        Resolution order for provider:
        1. Explicit params.provider
        2. URL/path pattern matching
        3. default_provider ("frontmatter")
        """
        registry = ProviderRegistry()
        registry.discover()

        # Resolve which provider to use
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

        # Get the provider instance (with requirements validation)
        provider = registry.get_provider_checked(self.name, provider_name)

        self.emit_progress(
            on_progress,
            substep="parse",
            status="running",
            message=f"Parsing with {provider_name}",
        )

        # Run the parse
        parse_result = provider.parse(params.source)

        self.emit_progress(
            on_progress,
            substep="parse",
            status="completed",
            message="Parse complete",
        )

        result = ToolResult(
            success=parse_result.success,
            data=[parse_result.model_dump()],
        )

        if parse_result.error:
            result.add_error("parse_error", parse_result.error)

        return result
