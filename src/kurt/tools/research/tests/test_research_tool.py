"""
Unit tests for ResearchTool.

Tests tool registration, input/output validation, and basic functionality
with mocked Perplexity integration.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from kurt.integrations.research.base import Citation, ResearchResult
from kurt.tools.core import (
    TOOLS,
    SubstepEvent,
    ToolContext,
    clear_registry,
    execute_tool,
    get_tool,
)
from kurt.tools.research import (
    CitationOutput,
    ResearchInput,
    ResearchOutput,
    ResearchTool,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear the registry before and after each test."""
    clear_registry()
    yield
    clear_registry()


@pytest.fixture
def mock_research_result():
    """Create a mock ResearchResult for testing."""
    return ResearchResult(
        id="res_20240115_abc12345",
        query="What are the latest AI trends?",
        answer="The latest AI trends include generative AI, multimodal models, and AI agents.",
        citations=[
            Citation(
                title="AI Trends Report",
                url="https://example.com/ai-trends",
                snippet="Key trends in artificial intelligence...",
                published_date="2024-01-10",
                domain="example.com",
            ),
            Citation(
                title="Tech News Today",
                url="https://technews.example.com/article",
                domain="technews.example.com",
            ),
        ],
        source="perplexity",
        model="sonar-reasoning",
        timestamp=datetime(2024, 1, 15, 10, 30, 0),
        response_time_seconds=2.5,
    )


@pytest.fixture
def tool_context(tmp_path):
    """Create a basic ToolContext for testing."""
    return ToolContext(
        settings={"project_root": str(tmp_path)},
    )


@pytest.fixture
def mock_perplexity(mock_research_result):
    """
    Fixture that patches Perplexity adapter and config for all tests.

    Returns a tuple of (mock_config, mock_adapter) for assertions.
    """
    with patch(
        "kurt.integrations.research.config.get_source_config"
    ) as mock_config, patch(
        "kurt.integrations.research.perplexity.PerplexityAdapter"
    ) as mock_adapter_class:
        mock_config.return_value = {"api_key": "test_key"}
        mock_adapter = MagicMock()
        mock_adapter.search.return_value = mock_research_result
        mock_adapter_class.return_value = mock_adapter

        yield mock_config, mock_adapter


# ============================================================================
# Tool Registration Tests
# ============================================================================


class TestResearchToolRegistration:
    """Test ResearchTool registration and metadata."""

    def test_tool_has_required_attributes(self):
        """ResearchTool has all required class attributes."""
        assert hasattr(ResearchTool, "name")
        assert hasattr(ResearchTool, "description")
        assert hasattr(ResearchTool, "InputModel")
        assert hasattr(ResearchTool, "OutputModel")

    def test_tool_name(self):
        """ResearchTool name is 'research'."""
        assert ResearchTool.name == "research"

    def test_tool_description(self):
        """ResearchTool has a description."""
        assert ResearchTool.description
        assert "research" in ResearchTool.description.lower()

    def test_tool_input_model(self):
        """ResearchTool.InputModel is ResearchInput."""
        assert ResearchTool.InputModel is ResearchInput

    def test_tool_output_model(self):
        """ResearchTool.OutputModel is ResearchOutput."""
        assert ResearchTool.OutputModel is ResearchOutput

    def test_tool_is_registered(self):
        """ResearchTool is registered via @register_tool decorator."""
        # Import triggers registration
        from kurt.tools.research import ResearchTool as ResearchToolCls

        # Manually add to registry for this test since we cleared it
        TOOLS["research"] = ResearchToolCls
        tool_class = get_tool("research")
        assert tool_class is ResearchToolCls


# ============================================================================
# Input Validation Tests
# ============================================================================


class TestResearchInput:
    """Test ResearchInput validation."""

    def test_minimal_input(self):
        """ResearchInput requires only query."""
        input_model = ResearchInput(query="test query")
        assert input_model.query == "test query"
        assert input_model.source == "perplexity"
        assert input_model.recency == "day"
        assert input_model.model == "sonar-reasoning"
        assert input_model.save is False
        assert input_model.dry_run is False

    def test_all_fields(self):
        """ResearchInput accepts all optional fields."""
        input_model = ResearchInput(
            query="test query",
            source="perplexity",
            recency="week",
            model="sonar-pro",
            save=True,
            output_dir="custom/output",
            dry_run=True,
        )
        assert input_model.query == "test query"
        assert input_model.source == "perplexity"
        assert input_model.recency == "week"
        assert input_model.model == "sonar-pro"
        assert input_model.save is True
        assert input_model.output_dir == "custom/output"
        assert input_model.dry_run is True

    def test_recency_validation(self):
        """ResearchInput validates recency values."""
        # Valid recency values
        for recency in ["hour", "day", "week", "month"]:
            input_model = ResearchInput(query="test", recency=recency)
            assert input_model.recency == recency

        # Invalid recency raises
        with pytest.raises(ValueError):
            ResearchInput(query="test", recency="invalid")

    def test_source_validation(self):
        """ResearchInput validates source values."""
        # Valid source
        input_model = ResearchInput(query="test", source="perplexity")
        assert input_model.source == "perplexity"

        # Invalid source raises
        with pytest.raises(ValueError):
            ResearchInput(query="test", source="unknown_source")

    def test_query_required(self):
        """ResearchInput requires query field."""
        with pytest.raises(ValueError):
            ResearchInput()


# ============================================================================
# Output Model Tests
# ============================================================================


class TestResearchOutput:
    """Test ResearchOutput model."""

    def test_output_model_structure(self):
        """ResearchOutput has expected fields."""
        output = ResearchOutput(
            id="res_123",
            query="test query",
            answer="test answer",
            source="perplexity",
        )
        assert output.id == "res_123"
        assert output.query == "test query"
        assert output.answer == "test answer"
        assert output.source == "perplexity"
        assert output.model is None
        assert output.citations == []
        assert output.response_time_seconds is None
        assert output.content_path is None

    def test_output_with_citations(self):
        """ResearchOutput can include citations."""
        citations = [
            CitationOutput(
                title="Source 1",
                url="https://example.com/1",
                snippet="Snippet text",
                published_date="2024-01-01",
                domain="example.com",
            ),
        ]
        output = ResearchOutput(
            id="res_123",
            query="test",
            answer="answer",
            source="perplexity",
            citations=citations,
        )
        assert len(output.citations) == 1
        assert output.citations[0].title == "Source 1"


class TestCitationOutput:
    """Test CitationOutput model."""

    def test_citation_minimal(self):
        """CitationOutput requires title and url."""
        citation = CitationOutput(title="Title", url="https://example.com")
        assert citation.title == "Title"
        assert citation.url == "https://example.com"
        assert citation.snippet is None
        assert citation.published_date is None
        assert citation.domain is None

    def test_citation_all_fields(self):
        """CitationOutput accepts all optional fields."""
        citation = CitationOutput(
            title="Full Title",
            url="https://example.com/article",
            snippet="Article snippet text",
            published_date="2024-01-15",
            domain="example.com",
        )
        assert citation.title == "Full Title"
        assert citation.url == "https://example.com/article"
        assert citation.snippet == "Article snippet text"
        assert citation.published_date == "2024-01-15"
        assert citation.domain == "example.com"


# ============================================================================
# Tool Execution Tests
# ============================================================================


class TestResearchToolExecution:
    """Test ResearchTool execution with mocked Perplexity."""

    @pytest.mark.asyncio
    async def test_run_success(self, mock_research_result, tool_context):
        """ResearchTool.run returns successful result with mocked adapter."""
        TOOLS["research"] = ResearchTool

        with patch(
            "kurt.integrations.research.config.get_source_config"
        ) as mock_config, patch(
            "kurt.integrations.research.perplexity.PerplexityAdapter"
        ) as mock_adapter_class:
            mock_config.return_value = {"api_key": "test_key"}
            mock_adapter = MagicMock()
            mock_adapter.search.return_value = mock_research_result
            mock_adapter_class.return_value = mock_adapter

            result = await execute_tool(
                "research",
                {"query": "What are the latest AI trends?"},
                context=tool_context,
            )

            assert result.success is True
            assert len(result.data) == 1
            assert result.data[0]["id"] == "res_20240115_abc12345"
            assert result.data[0]["query"] == "What are the latest AI trends?"
            assert "AI trends" in result.data[0]["answer"]
            assert result.data[0]["source"] == "perplexity"
            assert len(result.data[0]["citations"]) == 2

            mock_adapter.search.assert_called_once_with(
                query="What are the latest AI trends?",
                recency="day",
                model="sonar-reasoning",
            )

    @pytest.mark.asyncio
    async def test_run_with_custom_params(self, mock_research_result, tool_context):
        """ResearchTool.run passes custom parameters to adapter."""
        TOOLS["research"] = ResearchTool

        with patch(
            "kurt.integrations.research.config.get_source_config"
        ) as mock_config, patch(
            "kurt.integrations.research.perplexity.PerplexityAdapter"
        ) as mock_adapter_class:
            mock_config.return_value = {"api_key": "test_key"}
            mock_adapter = MagicMock()
            mock_adapter.search.return_value = mock_research_result
            mock_adapter_class.return_value = mock_adapter

            await execute_tool(
                "research",
                {
                    "query": "test query",
                    "recency": "week",
                    "model": "sonar-pro",
                },
                context=tool_context,
            )

            mock_adapter.search.assert_called_once_with(
                query="test query",
                recency="week",
                model="sonar-pro",
            )

    @pytest.mark.asyncio
    async def test_run_emits_progress(self, mock_research_result, tool_context):
        """ResearchTool.run emits progress events."""
        TOOLS["research"] = ResearchTool
        events: list[SubstepEvent] = []

        def on_progress(event: SubstepEvent):
            events.append(event)

        with patch(
            "kurt.integrations.research.config.get_source_config"
        ) as mock_config, patch(
            "kurt.integrations.research.perplexity.PerplexityAdapter"
        ) as mock_adapter_class:
            mock_config.return_value = {"api_key": "test_key"}
            mock_adapter = MagicMock()
            mock_adapter.search.return_value = mock_research_result
            mock_adapter_class.return_value = mock_adapter

            await execute_tool(
                "research",
                {"query": "test"},
                context=tool_context,
                on_progress=on_progress,
            )

        assert len(events) >= 2
        assert events[0].substep == "research_query"
        assert events[0].status == "running"
        assert events[1].substep == "research_query"
        assert events[1].status == "completed"

    @pytest.mark.asyncio
    async def test_run_handles_adapter_error(self, tool_context):
        """ResearchTool.run returns error result when adapter fails."""
        TOOLS["research"] = ResearchTool

        with patch(
            "kurt.integrations.research.config.get_source_config"
        ) as mock_config, patch(
            "kurt.integrations.research.perplexity.PerplexityAdapter"
        ) as mock_adapter_class:
            mock_config.return_value = {"api_key": "test_key"}
            mock_adapter = MagicMock()
            mock_adapter.search.side_effect = Exception("API request failed")
            mock_adapter_class.return_value = mock_adapter

            result = await execute_tool(
                "research",
                {"query": "test"},
                context=tool_context,
            )

            assert result.success is False
            assert len(result.errors) == 1
            assert result.errors[0].error_type == "research_failed"
            assert "API request failed" in result.errors[0].message


# ============================================================================
# Save Results Tests
# ============================================================================


class TestResearchToolSave:
    """Test ResearchTool save functionality."""

    @pytest.mark.asyncio
    async def test_save_results_to_file(self, mock_research_result, tool_context, tmp_path):
        """ResearchTool saves results when save=True."""
        TOOLS["research"] = ResearchTool
        tool_context.settings["project_root"] = str(tmp_path)

        with patch(
            "kurt.integrations.research.config.get_source_config"
        ) as mock_config, patch(
            "kurt.integrations.research.perplexity.PerplexityAdapter"
        ) as mock_adapter_class:
            mock_config.return_value = {"api_key": "test_key"}
            mock_adapter = MagicMock()
            mock_adapter.search.return_value = mock_research_result
            mock_adapter_class.return_value = mock_adapter

            result = await execute_tool(
                "research",
                {
                    "query": "test query",
                    "save": True,
                    "output_dir": "research_output",
                },
                context=tool_context,
            )

            assert result.success is True
            assert result.data[0]["content_path"] is not None
            output_dir = tmp_path / "research_output"
            assert output_dir.exists()
            files = list(output_dir.glob("*.md"))
            assert len(files) == 1

    @pytest.mark.asyncio
    async def test_no_save_in_dry_run(self, mock_research_result, tool_context, tmp_path):
        """ResearchTool does not save when dry_run=True."""
        TOOLS["research"] = ResearchTool
        tool_context.settings["project_root"] = str(tmp_path)

        with patch(
            "kurt.integrations.research.config.get_source_config"
        ) as mock_config, patch(
            "kurt.integrations.research.perplexity.PerplexityAdapter"
        ) as mock_adapter_class:
            mock_config.return_value = {"api_key": "test_key"}
            mock_adapter = MagicMock()
            mock_adapter.search.return_value = mock_research_result
            mock_adapter_class.return_value = mock_adapter

            result = await execute_tool(
                "research",
                {
                    "query": "test query",
                    "save": True,
                    "dry_run": True,
                    "output_dir": "research_output",
                },
                context=tool_context,
            )

            assert result.success is True
            assert result.data[0]["content_path"] is None
            output_dir = tmp_path / "research_output"
            assert not output_dir.exists()

    @pytest.mark.asyncio
    async def test_no_save_by_default(self, mock_research_result, tool_context, tmp_path):
        """ResearchTool does not save by default."""
        TOOLS["research"] = ResearchTool
        tool_context.settings["project_root"] = str(tmp_path)

        with patch(
            "kurt.integrations.research.config.get_source_config"
        ) as mock_config, patch(
            "kurt.integrations.research.perplexity.PerplexityAdapter"
        ) as mock_adapter_class:
            mock_config.return_value = {"api_key": "test_key"}
            mock_adapter = MagicMock()
            mock_adapter.search.return_value = mock_research_result
            mock_adapter_class.return_value = mock_adapter

            result = await execute_tool(
                "research",
                {"query": "test query"},
                context=tool_context,
            )

            assert result.success is True
            assert result.data[0]["content_path"] is None


# ============================================================================
# Substep Tests
# ============================================================================


class TestResearchToolSubsteps:
    """Test ResearchTool substep tracking."""

    @pytest.mark.asyncio
    async def test_substeps_without_save(self, mock_research_result, tool_context):
        """ResearchTool includes research_query substep."""
        TOOLS["research"] = ResearchTool

        with patch(
            "kurt.integrations.research.config.get_source_config"
        ) as mock_config, patch(
            "kurt.integrations.research.perplexity.PerplexityAdapter"
        ) as mock_adapter_class:
            mock_config.return_value = {"api_key": "test_key"}
            mock_adapter = MagicMock()
            mock_adapter.search.return_value = mock_research_result
            mock_adapter_class.return_value = mock_adapter

            result = await execute_tool(
                "research",
                {"query": "test"},
                context=tool_context,
            )

            assert len(result.substeps) >= 1
            substep_names = [s.name for s in result.substeps]
            assert "research_query" in substep_names

    @pytest.mark.asyncio
    async def test_substeps_with_save(self, mock_research_result, tool_context, tmp_path):
        """ResearchTool includes save_results substep when save=True."""
        TOOLS["research"] = ResearchTool
        tool_context.settings["project_root"] = str(tmp_path)

        with patch(
            "kurt.integrations.research.config.get_source_config"
        ) as mock_config, patch(
            "kurt.integrations.research.perplexity.PerplexityAdapter"
        ) as mock_adapter_class:
            mock_config.return_value = {"api_key": "test_key"}
            mock_adapter = MagicMock()
            mock_adapter.search.return_value = mock_research_result
            mock_adapter_class.return_value = mock_adapter

            result = await execute_tool(
                "research",
                {"query": "test", "save": True},
                context=tool_context,
            )

            substep_names = [s.name for s in result.substeps]
            assert "research_query" in substep_names
            assert "save_results" in substep_names
