"""
FetchTool - Content fetching tool for Kurt workflows.

Fetches content from URLs using configurable engines (trafilatura, httpx, tavily, firecrawl).
Supports parallel fetching with concurrency control and exponential backoff retries.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from enum import Enum
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from .base import ProgressCallback, Tool, ToolContext, ToolResult
from .registry import register_tool

logger = logging.getLogger(__name__)


# ============================================================================
# Constants
# ============================================================================

# Maximum content size (10 MB)
MAX_CONTENT_SIZE_BYTES = 10 * 1024 * 1024

# HTTP status codes that should trigger a retry
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# HTTP status codes that should NOT be retried
NON_RETRYABLE_STATUS_CODES = {400, 401, 403, 404}

# Valid content types for text extraction
VALID_CONTENT_TYPES = {
    "text/html",
    "text/plain",
    "application/xhtml+xml",
    "application/xml",
    "text/xml",
}


# ============================================================================
# Pydantic Models
# ============================================================================


class FetchEngine(str, Enum):
    """Supported fetch engines."""

    TRAFILATURA = "trafilatura"
    HTTPX = "httpx"
    TAVILY = "tavily"
    FIRECRAWL = "firecrawl"


class FetchStatus(str, Enum):
    """Status of a fetch operation."""

    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"


class FetchInput(BaseModel):
    """Input for a single URL to fetch."""

    url: str = Field(..., description="URL to fetch")


class FetchConfig(BaseModel):
    """Configuration for the fetch tool."""

    engine: Literal["trafilatura", "httpx", "tavily", "firecrawl"] = Field(
        default="trafilatura",
        description="Fetch engine to use",
    )
    concurrency: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum parallel fetches (1-20)",
    )
    timeout_ms: int = Field(
        default=30000,
        ge=1000,
        le=120000,
        description="Request timeout in milliseconds",
    )
    retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts",
    )
    retry_backoff_ms: int = Field(
        default=1000,
        ge=100,
        le=60000,
        description="Base backoff delay in milliseconds (exponential: delay * 2^attempt)",
    )
    embed: bool = Field(
        default=False,
        description="Generate embeddings after fetch",
    )
    content_dir: str | None = Field(
        default=None,
        description="Directory to save content (relative to project root)",
    )


class FetchOutput(BaseModel):
    """Output for a fetched URL."""

    url: str = Field(..., description="URL that was fetched")
    content_path: str = Field(default="", description="Path to saved content file")
    content_hash: str = Field(default="", description="SHA256 hash of content")
    status: Literal["success", "error", "skipped"] = Field(
        default="success",
        description="Fetch status",
    )
    error: str | None = Field(default=None, description="Error message if failed")
    bytes_fetched: int = Field(default=0, description="Size of fetched content")
    latency_ms: int = Field(default=0, description="Time taken to fetch in ms")


class FetchParams(BaseModel):
    """Combined parameters for the fetch tool.

    Accepts two input styles:
    1. Executor style (flat): input_data + config fields directly
    2. Direct API style (nested): inputs + config

    The executor passes:
    - input_data: list of dicts with 'url' key (from upstream steps)
    - Config fields directly: engine, concurrency, timeout_ms, etc.
    """

    # Input from upstream steps (executor passes "input_data")
    # Also accepts "inputs" for direct API usage
    input_data: list[FetchInput] = Field(
        default_factory=list,
        description="List of URLs to fetch (from upstream steps)",
    )

    # Alternative field name for direct API usage
    inputs: list[FetchInput] = Field(
        default_factory=list,
        description="List of URLs to fetch (alternative to input_data)",
    )

    # Nested config for direct API usage
    config: FetchConfig | None = Field(
        default=None,
        description="Fetch configuration (alternative to flat fields)",
    )

    # Config fields (flattened for executor compatibility)
    engine: Literal["trafilatura", "httpx", "tavily", "firecrawl"] = Field(
        default="trafilatura",
        description="Fetch engine to use",
    )
    concurrency: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum parallel fetches (1-20)",
    )
    timeout_ms: int = Field(
        default=30000,
        ge=1000,
        le=120000,
        description="Request timeout in milliseconds",
    )
    retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts",
    )
    retry_backoff_ms: int = Field(
        default=1000,
        ge=100,
        le=60000,
        description="Base backoff delay in milliseconds (exponential: delay * 2^attempt)",
    )
    embed: bool = Field(
        default=False,
        description="Generate embeddings after fetch",
    )
    content_dir: str | None = Field(
        default=None,
        description="Directory to save content (relative to project root)",
    )

    def get_inputs(self) -> list[FetchInput]:
        """Get the input list from either input_data or inputs field."""
        # Prefer input_data (from executor), fall back to inputs (from direct API)
        if self.input_data:
            return self.input_data
        return self.inputs

    def get_config(self) -> FetchConfig:
        """Get config from nested config field or flat fields."""
        # If nested config is provided, use it; otherwise build from flat fields
        if self.config is not None:
            return self.config
        return FetchConfig(
            engine=self.engine,
            concurrency=self.concurrency,
            timeout_ms=self.timeout_ms,
            retries=self.retries,
            retry_backoff_ms=self.retry_backoff_ms,
            embed=self.embed,
            content_dir=self.content_dir,
        )


# ============================================================================
# Fetch Engines
# ============================================================================


async def _fetch_with_trafilatura(
    url: str,
    timeout_s: float,
    client: httpx.AsyncClient,
) -> tuple[str, dict[str, Any]]:
    """
    Fetch content using trafilatura for extraction.

    Args:
        url: URL to fetch
        timeout_s: Timeout in seconds
        client: Async HTTP client

    Returns:
        Tuple of (markdown_content, metadata_dict)

    Raises:
        ValueError: If fetch or extraction fails
    """
    import trafilatura

    from kurt.workflows.fetch.utils import extract_with_trafilatura

    # Use httpx for the download (async-compatible)
    response = await client.get(url, timeout=timeout_s, follow_redirects=True)
    response.raise_for_status()

    # Check content type
    content_type = response.headers.get("content-type", "")
    if not any(ct in content_type.lower() for ct in VALID_CONTENT_TYPES):
        raise ValueError(f"invalid_content_type: {content_type}")

    # Check content length
    content_length = len(response.content)
    if content_length > MAX_CONTENT_SIZE_BYTES:
        raise ValueError(f"content_too_large: {content_length} bytes")

    html = response.text
    if not html:
        raise ValueError(f"No content from: {url}")

    return extract_with_trafilatura(html, url)


async def _fetch_with_httpx(
    url: str,
    timeout_s: float,
    client: httpx.AsyncClient,
) -> tuple[str, dict[str, Any]]:
    """
    Fetch content using httpx + trafilatura extraction.

    Args:
        url: URL to fetch
        timeout_s: Timeout in seconds
        client: Async HTTP client

    Returns:
        Tuple of (markdown_content, metadata_dict)

    Raises:
        ValueError: If fetch or extraction fails
    """
    from kurt.workflows.fetch.utils import extract_with_trafilatura

    response = await client.get(url, timeout=timeout_s, follow_redirects=True)
    response.raise_for_status()

    # Check content type
    content_type = response.headers.get("content-type", "")
    if not any(ct in content_type.lower() for ct in VALID_CONTENT_TYPES):
        raise ValueError(f"invalid_content_type: {content_type}")

    # Check content length
    content_length = len(response.content)
    if content_length > MAX_CONTENT_SIZE_BYTES:
        raise ValueError(f"content_too_large: {content_length} bytes")

    html = response.text
    if not html:
        raise ValueError(f"No content from: {url}")

    return extract_with_trafilatura(html, url)


async def _fetch_with_tavily(
    url: str,
    timeout_s: float,
    client: httpx.AsyncClient,
) -> tuple[str, dict[str, Any]]:
    """
    Fetch content using Tavily API (stub - not implemented).

    Args:
        url: URL to fetch
        timeout_s: Timeout in seconds
        client: Async HTTP client (unused for Tavily)

    Returns:
        Tuple of (markdown_content, metadata_dict)

    Raises:
        NotImplementedError: Always raises - Tavily is a stub
    """
    raise NotImplementedError("Tavily engine not yet implemented")


async def _fetch_with_firecrawl(
    url: str,
    timeout_s: float,
    client: httpx.AsyncClient,
) -> tuple[str, dict[str, Any]]:
    """
    Fetch content using Firecrawl API (stub - not implemented).

    Args:
        url: URL to fetch
        timeout_s: Timeout in seconds
        client: Async HTTP client (unused for Firecrawl)

    Returns:
        Tuple of (markdown_content, metadata_dict)

    Raises:
        NotImplementedError: Always raises - Firecrawl is a stub
    """
    raise NotImplementedError("Firecrawl engine not yet implemented")


# Engine dispatcher
_FETCH_ENGINES = {
    "trafilatura": _fetch_with_trafilatura,
    "httpx": _fetch_with_httpx,
    "tavily": _fetch_with_tavily,
    "firecrawl": _fetch_with_firecrawl,
}


# ============================================================================
# Retry Logic
# ============================================================================


def _is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error should trigger a retry.

    Retryable:
    - HTTP 429, 500, 502, 503, 504
    - Connection errors
    - Timeouts

    Not retryable:
    - HTTP 400, 401, 403, 404
    - Content too large
    - Invalid content type

    Args:
        error: The exception that occurred

    Returns:
        True if the error should be retried
    """
    if isinstance(error, httpx.HTTPStatusError):
        status_code = error.response.status_code
        if status_code in RETRYABLE_STATUS_CODES:
            return True
        if status_code in NON_RETRYABLE_STATUS_CODES:
            return False
        # Other status codes: don't retry by default
        return False

    if isinstance(error, (httpx.ConnectError, httpx.ConnectTimeout)):
        return True

    if isinstance(error, (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout)):
        return True

    if isinstance(error, ValueError):
        error_msg = str(error).lower()
        # Don't retry content-related errors
        if "content_too_large" in error_msg or "invalid_content_type" in error_msg:
            return False

    # Default: don't retry unknown errors
    return False


async def _fetch_with_retry(
    url: str,
    engine: str,
    timeout_s: float,
    retries: int,
    retry_backoff_ms: int,
    client: httpx.AsyncClient,
) -> tuple[str, dict[str, Any], int]:
    """
    Fetch a URL with exponential backoff retry.

    Args:
        url: URL to fetch
        engine: Fetch engine to use
        timeout_s: Request timeout in seconds
        retries: Maximum retry attempts
        retry_backoff_ms: Base backoff delay in milliseconds
        client: Async HTTP client

    Returns:
        Tuple of (content, metadata, latency_ms)

    Raises:
        Exception: The last error if all retries fail
    """
    fetch_fn = _FETCH_ENGINES[engine]
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        start_time = time.monotonic()
        try:
            content, metadata = await fetch_fn(url, timeout_s, client)
            latency_ms = int((time.monotonic() - start_time) * 1000)
            return content, metadata, latency_ms

        except Exception as e:
            last_error = e
            latency_ms = int((time.monotonic() - start_time) * 1000)

            # Check if we should retry
            if attempt < retries and _is_retryable_error(e):
                # Calculate backoff: delay * 2^attempt
                delay_ms = retry_backoff_ms * (2**attempt)
                logger.debug(
                    f"Retry {attempt + 1}/{retries} for {url} after {delay_ms}ms: {e}"
                )
                await asyncio.sleep(delay_ms / 1000)
            else:
                # No more retries or non-retryable error
                raise

    # Should not reach here, but just in case
    if last_error:
        raise last_error
    raise RuntimeError(f"Unexpected state in _fetch_with_retry for {url}")


# ============================================================================
# Content Saving
# ============================================================================


def _compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _generate_content_path(url: str, content_dir: str | None) -> str:
    """
    Generate a file path for saving content.

    Uses URL-based path for readability:
    - https://example.com/blog/post -> content_dir/example.com/blog/post.md

    Args:
        url: Source URL
        content_dir: Base directory for content (or None for default)

    Returns:
        Relative path for the content file
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    domain = parsed.netloc or "unknown"
    path = parsed.path.strip("/")

    # Handle empty path (root URL)
    if not path:
        path = "index"

    # Remove file extension if present (we'll add .md)
    if path.endswith(".html") or path.endswith(".htm"):
        path = path.rsplit(".", 1)[0]

    # Sanitize path components
    safe_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/.")
    sanitized_path = "".join(c if c in safe_chars else "_" for c in path)

    # Collapse multiple underscores
    while "__" in sanitized_path:
        sanitized_path = sanitized_path.replace("__", "_")

    # Remove trailing underscores from path segments
    sanitized_path = "/".join(
        seg.strip("_") for seg in sanitized_path.split("/") if seg.strip("_")
    )

    # Handle edge case of empty path after sanitization
    if not sanitized_path:
        sanitized_path = "index"

    base_dir = content_dir or "sources"
    return f"{base_dir}/{domain}/{sanitized_path}.md"


def _save_content(content: str, content_path: str, context: ToolContext) -> str:
    """
    Save content to a file.

    Args:
        content: Markdown content to save
        content_path: Relative path for the file
        context: Tool context (for settings like project root)

    Returns:
        The content_path that was saved
    """
    # Get project root from context settings, or use current directory
    project_root = Path(context.settings.get("project_root", "."))
    full_path = project_root / content_path

    # Ensure directory exists
    full_path.parent.mkdir(parents=True, exist_ok=True)

    # Write content
    full_path.write_text(content, encoding="utf-8")

    return content_path


# ============================================================================
# FetchTool Implementation
# ============================================================================


@register_tool
class FetchTool(Tool[FetchParams, FetchOutput]):
    """
    Fetch content from URLs.

    Substeps:
    - fetch_urls: HTTP fetch with retry (progress: urls fetched)
    - save_content: Write content to disk (progress: files saved)
    - generate_embeddings: If embed=true (progress: embeddings generated)

    Engines:
    - trafilatura: Free, local extraction with trafilatura
    - httpx: HTTP fetch + trafilatura extraction (proxy-friendly)
    - tavily: Tavily API (stub, not implemented)
    - firecrawl: Firecrawl API (stub, not implemented)
    """

    name = "fetch"
    description = "Fetch content from URLs with configurable engines and retry"
    InputModel = FetchParams
    OutputModel = FetchOutput

    async def run(
        self,
        params: FetchParams,
        context: ToolContext,
        on_progress: ProgressCallback | None = None,
    ) -> ToolResult:
        """
        Execute the fetch tool.

        Args:
            params: Fetch parameters (inputs and config)
            context: Execution context
            on_progress: Optional progress callback

        Returns:
            ToolResult with fetched URLs
        """
        config = params.get_config()
        inputs = params.get_inputs()

        if not inputs:
            return ToolResult(
                success=True,
                data=[],
            )

        total_urls = len(inputs)
        results: list[dict[str, Any]] = []

        # ----------------------------------------------------------------
        # Substep 1: fetch_urls
        # ----------------------------------------------------------------
        self.emit_progress(
            on_progress,
            substep="fetch_urls",
            status="running",
            current=0,
            total=total_urls,
            message=f"Fetching {total_urls} URL(s) with {config.engine}",
        )

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(config.concurrency)
        timeout_s = config.timeout_ms / 1000

        # Check if engine is a stub (no HTTP client needed)
        if config.engine in ("tavily", "firecrawl"):
            # Stub engines - don't create HTTP client
            fetch_results = [
                await self._fetch_single_url(
                    input_item.url,
                    config,
                    timeout_s,
                    semaphore,
                    None,  # No client needed for stubs
                )
                for input_item in inputs
            ]
        else:
            # Create shared HTTP client for real engines
            async with httpx.AsyncClient() as client:
                # Create tasks for all URLs
                fetch_tasks = [
                    self._fetch_single_url(
                        input_item.url,
                        config,
                        timeout_s,
                        semaphore,
                        client,
                    )
                    for input_item in inputs
                ]

                # Execute all tasks concurrently
                fetch_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        # Process results and emit progress
        fetched_count = 0
        failed_count = 0
        skipped_count = 0

        for i, (input_item, result) in enumerate(zip(inputs, fetch_results)):
            if isinstance(result, Exception):
                # Task raised an exception
                error_msg = str(result)
                results.append({
                    "url": input_item.url,
                    "content": None,
                    "metadata": None,
                    "content_hash": "",
                    "status": FetchStatus.ERROR.value,
                    "error": error_msg,
                    "bytes_fetched": 0,
                    "latency_ms": 0,
                })
                failed_count += 1
            else:
                # Result is a dict from _fetch_single_url
                results.append(result)
                if result["status"] == FetchStatus.SUCCESS.value:
                    fetched_count += 1
                elif result["status"] == FetchStatus.SKIPPED.value:
                    skipped_count += 1
                else:
                    failed_count += 1

            # Emit progress
            self.emit_progress(
                on_progress,
                substep="fetch_urls",
                status="progress",
                current=i + 1,
                total=total_urls,
                message=f"Fetched {i + 1}/{total_urls}",
                metadata={
                    "url": input_item.url,
                    "status": results[-1]["status"],
                },
            )

        self.emit_progress(
            on_progress,
            substep="fetch_urls",
            status="completed",
            current=total_urls,
            total=total_urls,
            message=f"Fetched {fetched_count}, failed {failed_count}, skipped {skipped_count}",
        )

        # ----------------------------------------------------------------
        # Substep 2: save_content
        # ----------------------------------------------------------------
        successful_results = [r for r in results if r["status"] == FetchStatus.SUCCESS.value]
        save_count = len(successful_results)

        self.emit_progress(
            on_progress,
            substep="save_content",
            status="running",
            current=0,
            total=save_count,
            message=f"Saving {save_count} file(s)",
        )

        saved_count = 0
        for i, result in enumerate(results):
            if result["status"] == FetchStatus.SUCCESS.value and result.get("content"):
                try:
                    content_path = _generate_content_path(result["url"], config.content_dir)
                    _save_content(result["content"], content_path, context)
                    result["content_path"] = content_path
                    saved_count += 1
                except Exception as e:
                    logger.error(f"Failed to save content for {result['url']}: {e}")
                    result["content_path"] = ""

                # Emit progress
                self.emit_progress(
                    on_progress,
                    substep="save_content",
                    status="progress",
                    current=saved_count,
                    total=save_count,
                    message=f"Saved {saved_count}/{save_count}",
                    metadata={"url": result["url"]},
                )

            # Remove content from result (don't include in output)
            result.pop("content", None)
            result.pop("metadata", None)

        self.emit_progress(
            on_progress,
            substep="save_content",
            status="completed",
            current=saved_count,
            total=save_count,
            message=f"Saved {saved_count} file(s)",
        )

        # ----------------------------------------------------------------
        # Substep 3: generate_embeddings (if enabled)
        # ----------------------------------------------------------------
        if config.embed:
            self.emit_progress(
                on_progress,
                substep="generate_embeddings",
                status="running",
                current=0,
                total=saved_count,
                message="Generating embeddings (not implemented)",
            )

            # TODO: Implement embedding generation
            # For now, just emit completion without doing anything

            self.emit_progress(
                on_progress,
                substep="generate_embeddings",
                status="completed",
                current=0,
                total=0,
                message="Embedding generation not yet implemented",
            )

        # Build final output
        output_data = [
            {
                "url": r["url"],
                "content_path": r.get("content_path", ""),
                "content_hash": r.get("content_hash", ""),
                "status": r["status"],
                "error": r.get("error"),
                "bytes_fetched": r.get("bytes_fetched", 0),
                "latency_ms": r.get("latency_ms", 0),
            }
            for r in results
        ]

        # Build result with substep summaries
        result = ToolResult(
            success=failed_count < total_urls,  # Success if at least one URL succeeded
            data=output_data,
        )

        result.add_substep(
            name="fetch_urls",
            status="completed",
            current=total_urls,
            total=total_urls,
        )
        result.add_substep(
            name="save_content",
            status="completed",
            current=saved_count,
            total=save_count,
        )

        if config.embed:
            result.add_substep(
                name="generate_embeddings",
                status="completed",
                current=0,
                total=0,
            )

        # Add errors for failed URLs
        for i, r in enumerate(results):
            if r.get("error"):
                result.add_error(
                    error_type=r["status"],
                    message=r["error"],
                    row_idx=i,
                    details={"url": r["url"]},
                )

        return result

    async def _fetch_single_url(
        self,
        url: str,
        config: FetchConfig,
        timeout_s: float,
        semaphore: asyncio.Semaphore,
        client: httpx.AsyncClient | None,
    ) -> dict[str, Any]:
        """
        Fetch a single URL with semaphore-controlled concurrency.

        Args:
            url: URL to fetch
            config: Fetch configuration
            timeout_s: Timeout in seconds
            semaphore: Concurrency semaphore
            client: Async HTTP client

        Returns:
            Result dict with url, content, status, error, etc.
        """
        async with semaphore:
            try:
                content, metadata, latency_ms = await _fetch_with_retry(
                    url=url,
                    engine=config.engine,
                    timeout_s=timeout_s,
                    retries=config.retries,
                    retry_backoff_ms=config.retry_backoff_ms,
                    client=client,
                )

                content_hash = _compute_content_hash(content)
                bytes_fetched = len(content.encode("utf-8"))

                return {
                    "url": url,
                    "content": content,
                    "metadata": metadata,
                    "content_hash": content_hash,
                    "status": FetchStatus.SUCCESS.value,
                    "error": None,
                    "bytes_fetched": bytes_fetched,
                    "latency_ms": latency_ms,
                }

            except NotImplementedError as e:
                # Engine not implemented
                return {
                    "url": url,
                    "content": None,
                    "metadata": None,
                    "content_hash": "",
                    "status": FetchStatus.SKIPPED.value,
                    "error": str(e),
                    "bytes_fetched": 0,
                    "latency_ms": 0,
                }

            except Exception as e:
                error_msg = str(e)

                # Categorize the error
                if isinstance(e, httpx.HTTPStatusError):
                    error_msg = f"HTTP {e.response.status_code}: {error_msg}"
                elif isinstance(e, httpx.TimeoutException):
                    error_msg = "timeout"
                elif isinstance(e, httpx.ConnectError):
                    error_msg = "connection_error"
                elif "content_too_large" in error_msg.lower():
                    error_msg = "content_too_large"
                elif "invalid_content_type" in error_msg.lower():
                    error_msg = "invalid_content_type"

                return {
                    "url": url,
                    "content": None,
                    "metadata": None,
                    "content_hash": "",
                    "status": FetchStatus.ERROR.value,
                    "error": error_msg,
                    "bytes_fetched": 0,
                    "latency_ms": 0,
                }
