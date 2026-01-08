"""
Unit tests for Mock Utilities.

Tests mock_llm context manager, create_response_factory, create_content_aware_factory,
and their with_metrics variants.
"""

from __future__ import annotations

from unittest.mock import Mock

from pydantic import BaseModel

from kurt_new.core.llm_step import LLMStep
from kurt_new.core.mocking import (
    create_content_aware_factory,
    create_content_aware_factory_with_metrics,
    create_response_factory,
    create_response_factory_with_metrics,
    mock_llm,
)

# ============================================================================
# Test Schemas
# ============================================================================


class MockSchema(BaseModel):
    """Simple schema for tests."""

    field: str = ""
    score: float = 0.0


class SentimentSchema(BaseModel):
    """Schema for sentiment tests."""

    sentiment: str
    confidence: float


class ComplexSchema(BaseModel):
    """Schema with multiple field types."""

    name: str
    count: int
    score: float
    items: list[str]
    data: dict | None = None


# ============================================================================
# mock_llm Context Manager Tests
# ============================================================================


class TestMockLLM:
    """Test mock_llm context manager."""

    def test_replaces_llm_fn_in_context(self, mock_dbos):
        """llm_fn is replaced within context."""
        original_fn = Mock(return_value=MockSchema(field="original", score=0.5))
        step = LLMStep(
            name="test",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=MockSchema,
            llm_fn=original_fn,
            concurrency=1,
        )

        mock_fn = Mock(return_value=MockSchema(field="mocked", score=0.9))

        with mock_llm([step], mock_fn):
            assert step._llm_fn is mock_fn

    def test_restores_llm_fn_after_context(self, mock_dbos):
        """Original llm_fn is restored after context exits."""
        original = Mock(return_value=MockSchema())
        step = LLMStep(
            name="test",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=MockSchema,
            llm_fn=original,
            concurrency=1,
        )

        with mock_llm([step], Mock(return_value=MockSchema())):
            pass

        assert step._llm_fn is original

    def test_restores_on_exception(self, mock_dbos):
        """Original llm_fn is restored even if exception raised."""
        original = Mock(return_value=MockSchema())
        step = LLMStep(
            name="test",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=MockSchema,
            llm_fn=original,
            concurrency=1,
        )

        try:
            with mock_llm([step], Mock()):
                raise ValueError("test")
        except ValueError:
            pass

        assert step._llm_fn is original

    def test_multiple_steps(self, mock_dbos):
        """Works with multiple steps."""
        step1 = LLMStep(
            name="step1",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=MockSchema,
            llm_fn=Mock(return_value=MockSchema()),
            concurrency=1,
        )
        step2 = LLMStep(
            name="step2",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=MockSchema,
            llm_fn=Mock(return_value=MockSchema()),
            concurrency=1,
        )
        mock_fn = Mock(return_value=MockSchema())

        with mock_llm([step1, step2], mock_fn):
            assert step1._llm_fn is mock_fn
            assert step2._llm_fn is mock_fn

    def test_default_factory_returns_empty(self, mock_dbos):
        """Without factory, returns empty dict."""
        step = LLMStep(
            name="test",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=MockSchema,
            llm_fn=Mock(return_value=MockSchema()),
            concurrency=1,
        )
        with mock_llm([step]):
            result = step._llm_fn("prompt")
        assert result == {}


# ============================================================================
# create_response_factory Tests
# ============================================================================


class TestCreateResponseFactory:
    """Test create_response_factory function."""

    def test_str_field_default(self):
        """String fields default to 'mock_{field_name}'."""

        class Schema(BaseModel):
            name: str

        factory = create_response_factory(Schema)
        result = factory("prompt")
        assert result.name == "mock_name"

    def test_float_field_default(self):
        """Float fields default to 0.85."""

        class Schema(BaseModel):
            score: float

        factory = create_response_factory(Schema)
        result = factory("prompt")
        assert result.score == 0.85

    def test_int_field_default(self):
        """Int fields default to 42."""

        class Schema(BaseModel):
            count: int

        factory = create_response_factory(Schema)
        result = factory("prompt")
        assert result.count == 42

    def test_list_field_default(self):
        """List fields default to empty list."""

        class Schema(BaseModel):
            items: list[str]

        factory = create_response_factory(Schema)
        result = factory("prompt")
        assert result.items == []

    def test_other_field_default_none(self):
        """Other types default to None."""

        class Schema(BaseModel):
            data: dict | None

        factory = create_response_factory(Schema)
        result = factory("prompt")
        assert result.data is None

    def test_custom_field_values(self):
        """Custom field_values override defaults."""

        class Schema(BaseModel):
            name: str
            score: float

        factory = create_response_factory(Schema, {"name": "custom", "score": 0.99})
        result = factory("prompt")
        assert result.name == "custom"
        assert result.score == 0.99

    def test_partial_custom_values(self):
        """Can override some fields, others use defaults."""

        class Schema(BaseModel):
            name: str
            count: int

        factory = create_response_factory(Schema, {"name": "custom"})
        result = factory("prompt")
        assert result.name == "custom"
        assert result.count == 42  # default

    def test_returns_pydantic_model(self):
        """Factory returns a Pydantic model instance."""
        factory = create_response_factory(MockSchema)
        result = factory("prompt")
        assert isinstance(result, MockSchema)


# ============================================================================
# create_content_aware_factory Tests
# ============================================================================


class TestCreateContentAwareFactory:
    """Test create_content_aware_factory function."""

    def test_keyword_match_returns_values(self):
        """Matching keyword returns specified values."""

        class Schema(BaseModel):
            sentiment: str

        factory = create_content_aware_factory(
            Schema,
            keyword_responses={"positive": {"sentiment": "happy"}},
        )
        result = factory("This is a positive review")
        assert result.sentiment == "happy"

    def test_keyword_case_insensitive(self):
        """Keyword matching is case-insensitive."""

        class Schema(BaseModel):
            sentiment: str

        factory = create_content_aware_factory(
            Schema,
            keyword_responses={"POSITIVE": {"sentiment": "happy"}},
        )
        result = factory("this is positive")
        assert result.sentiment == "happy"

    def test_no_match_uses_default(self):
        """No keyword match falls back to default factory."""

        class Schema(BaseModel):
            sentiment: str

        factory = create_content_aware_factory(
            Schema,
            keyword_responses={"positive": {"sentiment": "happy"}},
        )
        result = factory("neutral text")
        assert result.sentiment == "mock_sentiment"

    def test_first_match_wins(self):
        """First matching keyword is used."""

        class Schema(BaseModel):
            value: str

        factory = create_content_aware_factory(
            Schema,
            keyword_responses={
                "first": {"value": "one"},
                "second": {"value": "two"},
            },
        )
        result = factory("first and second")
        assert result.value == "one"

    def test_default_values_param(self):
        """default_values are used for unspecified fields."""

        class Schema(BaseModel):
            sentiment: str
            confidence: float

        factory = create_content_aware_factory(
            Schema,
            keyword_responses={"positive": {"sentiment": "happy"}},
            default_values={"confidence": 0.95},
        )
        result = factory("positive text")
        assert result.sentiment == "happy"
        assert result.confidence == 0.95

    def test_returns_pydantic_model(self):
        """Factory returns a Pydantic model instance."""
        factory = create_content_aware_factory(
            SentimentSchema,
            keyword_responses={"test": {"sentiment": "ok", "confidence": 0.5}},
        )
        result = factory("test prompt")
        assert isinstance(result, SentimentSchema)


# ============================================================================
# Factories with Metrics Tests
# ============================================================================


class TestFactoriesWithMetrics:
    """Test *_with_metrics factory variants."""

    def test_response_factory_returns_tuple(self):
        """create_response_factory_with_metrics returns (result, metrics)."""

        class Schema(BaseModel):
            name: str

        factory = create_response_factory_with_metrics(Schema)
        result = factory("prompt")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_response_factory_result_is_model(self):
        """First element is the Pydantic model."""

        class Schema(BaseModel):
            name: str

        factory = create_response_factory_with_metrics(Schema)
        result, metrics = factory("prompt")
        assert isinstance(result, Schema)

    def test_response_factory_metrics_dict(self):
        """Second element is metrics dict."""
        factory = create_response_factory_with_metrics(MockSchema)
        result, metrics = factory("prompt")
        assert "tokens_in" in metrics
        assert "tokens_out" in metrics
        assert "cost" in metrics

    def test_metrics_scaled_by_prompt_length(self):
        """tokens_in is scaled by prompt length."""
        factory = create_response_factory_with_metrics(
            MockSchema,
            metrics={"tokens_in": 100, "tokens_out": 50, "cost": 0.01},
        )
        _, metrics_short = factory("short")
        _, metrics_long = factory("a" * 400)
        assert metrics_long["tokens_in"] > metrics_short["tokens_in"]

    def test_content_aware_with_metrics(self):
        """create_content_aware_factory_with_metrics returns tuple."""

        class Schema(BaseModel):
            sentiment: str

        factory = create_content_aware_factory_with_metrics(
            Schema,
            keyword_responses={"positive": {"sentiment": "happy"}},
        )
        result, metrics = factory("positive text")
        assert result.sentiment == "happy"
        assert "tokens_in" in metrics

    def test_custom_metrics_values(self):
        """Custom metrics values are used."""
        factory = create_response_factory_with_metrics(
            MockSchema,
            metrics={"tokens_in": 200, "tokens_out": 100, "cost": 0.05},
        )
        _, metrics = factory("x")
        assert metrics["tokens_out"] == 100
        assert metrics["cost"] == 0.05

    def test_content_aware_with_metrics_keyword_match(self):
        """Content-aware factory with metrics returns correct values on keyword match."""

        class Schema(BaseModel):
            sentiment: str
            confidence: float

        factory = create_content_aware_factory_with_metrics(
            Schema,
            keyword_responses={"positive": {"sentiment": "happy", "confidence": 0.95}},
            default_values={"sentiment": "neutral", "confidence": 0.5},
        )
        result, metrics = factory("positive review")
        assert result.sentiment == "happy"
        assert result.confidence == 0.95
        assert isinstance(metrics, dict)

    def test_content_aware_with_metrics_no_match(self):
        """Content-aware factory with metrics uses defaults on no match."""

        class Schema(BaseModel):
            sentiment: str

        factory = create_content_aware_factory_with_metrics(
            Schema,
            keyword_responses={"positive": {"sentiment": "happy"}},
        )
        result, metrics = factory("neutral text")
        assert result.sentiment == "mock_sentiment"
        assert isinstance(metrics, dict)
