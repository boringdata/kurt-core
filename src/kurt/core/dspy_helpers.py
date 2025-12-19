"""
DSPy helpers for the indexing pipeline.

Provides utilities for running DSPy signatures and modules with
concurrency control, error handling, and telemetry.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Type, Union

import dspy

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)


# ============================================================================
# Generic Conversion Utilities
# ============================================================================


def to_dict(value: Any) -> Optional[dict]:
    """Convert Pydantic model or dict to dict.

    Args:
        value: Pydantic model, dict, or None

    Returns:
        Dict representation or None
    """
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def to_list(value: Any) -> Optional[list]:
    """Convert list of Pydantic models to list of dicts.

    Args:
        value: List of Pydantic models, list of dicts, or None

    Returns:
        List of dicts or None
    """
    if value is None:
        return None
    return [v.model_dump() if hasattr(v, "model_dump") else v for v in value]


def parse_json_columns(
    df: "pd.DataFrame", columns: List[str], default: Any = None
) -> "pd.DataFrame":
    """Parse JSON string columns in a DataFrame.

    SQLite stores JSON as text strings. This function parses them back to Python objects.

    Args:
        df: DataFrame with JSON string columns
        columns: List of column names to parse
        default: Default value if parsing fails (default: None, uses [] for *_json columns)

    Returns:
        DataFrame with parsed JSON columns

    Example:
        df = parse_json_columns(df, ["entities_json", "claims_json"])
    """
    import json

    for col in columns:
        if col not in df.columns:
            continue
        col_default = default if default is not None else ([] if col.endswith("_json") else {})
        df[col] = df[col].apply(
            lambda v: json.loads(v) if isinstance(v, str) else (v if v is not None else col_default)
        )
    return df


class LLMAuthenticationError(Exception):
    """Raised when LLM API authentication fails."""

    def __init__(self, provider: str, original_error: Exception):
        self.provider = provider
        self.original_error = original_error
        super().__init__(
            f"{provider} API authentication failed. "
            f"Please check your API key is valid and not expired.\n"
            f"Set the appropriate environment variable (e.g., OPENAI_API_KEY, ANTHROPIC_API_KEY)."
        )


class LLMRateLimitError(Exception):
    """Raised when LLM API rate limit is exceeded."""

    def __init__(self, provider: str, original_error: Exception):
        self.provider = provider
        self.original_error = original_error
        super().__init__(
            f"{provider} API rate limit exceeded. "
            f"Please wait a moment and try again, or reduce concurrency."
        )


class LLMAPIError(Exception):
    """Raised for general LLM API errors."""

    def __init__(self, provider: str, message: str, original_error: Exception):
        self.provider = provider
        self.original_error = original_error
        super().__init__(f"{provider} API error: {message}")


def _handle_llm_error(exc: Exception) -> Exception:
    """Convert LiteLLM/provider exceptions to user-friendly errors.

    Args:
        exc: The original exception

    Returns:
        A user-friendly exception with clear guidance
    """
    error_str = str(exc).lower()
    error_type = type(exc).__name__

    # Detect provider from error message
    provider = "LLM"
    if "openai" in error_str:
        provider = "OpenAI"
    elif "anthropic" in error_str:
        provider = "Anthropic"
    elif "azure" in error_str:
        provider = "Azure OpenAI"
    elif "google" in error_str or "gemini" in error_str:
        provider = "Google"

    # Authentication errors
    if "authentication" in error_type.lower() or "authenticationerror" in error_type.lower():
        return LLMAuthenticationError(provider, exc)
    if "invalid" in error_str and "api key" in error_str:
        return LLMAuthenticationError(provider, exc)
    if "incorrect api key" in error_str:
        return LLMAuthenticationError(provider, exc)
    if "unauthorized" in error_str or "401" in error_str:
        return LLMAuthenticationError(provider, exc)

    # Rate limit errors
    if "ratelimit" in error_type.lower() or "rate_limit" in error_str:
        return LLMRateLimitError(provider, exc)
    if "429" in error_str or "too many requests" in error_str:
        return LLMRateLimitError(provider, exc)

    # Return original exception if no specific handling
    return exc


def get_dspy_lm(model_name: Optional[str] = None) -> dspy.LM:
    """Get a DSPy LM instance for the specified model.

    Args:
        model_name: Model name to use. If None, uses INDEXING_LLM_MODEL from config.

    Returns:
        dspy.LM instance configured for the model
    """
    from kurt.config import get_config_or_default

    if model_name is None:
        config = get_config_or_default()
        model_name = config.INDEXING_LLM_MODEL

    max_tokens = 4000 if "haiku" in model_name.lower() else 8000
    lm = dspy.LM(model_name, max_tokens=max_tokens)
    logger.debug(f"Created DSPy LM for model {model_name}")
    return lm


def configure_dspy_model(model_name: Optional[str] = None) -> None:
    """Configure DSPy globally with a specific LLM model.

    WARNING: This uses dspy.configure() which can only be called from
    the same async task that called it first. For async/parallel contexts,
    use get_dspy_lm() with dspy.context() instead.

    Args:
        model_name: Model name to use. If None, uses INDEXING_LLM_MODEL from config.
    """
    lm = get_dspy_lm(model_name)
    dspy.configure(lm=lm)
    logger.debug(f"Configured DSPy globally with model {model_name or 'default'}")


@dataclass
class DSPyResult:
    """Result from a DSPy execution."""

    payload: Dict[str, Any]
    result: Optional[Any]
    error: Optional[Exception]
    telemetry: Dict[str, Any]


async def run_batch(
    *,
    signature: Union[Type[dspy.Signature], dspy.Module],
    items: List[Dict[str, Any]],
    max_concurrent: int = 1,
    context: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None,
    llm_model: Optional[str] = None,
) -> List[DSPyResult]:
    """
    Run a DSPy signature or module on a batch of items concurrently.

    Uses dspy.context() for thread-safe configuration that works correctly
    with asyncio.gather and parallel execution.

    Args:
        signature: DSPy signature class or module instance
        items: List of input payloads for the signature
        max_concurrent: Maximum number of concurrent executions
        context: Optional shared context for all calls
        timeout: Optional timeout in seconds for each call
        llm_model: Optional LLM model name to use (default: INDEXING_LLM_MODEL)

    Returns:
        List of DSPyResult objects with results or errors
    """
    # Get LM instance (don't use dspy.configure() - not safe for parallel async)
    lm = get_dspy_lm(llm_model)

    semaphore = asyncio.Semaphore(max_concurrent)
    context = context or {}

    async def invoke_single(payload: Dict[str, Any]) -> DSPyResult:
        """Invoke the signature/module on a single payload."""
        async with semaphore:
            start_time = datetime.utcnow()

            try:
                # Merge context into payload
                merged_payload = {**context, **payload}

                # Create executor based on type
                if isinstance(signature, type) and issubclass(signature, dspy.Signature):
                    # It's a signature class
                    executor = dspy.ChainOfThought(signature)
                elif isinstance(signature, dspy.Module):
                    # It's a module instance
                    executor = signature
                else:
                    # Try to use it directly
                    executor = signature

                # Helper to run sync executor with dspy.context (thread-safe config)
                def run_with_context():
                    with dspy.context(lm=lm):
                        return executor(**merged_payload)

                # Execute (handling both sync and async)
                if hasattr(executor, "acall") and callable(getattr(executor, "acall", None)):
                    # Async execution - use dspy.context around the call
                    with dspy.context(lm=lm):
                        if timeout:
                            result = await asyncio.wait_for(
                                executor.acall(**merged_payload), timeout=timeout
                            )
                        else:
                            result = await executor.acall(**merged_payload)
                elif asyncio.iscoroutinefunction(executor):
                    # It's an async function
                    with dspy.context(lm=lm):
                        if timeout:
                            result = await asyncio.wait_for(
                                executor(**merged_payload), timeout=timeout
                            )
                        else:
                            result = await executor(**merged_payload)
                else:
                    # Sync execution - run in thread pool with dspy.context
                    loop = asyncio.get_event_loop()
                    if timeout:
                        result = await asyncio.wait_for(
                            loop.run_in_executor(None, run_with_context),
                            timeout=timeout,
                        )
                    else:
                        result = await loop.run_in_executor(None, run_with_context)

                # Extract telemetry
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                telemetry = {
                    "execution_time": execution_time,
                    "model_name": getattr(
                        executor, "model_name", getattr(dspy.settings.lm, "model_name", None)
                    ),
                    "tokens_prompt": getattr(result, "prompt_tokens", None),
                    "tokens_completion": getattr(result, "completion_tokens", None),
                }

                return DSPyResult(
                    payload=payload,
                    result=result,
                    error=None,
                    telemetry=telemetry,
                )

            except asyncio.TimeoutError as exc:
                logger.warning(
                    f"DSPy execution timed out after {timeout}s",
                    extra={"payload": payload, "timeout": timeout},
                )
                return DSPyResult(
                    payload=payload,
                    result=None,
                    error=exc,
                    telemetry={"error": "timeout", "timeout": timeout},
                )

            except Exception as exc:
                logger.exception(
                    "DSPy execution failed",
                    extra={"payload": payload, "error": str(exc)},
                )
                return DSPyResult(
                    payload=payload,
                    result=None,
                    error=exc,
                    telemetry={"error": str(exc)},
                )

    # Execute all items concurrently
    tasks = [invoke_single(item) for item in items]
    results = await asyncio.gather(*tasks)

    # Log summary
    successful = sum(1 for r in results if r.error is None)
    failed = sum(1 for r in results if r.error is not None)

    logger.info(
        f"DSPy batch completed: {successful}/{len(items)} successful",
        extra={
            "total": len(items),
            "successful": successful,
            "failed": failed,
            "max_concurrent": max_concurrent,
        },
    )

    return results


def run_batch_sync(
    *,
    signature: Union[Type[dspy.Signature], dspy.Module],
    items: List[Dict[str, Any]],
    max_concurrent: int = 1,
    context: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None,
    on_progress: Optional[Callable[[int, int, Optional[DSPyResult]], None]] = None,
    llm_model: Optional[str] = None,
) -> List[DSPyResult]:
    """
    Synchronous version of run_batch using thread pool.

    Uses dspy.context() for thread-safe configuration that works correctly
    with concurrent.futures ThreadPoolExecutor.

    Args:
        signature: DSPy signature class or module instance
        items: List of input payloads
        max_concurrent: Maximum concurrent executions
        context: Optional shared context
        timeout: Optional timeout per call
        on_progress: Optional callback(completed, total, result) called after each item completes
        llm_model: Optional LLM model name to use (default: INDEXING_LLM_MODEL)

    Returns:
        List of DSPyResult objects
    """
    import concurrent.futures
    import threading

    # Get LM instance (don't use dspy.configure() - not safe for parallel threads)
    lm = get_dspy_lm(llm_model)

    context = context or {}
    results = []
    total_count = len(items)
    completed_count = 0
    progress_lock = threading.Lock()

    def invoke_single(payload: Dict[str, Any]) -> DSPyResult:
        """Invoke signature on single payload."""
        nonlocal completed_count
        start_time = datetime.utcnow()

        try:
            # Merge context
            merged_payload = {**context, **payload}

            # Create executor
            if isinstance(signature, type) and issubclass(signature, dspy.Signature):
                executor = dspy.ChainOfThought(signature)
            elif isinstance(signature, dspy.Module):
                executor = signature
            else:
                executor = signature

            # Execute with dspy.context for thread-safe LM configuration
            with dspy.context(lm=lm):
                result = executor(**merged_payload)

            # Extract telemetry
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            telemetry = {
                "execution_time": execution_time,
                "model_name": getattr(executor, "model_name", None),
                "tokens_prompt": getattr(result, "prompt_tokens", None),
                "tokens_completion": getattr(result, "completion_tokens", None),
            }

            dspy_result = DSPyResult(
                payload=payload,
                result=result,
                error=None,
                telemetry=telemetry,
            )

        except Exception as exc:
            # Convert to user-friendly error
            friendly_error = _handle_llm_error(exc)

            # For authentication errors, re-raise immediately to fail fast
            # (no point retrying other items with bad credentials)
            if isinstance(friendly_error, LLMAuthenticationError):
                raise friendly_error from exc

            logger.exception("DSPy execution failed")
            dspy_result = DSPyResult(
                payload=payload,
                result=None,
                error=friendly_error,
                telemetry={"error": str(friendly_error)},
            )

        # Update progress counter and call callback
        if on_progress:
            with progress_lock:
                completed_count += 1
                try:
                    on_progress(completed_count, total_count, dspy_result)
                except Exception as e:
                    logger.warning(f"Progress callback error: {e}")

        return dspy_result

    # Emit start event before any work begins
    if on_progress:
        try:
            on_progress(0, total_count, None)
        except Exception as e:
            logger.warning(f"Progress callback error on start: {e}")

    # Execute with thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        futures = [executor.submit(invoke_single, item) for item in items]

        # Collect results with timeout
        for future in concurrent.futures.as_completed(futures, timeout=timeout):
            try:
                results.append(future.result())
            except concurrent.futures.TimeoutError:
                # Create timeout result
                results.append(
                    DSPyResult(
                        payload={},  # We lost track of which payload
                        result=None,
                        error=TimeoutError(f"Timed out after {timeout}s"),
                        telemetry={"error": "timeout"},
                    )
                )

    return results
