"""Fetch tool implementation - Content fetching from URLs.

FetchTool - Content fetching tool for Kurt workflows.

Fetches content from URLs using configurable engines (trafilatura, httpx, tavily, firecrawl, apify).
Supports parallel fetching with concurrency control and exponential backoff retries.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from kurt.tools.core import ProgressCallback, Tool, ToolContext, ToolResult, register_tool

from .config import FetchConfig, has_embedding_api_keys
from .models import (
    BatchFetcher,
    BatchFetchResult,
    FetchDocument,
    FetchResult,
    FetchStatus,
)

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
# Pydantic Models for Tool Parameters
# ============================================================================


class FetchInput(BaseModel):
    """Input for a single URL to fetch."""

    url: str = Field(..., description="URL to fetch")
    document_id: str | None = Field(
        default=None,
        description="Document ID for persistence (optional)",
    )
    source_type: str | None = Field(
        default=None,
        description="Source type (url, file, cms)",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Source metadata for CMS/file fetches",
    )
    discovery_url: str | None = Field(
        default=None,
        description="Discovery URL for CMS sources (public URL)",
    )


class FetchToolConfig(BaseModel):
    """Configuration for the fetch tool (Pydantic model for tool parameters).

    Note: This is distinct from FetchConfig (StepConfig) used by workflows.
    """

    engine: Literal["trafilatura", "httpx", "tavily", "firecrawl", "apify"] = Field(
        default="trafilatura",
        description="Fetch engine to use",
    )
    platform: str | None = Field(
        default=None,
        description="Social platform for apify engine (twitter, linkedin, threads, substack)",
    )
    apify_actor: str | None = Field(
        default=None,
        description="Specific Apify actor ID (e.g., 'apidojo/tweet-scraper')",
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
    batch_size: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="Batch size for engines with batch support (tavily/firecrawl)",
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
    embed: bool | None = Field(
        default=None,
        description="Generate embeddings after fetch (None = auto-detect from API keys)",
    )
    embedding_max_chars: int = Field(
        default=1000,
        ge=100,
        le=5000,
        description="Maximum characters for embedding generation",
    )
    embedding_batch_size: int = Field(
        default=100,
        ge=1,
        le=500,
        description="Batch size for embedding generation",
    )
    content_dir: str | None = Field(
        default=None,
        description="Directory to save content (relative to project root)",
    )
    dry_run: bool = Field(
        default=False,
        description="Preview mode - skip persistence",
    )


class FetchOutput(BaseModel):
    """Output for a fetched URL."""

    url: str = Field(..., description="URL that was fetched")
    document_id: str | None = Field(
        default=None,
        description="Document ID for persistence (optional)",
    )
    content_path: str = Field(default="", description="Path to saved content file")
    content_hash: str = Field(default="", description="SHA256 hash of content")
    status: Literal["SUCCESS", "ERROR", "SKIPPED"] = Field(
        default="SUCCESS",
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
    config: FetchToolConfig | None = Field(
        default=None,
        description="Fetch configuration (alternative to flat fields)",
    )

    # Config fields (flattened for executor compatibility)
    engine: Literal["trafilatura", "httpx", "tavily", "firecrawl", "apify"] = Field(
        default="trafilatura",
        description="Fetch engine to use",
    )
    platform: str | None = Field(
        default=None,
        description="Social platform for apify engine (twitter, linkedin, threads, substack)",
    )
    apify_actor: str | None = Field(
        default=None,
        description="Specific Apify actor ID (e.g., 'apidojo/tweet-scraper')",
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
    batch_size: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="Batch size for engines with batch support (tavily/firecrawl)",
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
    embed: bool | None = Field(
        default=None,
        description="Generate embeddings after fetch (None = auto-detect from API keys)",
    )
    embedding_max_chars: int = Field(
        default=1000,
        ge=100,
        le=5000,
        description="Maximum characters for embedding generation",
    )
    embedding_batch_size: int = Field(
        default=100,
        ge=1,
        le=500,
        description="Batch size for embedding generation",
    )
    content_dir: str | None = Field(
        default=None,
        description="Directory to save content (relative to project root)",
    )
    dry_run: bool = Field(
        default=False,
        description="Preview mode - skip persistence",
    )

    def get_inputs(self) -> list[FetchInput]:
        """Get the input list from either input_data or inputs field."""
        # Prefer input_data (from executor), fall back to inputs (from direct API)
        if self.input_data:
            return self.input_data
        return self.inputs

    def get_config(self) -> FetchToolConfig:
        """Get config from nested config field or flat fields."""
        # If nested config is provided, use it; otherwise build from flat fields
        if self.config is not None:
            return self.config
        return FetchToolConfig(
            engine=self.engine,
            platform=self.platform,
            apify_actor=self.apify_actor,
            concurrency=self.concurrency,
            timeout_ms=self.timeout_ms,
            batch_size=self.batch_size,
            retries=self.retries,
            retry_backoff_ms=self.retry_backoff_ms,
            embed=self.embed,
            embedding_max_chars=self.embedding_max_chars,
            embedding_batch_size=self.embedding_batch_size,
            content_dir=self.content_dir,
            dry_run=self.dry_run,
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

    Delegates to the consolidated TrafilaturaFetcher engine.

    Args:
        url: URL to fetch
        timeout_s: Timeout in seconds (used for config)
        client: Async HTTP client (unused, kept for interface consistency)

    Returns:
        Tuple of (markdown_content, metadata_dict)

    Raises:
        ValueError: If fetch or extraction fails
    """
    from kurt.tools.fetch.engines.trafilatura import TrafilaturaFetcher

    fetcher = TrafilaturaFetcher()
    result = await asyncio.to_thread(fetcher.fetch, url)
    if not result.success:
        raise ValueError(result.error or "No result from Trafilatura")
    return result.content, result.metadata


async def _fetch_with_httpx(
    url: str,
    timeout_s: float,
    client: httpx.AsyncClient,
) -> tuple[str, dict[str, Any]]:
    """
    Fetch content using httpx + trafilatura extraction.

    Delegates to the consolidated HttpxFetcher engine.

    Args:
        url: URL to fetch
        timeout_s: Timeout in seconds (used for config)
        client: Async HTTP client (unused, kept for interface consistency)

    Returns:
        Tuple of (markdown_content, metadata_dict)

    Raises:
        ValueError: If fetch or extraction fails
    """
    from kurt.tools.fetch.core import FetcherConfig
    from kurt.tools.fetch.engines.httpx import HttpxFetcher

    config = FetcherConfig(timeout=timeout_s)
    fetcher = HttpxFetcher(config)
    result = await asyncio.to_thread(fetcher.fetch, url)
    if not result.success:
        raise ValueError(result.error or "No result from httpx")
    return result.content, result.metadata


async def _fetch_with_tavily(
    url: str,
    timeout_s: float,
    client: httpx.AsyncClient,
) -> tuple[str, dict[str, Any]]:
    """
    Fetch content using Tavily API.

    Args:
        url: URL to fetch
        timeout_s: Timeout in seconds
        client: Async HTTP client (unused for Tavily)

    Returns:
        Tuple of (markdown_content, metadata_dict)

    Raises:
        ValueError: If Tavily returns an error for the URL
    """
    from kurt.tools.fetch.engines.tavily import TavilyFetcher

    fetcher = TavilyFetcher()
    result = await asyncio.to_thread(fetcher.fetch, url)
    if not result.success:
        raise ValueError(result.error or "No result from Tavily")
    return result.content, result.metadata


async def _fetch_with_firecrawl(
    url: str,
    timeout_s: float,
    client: httpx.AsyncClient,
) -> tuple[str, dict[str, Any]]:
    """
    Fetch content using Firecrawl API.

    Args:
        url: URL to fetch
        timeout_s: Timeout in seconds
        client: Async HTTP client (unused for Firecrawl)

    Returns:
        Tuple of (markdown_content, metadata_dict)

    Raises:
        ValueError: If Firecrawl returns an error for the URL
    """
    from kurt.tools.fetch.engines.firecrawl import FirecrawlFetcher

    fetcher = FirecrawlFetcher()
    result = await asyncio.to_thread(fetcher.fetch, url)
    if not result.success:
        raise ValueError(result.error or "No result from Firecrawl")
    return result.content, result.metadata


async def _fetch_with_apify(
    url: str,
    timeout_s: float,
    client: httpx.AsyncClient,
    platform: str | None = None,
    apify_actor: str | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Fetch content using Apify for social platforms.

    Delegates to the consolidated ApifyFetcher engine.

    Args:
        url: URL to fetch (social media profile, post, or newsletter)
        timeout_s: Timeout in seconds (used for config)
        client: Async HTTP client (unused, kept for interface consistency)
        platform: Social platform (twitter, linkedin, threads, substack)
        apify_actor: Specific Apify actor ID to use

    Returns:
        Tuple of (markdown_content, metadata_dict)

    Raises:
        ValueError: If fetch or extraction fails
    """
    from kurt.tools.fetch.engines.apify import ApifyFetcher, ApifyFetcherConfig

    config = ApifyFetcherConfig(
        timeout=timeout_s,
        platform=platform,
        apify_actor=apify_actor,
    )
    fetcher = ApifyFetcher(config)
    result = await asyncio.to_thread(fetcher.fetch, url)
    if not result.success:
        raise ValueError(result.error or "No result from Apify")
    return result.content, result.metadata


# Engine dispatcher
_FETCH_ENGINES = {
    "trafilatura": _fetch_with_trafilatura,
    "httpx": _fetch_with_httpx,
    "tavily": _fetch_with_tavily,
    "firecrawl": _fetch_with_firecrawl,
    "apify": _fetch_with_apify,
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
    **engine_kwargs: Any,
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
        **engine_kwargs: Additional keyword arguments passed to engine (e.g., platform, apify_actor)

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
            # Pass extra kwargs for engines that need them (e.g., apify)
            if engine_kwargs:
                content, metadata = await fetch_fn(url, timeout_s, client, **engine_kwargs)
            else:
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

    Delegates to the canonical _url_to_path() function in utils.py for the
    URL-to-path conversion logic, then prepends the content_dir prefix.

    Args:
        url: Source URL
        content_dir: Base directory for content (or None for default "sources")

    Returns:
        Relative path for the content file
    """
    from kurt.tools.fetch.utils import _url_to_path

    base_dir = content_dir or "sources"
    relative_path = _url_to_path(url)
    return f"{base_dir}/{relative_path}"


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
    - tavily: Tavily API (native batch support)
    - firecrawl: Firecrawl API (native batch support)
    - apify: Apify social platform extraction (twitter, linkedin, threads, substack)
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

        timeout_s = config.timeout_ms / 1000
        fetch_results: list[dict[str, Any] | Exception | None] = [None] * total_urls
        web_inputs: list[FetchInput] = []
        web_indices: list[int] = []

        for idx, input_item in enumerate(inputs):
            source_type = (input_item.source_type or "url").lower()
            if source_type == "file":
                fetch_results[idx] = await self._fetch_file_input(input_item)
            elif source_type == "cms":
                fetch_results[idx] = await self._fetch_cms_input(input_item)
            else:
                web_inputs.append(input_item)
                web_indices.append(idx)

        if web_inputs:
            if config.engine in ("tavily", "firecrawl"):
                batch_results = await self._fetch_web_batch(web_inputs, config)
                for idx, input_item in zip(web_indices, web_inputs):
                    fetch_results[idx] = batch_results.get(input_item.url) or {
                        "url": input_item.url,
                        "content": None,
                        "metadata": None,
                        "content_hash": "",
                        "status": FetchStatus.ERROR.value,
                        "error": "No result",
                        "bytes_fetched": 0,
                        "latency_ms": 0,
                    }
            else:
                semaphore = asyncio.Semaphore(config.concurrency)
                async with httpx.AsyncClient() as client:
                    fetch_tasks = [
                        self._fetch_single_url(
                            input_item.url,
                            config,
                            timeout_s,
                            semaphore,
                            client,
                        )
                        for input_item in web_inputs
                    ]
                    web_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
                for idx, result in zip(web_indices, web_results):
                    fetch_results[idx] = result

        # Process results and emit progress
        fetched_count = 0
        failed_count = 0
        skipped_count = 0

        for i, (input_item, result) in enumerate(zip(inputs, fetch_results)):
            document_id = input_item.document_id
            if result is None or isinstance(result, Exception):
                # Task raised an exception
                error_msg = str(result) if result is not None else "No result"
                results.append({
                    "document_id": document_id,
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
                result["document_id"] = document_id
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
        # Collect content for embedding before it's removed from results
        embedding_content: list[tuple[int, str, str]] = []  # (idx, document_id, content)

        for i, result in enumerate(results):
            if result["status"] == FetchStatus.SUCCESS.value and result.get("content"):
                # Save content for embedding before it's popped
                doc_id = result.get("document_id", "")
                content_text = result.get("content", "")
                if doc_id and content_text:
                    embedding_content.append((i, doc_id, content_text))

                try:
                    path_source = result.get("public_url") or result["url"]
                    content_path = _generate_content_path(path_source, config.content_dir)
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
        # Substep 3: generate_embeddings (if enabled or auto-detected)
        # ----------------------------------------------------------------
        # Auto-detect embedding capability if embed is None
        should_embed = config.embed
        if should_embed is None:
            should_embed = has_embedding_api_keys()
            if should_embed:
                logger.debug("Auto-detected embedding API keys, enabling embeddings")

        embedded_count = 0
        if should_embed and embedding_content:
            self.emit_progress(
                on_progress,
                substep="generate_embeddings",
                status="running",
                current=0,
                total=len(embedding_content),
                message=f"Generating embeddings for {len(embedding_content)} document(s)",
            )

            try:
                from kurt.tools.batch_embedding import embedding_to_bytes, generate_embeddings

                # Prepare texts for embedding (truncate to max chars from config)
                max_chars = config.embedding_max_chars
                texts = [content[:max_chars] for _, _, content in embedding_content]

                # Generate embeddings in a single batch
                embeddings = generate_embeddings(
                    texts,
                    module_name="FETCH",
                    step_name="generate_embeddings",
                )

                # Store embeddings in results
                for (idx, doc_id, _), emb in zip(embedding_content, embeddings):
                    results[idx]["embedding"] = embedding_to_bytes(emb)
                    embedded_count += 1

                    self.emit_progress(
                        on_progress,
                        substep="generate_embeddings",
                        status="progress",
                        current=embedded_count,
                        total=len(embedding_content),
                        message=f"Embedded {embedded_count}/{len(embedding_content)}",
                    )

                self.emit_progress(
                    on_progress,
                    substep="generate_embeddings",
                    status="completed",
                    current=embedded_count,
                    total=len(embedding_content),
                    message=f"Generated {embedded_count} embedding(s)",
                )

            except ImportError as e:
                logger.warning(f"Embedding dependencies not available: {e}")
                self.emit_progress(
                    on_progress,
                    substep="generate_embeddings",
                    status="completed",
                    current=0,
                    total=len(embedding_content),
                    message="Embedding skipped - dependencies not installed",
                )
            except Exception as e:
                logger.error(f"Failed to generate embeddings: {e}")
                self.emit_progress(
                    on_progress,
                    substep="generate_embeddings",
                    status="completed",
                    current=embedded_count,
                    total=len(embedding_content),
                    message=f"Embedding failed: {e}",
                )
        elif should_embed:
            # No content to embed
            self.emit_progress(
                on_progress,
                substep="generate_embeddings",
                status="completed",
                current=0,
                total=0,
                message="No content to embed",
            )

        if not config.dry_run and results:
            from kurt.tools.fetch.utils import persist_fetch_documents

            try:
                persist_fetch_documents(results, fetch_engine=config.engine)
            except Exception as exc:
                result = ToolResult(success=False, data=[])
                result.add_error(
                    error_type="persist_failed",
                    message=str(exc),
                )
                return result

        # Build final output
        output_data = [
            {
                "url": r["url"],
                "document_id": r.get("document_id"),
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

        if should_embed:
            result.add_substep(
                name="generate_embeddings",
                status="completed",
                current=embedded_count,
                total=len(embedding_content),
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

    async def _fetch_file_input(self, input_item: FetchInput) -> dict[str, Any]:
        from kurt.tools.fetch.file import fetch_from_file

        try:
            started = time.time()
            content, metadata = await asyncio.to_thread(fetch_from_file, input_item.url)
            latency_ms = int((time.time() - started) * 1000)
            content_hash = _compute_content_hash(content)
            bytes_fetched = len(content.encode("utf-8"))
            return {
                "url": input_item.url,
                "content": content,
                "metadata": metadata,
                "content_hash": content_hash,
                "status": FetchStatus.SUCCESS.value,
                "error": None,
                "bytes_fetched": bytes_fetched,
                "latency_ms": latency_ms,
                "public_url": None,
            }
        except Exception as exc:
            return {
                "url": input_item.url,
                "content": None,
                "metadata": None,
                "content_hash": "",
                "status": FetchStatus.ERROR.value,
                "error": str(exc),
                "bytes_fetched": 0,
                "latency_ms": 0,
                "public_url": None,
            }

    async def _fetch_cms_input(self, input_item: FetchInput) -> dict[str, Any]:
        from kurt.integrations.cms.fetch import fetch_from_cms

        metadata = input_item.metadata or {}
        cms_platform = metadata.get("cms_platform")
        cms_instance = metadata.get("cms_instance")
        cms_document_id = metadata.get("cms_id") or metadata.get("cms_document_id")

        if not cms_platform or not cms_instance or not cms_document_id:
            return {
                "url": input_item.url,
                "content": None,
                "metadata": None,
                "content_hash": "",
                "status": FetchStatus.ERROR.value,
                "error": "cms_metadata_missing",
                "bytes_fetched": 0,
                "latency_ms": 0,
                "public_url": None,
            }

        try:
            started = time.time()
            content, fetch_metadata, public_url = await asyncio.to_thread(
                fetch_from_cms,
                cms_platform,
                cms_instance,
                cms_document_id,
                input_item.discovery_url,
            )
            latency_ms = int((time.time() - started) * 1000)
            content_hash = _compute_content_hash(content)
            bytes_fetched = len(content.encode("utf-8"))
            return {
                "url": input_item.url,
                "content": content,
                "metadata": fetch_metadata,
                "content_hash": content_hash,
                "status": FetchStatus.SUCCESS.value,
                "error": None,
                "bytes_fetched": bytes_fetched,
                "latency_ms": latency_ms,
                "public_url": public_url,
            }
        except Exception as exc:
            return {
                "url": input_item.url,
                "content": None,
                "metadata": None,
                "content_hash": "",
                "status": FetchStatus.ERROR.value,
                "error": str(exc),
                "bytes_fetched": 0,
                "latency_ms": 0,
                "public_url": None,
            }

    async def _fetch_web_batch(
        self,
        inputs: list[FetchInput],
        config: FetchToolConfig,
    ) -> dict[str, dict[str, Any]]:
        from kurt.tools.fetch.web import fetch_from_web

        urls = [input_item.url for input_item in inputs]
        if not urls:
            return {}

        batch_size = config.batch_size or len(urls)
        if config.engine == "tavily":
            batch_size = min(batch_size, 20)

        results_by_url: dict[str, dict[str, Any]] = {}
        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i : i + batch_size]
            batch_results = await asyncio.to_thread(fetch_from_web, batch_urls, config.engine)
            for url in batch_urls:
                result = batch_results.get(url)
                if isinstance(result, Exception) or result is None:
                    results_by_url[url] = {
                        "url": url,
                        "content": None,
                        "metadata": None,
                        "content_hash": "",
                        "status": FetchStatus.ERROR.value,
                        "error": str(result) if result else "No result",
                        "bytes_fetched": 0,
                        "latency_ms": 0,
                        "public_url": None,
                    }
                    continue

                content, metadata = result
                content_hash = _compute_content_hash(content)
                bytes_fetched = len(content.encode("utf-8"))
                results_by_url[url] = {
                    "url": url,
                    "content": content,
                    "metadata": metadata,
                    "content_hash": content_hash,
                    "status": FetchStatus.SUCCESS.value,
                    "error": None,
                    "bytes_fetched": bytes_fetched,
                    "latency_ms": 0,
                    "public_url": None,
                }

        return results_by_url

    async def _fetch_single_url(
        self,
        url: str,
        config: FetchToolConfig,
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
                # Build engine-specific kwargs
                engine_kwargs: dict[str, Any] = {}
                if config.engine == "apify":
                    if config.platform:
                        engine_kwargs["platform"] = config.platform
                    if config.apify_actor:
                        engine_kwargs["apify_actor"] = config.apify_actor

                content, metadata, latency_ms = await _fetch_with_retry(
                    url=url,
                    engine=config.engine,
                    timeout_s=timeout_s,
                    retries=config.retries,
                    retry_backoff_ms=config.retry_backoff_ms,
                    client=client,
                    **engine_kwargs,
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


__all__ = [
    # Workflow config (from config.py)
    "FetchConfig",
    "has_embedding_api_keys",
    # Database models (from models.py)
    "FetchDocument",
    "FetchStatus",
    "FetchResult",
    "BatchFetchResult",
    "BatchFetcher",
    # Tool parameter models
    "FetchInput",
    "FetchOutput",
    "FetchParams",
    "FetchToolConfig",
    # Tool class
    "FetchTool",
    # Constants
    "MAX_CONTENT_SIZE_BYTES",
    "RETRYABLE_STATUS_CODES",
    "NON_RETRYABLE_STATUS_CODES",
    "VALID_CONTENT_TYPES",
    # Utility functions (for testing)
    "_compute_content_hash",
    "_generate_content_path",
    "_save_content",
    "_is_retryable_error",
]
