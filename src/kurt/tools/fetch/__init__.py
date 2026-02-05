"""
Fetch tool - Content fetching from URLs.

FetchTool - Content fetching tool for Kurt workflows.

Fetches content from URLs using configurable engines (trafilatura, httpx, tavily, firecrawl).
Supports parallel fetching with concurrency control and exponential backoff retries.

Provides:
- FetchTool: Tool class for fetching content
- FetchDocument, FetchStatus: Database models
- FetchConfig (from config.py): Configuration for fetch workflows
- FetchInput, FetchOutput, FetchParams, FetchToolConfig: Tool parameter models
- Fetch engines: trafilatura, httpx, tavily, firecrawl
"""

from .config import FetchConfig, has_embedding_api_keys
from .models import (
    BatchFetcher,
    BatchFetchResult,
    FetchDocument,
    FetchResult,
    FetchStatus,
)
from .tool import (
    MAX_CONTENT_SIZE_BYTES,
    NON_RETRYABLE_STATUS_CODES,
    RETRYABLE_STATUS_CODES,
    VALID_CONTENT_TYPES,
    FetchInput,
    FetchOutput,
    FetchParams,
    FetchTool,
    FetchToolConfig,
    _compute_content_hash,
    _fetch_with_firecrawl,
    _fetch_with_httpx,
    _fetch_with_retry,
    _fetch_with_tavily,
    _fetch_with_trafilatura,
    _generate_content_path,
    _is_retryable_error,
    _save_content,
)

__all__ = [
    # Tool class
    "FetchTool",
    # Pydantic models
    "FetchConfig",
    "FetchInput",
    "FetchOutput",
    "FetchParams",
    "FetchToolConfig",
    # Database models
    "FetchDocument",
    "FetchResult",
    "FetchStatus",
    "BatchFetcher",
    "BatchFetchResult",
    # Constants
    "MAX_CONTENT_SIZE_BYTES",
    "NON_RETRYABLE_STATUS_CODES",
    "RETRYABLE_STATUS_CODES",
    "VALID_CONTENT_TYPES",
    # Config helpers
    "has_embedding_api_keys",
]

# Note: Internal utilities (_compute_content_hash, _fetch_with_*, etc.) are
# imported above but NOT exported in __all__. They can still be accessed via
# direct import for testing purposes:
#   from kurt.tools.fetch.tool import _compute_content_hash
