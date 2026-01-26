"""
ResearchTool - Research query tool for Kurt workflows.

Executes research queries via Perplexity API, returning synthesized answers
with citations. Thin wrapper around kurt.integrations.research.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from kurt.tools.base import ProgressCallback, Tool, ToolContext, ToolResult
from kurt.tools.registry import register_tool

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models
# ============================================================================


class CitationOutput(BaseModel):
    """A citation/source from research."""

    title: str = Field(..., description="Citation title")
    url: str = Field(..., description="Citation URL")
    snippet: str | None = Field(default=None, description="Relevant snippet from source")
    published_date: str | None = Field(default=None, description="Publication date if available")
    domain: str | None = Field(default=None, description="Source domain")


class ResearchInput(BaseModel):
    """Input parameters for the Research tool."""

    query: str = Field(..., description="Research query to execute")

    source: Literal["perplexity"] = Field(
        default="perplexity",
        description="Research source (currently only perplexity supported)",
    )

    recency: Literal["hour", "day", "week", "month"] = Field(
        default="day",
        description="Recency filter for results",
    )

    model: str = Field(
        default="sonar-reasoning",
        description="Perplexity model to use",
    )

    save: bool = Field(
        default=False,
        description="Save results to markdown file",
    )

    output_dir: str = Field(
        default="sources/research",
        description="Directory to save research results",
    )

    dry_run: bool = Field(
        default=False,
        description="Preview mode - execute but don't persist",
    )


class ResearchOutput(BaseModel):
    """Output from a research query."""

    id: str = Field(..., description="Unique research result ID")
    query: str = Field(..., description="Original query")
    answer: str = Field(..., description="Synthesized research answer")
    source: str = Field(..., description="Research source used")
    model: str | None = Field(default=None, description="Model used")
    citations: list[CitationOutput] = Field(
        default_factory=list,
        description="List of citations/sources",
    )
    response_time_seconds: float | None = Field(
        default=None,
        description="API response time in seconds",
    )
    content_path: str | None = Field(
        default=None,
        description="Path to saved markdown file (if save=True)",
    )


# ============================================================================
# ResearchTool Implementation
# ============================================================================


@register_tool
class ResearchTool(Tool[ResearchInput, ResearchOutput]):
    """
    Execute research queries via Perplexity API.

    Substeps:
    - research_query: Execute research query via API
    - save_results: Save to markdown file (if save=True)

    Uses the perplexity adapter from kurt.integrations.research.
    """

    name = "research"
    description = "Execute research queries via Perplexity API with citations"
    InputModel = ResearchInput
    OutputModel = ResearchOutput

    async def run(
        self,
        params: ResearchInput,
        context: ToolContext,
        on_progress: ProgressCallback | None = None,
    ) -> ToolResult:
        """
        Execute the research tool.

        Args:
            params: Research parameters (query, source, recency, etc.)
            context: Execution context
            on_progress: Optional progress callback

        Returns:
            ToolResult with research answer and citations
        """
        from kurt.integrations.research import ResearchResult
        from kurt.integrations.research.config import get_source_config
        from kurt.integrations.research.perplexity import PerplexityAdapter

        # ----------------------------------------------------------------
        # Substep 1: research_query
        # ----------------------------------------------------------------
        self.emit_progress(
            on_progress,
            substep="research_query",
            status="running",
            current=0,
            total=1,
            message=f"Executing research query: {params.query[:50]}...",
        )

        try:
            # Get adapter config
            source_config = get_source_config(params.source)

            # Create adapter
            if params.source == "perplexity":
                adapter = PerplexityAdapter(source_config)
            else:
                return ToolResult(
                    success=False,
                    errors=[],
                ).tap(
                    lambda r: r.add_error(
                        error_type="invalid_source",
                        message=f"Unknown research source: {params.source}",
                    )
                )

            # Execute search
            result: ResearchResult = adapter.search(
                query=params.query,
                recency=params.recency,
                model=params.model,
            )

            self.emit_progress(
                on_progress,
                substep="research_query",
                status="completed",
                current=1,
                total=1,
                message=f"Received {len(result.citations)} citation(s)",
                metadata={
                    "citations_count": len(result.citations),
                    "response_time": result.response_time_seconds,
                },
            )

        except Exception as e:
            logger.error(f"Research query failed: {e}")
            self.emit_progress(
                on_progress,
                substep="research_query",
                status="failed",
                message=str(e),
            )
            tool_result = ToolResult(success=False)
            tool_result.add_error(
                error_type="research_failed",
                message=str(e),
            )
            return tool_result

        # ----------------------------------------------------------------
        # Substep 2: save_results (if save=True)
        # ----------------------------------------------------------------
        content_path = None

        if params.save and not params.dry_run:
            self.emit_progress(
                on_progress,
                substep="save_results",
                status="running",
                message="Saving research results to file",
            )

            try:
                # Generate markdown content
                markdown = result.to_markdown()

                # Build file path
                timestamp = result.timestamp or datetime.utcnow()
                date_str = timestamp.strftime("%Y%m%d")
                filename = f"{date_str}-{result.id}.md"

                # Get project root from context
                project_root = Path(context.settings.get("project_root", "."))
                output_dir = project_root / params.output_dir
                output_dir.mkdir(parents=True, exist_ok=True)

                file_path = output_dir / filename
                file_path.write_text(markdown, encoding="utf-8")
                content_path = str(file_path)

                self.emit_progress(
                    on_progress,
                    substep="save_results",
                    status="completed",
                    message=f"Saved to {content_path}",
                )

            except Exception as e:
                logger.error(f"Failed to save research results: {e}")
                self.emit_progress(
                    on_progress,
                    substep="save_results",
                    status="failed",
                    message=str(e),
                )
                # Don't fail the whole operation, just log the error
                content_path = None

        # Build output data
        output_data = {
            "id": result.id,
            "query": result.query,
            "answer": result.answer,
            "source": result.source,
            "model": result.model,
            "citations": [
                {
                    "title": c.title,
                    "url": c.url,
                    "snippet": c.snippet,
                    "published_date": c.published_date,
                    "domain": c.domain,
                }
                for c in result.citations
            ],
            "response_time_seconds": result.response_time_seconds,
            "content_path": content_path,
        }

        # Build result
        tool_result = ToolResult(
            success=True,
            data=[output_data],
        )

        tool_result.add_substep(
            name="research_query",
            status="completed",
            current=1,
            total=1,
        )

        if params.save:
            tool_result.add_substep(
                name="save_results",
                status="completed" if content_path else "skipped",
                current=1 if content_path else 0,
                total=1,
            )

        return tool_result


__all__ = [
    "ResearchTool",
    "ResearchInput",
    "ResearchOutput",
    "CitationOutput",
]
