"""
Unit tests for LLMTool.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kurt.tools.base import SubstepEvent, ToolContext
from kurt.tools.llm_tool import (
    LLMBatchProcessor,
    LLMConfig,
    LLMInput,
    LLMOutput,
    LLMParams,
    LLMTool,
    QuotaExceededError,
    RateLimitError,
    call_anthropic,
    call_openai,
    resolve_output_schema,
)
from kurt.tools.registry import TOOLS, clear_registry

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def clean_registry():
    """Clear the registry before and after each test."""
    saved_tools = dict(TOOLS)
    clear_registry()
    TOOLS["llm"] = LLMTool
    yield
    clear_registry()
    TOOLS.update(saved_tools)


@pytest.fixture
def sample_config():
    """Sample LLM configuration."""
    return LLMConfig(
        prompt_template="Summarize: {content}",
        model="gpt-4o-mini",
        provider="openai",
        concurrency=2,
        timeout_ms=5000,
        max_retries=1,
    )


@pytest.fixture
def sample_inputs():
    """Sample LLM inputs."""
    return [
        LLMInput(row={"content": "The quick brown fox"}),
        LLMInput(row={"content": "Lorem ipsum dolor sit amet"}),
        LLMInput(row={"content": "Hello world"}),
    ]


# ============================================================================
# Output Schema Resolution Tests
# ============================================================================


class TestResolveOutputSchema:
    """Test output schema resolution."""

    def test_resolve_builtin_schema(self):
        """Resolve built-in schemas."""
        schema = resolve_output_schema("ExtractEntities")
        assert schema is not None
        assert schema.__name__ == "ExtractEntities"

    def test_resolve_builtin_sentiment(self):
        """Resolve SentimentAnalysis schema."""
        schema = resolve_output_schema("SentimentAnalysis")
        assert schema is not None
        assert "sentiment" in schema.model_fields

    def test_resolve_builtin_keywords(self):
        """Resolve ExtractKeywords schema."""
        schema = resolve_output_schema("ExtractKeywords")
        assert schema is not None
        assert "keywords" in schema.model_fields

    def test_resolve_builtin_summarize(self):
        """Resolve Summarize schema."""
        schema = resolve_output_schema("Summarize")
        assert schema is not None
        assert "summary" in schema.model_fields

    def test_unknown_schema_returns_none(self):
        """Unknown schema name returns None."""
        schema = resolve_output_schema("UnknownSchema")
        assert schema is None

    def test_empty_schema_name(self):
        """Empty schema name returns None."""
        schema = resolve_output_schema("")
        assert schema is None


# ============================================================================
# LLMConfig Tests
# ============================================================================


class TestLLMConfig:
    """Test LLMConfig validation."""

    def test_default_values(self):
        """Default values are set correctly."""
        config = LLMConfig(prompt_template="Hello {name}")
        assert config.model == "gpt-4o-mini"
        assert config.provider == "openai"
        assert config.concurrency == 3
        assert config.timeout_ms == 60000
        assert config.max_retries == 2
        assert config.temperature == 0.0
        assert config.max_tokens == 4096

    def test_custom_values(self):
        """Custom values override defaults."""
        config = LLMConfig(
            prompt_template="Test {content}",
            output_schema="ExtractEntities",
            model="claude-3-haiku-20240307",
            provider="anthropic",
            concurrency=5,
            timeout_ms=30000,
            max_retries=3,
            temperature=0.7,
            max_tokens=8192,
        )
        assert config.model == "claude-3-haiku-20240307"
        assert config.provider == "anthropic"
        assert config.concurrency == 5
        assert config.timeout_ms == 30000
        assert config.max_retries == 3
        assert config.temperature == 0.7
        assert config.max_tokens == 8192

    def test_concurrency_bounds(self):
        """Concurrency must be between 1 and 20."""
        with pytest.raises(Exception):
            LLMConfig(prompt_template="Test", concurrency=0)

        with pytest.raises(Exception):
            LLMConfig(prompt_template="Test", concurrency=21)

    def test_temperature_bounds(self):
        """Temperature must be between 0 and 2."""
        with pytest.raises(Exception):
            LLMConfig(prompt_template="Test", temperature=-0.1)

        with pytest.raises(Exception):
            LLMConfig(prompt_template="Test", temperature=2.1)


# ============================================================================
# LLMInput Tests
# ============================================================================


class TestLLMInput:
    """Test LLMInput validation."""

    def test_valid_input(self):
        """Valid input with row dict."""
        input_item = LLMInput(row={"content": "Hello world", "title": "Test"})
        assert input_item.row["content"] == "Hello world"
        assert input_item.row["title"] == "Test"

    def test_empty_row(self):
        """Empty row is valid."""
        input_item = LLMInput(row={})
        assert input_item.row == {}

    def test_nested_row_values(self):
        """Row can contain nested values."""
        input_item = LLMInput(row={"metadata": {"author": "Test", "date": "2024-01-01"}})
        assert input_item.row["metadata"]["author"] == "Test"


# ============================================================================
# Prompt Template Tests
# ============================================================================


class TestPromptTemplate:
    """Test prompt template substitution."""

    def test_simple_substitution(self, sample_config):
        """Simple field substitution works."""
        processor = LLMBatchProcessor(
            config=sample_config,
            output_schema=None,
            on_progress=None,
            emit_fn=lambda *args, **kwargs: None,
        )
        row = {"content": "Hello world"}
        prompt = processor._build_prompt(row)
        assert prompt == "Summarize: Hello world"

    def test_multiple_fields(self):
        """Multiple field substitution."""
        config = LLMConfig(
            prompt_template="Title: {title}\nContent: {content}",
        )
        processor = LLMBatchProcessor(
            config=config,
            output_schema=None,
            on_progress=None,
            emit_fn=lambda *args, **kwargs: None,
        )
        row = {"title": "Test Title", "content": "Test content"}
        prompt = processor._build_prompt(row)
        assert prompt == "Title: Test Title\nContent: Test content"

    def test_missing_field_raises(self, sample_config):
        """Missing field raises KeyError."""
        processor = LLMBatchProcessor(
            config=sample_config,
            output_schema=None,
            on_progress=None,
            emit_fn=lambda *args, **kwargs: None,
        )
        row = {"title": "No content field"}
        with pytest.raises(KeyError):
            processor._build_prompt(row)


# ============================================================================
# Mock LLM Provider Tests
# ============================================================================

# Check if packages are available
try:
    import openai  # noqa: F401
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import anthropic  # noqa: F401
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


@pytest.mark.skipif(not HAS_OPENAI, reason="openai package not installed")
class TestMockOpenAI:
    """Test OpenAI provider with mocks."""

    @pytest.mark.asyncio
    async def test_call_openai_success(self):
        """Successful OpenAI call."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is a summary"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20

        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            with patch("openai.AsyncOpenAI", return_value=mock_client):
                config = LLMConfig(prompt_template="Test")
                output, tokens_in, tokens_out, cost = await call_openai(
                    "Test prompt",
                    config,
                    None,
                    5.0,
                )

                assert output == "This is a summary"
                assert tokens_in == 10
                assert tokens_out == 20
                assert cost > 0

    @pytest.mark.asyncio
    async def test_call_openai_missing_api_key(self):
        """Missing API key raises error."""
        with patch.dict("os.environ", {}, clear=True):
            config = LLMConfig(prompt_template="Test")
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                await call_openai("Test", config, None, 5.0)


@pytest.mark.skipif(not HAS_ANTHROPIC, reason="anthropic package not installed")
class TestMockAnthropic:
    """Test Anthropic provider with mocks."""

    @pytest.mark.asyncio
    async def test_call_anthropic_success(self):
        """Successful Anthropic call."""
        mock_content = MagicMock()
        mock_content.type = "text"
        mock_content.text = "This is a summary"

        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 15
        mock_response.usage.output_tokens = 25

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("anthropic.AsyncAnthropic", return_value=mock_client):
                config = LLMConfig(
                    prompt_template="Test",
                    provider="anthropic",
                    model="claude-3-haiku-20240307",
                )
                output, tokens_in, tokens_out, cost = await call_anthropic(
                    "Test prompt",
                    config,
                    None,
                    5.0,
                )

                assert output == "This is a summary"
                assert tokens_in == 15
                assert tokens_out == 25
                assert cost > 0

    @pytest.mark.asyncio
    async def test_call_anthropic_missing_api_key(self):
        """Missing API key raises error."""
        with patch.dict("os.environ", {}, clear=True):
            config = LLMConfig(prompt_template="Test", provider="anthropic")
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                await call_anthropic("Test", config, None, 5.0)


# ============================================================================
# Batch Processor Tests
# ============================================================================


class TestLLMBatchProcessor:
    """Test LLMBatchProcessor."""

    @pytest.mark.asyncio
    async def test_process_batch_success(self, sample_config, sample_inputs):
        """Successful batch processing."""

        async def mock_call_openai(*args, **kwargs):
            return "Summary text", 10, 5, 0.001

        with patch("kurt.tools.llm_tool.call_openai", mock_call_openai):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                events: list[dict[str, Any]] = []

                def emit_fn(
                    on_progress, substep, status, current=None, total=None, message=None, metadata=None
                ):
                    events.append({
                        "substep": substep,
                        "status": status,
                        "current": current,
                        "total": total,
                    })

                processor = LLMBatchProcessor(
                    config=sample_config,
                    output_schema=None,
                    on_progress=None,
                    emit_fn=emit_fn,
                )

                results = await processor.process_batch(sample_inputs)

                assert len(results) == 3
                for result in results:
                    assert result["status"] == "success"
                    assert result["llm_output"] == "Summary text"
                    assert result["tokens_in"] == 10
                    assert result["tokens_out"] == 5

                # Check progress events
                assert len(events) == 3  # One per input

    @pytest.mark.asyncio
    async def test_process_batch_with_errors(self, sample_config, sample_inputs):
        """Batch with some failures."""
        call_count = 0

        async def mock_call_with_errors(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("API Error")
            return "Summary", 10, 5, 0.001

        with patch("kurt.tools.llm_tool.call_openai", mock_call_with_errors):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                processor = LLMBatchProcessor(
                    config=sample_config,
                    output_schema=None,
                    on_progress=None,
                    emit_fn=lambda *args, **kwargs: None,
                )

                results = await processor.process_batch(sample_inputs)

                assert len(results) == 3
                success_count = sum(1 for r in results if r["status"] == "success")
                error_count = sum(1 for r in results if r["status"] == "error")
                assert success_count == 2
                assert error_count == 1

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, sample_config):
        """Rate limit triggers wait and retry."""
        call_count = 0

        async def mock_with_rate_limit(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitError("Rate limited", retry_after=0.01)
            return "Success", 10, 5, 0.001

        inputs = [LLMInput(row={"content": "test"})]

        with patch("kurt.tools.llm_tool.call_openai", mock_with_rate_limit):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                processor = LLMBatchProcessor(
                    config=sample_config,
                    output_schema=None,
                    on_progress=None,
                    emit_fn=lambda *args, **kwargs: None,
                )

                results = await processor.process_batch(inputs)

                assert len(results) == 1
                assert results[0]["status"] == "success"
                assert call_count == 2  # First call failed, second succeeded

    @pytest.mark.asyncio
    async def test_quota_exceeded_stops_processing(self, sample_config, sample_inputs):
        """Quota exceeded marks remaining as errors."""
        call_count = 0

        async def mock_with_quota(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "Success", 10, 5, 0.001
            raise QuotaExceededError("Quota exceeded")

        with patch("kurt.tools.llm_tool.call_openai", mock_with_quota):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                # Use concurrency=1 to ensure sequential processing
                config = LLMConfig(
                    prompt_template="Test: {content}",
                    concurrency=1,
                )
                processor = LLMBatchProcessor(
                    config=config,
                    output_schema=None,
                    on_progress=None,
                    emit_fn=lambda *args, **kwargs: None,
                )

                results = await processor.process_batch(sample_inputs)

                # First succeeds, rest should fail with quota_exceeded
                assert results[0]["status"] == "success"
                assert results[1]["status"] == "error"
                assert "quota_exceeded" in results[1]["error"]


# ============================================================================
# LLMTool Integration Tests
# ============================================================================


class TestLLMTool:
    """Test LLMTool class."""

    def test_tool_registered(self):
        """LLMTool is registered in TOOLS."""
        assert "llm" in TOOLS
        assert TOOLS["llm"] is LLMTool

    def test_tool_attributes(self):
        """LLMTool has correct attributes."""
        assert LLMTool.name == "llm"
        assert LLMTool.description is not None
        assert LLMTool.InputModel is LLMParams
        assert LLMTool.OutputModel is LLMOutput

    @pytest.mark.asyncio
    async def test_run_empty_inputs(self):
        """Empty inputs returns empty result."""
        tool = LLMTool()
        params = LLMParams(
            inputs=[],
            config=LLMConfig(prompt_template="Test"),
        )
        context = ToolContext()

        result = await tool.run(params, context)

        assert result.success is True
        assert result.data == []

    @pytest.mark.asyncio
    async def test_run_with_mock_llm(self, sample_config, sample_inputs):
        """Run tool with mocked LLM."""

        async def mock_call(*args, **kwargs):
            return "Summarized text", 10, 5, 0.001

        with patch("kurt.tools.llm_tool.call_openai", mock_call):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                tool = LLMTool()
                params = LLMParams(inputs=sample_inputs, config=sample_config)
                context = ToolContext()

                events: list[SubstepEvent] = []

                def on_progress(event: SubstepEvent):
                    events.append(event)

                result = await tool.run(params, context, on_progress)

                assert result.success is True
                assert len(result.data) == 3

                # Check merged output
                for item in result.data:
                    assert "content" in item  # Original row field
                    assert "llm_response" in item  # LLM output
                    assert item["_status"] == "success"
                    assert item["_tokens_in"] == 10
                    assert item["_tokens_out"] == 5

                # Check substeps
                assert len(result.substeps) == 1
                assert result.substeps[0].name == "llm_batch"
                assert result.substeps[0].status == "completed"

                # Check progress events
                assert len(events) >= 2  # At least running + completed

    @pytest.mark.asyncio
    async def test_run_with_invalid_schema(self, sample_inputs):
        """Invalid schema name returns error."""
        tool = LLMTool()
        config = LLMConfig(
            prompt_template="Test: {content}",
            output_schema="NonExistentSchema",
        )
        params = LLMParams(inputs=sample_inputs, config=config)
        context = ToolContext()

        result = await tool.run(params, context)

        assert result.success is False
        assert len(result.errors) == 1
        assert result.errors[0].error_type == "schema_not_found"

    @pytest.mark.asyncio
    async def test_run_with_structured_output(self, sample_inputs):
        """Run with structured output schema."""

        async def mock_call(*args, **kwargs):
            return {
                "sentiment": "positive",
                "confidence": 0.95,
                "reasoning": "Happy words",
            }, 15, 10, 0.002

        with patch("kurt.tools.llm_tool.call_openai", mock_call):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                tool = LLMTool()
                config = LLMConfig(
                    prompt_template="Analyze: {content}",
                    output_schema="SentimentAnalysis",
                )
                params = LLMParams(inputs=sample_inputs, config=config)
                context = ToolContext()

                result = await tool.run(params, context)

                assert result.success is True
                assert len(result.data) == 3

                for item in result.data:
                    # Structured output fields merged
                    assert item["sentiment"] == "positive"
                    assert item["confidence"] == 0.95
                    assert item["reasoning"] == "Happy words"

    @pytest.mark.asyncio
    async def test_progress_callback(self, sample_config, sample_inputs):
        """Progress callback is called."""

        async def mock_call(*args, **kwargs):
            return "Test", 10, 5, 0.001

        with patch("kurt.tools.llm_tool.call_openai", mock_call):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                tool = LLMTool()
                params = LLMParams(inputs=sample_inputs, config=sample_config)
                context = ToolContext()

                events: list[SubstepEvent] = []

                def on_progress(event: SubstepEvent):
                    events.append(event)

                await tool.run(params, context, on_progress)

                # Should have running, progress for each input, and completed
                assert any(e.substep == "llm_batch" and e.status == "running" for e in events)
                assert any(e.substep == "llm_batch" and e.status == "completed" for e in events)
                progress_events = [e for e in events if e.status == "progress"]
                assert len(progress_events) == 3


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_missing_template_field(self, sample_config):
        """Missing template field is handled gracefully."""

        async def mock_call(*args, **kwargs):
            return "Test", 10, 5, 0.001

        with patch("kurt.tools.llm_tool.call_openai", mock_call):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                tool = LLMTool()
                inputs = [
                    LLMInput(row={"wrong_field": "value"}),  # Missing 'content'
                ]
                params = LLMParams(inputs=inputs, config=sample_config)
                context = ToolContext()

                result = await tool.run(params, context)

                # Should complete but with errors
                assert len(result.data) == 1
                assert result.data[0]["_status"] == "error"
                assert "Missing field" in result.data[0]["_error"]

    @pytest.mark.asyncio
    async def test_timeout_handling(self, sample_config, sample_inputs):
        """Timeout is handled gracefully."""

        async def mock_timeout(*args, **kwargs):
            raise asyncio.TimeoutError()

        with patch("kurt.tools.llm_tool.call_openai", mock_timeout):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                tool = LLMTool()
                params = LLMParams(inputs=sample_inputs, config=sample_config)
                context = ToolContext()

                result = await tool.run(params, context)

                for item in result.data:
                    assert item["_status"] == "error"
                    assert item["_error"] == "timeout"

    @pytest.mark.asyncio
    async def test_partial_success(self, sample_config):
        """Partial success is reported correctly."""
        call_count = 0

        async def mock_partial(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                raise Exception("Error on even")
            return "Success", 10, 5, 0.001

        with patch("kurt.tools.llm_tool.call_openai", mock_partial):
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
                tool = LLMTool()
                inputs = [LLMInput(row={"content": f"test{i}"}) for i in range(4)]
                params = LLMParams(inputs=inputs, config=sample_config)
                context = ToolContext()

                result = await tool.run(params, context)

                # Overall success because some succeeded
                assert result.success is True
                success_count = sum(1 for d in result.data if d["_status"] == "success")
                error_count = sum(1 for d in result.data if d["_status"] == "error")
                assert success_count == 2
                assert error_count == 2


# ============================================================================
# Cost Estimation Tests
# ============================================================================


class TestCostEstimation:
    """Test cost estimation functions."""

    def test_openai_cost_gpt4o(self):
        """GPT-4o cost estimation."""
        from kurt.tools.llm_tool import _estimate_openai_cost

        cost = _estimate_openai_cost("gpt-4o", 1000, 500)
        # $5/1M in + $15/1M out
        expected = (1000 * 5 + 500 * 15) / 1_000_000
        assert abs(cost - expected) < 0.0001

    def test_openai_cost_gpt4o_mini(self):
        """GPT-4o-mini cost estimation."""
        from kurt.tools.llm_tool import _estimate_openai_cost

        cost = _estimate_openai_cost("gpt-4o-mini", 1000, 500)
        # $0.15/1M in + $0.60/1M out
        expected = (1000 * 0.15 + 500 * 0.60) / 1_000_000
        assert abs(cost - expected) < 0.0001

    def test_anthropic_cost_haiku(self):
        """Claude Haiku cost estimation."""
        from kurt.tools.llm_tool import _estimate_anthropic_cost

        cost = _estimate_anthropic_cost("claude-3-haiku-20240307", 1000, 500)
        # $0.25/1M in + $1.25/1M out
        expected = (1000 * 0.25 + 500 * 1.25) / 1_000_000
        assert abs(cost - expected) < 0.0001

    def test_anthropic_cost_sonnet(self):
        """Claude Sonnet cost estimation."""
        from kurt.tools.llm_tool import _estimate_anthropic_cost

        cost = _estimate_anthropic_cost("claude-3-5-sonnet-20240620", 1000, 500)
        # $3/1M in + $15/1M out
        expected = (1000 * 3 + 500 * 15) / 1_000_000
        assert abs(cost - expected) < 0.0001
