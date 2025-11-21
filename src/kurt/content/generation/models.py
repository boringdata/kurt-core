"""Data models for content generation."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ContentFormat(str, Enum):
    """Supported content formats for generation."""

    BLOG_POST = "blog-post"
    TUTORIAL = "tutorial"
    GUIDE = "guide"
    PRODUCT_PAGE = "product-page"
    SOLUTION_PAGE = "solution-page"
    CASE_STUDY = "case-study"
    LANDING_PAGE = "landing-page"
    EMAIL = "email"
    SOCIAL_POST = "social-post"
    DOCUMENTATION = "documentation"
    README = "readme"


class ContentTone(str, Enum):
    """Tone options for generated content."""

    PROFESSIONAL = "professional"
    CONVERSATIONAL = "conversational"
    TECHNICAL = "technical"
    FRIENDLY = "friendly"
    FORMAL = "formal"
    CASUAL = "casual"


class ContentGenerationRequest(BaseModel):
    """Request for content generation."""

    # Core requirements
    goal: str = Field(
        ..., description="What the content should achieve (e.g., 'Explain authentication flows')"
    )
    format: ContentFormat = Field(
        default=ContentFormat.BLOG_POST, description="Content format to generate"
    )

    # Context sources
    source_document_ids: list[UUID] = Field(
        default_factory=list,
        description="Specific documents to use as source material",
    )
    source_entity_names: list[str] = Field(
        default_factory=list,
        description="Knowledge graph entities to include (e.g., 'Topic:authentication', 'Technology:OAuth')",
    )
    source_query: Optional[str] = Field(
        default=None,
        description="Search query to find relevant documents automatically",
    )

    # Content parameters
    tone: ContentTone = Field(default=ContentTone.PROFESSIONAL, description="Writing tone")
    target_word_count: Optional[int] = Field(
        default=None, description="Target word count (approximate)"
    )
    include_code_examples: bool = Field(
        default=False, description="Include code examples in content"
    )
    include_citations: bool = Field(
        default=True, description="Include citations to source documents"
    )

    # AI parameters
    ai_provider: str = Field(
        default="anthropic", description="LLM provider (anthropic, openai, etc.)"
    )
    ai_model: Optional[str] = Field(
        default=None, description="Specific model to use (defaults to provider default)"
    )

    # Output parameters
    output_path: Optional[str] = Field(
        default=None, description="Where to save the generated content"
    )
    add_frontmatter: bool = Field(default=True, description="Add YAML frontmatter with metadata")


class SourceReference(BaseModel):
    """Reference to a source document used in generation."""

    document_id: UUID
    document_title: str
    document_url: Optional[str] = None
    relevance_score: Optional[float] = None
    excerpts_used: list[str] = Field(
        default_factory=list, description="Specific excerpts referenced"
    )


class GeneratedContent(BaseModel):
    """Result of content generation."""

    id: UUID = Field(default_factory=uuid4)
    request: ContentGenerationRequest

    # Generated content
    title: str
    content: str  # Markdown content
    word_count: int

    # Metadata
    sources: list[SourceReference] = Field(
        default_factory=list, description="Documents used as sources"
    )
    entities_used: list[str] = Field(
        default_factory=list, description="Knowledge graph entities referenced"
    )

    # Generation details
    ai_provider: str
    ai_model: str
    tokens_used: Optional[int] = None
    generation_time_seconds: Optional[float] = None

    # Timestamps
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    def to_markdown(self, include_metadata: bool = True) -> str:
        """Convert to markdown format with optional frontmatter."""
        parts = []

        if include_metadata and self.request.add_frontmatter:
            parts.append("---")
            parts.append(f"title: {self.title}")
            parts.append(f"generated_at: {self.generated_at.isoformat()}")
            parts.append(f"format: {self.request.format.value}")
            parts.append(f"tone: {self.request.tone.value}")
            parts.append(f"word_count: {self.word_count}")
            parts.append(f"ai_provider: {self.ai_provider}")
            parts.append(f"ai_model: {self.ai_model}")

            if self.sources:
                parts.append("sources:")
                for source in self.sources:
                    parts.append(f"  - id: {source.document_id}")
                    parts.append(f"    title: {source.document_title}")
                    if source.document_url:
                        parts.append(f"    url: {source.document_url}")

            if self.entities_used:
                parts.append(f"entities: {', '.join(self.entities_used)}")

            parts.append("---")
            parts.append("")

        parts.append(self.content)

        return "\n".join(parts)
