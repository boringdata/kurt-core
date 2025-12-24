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

    from kurt.config import ModelConfig

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


def _is_reasoning_model(model_name: str) -> bool:
    """Check if a model is a reasoning model that requires special parameters.

    Reasoning models (o1, o3, gpt-5-mini) require:
    - temperature=1.0 (exactly 1.0, no other values allowed)
    - max_tokens >= 16000 (minimum for reasoning output)
    """
    model_lower = model_name.lower()
    # OpenAI reasoning models: o1, o3, gpt-5 series
    reasoning_patterns = ["o1", "o3", "gpt-5"]
    return any(pattern in model_lower for pattern in reasoning_patterns)


def _infer_model_type_from_caller() -> str | None:
    """Infer model type from caller's module path.

    Returns:
        "ANSWER" if caller is in kurt.commands.ask.* or kurt.answer.*
        "INDEXING" if caller is in kurt.content.indexing.*
        None otherwise (use global LLM.* config)
    """
    import inspect

    # Walk up the call stack to find the calling module
    for frame_info in inspect.stack():
        module = frame_info.frame.f_globals.get("__name__", "")
        # Check for answer-related modules
        if "kurt.commands.ask" in module or "kurt.answer" in module:
            return "ANSWER"
        # Check for indexing-related modules
        if "kurt.content.indexing" in module:
            return "INDEXING"

    # No specific module detected - use global config
    return None


def get_dspy_lm(config: "ModelConfig | None" = None) -> dspy.LM:
    """Get a DSPy LM instance using step config or auto-inferred settings.

    Supports both cloud providers (OpenAI, Anthropic, etc.) and local
    OpenAI-compatible servers (e.g., mlx_lm.server, ollama, vllm).

    Model resolution:
        1. config.llm_model (if config provided with llm_model attribute)
        2. Inferred from caller's module path:
           - kurt.commands.ask.* or kurt.answer.* -> ANSWER_LLM_MODEL
           - kurt.content.indexing.* -> INDEXING_LLM_MODEL
           - Otherwise -> LLM.MODEL global config

    API settings resolution (in order of priority):
        1. LLM.<type>.API_BASE, LLM.<type>.API_KEY (if model_type inferred)
        2. LLM.API_BASE, LLM.API_KEY (global defaults)

    Example kurt.config:
        # Global config for all LLM calls
        LLM.API_BASE="http://localhost:8080/v1/"
        LLM.API_KEY="not_needed"

        # Or per-type overrides
        LLM.INDEXING.API_BASE="http://localhost:8080/v1/"
        LLM.ANSWER.API_BASE="http://localhost:9090/v1/"

    Args:
        config: Step's ModelConfig instance with llm_model attribute.
                If None, model is inferred from caller's module path.

    Returns:
        dspy.LM instance configured for the model
    """
    from kurt.config import get_config_or_default
    from kurt.config.base import get_step_config

    kurt_config = get_config_or_default()

    # Infer model type from caller's module path (for API settings resolution)
    model_type = _infer_model_type_from_caller()

    # Get model name from config or infer from global settings
    if config and hasattr(config, "llm_model") and config.llm_model:
        model_name = config.llm_model
    else:
        # Determine fallback key based on model type
        if model_type == "ANSWER":
            fallback_model_key = "ANSWER_LLM_MODEL"
            default_model = kurt_config.ANSWER_LLM_MODEL
        else:
            # INDEXING or None - use INDEXING as legacy fallback
            fallback_model_key = "INDEXING_LLM_MODEL"
            default_model = kurt_config.INDEXING_LLM_MODEL

        # Resolution: LLM.<type>.MODEL -> LLM.MODEL -> legacy fallback
        model_name = None
        if model_type:
            model_name = get_step_config(kurt_config, "LLM", model_type, "MODEL", default=None)
        if model_name is None:
            model_name = get_step_config(
                kurt_config,
                "LLM",
                None,
                "MODEL",
                fallback_key=fallback_model_key,
                default=default_model,
            )

    # Resolution: LLM.<type>.API_BASE -> LLM.API_BASE -> None
    api_base = None
    if model_type:
        api_base = get_step_config(kurt_config, "LLM", model_type, "API_BASE", default=None)
    if api_base is None:
        api_base = get_step_config(kurt_config, "LLM", None, "API_BASE", default=None)

    # Resolution: LLM.<type>.API_KEY -> LLM.API_KEY -> None
    api_key = None
    if model_type:
        api_key = get_step_config(kurt_config, "LLM", model_type, "API_KEY", default=None)
    if api_key is None:
        api_key = get_step_config(kurt_config, "LLM", None, "API_KEY", default=None)

    # Check if this is a reasoning model requiring special parameters
    if _is_reasoning_model(model_name):
        # Reasoning models require temperature=1.0 and max_tokens >= 16000
        if api_base:
            # Local server with reasoning model
            if "/" in model_name:
                model_name = model_name.split("/", 1)[1]
            lm = dspy.LM(
                model=f"openai/{model_name}",
                api_base=api_base,
                api_key=api_key or "not_needed",
                temperature=1.0,
                max_tokens=16000,
            )
            logger.debug(
                f"Created DSPy LM for local reasoning model {model_name} at {api_base} "
                f"(temperature=1.0, max_tokens=16000)"
            )
        else:
            lm = dspy.LM(model_name, temperature=1.0, max_tokens=16000)
            logger.debug(
                f"Created DSPy LM for reasoning model {model_name} (temperature=1.0, max_tokens=16000)"
            )
    else:
        max_tokens = 4000 if "haiku" in model_name.lower() else 8000

        if api_base:
            # Use OpenAI-compatible endpoint for local servers
            # Strip provider prefix if present (e.g., "openai/gpt-4o" -> "gpt-4o")
            # since we're using a local server with openai-compatible API
            if "/" in model_name:
                model_name = model_name.split("/", 1)[1]
            lm = dspy.LM(
                model=f"openai/{model_name}",
                api_base=api_base,
                api_key=api_key or "not_needed",
                max_tokens=max_tokens,
            )
            logger.debug(f"Created DSPy LM for local model {model_name} at {api_base}")
        else:
            # Standard cloud provider
            lm = dspy.LM(model_name, max_tokens=max_tokens)
            logger.debug(f"Created DSPy LM for model {model_name}")

    return lm


def configure_dspy_model(config: "ModelConfig | None" = None) -> None:
    """Configure DSPy globally with a specific LLM model.

    WARNING: This uses dspy.configure() which can only be called from
    the same async task that called it first. For async/parallel contexts,
    use get_dspy_lm() with dspy.context() instead.

    Args:
        config: Step's ModelConfig instance with llm_model attribute.
                If None, model is inferred from caller's module path.
    """
    lm = get_dspy_lm(config)
    dspy.configure(lm=lm)
    logger.debug("Configured DSPy globally")


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
    config: "ModelConfig | None" = None,
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
        config: Step's ModelConfig instance with llm_model attribute.
                If None, model is inferred from caller's module path.

    Returns:
        List of DSPyResult objects with results or errors
    """
    # Get LM instance (don't use dspy.configure() - not safe for parallel async)
    lm = get_dspy_lm(config)

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
    config: "ModelConfig | None" = None,
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
        config: Step's ModelConfig instance with llm_model attribute.
                If None, model is inferred from caller's module path.

    Returns:
        List of DSPyResult objects
    """
    import concurrent.futures
    import threading

    # Get LM instance (don't use dspy.configure() - not safe for parallel threads)
    lm = get_dspy_lm(config)

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
