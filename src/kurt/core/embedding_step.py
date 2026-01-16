"""Embedding step abstraction with DBOS durability.

Complementary to LLMStep - provides batched embedding generation
with queue-based concurrency and lifecycle hooks.
"""

from __future__ import annotations

import logging
import struct
import time
from typing import TYPE_CHECKING, Any, Callable

import litellm
from dbos import DBOS, Queue

from .hooks import NoopStepHooks, StepHooks

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)


def _extract_usage_tokens(response: Any) -> tuple[int, int]:
    usage = getattr(response, "usage", None)
    if isinstance(usage, dict):
        tokens_in = usage.get("prompt_tokens", usage.get("input_tokens"))
        tokens_out = usage.get("completion_tokens", usage.get("output_tokens", 0))
        if tokens_in is None:
            total_tokens = usage.get("total_tokens")
            if total_tokens is not None:
                tokens_in = total_tokens - (tokens_out or 0)
        return int(tokens_in or 0), int(tokens_out or 0)

    if usage is not None:
        tokens_in = getattr(usage, "prompt_tokens", None)
        if tokens_in is None:
            tokens_in = getattr(usage, "input_tokens", None)
        tokens_out = getattr(usage, "completion_tokens", None)
        if tokens_out is None:
            tokens_out = getattr(usage, "output_tokens", 0)
        if tokens_in is None:
            total_tokens = getattr(usage, "total_tokens", None)
            if total_tokens is not None:
                tokens_in = total_tokens - (tokens_out or 0)
        return int(tokens_in or 0), int(tokens_out or 0)

    return 0, 0


def _calculate_embedding_cost(response: Any, model: str | None) -> float:
    if not model:
        return 0.0
    try:
        return float(
            litellm.response_cost_calculator(
                response_object=response,
                model=model,
                custom_llm_provider=None,
                call_type="embedding",
                optional_params={},
            )
        )
    except Exception:
        return 0.0


def embedding_to_bytes(embedding: list[float]) -> bytes:
    """Convert embedding vector to bytes for database storage."""
    try:
        import numpy as np
    except ImportError as e:
        raise ImportError(
            "numpy is required for embeddings. Install with: pip install kurt-core[workflows]"
        ) from e
    return np.array(embedding, dtype=np.float32).tobytes()


def bytes_to_embedding(embedding_bytes: bytes) -> list[float]:
    """Convert stored bytes back to embedding vector."""
    return list(struct.unpack(f"{len(embedding_bytes)//4}f", embedding_bytes))


def embedding_step(
    *,
    input_column: str,
    output_column: str = "embedding",
    max_chars: int = 1000,
    batch_size: int = 100,
    concurrency: int = 3,
    model: str | None = None,
    module_name: str | None = None,
    step_name: str | None = None,
    hooks: StepHooks | None = None,
    as_bytes: bool = True,
):
    """
    Decorator that converts a text preparation function into an EmbeddingStep.

    The wrapped function receives a text string and can transform it before embedding.

    Args:
        input_column: Column containing text to embed
        output_column: Column to store embeddings (default: "embedding")
        max_chars: Maximum characters to use per text (default: 1000)
        batch_size: Number of texts per batch (default: 100)
        concurrency: Number of concurrent batches (default: 3)
        model: Embedding model (optional, uses config resolution)
        module_name: Module name for config resolution (e.g., "FETCH")
        step_name: Step name for config resolution
        hooks: Optional lifecycle hooks
        as_bytes: Store as bytes (True) or list[float] (False)
    """

    def decorator(prepare_fn: Callable[[str], str] | None = None):
        return EmbeddingStep(
            name=prepare_fn.__name__ if prepare_fn else "embed",
            input_column=input_column,
            output_column=output_column,
            max_chars=max_chars,
            batch_size=batch_size,
            concurrency=concurrency,
            model=model,
            module_name=module_name,
            step_name=step_name,
            prepare_fn=prepare_fn,
            hooks=hooks,
            as_bytes=as_bytes,
        )

    return decorator


class EmbeddingStep:
    """
    Embedding step abstraction with DBOS durability.

    - Batched embedding generation for efficiency
    - Fan-out via DBOS Queue
    - Fan-in and merge results onto DataFrame
    - Optional lifecycle hooks for tracking/tracing
    """

    def __init__(
        self,
        *,
        name: str,
        input_column: str,
        output_column: str = "embedding",
        max_chars: int = 1000,
        batch_size: int = 100,
        concurrency: int = 3,
        model: str | None = None,
        module_name: str | None = None,
        step_name: str | None = None,
        prepare_fn: Callable[[str], str] | None = None,
        hooks: StepHooks | None = None,
        as_bytes: bool = True,
    ) -> None:
        self.name = name
        self.input_column = input_column
        self.output_column = output_column
        self.max_chars = max_chars
        self.batch_size = batch_size
        self.concurrency = concurrency
        self.model = model
        self.module_name = module_name
        self.step_name = step_name
        self._prepare_fn = prepare_fn
        self._hooks = hooks or NoopStepHooks()
        self._as_bytes = as_bytes

        self._resolved_model: str | None = None
        self._api_base: str | None = None
        self._api_key: str | None = None

        self.queue = Queue(
            f"{name}_embedding_queue",
            concurrency=concurrency,
        )
        self._register_step()

    def _resolve_model_settings(self) -> None:
        """Resolve model settings from config hierarchy."""
        if self._resolved_model is not None:
            return

        if self.model:
            self._resolved_model = self.model
            return

        from kurt.config import resolve_model_settings

        settings = resolve_model_settings(
            model_category="EMBEDDING",
            module_name=self.module_name,
            step_name=self.step_name,
        )
        self._resolved_model = settings.model
        self._api_base = settings.api_base
        self._api_key = settings.api_key

    def _register_step(self) -> None:
        step_instance = self

        @DBOS.step(name=f"{self.name}_process_batch")
        def process_batch(
            texts: list[str],
            indices: list[int],
            batch_idx: int,
            total_batches: int,
        ) -> dict[str, Any]:
            """Process a batch of texts and return embeddings."""
            start = time.time()
            try:
                try:
                    DBOS.set_event("parent_step_name", step_instance.name)
                except Exception:
                    pass

                step_instance._resolve_model_settings()

                # Prepare texts
                prepared_texts = []
                for text in texts:
                    if step_instance._prepare_fn:
                        text = step_instance._prepare_fn(text)
                    # Truncate to max_chars
                    if len(text) > step_instance.max_chars:
                        text = text[: step_instance.max_chars]
                    prepared_texts.append(text)

                # Call embedding API
                kwargs = {
                    "model": step_instance._resolved_model,
                    "input": prepared_texts,
                }
                if step_instance._api_base:
                    kwargs["api_base"] = step_instance._api_base
                if step_instance._api_key:
                    kwargs["api_key"] = step_instance._api_key

                response = litellm.embedding(**kwargs)
                embeddings = [item["embedding"] for item in response.data]
                tokens_in, tokens_out = _extract_usage_tokens(response)
                cost = _calculate_embedding_cost(response, step_instance._resolved_model)

                # Convert to bytes if requested
                if step_instance._as_bytes:
                    embeddings = [embedding_to_bytes(e) for e in embeddings]

                latency_ms = int((time.time() - start) * 1000)

                step_instance._hooks.on_row_success(
                    step_name=step_instance.name,
                    idx=batch_idx,
                    total=total_batches,
                    latency_ms=latency_ms,
                    prompt=f"batch of {len(texts)} texts",
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost=cost,
                    result={"count": len(embeddings)},
                )

                return {
                    "batch_idx": batch_idx,
                    "status": "success",
                    "indices": indices,
                    "embeddings": embeddings,
                }

            except Exception as exc:
                latency_ms = int((time.time() - start) * 1000)
                step_instance._hooks.on_row_error(
                    step_name=step_instance.name,
                    idx=batch_idx,
                    total=total_batches,
                    latency_ms=latency_ms,
                    prompt=f"batch of {len(texts)} texts",
                    tokens_in=0,
                    tokens_out=0,
                    cost=0.0,
                    error=exc,
                )
                return {
                    "batch_idx": batch_idx,
                    "status": "error",
                    "indices": indices,
                    "error": str(exc),
                }

        self._process_batch = process_batch

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Run embedding step on DataFrame.

        Args:
            df: DataFrame with input_column containing text

        Returns:
            DataFrame with output_column containing embeddings
        """
        try:
            import pandas  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "pandas is required for EmbeddingStep. Install with: pip install kurt-core[workflows]"
            ) from e

        total = len(df)
        texts = df[self.input_column].tolist()

        # Create batches
        batches: list[tuple[list[str], list[int]]] = []
        for i in range(0, total, self.batch_size):
            batch_texts = texts[i : i + self.batch_size]
            batch_indices = list(range(i, min(i + self.batch_size, total)))
            batches.append((batch_texts, batch_indices))

        total_batches = len(batches)

        self._hooks.on_start(
            step_name=self.name,
            total=total_batches,
            concurrency=self.concurrency,
        )

        # Enqueue all batches
        handles = [
            self.queue.enqueue(self._process_batch, batch_texts, batch_indices, i, total_batches)
            for i, (batch_texts, batch_indices) in enumerate(batches)
        ]

        # Collect results
        embeddings_map: dict[int, Any] = {}
        errors: list[str] = []
        successful_batches = 0

        for handle in handles:
            result = handle.get_result()
            status = result.get("status", "error")
            self._hooks.on_result(
                step_name=self.name,
                idx=result.get("batch_idx", 0),
                total=total_batches,
                status=status,
                error=result.get("error"),
            )

            if status == "success":
                successful_batches += 1
                for idx, emb in zip(result["indices"], result["embeddings"]):
                    embeddings_map[idx] = emb
            else:
                errors.append(f"Batch {result.get('batch_idx')}: {result.get('error', 'unknown')}")

        # Merge results into DataFrame
        result_df = df.copy()
        result_df[self.output_column] = [embeddings_map.get(i) for i in range(total)]
        result_df[f"{self.name}_status"] = [
            "success" if i in embeddings_map else "error" for i in range(total)
        ]

        self._hooks.on_end(
            step_name=self.name,
            successful=successful_batches,
            total=total_batches,
            errors=errors,
        )

        return result_df


def generate_embeddings(
    texts: list[str],
    model: str | None = None,
    api_base: str | None = None,
    api_key: str | None = None,
    module_name: str | None = None,
    step_name: str | None = None,
    record_trace: bool = True,
) -> list[list[float]]:
    """
    Generate embeddings for a list of texts using LiteLLM.

    Model resolution (hierarchical):
        1. Explicit model parameter
        2. MODULE.STEP.EMBEDDING_MODEL
        3. MODULE.EMBEDDING_MODEL
        4. EMBEDDING_MODEL (global)

    Args:
        texts: List of text strings to embed
        model: Model name (optional, uses config resolution)
        api_base: API base URL (optional)
        api_key: API key (optional)
        module_name: Module name for config resolution
        step_name: Step name for config resolution
        record_trace: Whether to record the embedding call in LLMTrace table

    Returns:
        List of embedding vectors
    """
    # Only resolve config if model not provided
    if model is None:
        from kurt.config import resolve_model_settings

        settings = resolve_model_settings(
            model_category="EMBEDDING",
            module_name=module_name,
            step_name=step_name,
        )
        model = settings.model
        if api_base is None:
            api_base = settings.api_base
        if api_key is None:
            api_key = settings.api_key

    start = time.time()

    kwargs = {"model": model, "input": texts}
    if api_base:
        kwargs["api_base"] = api_base
    if api_key:
        kwargs["api_key"] = api_key

    response = litellm.embedding(**kwargs)
    duration_ms = int((time.time() - start) * 1000)

    # Extract usage and cost
    tokens_in, tokens_out = _extract_usage_tokens(response)
    cost = _calculate_embedding_cost(response, model)

    result = [item["embedding"] for item in response.data]
    logger.debug(f"Generated {len(texts)} embeddings in {duration_ms}ms (model={model})")

    # Record trace if enabled
    if record_trace:
        _record_embedding_trace(
            model=model,
            texts_count=len(texts),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=cost,
            latency_ms=duration_ms,
            step_name=step_name or "embedding",
            module_name=module_name,
        )

    return result


def _record_embedding_trace(
    *,
    model: str,
    texts_count: int,
    tokens_in: int,
    tokens_out: int,
    cost: float,
    latency_ms: int,
    step_name: str,
    module_name: str | None = None,
    error: str | None = None,
) -> None:
    """Record embedding API call to LLMTrace table."""
    try:
        from .tracing import LLMTracer

        tracer = LLMTracer(auto_init=False)

        # Determine provider from model name
        provider = "openai" if "text-embedding" in model else "unknown"
        if "/" in model:
            provider = model.split("/")[0]

        tracer.record(
            prompt=f"[embedding batch: {texts_count} texts]",
            response=f"[{texts_count} embeddings generated]",
            model=model,
            provider=provider,
            latency_ms=latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost=cost,
            step_name=f"{module_name}.{step_name}" if module_name else step_name,
            error=error,
        )
    except Exception as e:
        logger.warning(f"Failed to record embedding trace: {e}")


def generate_document_embedding(
    content: str,
    max_chars: int = 1000,
    module_name: str | None = None,
    step_name: str | None = None,
) -> bytes:
    """
    Generate embedding for document content.

    Args:
        content: Document content
        max_chars: Maximum characters to use
        module_name: Module name for config resolution
        step_name: Step name for config resolution

    Returns:
        Embedding as bytes
    """
    content_sample = content[:max_chars] if len(content) > max_chars else content
    embeddings = generate_embeddings(
        [content_sample],
        module_name=module_name,
        step_name=step_name,
    )
    return embedding_to_bytes(embeddings[0])
