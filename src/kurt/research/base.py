"""
Base adapter interface for research integrations.

All research adapters (Perplexity, Tavily, etc.) implement this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Citation:
    """A citation/source from research."""

    title: str
    url: str
    snippet: Optional[str] = None
    published_date: Optional[str] = None
    domain: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ResearchResult:
    """Result from a research query."""

    id: str
    query: str
    answer: str  # The synthesized research report
    citations: List[Citation]
    source: str  # "perplexity", "tavily", etc.
    model: Optional[str] = None
    timestamp: Optional[datetime] = None
    response_time_seconds: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert citations to list of dicts
        data["citations"] = [c.to_dict() for c in self.citations]
        return data

    def to_markdown(self) -> str:
        """Convert to markdown format with frontmatter."""
        # YAML frontmatter
        frontmatter_lines = [
            "---",
            f"research_id: {self.id}",
            f'research_query: "{self.query}"',
            f"research_source: {self.source}",
        ]

        if self.model:
            frontmatter_lines.append(f"research_model: {self.model}")

        if self.timestamp:
            frontmatter_lines.append(f"research_date: {self.timestamp.isoformat()}")

        if self.response_time_seconds:
            frontmatter_lines.append(f"response_time_seconds: {self.response_time_seconds:.1f}")

        frontmatter_lines.append(f"sources_count: {len(self.citations)}")

        # Add citations to frontmatter
        if self.citations:
            frontmatter_lines.append("citations:")
            for i, citation in enumerate(self.citations, 1):
                frontmatter_lines.append(f'  - title: "{citation.title}"')
                frontmatter_lines.append(f"    url: {citation.url}")
                if citation.published_date:
                    frontmatter_lines.append(f"    published: {citation.published_date}")

        frontmatter_lines.append("---")

        # Body: research report with inline citation references
        body_lines = ["", f"# {self.query}", "", self.answer, "", "## Sources", ""]

        # List sources
        for i, citation in enumerate(self.citations, 1):
            source_line = f"[{i}] {citation.title} - {citation.url}"
            if citation.published_date:
                source_line += f" ({citation.published_date})"
            body_lines.append(source_line)

        return "\n".join(frontmatter_lines + body_lines)


class ResearchAdapter(ABC):
    """Base adapter interface for research sources."""

    @abstractmethod
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize with API credentials and settings.

        Args:
            config: Dictionary containing API-specific configuration
        """
        pass

    @abstractmethod
    def search(self, query: str, recency: Optional[str] = None, **kwargs) -> ResearchResult:
        """
        Execute research query.

        Args:
            query: Research question or topic
            recency: Time filter (hour, day, week, month)
            **kwargs: Additional provider-specific parameters

        Returns:
            ResearchResult with synthesized answer and citations
        """
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test if API connection is working.

        Returns:
            True if connection successful, False otherwise
        """
        pass
