"""
Batch LLM tool subpackage.

Contains:
- BatchLLMTool: Batch LLM processing tool for Kurt workflows
- Pydantic models for input/output (BatchLLMConfig, BatchLLMInput, BatchLLMOutput, BatchLLMParams)
- Built-in output schema models (ExtractEntities, etc.)

Processes rows through an LLM with configurable:
- Prompt template with {field} substitution
- Structured output via Pydantic models
- Concurrency control via asyncio.Semaphore
- Rate limiting and backpressure handling
- Support for OpenAI and Anthropic providers
"""

from .models import (
    ExtractEntities,
    ExtractKeywords,
    SentimentAnalysis,
    Summarize,
)
from .tool import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_BACKOFF_MS,
    MAX_BATCH_SIZE,
    QUOTA_EXCEEDED_STATUS_CODES,
    RATE_LIMIT_STATUS_CODE,
    BatchLLMConfig,
    BatchLLMInput,
    BatchLLMOutput,
    BatchLLMParams,
    BatchLLMProcessor,
    BatchLLMTool,
    QuotaExceededError,
    RateLimitError,
    _estimate_anthropic_cost,
    _estimate_openai_cost,
    call_anthropic,
    call_openai,
    resolve_output_schema,
)

__all__ = [
    # Tool class
    "BatchLLMTool",
    # Pydantic models
    "BatchLLMConfig",
    "BatchLLMInput",
    "BatchLLMOutput",
    "BatchLLMParams",
    # Processor
    "BatchLLMProcessor",
    # LLM call functions
    "call_openai",
    "call_anthropic",
    # Schema resolution
    "resolve_output_schema",
    # Cost estimation
    "_estimate_openai_cost",
    "_estimate_anthropic_cost",
    # Exceptions
    "RateLimitError",
    "QuotaExceededError",
    # Built-in output schemas
    "ExtractEntities",
    "ExtractKeywords",
    "SentimentAnalysis",
    "Summarize",
    # Constants
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_RETRY_BACKOFF_MS",
    "MAX_BATCH_SIZE",
    "QUOTA_EXCEEDED_STATUS_CODES",
    "RATE_LIMIT_STATUS_CODE",
]
