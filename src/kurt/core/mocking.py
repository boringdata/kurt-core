from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Callable, Iterable
from unittest.mock import MagicMock

from pydantic import BaseModel

from .llm_step import LLMStep

if TYPE_CHECKING:
    from .embedding_step import EmbeddingStep


@contextmanager
def mock_llm(
    steps: Iterable[LLMStep],
    response_factory: Callable[[str], Any] | None = None,
):
    """
    Temporarily replace LLMStep llm_fn for tests.
    """
    steps = list(steps)
    original_fns = [step._llm_fn for step in steps]

    factory = response_factory or (lambda prompt: {})
    for step in steps:
        step._llm_fn = factory

    try:
        yield
    finally:
        for step, original in zip(steps, original_fns):
            step._llm_fn = original


def create_response_factory(
    output_schema: type[BaseModel],
    field_values: dict[str, Any] | None = None,
) -> Callable[[str], BaseModel]:
    """
    Create a response factory for a specific Pydantic schema.
    """

    def factory(prompt: str) -> BaseModel:
        values: dict[str, Any] = {}
        for field_name, info in output_schema.model_fields.items():
            if field_values and field_name in field_values:
                values[field_name] = field_values[field_name]
            else:
                anno = info.annotation
                if anno is str:
                    values[field_name] = f"mock_{field_name}"
                elif anno is float:
                    values[field_name] = 0.85
                elif anno is int:
                    values[field_name] = 42
                elif hasattr(anno, "__origin__") and anno.__origin__ is list:
                    values[field_name] = []
                else:
                    values[field_name] = None
        return output_schema(**values)

    return factory


def create_content_aware_factory(
    output_schema: type[BaseModel],
    keyword_responses: dict[str, dict[str, Any]],
    default_values: dict[str, Any] | None = None,
) -> Callable[[str], BaseModel]:
    """
    Create a factory that returns different values based on prompt content.
    """
    base_factory = create_response_factory(output_schema, default_values)

    def factory(prompt: str) -> BaseModel:
        prompt_lower = prompt.lower()
        for keyword, values in keyword_responses.items():
            if keyword.lower() in prompt_lower:
                merged: dict[str, Any] = {}
                for field_name, info in output_schema.model_fields.items():
                    if field_name in values:
                        merged[field_name] = values[field_name]
                    elif default_values and field_name in default_values:
                        merged[field_name] = default_values[field_name]
                    else:
                        anno = info.annotation
                        if anno is str:
                            merged[field_name] = f"mock_{field_name}"
                        elif anno is float:
                            merged[field_name] = 0.85
                        elif anno is int:
                            merged[field_name] = 42
                        elif hasattr(anno, "__origin__") and anno.__origin__ is list:
                            merged[field_name] = []
                        else:
                            merged[field_name] = None
                return output_schema(**merged)
        return base_factory(prompt)

    return factory


# ============================================================================
# Factories with Metrics (for token/cost tracking)
# ============================================================================


def create_response_factory_with_metrics(
    output_schema: type[BaseModel],
    field_values: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
) -> Callable[[str], tuple[BaseModel, dict[str, Any]]]:
    """
    Create a response factory that returns (result, metrics) tuples.

    This supports the LLMStep token/cost tracking feature.

    Args:
        output_schema: Pydantic model for the response
        field_values: Values to use for output fields
        metrics: Token/cost metrics to return (tokens_in, tokens_out, cost)

    Returns:
        Factory function that returns (BaseModel, metrics_dict) tuples
    """
    base_factory = create_response_factory(output_schema, field_values)
    default_metrics = metrics or {"tokens_in": 100, "tokens_out": 50, "cost": 0.01}

    def factory(prompt: str) -> tuple[BaseModel, dict[str, Any]]:
        result = base_factory(prompt)
        # Scale metrics by prompt length for more realistic simulation
        prompt_len = len(prompt)
        scaled_metrics = {
            "tokens_in": default_metrics.get("tokens_in", 100) + prompt_len // 4,
            "tokens_out": default_metrics.get("tokens_out", 50),
            "cost": default_metrics.get("cost", 0.01),
        }
        return (result, scaled_metrics)

    return factory


def create_content_aware_factory_with_metrics(
    output_schema: type[BaseModel],
    keyword_responses: dict[str, dict[str, Any]],
    default_values: dict[str, Any] | None = None,
    metrics: dict[str, Any] | None = None,
) -> Callable[[str], tuple[BaseModel, dict[str, Any]]]:
    """
    Create a content-aware factory that also returns metrics.

    Combines keyword-based responses with token/cost tracking.
    """
    base_factory = create_content_aware_factory(output_schema, keyword_responses, default_values)
    default_metrics = metrics or {"tokens_in": 100, "tokens_out": 50, "cost": 0.01}

    def factory(prompt: str) -> tuple[BaseModel, dict[str, Any]]:
        result = base_factory(prompt)
        prompt_len = len(prompt)
        scaled_metrics = {
            "tokens_in": default_metrics.get("tokens_in", 100) + prompt_len // 4,
            "tokens_out": default_metrics.get("tokens_out", 50),
            "cost": default_metrics.get("cost", 0.01),
        }
        return (result, scaled_metrics)

    return factory


# ============================================================================
# Embedding Mocking Utilities
# ============================================================================


def create_mock_embedding(dimensions: int = 1536) -> list[float]:
    """
    Create a mock embedding vector.

    Args:
        dimensions: Number of dimensions (default: 1536 for OpenAI)

    Returns:
        List of floats representing a mock embedding
    """
    import random

    # Generate deterministic-ish values based on dimension index
    return [random.random() * 0.1 for _ in range(dimensions)]


def create_embedding_response(
    texts: list[str],
    dimensions: int = 1536,
    tokens_per_text: int = 10,
) -> MagicMock:
    """
    Create a mock LiteLLM embedding response.

    Args:
        texts: List of input texts (determines number of embeddings)
        dimensions: Embedding dimensions
        tokens_per_text: Approximate tokens per text for usage tracking

    Returns:
        MagicMock mimicking litellm.embedding() response
    """
    response = MagicMock()
    response.data = [{"embedding": create_mock_embedding(dimensions)} for _ in texts]
    # Add usage data for cost tracking
    total_tokens = len(texts) * tokens_per_text
    response.usage = MagicMock()
    response.usage.prompt_tokens = total_tokens
    response.usage.total_tokens = total_tokens
    return response


@contextmanager
def mock_embeddings(dimensions: int = 1536):
    """
    Context manager to mock all embedding calls via litellm.

    Usage:
        with mock_embeddings():
            result = generate_embeddings(["hello", "world"])
            # Returns mock embeddings without API calls

    Args:
        dimensions: Embedding dimensions (default: 1536)

    Yields:
        The mock litellm module for assertions
    """
    import importlib

    embedding_step_module = importlib.import_module("kurt.core.embedding_step")

    # Create a mock litellm module
    mock_litellm = MagicMock()

    def mock_embedding_fn(**kwargs):
        texts = kwargs.get("input", [])
        return create_embedding_response(texts, dimensions)

    mock_litellm.embedding.side_effect = mock_embedding_fn
    # Also mock response_cost_calculator to return 0.0
    mock_litellm.response_cost_calculator.return_value = 0.0

    # Store original litellm (could be None or the real module)
    original_litellm = embedding_step_module.litellm

    # Replace litellm in the embedding_step module
    embedding_step_module.litellm = mock_litellm

    try:
        yield mock_litellm
    finally:
        embedding_step_module.litellm = original_litellm


@contextmanager
def mock_embedding_step(
    steps: Iterable[EmbeddingStep],
    dimensions: int = 1536,
):
    """
    Context manager to mock EmbeddingStep litellm calls.

    Similar to mock_llm() but for embedding steps.

    Usage:
        step = EmbeddingStep(name="embed", input_column="text", model="test")
        with mock_embedding_step([step]):
            result = step.run(df)

    Args:
        steps: EmbeddingStep instances to mock
        dimensions: Embedding dimensions

    Yields:
        The mock litellm module
    """
    with mock_embeddings(dimensions) as mock_litellm:
        yield mock_litellm
