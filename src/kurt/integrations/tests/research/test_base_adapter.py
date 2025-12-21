"""Unit tests for research base adapter interface and data classes."""

from datetime import datetime

import pytest

from kurt.integrations.research.base import Citation, ResearchAdapter, ResearchResult


class TestCitation:
    """Test Citation data class."""

    def test_citation_creation_minimal(self):
        """Test creating citation with minimal required fields."""
        citation = Citation(
            title="Example Article",
            url="https://example.com/article",
        )

        assert citation.title == "Example Article"
        assert citation.url == "https://example.com/article"
        assert citation.snippet is None
        assert citation.published_date is None
        assert citation.domain is None

    def test_citation_creation_full(self):
        """Test creating citation with all fields."""
        citation = Citation(
            title="Complete Article",
            url="https://docs.example.com/guide",
            snippet="This is a snippet from the article...",
            published_date="2024-01-15",
            domain="docs.example.com",
        )

        assert citation.title == "Complete Article"
        assert citation.url == "https://docs.example.com/guide"
        assert citation.snippet == "This is a snippet from the article..."
        assert citation.published_date == "2024-01-15"
        assert citation.domain == "docs.example.com"

    def test_citation_to_dict(self):
        """Test converting citation to dictionary."""
        citation = Citation(
            title="Dict Test",
            url="https://example.com/test",
            snippet="Test snippet",
        )

        result = citation.to_dict()

        assert isinstance(result, dict)
        assert result["title"] == "Dict Test"
        assert result["url"] == "https://example.com/test"
        assert result["snippet"] == "Test snippet"


class TestResearchResult:
    """Test ResearchResult data class."""

    def test_result_creation_minimal(self):
        """Test creating research result with minimal fields."""
        citations = [
            Citation(title="Source 1", url="https://example.com/1"),
            Citation(title="Source 2", url="https://example.com/2"),
        ]

        result = ResearchResult(
            id="res_12345",
            query="What is Kubernetes?",
            answer="Kubernetes is a container orchestration platform...",
            citations=citations,
            source="perplexity",
        )

        assert result.id == "res_12345"
        assert result.query == "What is Kubernetes?"
        assert "Kubernetes" in result.answer
        assert len(result.citations) == 2
        assert result.source == "perplexity"
        assert result.model is None
        assert result.timestamp is None

    def test_result_creation_full(self):
        """Test creating research result with all fields."""
        timestamp = datetime.now()
        citations = [Citation(title="Source", url="https://example.com")]
        metadata = {"recency": "day", "tokens": 1000}

        result = ResearchResult(
            id="res_67890",
            query="Research query",
            answer="Detailed answer",
            citations=citations,
            source="perplexity",
            model="sonar-reasoning",
            timestamp=timestamp,
            response_time_seconds=2.5,
            metadata=metadata,
        )

        assert result.model == "sonar-reasoning"
        assert result.timestamp == timestamp
        assert result.response_time_seconds == 2.5
        assert result.metadata["recency"] == "day"

    def test_result_to_dict(self):
        """Test converting research result to dictionary."""
        citations = [
            Citation(title="Source 1", url="https://example.com/1"),
        ]
        result = ResearchResult(
            id="res_test",
            query="Test query",
            answer="Test answer",
            citations=citations,
            source="perplexity",
        )

        data = result.to_dict()

        assert isinstance(data, dict)
        assert data["id"] == "res_test"
        assert data["query"] == "Test query"
        assert data["answer"] == "Test answer"
        assert data["source"] == "perplexity"
        assert isinstance(data["citations"], list)
        assert len(data["citations"]) == 1
        assert isinstance(data["citations"][0], dict)

    def test_result_to_markdown(self):
        """Test converting research result to markdown."""
        citations = [
            Citation(
                title="Kubernetes Documentation",
                url="https://kubernetes.io/docs",
                published_date="2024-01-15",
            ),
            Citation(
                title="CNCF Blog Post",
                url="https://cncf.io/blog/k8s",
            ),
        ]

        timestamp = datetime(2024, 1, 20, 10, 30, 0)

        result = ResearchResult(
            id="res_20240120_abc123",
            query="What is Kubernetes?",
            answer="Kubernetes is an open-source container orchestration platform.",
            citations=citations,
            source="perplexity",
            model="sonar-reasoning",
            timestamp=timestamp,
            response_time_seconds=3.2,
        )

        markdown = result.to_markdown()

        # Check frontmatter
        assert "---" in markdown
        assert "research_id: res_20240120_abc123" in markdown
        assert 'research_query: "What is Kubernetes?"' in markdown
        assert "research_source: perplexity" in markdown
        assert "research_model: sonar-reasoning" in markdown
        assert "research_date: 2024-01-20T10:30:00" in markdown
        assert "response_time_seconds: 3.2" in markdown
        assert "sources_count: 2" in markdown

        # Check citations in frontmatter
        assert "citations:" in markdown
        assert 'title: "Kubernetes Documentation"' in markdown
        assert "url: https://kubernetes.io/docs" in markdown
        assert "published: 2024-01-15" in markdown

        # Check body
        assert "# What is Kubernetes?" in markdown
        assert "Kubernetes is an open-source container orchestration platform" in markdown
        assert "## Sources" in markdown
        assert "[1] Kubernetes Documentation - https://kubernetes.io/docs (2024-01-15)" in markdown
        assert "[2] CNCF Blog Post - https://cncf.io/blog/k8s" in markdown

    def test_result_to_markdown_no_optional_fields(self):
        """Test markdown generation without optional fields."""
        citations = [Citation(title="Source", url="https://example.com")]

        result = ResearchResult(
            id="res_minimal",
            query="Minimal query",
            answer="Minimal answer",
            citations=citations,
            source="perplexity",
        )

        markdown = result.to_markdown()

        # Should have basic frontmatter
        assert "research_id: res_minimal" in markdown
        assert 'research_query: "Minimal query"' in markdown

        # Should NOT have optional fields
        assert "research_model:" not in markdown
        assert "research_date:" not in markdown
        assert "response_time_seconds:" not in markdown


class TestResearchAdapterInterface:
    """Test ResearchAdapter abstract interface."""

    def test_adapter_is_abstract(self):
        """Test that ResearchAdapter cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ResearchAdapter(config={})  # Should fail - abstract class

    def test_adapter_must_implement_search(self):
        """Test that subclasses must implement search."""

        class IncompleteAdapter(ResearchAdapter):
            def __init__(self, config):
                pass

            def test_connection(self):
                pass

        with pytest.raises(TypeError):
            IncompleteAdapter(config={})  # Should fail - missing search

    def test_adapter_must_implement_test_connection(self):
        """Test that subclasses must implement test_connection."""

        class IncompleteAdapter(ResearchAdapter):
            def __init__(self, config):
                pass

            def search(self, query, recency=None, **kwargs):
                pass

        with pytest.raises(TypeError):
            IncompleteAdapter(config={})  # Should fail - missing test_connection

    def test_adapter_complete_implementation(self):
        """Test that complete implementation can be instantiated."""

        class CompleteAdapter(ResearchAdapter):
            def __init__(self, config):
                self.config = config

            def search(self, query, recency=None, **kwargs):
                return ResearchResult(
                    id="test",
                    query=query,
                    answer="test answer",
                    citations=[],
                    source="test",
                )

            def test_connection(self):
                return True

        adapter = CompleteAdapter(config={"api_key": "test"})
        assert adapter is not None
        assert adapter.test_connection() is True

        result = adapter.search("test query")
        assert isinstance(result, ResearchResult)
        assert result.query == "test query"


class TestCitationEdgeCases:
    """Test edge cases for Citation."""

    def test_citation_with_special_characters(self):
        """Test citation with special characters in fields."""
        citation = Citation(
            title='Title with "quotes" and <special> chars',
            url="https://example.com/path?param=value&other=test",
            snippet="Snippet with émojis 🔍 and unicode: 中文",
        )

        assert '"quotes"' in citation.title
        assert "🔍" in citation.snippet
        assert "中文" in citation.snippet

    def test_citation_with_very_long_url(self):
        """Test citation with very long URL."""
        long_url = "https://example.com/" + "a" * 500
        citation = Citation(title="Long URL Test", url=long_url)

        assert len(citation.url) > 500
        assert citation.url.startswith("https://example.com/")

    def test_citation_with_empty_optional_fields(self):
        """Test that None values are preserved for optional fields."""
        citation = Citation(
            title="Test",
            url="https://example.com",
            snippet=None,
            published_date=None,
            domain=None,
        )

        data = citation.to_dict()
        assert data["snippet"] is None
        assert data["published_date"] is None
        assert data["domain"] is None


class TestResearchResultEdgeCases:
    """Test edge cases for ResearchResult."""

    def test_result_with_no_citations(self):
        """Test research result with empty citations list."""
        result = ResearchResult(
            id="res_no_cites",
            query="Query without sources",
            answer="Answer based on internal knowledge",
            citations=[],
            source="perplexity",
        )

        assert len(result.citations) == 0
        markdown = result.to_markdown()
        assert "sources_count: 0" in markdown

    def test_result_with_many_citations(self):
        """Test research result with many citations."""
        citations = [
            Citation(title=f"Source {i}", url=f"https://example.com/{i}") for i in range(1, 51)
        ]

        result = ResearchResult(
            id="res_many",
            query="Complex query",
            answer="Answer with many sources",
            citations=citations,
            source="perplexity",
        )

        assert len(result.citations) == 50

        markdown = result.to_markdown()
        assert "sources_count: 50" in markdown
        assert "[50] Source 50" in markdown

    def test_result_with_very_long_answer(self):
        """Test research result with very long answer."""
        long_answer = "Long answer. " * 1000  # ~13K chars

        result = ResearchResult(
            id="res_long",
            query="Query",
            answer=long_answer,
            citations=[],
            source="perplexity",
        )

        assert len(result.answer) > 10000

        markdown = result.to_markdown()
        assert long_answer in markdown
