"""Tests for content generation models."""

from uuid import UUID

from kurt.content.generation.models import (
    ContentFormat,
    ContentGenerationRequest,
    ContentTone,
    GeneratedContent,
    SourceReference,
)


def test_content_generation_request_defaults():
    """Test ContentGenerationRequest with minimal required fields."""
    request = ContentGenerationRequest(goal="Write about authentication")

    assert request.goal == "Write about authentication"
    assert request.format == ContentFormat.BLOG_POST
    assert request.tone == ContentTone.PROFESSIONAL
    assert request.source_document_ids == []
    assert request.source_entity_names == []
    assert request.source_query is None
    assert request.ai_provider == "anthropic"
    assert request.include_citations is True
    assert request.add_frontmatter is True


def test_content_generation_request_with_sources():
    """Test ContentGenerationRequest with source specifications."""
    doc_id = UUID("12345678-1234-5678-1234-567812345678")
    request = ContentGenerationRequest(
        goal="Write tutorial",
        format=ContentFormat.TUTORIAL,
        source_document_ids=[doc_id],
        source_entity_names=["Topic:authentication", "Technology:OAuth"],
        source_query="authentication flows",
    )

    assert request.format == ContentFormat.TUTORIAL
    assert len(request.source_document_ids) == 1
    assert request.source_document_ids[0] == doc_id
    assert len(request.source_entity_names) == 2
    assert request.source_query == "authentication flows"


def test_generated_content_to_markdown_with_frontmatter():
    """Test converting GeneratedContent to markdown with frontmatter."""
    request = ContentGenerationRequest(
        goal="Test goal",
        add_frontmatter=True,
    )

    doc_id = UUID("12345678-1234-5678-1234-567812345678")
    source = SourceReference(
        document_id=doc_id,
        document_title="Test Document",
        document_url="https://example.com/doc",
    )

    content = GeneratedContent(
        request=request,
        title="Test Title",
        content="# Introduction\n\nThis is test content.",
        word_count=100,
        sources=[source],
        entities_used=["Topic:testing"],
        ai_provider="anthropic",
        ai_model="claude-3-5-sonnet-20241022",
        tokens_used=500,
    )

    markdown = content.to_markdown(include_metadata=True)

    # Check frontmatter is included
    assert "---" in markdown
    assert "title: Test Title" in markdown
    assert "word_count: 100" in markdown
    assert "ai_provider: anthropic" in markdown
    assert "ai_model: claude-3-5-sonnet-20241022" in markdown
    assert "sources:" in markdown
    assert str(doc_id) in markdown
    assert "Test Document" in markdown
    assert "entities: Topic:testing" in markdown

    # Check content is included
    assert "# Introduction" in markdown
    assert "This is test content." in markdown


def test_generated_content_to_markdown_without_frontmatter():
    """Test converting GeneratedContent to markdown without frontmatter."""
    request = ContentGenerationRequest(
        goal="Test goal",
        add_frontmatter=False,
    )

    content = GeneratedContent(
        request=request,
        title="Test Title",
        content="# Introduction\n\nThis is test content.",
        word_count=100,
        sources=[],
        ai_provider="anthropic",
        ai_model="claude-3-5-sonnet-20241022",
    )

    markdown = content.to_markdown(include_metadata=False)

    # Frontmatter should not be included
    assert markdown.count("---") == 0
    assert "title:" not in markdown
    assert "word_count:" not in markdown

    # Content should still be there
    assert "# Introduction" in markdown
    assert "This is test content." in markdown


def test_content_format_enum():
    """Test ContentFormat enum values."""
    assert ContentFormat.BLOG_POST.value == "blog-post"
    assert ContentFormat.TUTORIAL.value == "tutorial"
    assert ContentFormat.GUIDE.value == "guide"
    assert ContentFormat.PRODUCT_PAGE.value == "product-page"


def test_content_tone_enum():
    """Test ContentTone enum values."""
    assert ContentTone.PROFESSIONAL.value == "professional"
    assert ContentTone.CONVERSATIONAL.value == "conversational"
    assert ContentTone.TECHNICAL.value == "technical"
    assert ContentTone.FRIENDLY.value == "friendly"
