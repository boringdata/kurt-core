"""
Unit tests for FetchTool.
"""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from pydantic import ValidationError

from kurt.tools.base import SubstepEvent, ToolContext, ToolResult
from kurt.tools.fetch_tool import (
    MAX_CONTENT_SIZE_BYTES,
    NON_RETRYABLE_STATUS_CODES,
    RETRYABLE_STATUS_CODES,
    FetchConfig,
    FetchEngine,
    FetchInput,
    FetchOutput,
    FetchParams,
    FetchStatus,
    FetchTool,
    _compute_content_hash,
    _fetch_with_retry,
    _generate_content_path,
    _is_retryable_error,
    _save_content,
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

    # Re-register FetchTool for tests
    from kurt.tools.fetch_tool import FetchTool

    TOOLS["fetch"] = FetchTool

    yield

    # Restore original registry
    clear_registry()
    TOOLS.update(saved_tools)


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    return tmp_path


@pytest.fixture
def tool_context(temp_project_dir):
    """Create a tool context with temp project directory."""
    return ToolContext(
        settings={"project_root": str(temp_project_dir)},
    )


@pytest.fixture
def mock_html_response():
    """Sample HTML response for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page</title></head>
    <body>
        <article>
            <h1>Test Article</h1>
            <p>This is test content for the fetch tool.</p>
        </article>
    </body>
    </html>
    """


# ============================================================================
# FetchInput Tests
# ============================================================================


class TestFetchInput:
    """Test FetchInput model."""

    def test_valid_url(self):
        """Valid URL input."""
        inp = FetchInput(url="https://example.com")
        assert inp.url == "https://example.com"

    def test_url_required(self):
        """URL is required."""
        with pytest.raises(ValidationError):
            FetchInput()


# ============================================================================
# FetchConfig Tests
# ============================================================================


class TestFetchConfig:
    """Test FetchConfig model."""

    def test_default_values(self):
        """Default configuration values."""
        config = FetchConfig()
        assert config.engine == "trafilatura"
        assert config.concurrency == 5
        assert config.timeout_ms == 30000
        assert config.retries == 3
        assert config.retry_backoff_ms == 1000
        assert config.embed is None  # None = auto-detect from API keys
        assert config.content_dir is None

    def test_custom_values(self):
        """Custom configuration values."""
        config = FetchConfig(
            engine="httpx",
            concurrency=10,
            timeout_ms=60000,
            retries=5,
            retry_backoff_ms=2000,
            embed=True,
            content_dir="custom_sources",
        )
        assert config.engine == "httpx"
        assert config.concurrency == 10
        assert config.timeout_ms == 60000
        assert config.retries == 5
        assert config.retry_backoff_ms == 2000
        assert config.embed is True
        assert config.content_dir == "custom_sources"

    def test_concurrency_bounds(self):
        """Concurrency must be between 1 and 20."""
        with pytest.raises(ValidationError):
            FetchConfig(concurrency=0)
        with pytest.raises(ValidationError):
            FetchConfig(concurrency=21)

        # Valid bounds
        FetchConfig(concurrency=1)
        FetchConfig(concurrency=20)

    def test_invalid_engine(self):
        """Invalid engine raises validation error."""
        with pytest.raises(ValidationError):
            FetchConfig(engine="invalid")


# ============================================================================
# FetchOutput Tests
# ============================================================================


class TestFetchOutput:
    """Test FetchOutput model."""

    def test_successful_output(self):
        """Successful fetch output."""
        out = FetchOutput(
            url="https://example.com",
            content_path="sources/example.com/index.md",
            content_hash="abc123",
            status="success",
            bytes_fetched=1024,
            latency_ms=150,
        )
        assert out.url == "https://example.com"
        assert out.status == "success"
        assert out.error is None

    def test_error_output(self):
        """Error fetch output."""
        out = FetchOutput(
            url="https://example.com",
            status="error",
            error="Connection refused",
        )
        assert out.status == "error"
        assert out.error == "Connection refused"

    def test_default_values(self):
        """Default values are set correctly."""
        out = FetchOutput(url="https://example.com")
        assert out.content_path == ""
        assert out.content_hash == ""
        assert out.status == "success"
        assert out.error is None
        assert out.bytes_fetched == 0
        assert out.latency_ms == 0


# ============================================================================
# FetchParams Tests
# ============================================================================


class TestFetchParams:
    """Test FetchParams model."""

    def test_with_urls(self):
        """Create params with URLs."""
        params = FetchParams(
            inputs=[
                FetchInput(url="https://example.com"),
                FetchInput(url="https://test.com"),
            ]
        )
        assert len(params.get_inputs()) == 2
        assert params.get_config().engine == "trafilatura"  # Default

    def test_with_custom_config(self):
        """Create params with custom config."""
        params = FetchParams(
            inputs=[FetchInput(url="https://example.com")],
            config=FetchConfig(engine="httpx", concurrency=10),
        )
        assert params.get_config().engine == "httpx"
        assert params.get_config().concurrency == 10

    def test_with_input_data(self):
        """Create params with input_data (executor style)."""
        params = FetchParams(
            input_data=[
                FetchInput(url="https://example.com"),
            ],
            engine="httpx",
            concurrency=3,
        )
        assert len(params.get_inputs()) == 1
        assert params.get_config().engine == "httpx"
        assert params.get_config().concurrency == 3


# ============================================================================
# Utility Function Tests
# ============================================================================


class TestUtilityFunctions:
    """Test utility functions."""

    def test_compute_content_hash(self):
        """Content hash is computed correctly."""
        content = "Hello, World!"
        expected = hashlib.sha256(content.encode("utf-8")).hexdigest()
        assert _compute_content_hash(content) == expected

    def test_generate_content_path_default_dir(self):
        """Generate path with default directory."""
        path = _generate_content_path("https://example.com/blog/post", None)
        assert path == "sources/example.com/blog/post.md"

    def test_generate_content_path_custom_dir(self):
        """Generate path with custom directory."""
        path = _generate_content_path("https://example.com/blog/post", "custom")
        assert path == "custom/example.com/blog/post.md"

    def test_generate_content_path_root_url(self):
        """Generate path for root URL."""
        path = _generate_content_path("https://example.com/", None)
        assert path == "sources/example.com/index.md"

    def test_generate_content_path_html_extension(self):
        """Generate path removes .html extension."""
        path = _generate_content_path("https://example.com/page.html", None)
        assert path == "sources/example.com/page.md"

    def test_generate_content_path_special_chars(self):
        """Generate path sanitizes special characters."""
        path = _generate_content_path("https://example.com/foo?bar=1&baz=2", None)
        assert "?" not in path
        assert "&" not in path
        assert path.endswith(".md")

    def test_save_content(self, temp_project_dir):
        """Content is saved to file."""
        context = ToolContext(settings={"project_root": str(temp_project_dir)})
        content = "# Test Content\n\nThis is a test."
        content_path = "sources/test.md"

        result = _save_content(content, content_path, context)

        assert result == content_path
        full_path = temp_project_dir / content_path
        assert full_path.exists()
        assert full_path.read_text() == content


# ============================================================================
# Retry Logic Tests
# ============================================================================


class TestRetryLogic:
    """Test retry logic."""

    def test_retryable_status_codes(self):
        """HTTP status codes that should be retried."""
        for code in RETRYABLE_STATUS_CODES:
            response = Mock()
            response.status_code = code
            error = httpx.HTTPStatusError("error", request=Mock(), response=response)
            assert _is_retryable_error(error) is True

    def test_non_retryable_status_codes(self):
        """HTTP status codes that should NOT be retried."""
        for code in NON_RETRYABLE_STATUS_CODES:
            response = Mock()
            response.status_code = code
            error = httpx.HTTPStatusError("error", request=Mock(), response=response)
            assert _is_retryable_error(error) is False

    def test_connection_errors_retryable(self):
        """Connection errors should be retried."""
        assert _is_retryable_error(httpx.ConnectError("failed")) is True
        assert _is_retryable_error(httpx.ConnectTimeout("timeout")) is True

    def test_timeout_errors_retryable(self):
        """Timeout errors should be retried."""
        assert _is_retryable_error(httpx.ReadTimeout("timeout")) is True
        assert _is_retryable_error(httpx.WriteTimeout("timeout")) is True
        assert _is_retryable_error(httpx.PoolTimeout("timeout")) is True

    def test_content_errors_not_retryable(self):
        """Content-related errors should NOT be retried."""
        assert _is_retryable_error(ValueError("content_too_large: 15MB")) is False
        assert _is_retryable_error(ValueError("invalid_content_type: image/png")) is False


# ============================================================================
# FetchTool Registration Tests
# ============================================================================


class TestFetchToolRegistration:
    """Test FetchTool is registered correctly."""

    def test_tool_registered(self):
        """FetchTool is registered in TOOLS."""
        assert "fetch" in TOOLS

    def test_get_tool(self):
        """get_tool returns FetchTool."""
        tool_class = get_tool("fetch")
        assert tool_class is FetchTool

    def test_tool_attributes(self):
        """FetchTool has correct attributes."""
        assert FetchTool.name == "fetch"
        assert FetchTool.description
        assert FetchTool.InputModel is FetchParams
        assert FetchTool.OutputModel is FetchOutput


# ============================================================================
# FetchTool Execution Tests
# ============================================================================


class TestFetchToolExecution:
    """Test FetchTool execution."""

    @pytest.mark.asyncio
    async def test_empty_inputs(self, tool_context):
        """Empty inputs returns empty result."""
        tool = FetchTool()
        params = FetchParams(inputs=[])

        result = await tool.run(params, tool_context)

        assert result.success is True
        assert result.data == []

    @pytest.mark.asyncio
    async def test_progress_callback(self, tool_context, mock_html_response):
        """Progress callback is called with SubstepEvents."""
        events: list[SubstepEvent] = []

        def on_progress(event: SubstepEvent):
            events.append(event)

        tool = FetchTool()
        params = FetchParams(
            inputs=[FetchInput(url="https://example.com")],
            config=FetchConfig(retries=0),
        )

        # Mock _fetch_single_url to avoid network calls
        async def mock_fetch(url, config, timeout_s, semaphore, client):
            return {
                "url": url,
                "content": "# Test Content",
                "metadata": {"fingerprint": "abc123"},
                "content_hash": "abc123def456",
                "status": "success",
                "error": None,
                "bytes_fetched": 100,
                "latency_ms": 50,
            }

        with patch.object(tool, "_fetch_single_url", side_effect=mock_fetch):
            with patch("kurt.tools.fetch_tool.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                result = await tool.run(params, tool_context, on_progress)

        # Check that progress events were emitted
        assert len(events) > 0

        # Check fetch_urls substep events
        fetch_events = [e for e in events if e.substep == "fetch_urls"]
        assert any(e.status == "running" for e in fetch_events)
        assert any(e.status == "completed" for e in fetch_events)

        # Check save_content substep events
        save_events = [e for e in events if e.substep == "save_content"]
        assert any(e.status == "running" for e in save_events)
        assert any(e.status == "completed" for e in save_events)

    @pytest.mark.asyncio
    async def test_successful_fetch(self, tool_context, mock_html_response):
        """Successful fetch returns content."""
        tool = FetchTool()
        params = FetchParams(
            inputs=[FetchInput(url="https://example.com")],
            config=FetchConfig(retries=0),
        )

        # Mock _fetch_single_url to avoid network calls
        async def mock_fetch(url, config, timeout_s, semaphore, client):
            return {
                "url": url,
                "content": "# Test Article\n\nThis is test content.",
                "metadata": {"title": "Test Page", "fingerprint": "abc123"},
                "content_hash": "abc123def456",
                "status": "success",
                "error": None,
                "bytes_fetched": 100,
                "latency_ms": 50,
            }

        with patch.object(tool, "_fetch_single_url", side_effect=mock_fetch):
            with patch("kurt.tools.fetch_tool.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                result = await tool.run(params, tool_context)

        assert result.success is True
        assert len(result.data) == 1
        assert result.data[0]["url"] == "https://example.com"
        assert result.data[0]["status"] == "success"
        assert result.data[0]["content_hash"]
        assert result.data[0]["bytes_fetched"] > 0

    @pytest.mark.asyncio
    async def test_failed_fetch(self, tool_context):
        """Failed fetch returns error."""
        tool = FetchTool()
        params = FetchParams(
            inputs=[FetchInput(url="https://example.com")],
            config=FetchConfig(retries=0),
        )

        # Mock _fetch_single_url to return an error
        async def mock_fetch(url, config, timeout_s, semaphore, client):
            return {
                "url": url,
                "content": None,
                "metadata": None,
                "content_hash": "",
                "status": "error",
                "error": "connection_error",
                "bytes_fetched": 0,
                "latency_ms": 0,
            }

        with patch.object(tool, "_fetch_single_url", side_effect=mock_fetch):
            with patch("kurt.tools.fetch_tool.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                result = await tool.run(params, tool_context)

        # Result is still success=True if at least partial success possible
        # But in this case, all failed, so success=False
        assert result.success is False
        assert len(result.data) == 1
        assert result.data[0]["status"] == "error"
        assert result.data[0]["error"] == "connection_error"

    @pytest.mark.asyncio
    async def test_concurrency_control(self, tool_context, mock_html_response):
        """Concurrency is controlled by semaphore."""
        tool = FetchTool()

        # Track concurrent calls
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def mock_fetch(url, config, timeout_s, semaphore, client):
            nonlocal max_concurrent, current_concurrent
            # The mock must use the semaphore to test concurrency control
            async with semaphore:
                async with lock:
                    current_concurrent += 1
                    if current_concurrent > max_concurrent:
                        max_concurrent = current_concurrent

                await asyncio.sleep(0.01)  # Small delay to allow overlap

                async with lock:
                    current_concurrent -= 1

                return {
                    "url": url,
                    "content": "# Content",
                    "metadata": {"fingerprint": "abc"},
                    "content_hash": "abc123",
                    "status": "success",
                    "error": None,
                    "bytes_fetched": 100,
                    "latency_ms": 50,
                }

        params = FetchParams(
            inputs=[FetchInput(url=f"https://example.com/{i}") for i in range(10)],
            config=FetchConfig(concurrency=3, retries=0),
        )

        with patch.object(tool, "_fetch_single_url", side_effect=mock_fetch):
            with patch("kurt.tools.fetch_tool.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                await tool.run(params, tool_context)

        # Max concurrent should not exceed configured concurrency
        assert max_concurrent <= 3

    @pytest.mark.asyncio
    async def test_content_saved_to_disk(self, tool_context, mock_html_response, temp_project_dir):
        """Fetched content is saved to disk."""
        tool = FetchTool()
        params = FetchParams(
            inputs=[FetchInput(url="https://example.com/test/page")],
            config=FetchConfig(retries=0),
        )

        # Mock _fetch_single_url to return content
        async def mock_fetch(url, config, timeout_s, semaphore, client):
            return {
                "url": url,
                "content": "# Test Content\n\nSaved to disk.",
                "metadata": {"fingerprint": "abc123"},
                "content_hash": "abc123def456",
                "status": "success",
                "error": None,
                "bytes_fetched": 100,
                "latency_ms": 50,
            }

        with patch.object(tool, "_fetch_single_url", side_effect=mock_fetch):
            with patch("kurt.tools.fetch_tool.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                result = await tool.run(params, tool_context)

        assert result.success is True
        assert result.data[0]["content_path"]

        # Verify file exists
        content_path = result.data[0]["content_path"]
        full_path = temp_project_dir / content_path
        assert full_path.exists()
        assert "Test Content" in full_path.read_text()

    @pytest.mark.asyncio
    async def test_substep_summaries(self, tool_context, mock_html_response):
        """Result includes substep summaries."""
        tool = FetchTool()
        params = FetchParams(
            inputs=[FetchInput(url="https://example.com")],
            config=FetchConfig(retries=0),
        )

        # Mock _fetch_single_url to return content
        async def mock_fetch(url, config, timeout_s, semaphore, client):
            return {
                "url": url,
                "content": "# Content",
                "metadata": {"fingerprint": "abc"},
                "content_hash": "abc123",
                "status": "success",
                "error": None,
                "bytes_fetched": 100,
                "latency_ms": 50,
            }

        with patch.object(tool, "_fetch_single_url", side_effect=mock_fetch):
            with patch("kurt.tools.fetch_tool.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                result = await tool.run(params, tool_context)

        # Check substeps
        substep_names = [s.name for s in result.substeps]
        assert "fetch_urls" in substep_names
        assert "save_content" in substep_names

    @pytest.mark.asyncio
    async def test_tavily_engine_stub(self, tool_context):
        """Tavily engine returns skipped status."""
        tool = FetchTool()
        params = FetchParams(
            inputs=[FetchInput(url="https://example.com")],
            config=FetchConfig(engine="tavily"),
        )

        result = await tool.run(params, tool_context)

        assert result.data[0]["status"] == "skipped"
        assert "not yet implemented" in result.data[0]["error"].lower()

    @pytest.mark.asyncio
    async def test_firecrawl_engine_stub(self, tool_context):
        """Firecrawl engine returns skipped status."""
        tool = FetchTool()
        params = FetchParams(
            inputs=[FetchInput(url="https://example.com")],
            config=FetchConfig(engine="firecrawl"),
        )

        result = await tool.run(params, tool_context)

        assert result.data[0]["status"] == "skipped"
        assert "not yet implemented" in result.data[0]["error"].lower()


# ============================================================================
# Integration Tests (with real network - marked for optional execution)
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_fetch(tool_context):
    """
    Integration test with real network.

    Run with: pytest -m integration
    """
    tool = FetchTool()
    params = FetchParams(
        inputs=[FetchInput(url="https://example.com")],
        config=FetchConfig(retries=1),
    )

    result = await tool.run(params, tool_context)

    assert result.success is True
    assert len(result.data) == 1
    assert result.data[0]["status"] == "success"
