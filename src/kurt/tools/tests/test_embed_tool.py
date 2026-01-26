"""
Unit tests for EmbedTool.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from kurt.tools.base import SubstepEvent, ToolContext
from kurt.tools.embed_tool import (
    PROVIDER_DEFAULT_MODELS,
    PROVIDER_MAX_BATCH_SIZES,
    EmbedConfig,
    EmbedInput,
    EmbedOutput,
    EmbedParams,
    EmbedTool,
    _is_retryable_error,
    bytes_to_embedding,
    embedding_to_bytes,
)
from kurt.tools.registry import TOOLS, clear_registry, get_tool

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset tool registry before and after each test."""
    # Save existing tools
    saved_tools = dict(TOOLS)
    clear_registry()

    # Re-register EmbedTool for tests
    from kurt.tools.embed_tool import EmbedTool

    TOOLS["embed"] = EmbedTool

    yield

    # Restore original registry
    clear_registry()
    TOOLS.update(saved_tools)


@pytest.fixture
def tool_context():
    """Create a tool context."""
    return ToolContext(
        settings={"openai_api_key": "test-key"},
    )


@pytest.fixture
def mock_embeddings():
    """Sample embedding vectors for testing."""
    return [
        [0.1, 0.2, 0.3, 0.4],
        [0.5, 0.6, 0.7, 0.8],
        [0.9, 1.0, 1.1, 1.2],
    ]


# ============================================================================
# EmbedInput Tests
# ============================================================================


class TestEmbedInput:
    """Test EmbedInput model."""

    def test_valid_text(self):
        """Valid text input."""
        inp = EmbedInput(text="Hello, world!")
        assert inp.text == "Hello, world!"

    def test_text_required(self):
        """Text is required."""
        with pytest.raises(ValidationError):
            EmbedInput()


# ============================================================================
# EmbedConfig Tests
# ============================================================================


class TestEmbedConfig:
    """Test EmbedConfig model."""

    def test_default_values(self):
        """Default configuration values."""
        config = EmbedConfig()
        assert config.model == "text-embedding-3-small"
        assert config.text_field == "content"
        assert config.provider == "openai"
        assert config.batch_size == 100
        assert config.concurrency == 2
        assert config.max_chars == 8000

    def test_custom_values(self):
        """Custom configuration values."""
        config = EmbedConfig(
            model="text-embedding-3-large",
            text_field="body",
            provider="cohere",
            batch_size=50,
            concurrency=5,
            max_chars=4000,
        )
        assert config.model == "text-embedding-3-large"
        assert config.text_field == "body"
        assert config.provider == "cohere"
        assert config.batch_size == 50
        assert config.concurrency == 5
        assert config.max_chars == 4000

    def test_batch_size_bounds(self):
        """Batch size must be between 1 and 2048."""
        with pytest.raises(ValidationError):
            EmbedConfig(batch_size=0)
        with pytest.raises(ValidationError):
            EmbedConfig(batch_size=3000)

        # Valid bounds
        EmbedConfig(batch_size=1)
        EmbedConfig(batch_size=2048)

    def test_concurrency_bounds(self):
        """Concurrency must be between 1 and 10."""
        with pytest.raises(ValidationError):
            EmbedConfig(concurrency=0)
        with pytest.raises(ValidationError):
            EmbedConfig(concurrency=11)

        # Valid bounds
        EmbedConfig(concurrency=1)
        EmbedConfig(concurrency=10)

    def test_invalid_provider(self):
        """Invalid provider raises validation error."""
        with pytest.raises(ValidationError):
            EmbedConfig(provider="invalid")


# ============================================================================
# EmbedOutput Tests
# ============================================================================


class TestEmbedOutput:
    """Test EmbedOutput model."""

    def test_successful_output(self):
        """Successful embed output."""
        embedding_bytes = embedding_to_bytes([0.1, 0.2, 0.3])
        out = EmbedOutput(
            text="Hello world",
            embedding=embedding_bytes,
            status="success",
        )
        assert out.text == "Hello world"
        assert out.embedding == embedding_bytes
        assert out.status == "success"
        assert out.error is None

    def test_error_output(self):
        """Error embed output."""
        out = EmbedOutput(
            text="Hello world",
            status="error",
            error="API error",
        )
        assert out.status == "error"
        assert out.error == "API error"
        assert out.embedding is None

    def test_skipped_output(self):
        """Skipped embed output."""
        out = EmbedOutput(
            text="",
            status="skipped",
            error="Empty text",
        )
        assert out.status == "skipped"


# ============================================================================
# EmbedParams Tests
# ============================================================================


class TestEmbedParams:
    """Test EmbedParams model."""

    def test_with_inputs(self):
        """Create params with inputs."""
        params = EmbedParams(
            inputs=[
                {"content": "Hello"},
                {"content": "World"},
            ]
        )
        assert len(params.get_inputs()) == 2
        assert params.get_config().model == "text-embedding-3-small"  # Default

    def test_with_custom_config(self):
        """Create params with custom config."""
        params = EmbedParams(
            inputs=[{"content": "Hello"}],
            config=EmbedConfig(model="text-embedding-3-large", provider="openai"),
        )
        assert params.get_config().model == "text-embedding-3-large"

    def test_with_input_data(self):
        """Create params with input_data (executor style)."""
        params = EmbedParams(
            input_data=[{"content": "Hello"}],
            model="text-embedding-3-large",
            provider="openai",
        )
        assert len(params.get_inputs()) == 1
        assert params.get_config().model == "text-embedding-3-large"


# ============================================================================
# Utility Function Tests
# ============================================================================


class TestUtilityFunctions:
    """Test utility functions."""

    def test_embedding_to_bytes_roundtrip(self):
        """Embedding to bytes and back preserves values."""
        original = [0.1, 0.2, 0.3, 0.4, 0.5]
        as_bytes = embedding_to_bytes(original)

        # Check it's bytes
        assert isinstance(as_bytes, bytes)

        # Convert back
        restored = bytes_to_embedding(as_bytes)

        # Check values (floating point comparison)
        assert len(restored) == len(original)
        for orig, rest in zip(original, restored):
            assert abs(orig - rest) < 1e-6

    def test_embedding_to_bytes_size(self):
        """Embedding bytes have correct size (4 bytes per float32)."""
        embedding = [0.1, 0.2, 0.3]
        as_bytes = embedding_to_bytes(embedding)
        assert len(as_bytes) == 3 * 4  # 3 floats * 4 bytes


# ============================================================================
# Retry Logic Tests
# ============================================================================


class TestRetryLogic:
    """Test retry logic."""

    def test_rate_limit_retryable(self):
        """Rate limit errors should be retried."""
        assert _is_retryable_error(Exception("Rate limit exceeded")) is True
        assert _is_retryable_error(Exception("Error: 429 Too Many Requests")) is True

    def test_server_errors_retryable(self):
        """Server errors should be retried."""
        assert _is_retryable_error(Exception("Error: 500 Internal Server Error")) is True
        assert _is_retryable_error(Exception("Error: 502 Bad Gateway")) is True
        assert _is_retryable_error(Exception("Error: 503 Service Unavailable")) is True
        assert _is_retryable_error(Exception("Error: 504 Gateway Timeout")) is True

    def test_timeout_retryable(self):
        """Timeout errors should be retried."""
        assert _is_retryable_error(Exception("Request timeout")) is True

    def test_connection_errors_retryable(self):
        """Connection errors should be retried."""
        assert _is_retryable_error(Exception("Connection refused")) is True

    def test_auth_errors_not_retryable(self):
        """Auth errors should NOT be retried."""
        assert _is_retryable_error(Exception("Authentication failed")) is False
        assert _is_retryable_error(Exception("Error: 401 Unauthorized")) is False
        assert _is_retryable_error(Exception("Error: 403 Forbidden")) is False

    def test_invalid_request_not_retryable(self):
        """Invalid request errors should NOT be retried."""
        assert _is_retryable_error(Exception("Error: 400 Bad Request")) is False
        assert _is_retryable_error(Exception("Invalid model specified")) is False


# ============================================================================
# EmbedTool Registration Tests
# ============================================================================


class TestEmbedToolRegistration:
    """Test EmbedTool is registered correctly."""

    def test_tool_registered(self):
        """EmbedTool is registered in TOOLS."""
        assert "embed" in TOOLS

    def test_get_tool(self):
        """get_tool returns EmbedTool."""
        tool_class = get_tool("embed")
        assert tool_class is EmbedTool

    def test_tool_attributes(self):
        """EmbedTool has correct attributes."""
        assert EmbedTool.name == "embed"
        assert EmbedTool.description
        assert EmbedTool.InputModel is EmbedParams
        assert EmbedTool.OutputModel is EmbedOutput


# ============================================================================
# EmbedTool Execution Tests
# ============================================================================


class TestEmbedToolExecution:
    """Test EmbedTool execution."""

    @pytest.mark.asyncio
    async def test_empty_inputs(self, tool_context):
        """Empty inputs returns empty result."""
        tool = EmbedTool()
        params = EmbedParams(inputs=[])

        result = await tool.run(params, tool_context)

        assert result.success is True
        assert result.data == []

    @pytest.mark.asyncio
    async def test_progress_callback(self, tool_context, mock_embeddings):
        """Progress callback is called with SubstepEvents."""
        events: list[SubstepEvent] = []

        def on_progress(event: SubstepEvent):
            events.append(event)

        tool = EmbedTool()
        params = EmbedParams(
            inputs=[
                {"content": "Hello"},
                {"content": "World"},
            ],
        )

        # Mock the embedding function
        with patch("kurt.tools.embed_tool._embed_with_retry") as mock_embed:
            mock_embed.return_value = (mock_embeddings[:2], 50)
            await tool.run(params, tool_context, on_progress)

        # Check that progress events were emitted
        assert len(events) > 0

        # Check generate_embeddings substep events
        embed_events = [e for e in events if e.substep == "generate_embeddings"]
        assert any(e.status == "running" for e in embed_events)
        assert any(e.status == "completed" for e in embed_events)

    @pytest.mark.asyncio
    async def test_successful_embed(self, tool_context, mock_embeddings):
        """Successful embedding returns embeddings."""
        tool = EmbedTool()
        params = EmbedParams(
            inputs=[
                {"content": "Hello, world!"},
                {"content": "Test embedding"},
            ],
        )

        # Mock the embedding function
        with patch("kurt.tools.embed_tool._embed_with_retry") as mock_embed:
            mock_embed.return_value = (mock_embeddings[:2], 50)
            result = await tool.run(params, tool_context)

        assert result.success is True
        assert len(result.data) == 2
        assert result.data[0]["status"] == "success"
        assert result.data[0]["embedding"] is not None
        assert result.data[1]["status"] == "success"
        assert result.data[1]["embedding"] is not None

    @pytest.mark.asyncio
    async def test_empty_text_skipped(self, tool_context, mock_embeddings):
        """Empty text inputs are skipped."""
        tool = EmbedTool()
        params = EmbedParams(
            inputs=[
                {"content": "Hello"},
                {"content": ""},  # Empty - should be skipped
                {"content": "World"},
            ],
        )

        # Mock the embedding function
        with patch("kurt.tools.embed_tool._embed_with_retry") as mock_embed:
            # Only 2 texts should be embedded (skipping empty)
            mock_embed.return_value = (mock_embeddings[:2], 50)
            result = await tool.run(params, tool_context)

        assert result.success is True
        assert len(result.data) == 3

        assert result.data[0]["status"] == "success"
        assert result.data[1]["status"] == "skipped"
        assert result.data[2]["status"] == "success"

    @pytest.mark.asyncio
    async def test_text_truncation(self, tool_context, mock_embeddings):
        """Long text is truncated."""
        tool = EmbedTool()

        # Create text longer than max_chars
        long_text = "x" * 10000
        params = EmbedParams(
            inputs=[{"content": long_text}],
            config=EmbedConfig(max_chars=1000),
        )

        # Track what text was passed to embedding function
        captured_texts = []

        async def mock_embed(texts, *args, **kwargs):
            captured_texts.extend(texts)
            return ([[0.1, 0.2, 0.3]], 50)

        with patch("kurt.tools.embed_tool._embed_with_retry", side_effect=mock_embed):
            result = await tool.run(params, tool_context)

        assert result.success is True
        # Verify text was truncated
        assert len(captured_texts[0]) == 1000

    @pytest.mark.asyncio
    async def test_custom_text_field(self, tool_context, mock_embeddings):
        """Custom text field is used."""
        tool = EmbedTool()
        params = EmbedParams(
            inputs=[
                {"body": "Hello from body field"},
                {"body": "Another body"},
            ],
            config=EmbedConfig(text_field="body"),
        )

        # Mock the embedding function
        with patch("kurt.tools.embed_tool._embed_with_retry") as mock_embed:
            mock_embed.return_value = (mock_embeddings[:2], 50)
            result = await tool.run(params, tool_context)

        assert result.success is True
        assert len(result.data) == 2
        assert result.data[0]["status"] == "success"

    @pytest.mark.asyncio
    async def test_batch_processing(self, tool_context):
        """Inputs are processed in batches."""
        tool = EmbedTool()

        # Create many inputs to test batching
        inputs = [{"content": f"Text {i}"} for i in range(10)]
        params = EmbedParams(
            inputs=inputs,
            config=EmbedConfig(batch_size=3),  # 10 texts in batches of 3 = 4 batches
        )

        # Track number of API calls
        call_count = 0

        async def mock_embed(texts, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            return ([[0.1, 0.2] for _ in texts], 50)

        with patch("kurt.tools.embed_tool._embed_with_retry", side_effect=mock_embed):
            result = await tool.run(params, tool_context)

        assert result.success is True
        # Should have 4 batches: 3+3+3+1 = 10 texts
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_concurrency_control(self, tool_context):
        """Concurrency is controlled by semaphore."""
        tool = EmbedTool()

        # Track concurrent calls
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def mock_embed(texts, *args, **kwargs):
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                if current_concurrent > max_concurrent:
                    max_concurrent = current_concurrent

            await asyncio.sleep(0.01)  # Small delay to allow overlap

            async with lock:
                current_concurrent -= 1

            return ([[0.1, 0.2] for _ in texts], 50)

        # 10 texts in batches of 2 = 5 batches, concurrency 2
        inputs = [{"content": f"Text {i}"} for i in range(10)]
        params = EmbedParams(
            inputs=inputs,
            config=EmbedConfig(batch_size=2, concurrency=2),
        )

        with patch("kurt.tools.embed_tool._embed_with_retry", side_effect=mock_embed):
            await tool.run(params, tool_context)

        # Max concurrent should not exceed configured concurrency
        assert max_concurrent <= 2

    @pytest.mark.asyncio
    async def test_failed_batch(self, tool_context, mock_embeddings):
        """Failed batch marks all items as errors."""
        tool = EmbedTool()
        params = EmbedParams(
            inputs=[
                {"content": "Hello"},
                {"content": "World"},
            ],
        )

        # Mock the embedding function to fail
        with patch("kurt.tools.embed_tool._embed_with_retry") as mock_embed:
            mock_embed.side_effect = Exception("API Error")
            result = await tool.run(params, tool_context)

        # All failed
        assert result.success is False
        assert len(result.data) == 2
        assert result.data[0]["status"] == "error"
        assert result.data[1]["status"] == "error"
        assert "API Error" in result.data[0]["error"]

    @pytest.mark.asyncio
    async def test_substep_summaries(self, tool_context, mock_embeddings):
        """Result includes substep summaries."""
        tool = EmbedTool()
        params = EmbedParams(
            inputs=[{"content": "Hello"}],
        )

        # Mock the embedding function
        with patch("kurt.tools.embed_tool._embed_with_retry") as mock_embed:
            mock_embed.return_value = (mock_embeddings[:1], 50)
            result = await tool.run(params, tool_context)

        # Check substeps
        substep_names = [s.name for s in result.substeps]
        assert "generate_embeddings" in substep_names

    @pytest.mark.asyncio
    async def test_provider_batch_size_limit(self, tool_context, mock_embeddings):
        """Batch size is capped by provider maximum."""
        tool = EmbedTool()

        # Cohere has max batch size of 96
        params = EmbedParams(
            inputs=[{"content": "Text"}],
            config=EmbedConfig(provider="cohere", batch_size=200),  # Over limit
        )

        # Track batch size passed to API
        captured_batch_size = 0

        async def mock_embed(texts, *args, **kwargs):
            nonlocal captured_batch_size
            captured_batch_size = len(texts)
            return ([[0.1, 0.2] for _ in texts], 50)

        with patch("kurt.tools.embed_tool._embed_with_retry", side_effect=mock_embed):
            await tool.run(params, tool_context)

        # Batch size should be capped to provider max (but we only have 1 text)
        # This test just verifies the batch size logic doesn't crash
        assert captured_batch_size == 1

    @pytest.mark.asyncio
    async def test_missing_text_field(self, tool_context, mock_embeddings):
        """Missing text field is handled gracefully."""
        tool = EmbedTool()
        params = EmbedParams(
            inputs=[
                {"other_field": "Hello"},  # Missing 'content' field
            ],
        )

        result = await tool.run(params, tool_context)

        # Should be skipped
        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_preserves_input_fields(self, tool_context, mock_embeddings):
        """Output includes all input fields plus embedding."""
        tool = EmbedTool()
        params = EmbedParams(
            inputs=[
                {"content": "Hello", "id": "doc1", "source": "test"},
            ],
        )

        with patch("kurt.tools.embed_tool._embed_with_retry") as mock_embed:
            mock_embed.return_value = (mock_embeddings[:1], 50)
            result = await tool.run(params, tool_context)

        # Check original fields are preserved
        assert result.data[0]["content"] == "Hello"
        assert result.data[0]["id"] == "doc1"
        assert result.data[0]["source"] == "test"
        # Plus new fields
        assert result.data[0]["embedding"] is not None
        assert result.data[0]["status"] == "success"


# ============================================================================
# Provider Configuration Tests
# ============================================================================


class TestProviderConfiguration:
    """Test provider-specific configuration."""

    def test_provider_max_batch_sizes(self):
        """Provider max batch sizes are defined."""
        assert PROVIDER_MAX_BATCH_SIZES["openai"] == 2048
        assert PROVIDER_MAX_BATCH_SIZES["cohere"] == 96
        assert PROVIDER_MAX_BATCH_SIZES["voyage"] == 128

    def test_provider_default_models(self):
        """Provider default models are defined."""
        assert PROVIDER_DEFAULT_MODELS["openai"] == "text-embedding-3-small"
        assert PROVIDER_DEFAULT_MODELS["cohere"] == "embed-english-v3.0"
        assert PROVIDER_DEFAULT_MODELS["voyage"] == "voyage-2"


# ============================================================================
# Integration Tests (with real API - marked for optional execution)
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_openai_embedding(tool_context):
    """
    Integration test with real OpenAI API.

    Run with: pytest -m integration

    Requires OPENAI_API_KEY environment variable.
    """
    import os

    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    tool = EmbedTool()
    params = EmbedParams(
        inputs=[{"content": "Hello, world!"}],
        config=EmbedConfig(model="text-embedding-3-small"),
    )

    # Don't mock - use real API
    result = await tool.run(params, ToolContext())

    assert result.success is True
    assert len(result.data) == 1
    assert result.data[0]["status"] == "success"
    assert result.data[0]["embedding"] is not None

    # Verify embedding dimensions (text-embedding-3-small has 1536 dims)
    embedding = bytes_to_embedding(result.data[0]["embedding"])
    assert len(embedding) == 1536
