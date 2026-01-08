"""
Unit tests for LLMStep.

Demonstrates mocking patterns for testing LLM workflows.
"""

from __future__ import annotations

import pandas as pd
from pydantic import BaseModel

from kurt_new.core.llm_step import LLMStep, llm_step
from kurt_new.core.mocking import (
    create_content_aware_factory,
    create_response_factory,
    mock_llm,
)

# ============================================================================
# Test Output Schemas
# ============================================================================


class SentimentOutput(BaseModel):
    sentiment: str
    confidence: float


class EntityOutput(BaseModel):
    entity_name: str
    entity_type: str
    confidence: float


class SummaryOutput(BaseModel):
    summary: str
    key_points: list[str]


# ============================================================================
# Basic LLMStep Tests
# ============================================================================


class TestLLMStepBasic:
    """Basic LLMStep functionality tests."""

    def test_llm_step_with_mock_fn(self, mock_llm_fn, mock_dbos):
        """Test LLMStep with a simple mock llm_fn."""
        llm_fn = mock_llm_fn(
            SentimentOutput,
            {"sentiment": "positive", "confidence": 0.95},
        )

        step = LLMStep(
            name="sentiment_analysis",
            input_columns=["text"],
            prompt_template="Analyze sentiment: {text}",
            output_schema=SentimentOutput,
            llm_fn=llm_fn,
            concurrency=1,
        )

        df = pd.DataFrame({"text": ["I love this!", "Great product"]})
        result = step.run(df)

        assert "sentiment" in result.columns
        assert "confidence" in result.columns
        assert result["sentiment"].iloc[0] == "positive"
        assert result["confidence"].iloc[0] == 0.95

    def test_llm_step_decorator(self, mock_llm_fn, mock_dbos):
        """Test the @llm_step decorator syntax."""

        @llm_step(
            input_columns=["text"],
            prompt_template="Summarize: {text}",
            output_schema=SummaryOutput,
            llm_fn=mock_llm_fn(SummaryOutput, {"summary": "Test summary", "key_points": []}),
            concurrency=1,
        )
        def summarize(row: dict) -> dict:
            # Prepare function can modify row before LLM call
            row["text"] = row["text"].strip()
            return row

        df = pd.DataFrame({"text": ["  Long document content  "]})
        result = summarize.run(df)

        assert "summary" in result.columns
        assert result["summary"].iloc[0] == "Test summary"

    def test_llm_step_preserves_input_columns(self, mock_llm_fn, mock_dbos):
        """Test that input DataFrame columns are preserved."""
        step = LLMStep(
            name="test",
            input_columns=["text"],
            prompt_template="{text}",
            output_schema=SentimentOutput,
            llm_fn=mock_llm_fn(SentimentOutput),
            concurrency=1,
        )

        df = pd.DataFrame(
            {
                "id": [1, 2],
                "text": ["a", "b"],
                "extra": ["x", "y"],
            }
        )
        result = step.run(df)

        # Original columns preserved
        assert "id" in result.columns
        assert "text" in result.columns
        assert "extra" in result.columns
        # Output columns added
        assert "sentiment" in result.columns


# ============================================================================
# Mock LLM Context Manager Tests
# ============================================================================


class TestMockLLMContextManager:
    """Tests for the mock_llm context manager."""

    def test_mock_llm_replaces_fn(self, mock_dbos):
        """Test that mock_llm temporarily replaces llm_fn."""

        def real_llm(prompt: str) -> SentimentOutput:
            raise RuntimeError("Should not be called")

        step = LLMStep(
            name="test",
            input_columns=["text"],
            prompt_template="{text}",
            output_schema=SentimentOutput,
            llm_fn=real_llm,
            concurrency=1,
        )

        factory = create_response_factory(
            SentimentOutput,
            {"sentiment": "mocked", "confidence": 1.0},
        )

        with mock_llm([step], factory):
            df = pd.DataFrame({"text": ["test"]})
            result = step.run(df)
            assert result["sentiment"].iloc[0] == "mocked"

    def test_mock_llm_restores_original(self, mock_dbos):
        """Test that mock_llm restores original llm_fn after context."""

        def original_fn(prompt):
            return SentimentOutput(sentiment="original", confidence=0.5)

        step = LLMStep(
            name="test",
            input_columns=["text"],
            prompt_template="{text}",
            output_schema=SentimentOutput,
            llm_fn=original_fn,
            concurrency=1,
        )

        with mock_llm([step], lambda p: SentimentOutput(sentiment="mock", confidence=1.0)):
            pass

        # Original function should be restored
        assert step._llm_fn == original_fn


# ============================================================================
# Content-Aware Factory Tests
# ============================================================================


class TestContentAwareFactory:
    """Tests for content-aware response factories."""

    def test_keyword_matching(self, mock_dbos):
        """Test that factory returns different responses based on keywords."""
        factory = create_content_aware_factory(
            EntityOutput,
            keyword_responses={
                "postgresql": {"entity_type": "database", "confidence": 0.95},
                "python": {"entity_type": "language", "confidence": 0.90},
            },
            default_values={"entity_name": "unknown", "entity_type": "other", "confidence": 0.5},
        )

        # Test PostgreSQL keyword
        result = factory("Tell me about PostgreSQL database")
        assert result.entity_type == "database"
        assert result.confidence == 0.95

        # Test Python keyword
        result = factory("Python is great for scripting")
        assert result.entity_type == "language"
        assert result.confidence == 0.90

        # Test no keyword match
        result = factory("Some other content")
        assert result.entity_type == "other"
        assert result.confidence == 0.5

    def test_content_aware_in_step(self, mock_dbos):
        """Test content-aware factory integrated with LLMStep."""
        factory = create_content_aware_factory(
            SentimentOutput,
            keyword_responses={
                "love": {"sentiment": "positive", "confidence": 0.99},
                "hate": {"sentiment": "negative", "confidence": 0.99},
            },
        )

        step = LLMStep(
            name="sentiment",
            input_columns=["text"],
            prompt_template="Analyze: {text}",
            output_schema=SentimentOutput,
            llm_fn=factory,
            concurrency=1,
        )

        df = pd.DataFrame(
            {
                "text": [
                    "I love this product",
                    "I hate waiting",
                    "It's okay I guess",
                ]
            }
        )

        result = step.run(df)

        assert result["sentiment"].iloc[0] == "positive"
        assert result["sentiment"].iloc[1] == "negative"
        # Default for no keyword match
        assert result["sentiment"].iloc[2] == "mock_sentiment"


# ============================================================================
# Hook Integration Tests
# ============================================================================


class TestHookIntegration:
    """Tests for hook lifecycle callbacks."""

    def test_hooks_called_in_order(self, recording_hooks, mock_dbos):
        """Test that hooks are called in correct order."""
        step = LLMStep(
            name="test_step",
            input_columns=["text"],
            prompt_template="{text}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="pos", confidence=0.9),
            concurrency=1,
            hooks=recording_hooks,
        )

        df = pd.DataFrame({"text": ["test"]})
        step.run(df)

        # Check call order
        call_types = [name for name, _ in recording_hooks.calls]
        assert call_types[0] == "on_start"
        assert "on_row_success" in call_types
        assert "on_result" in call_types
        assert call_types[-1] == "on_end"

    def test_hooks_receive_correct_data(self, recording_hooks, mock_dbos):
        """Test that hooks receive expected data."""
        step = LLMStep(
            name="my_step",
            input_columns=["text"],
            prompt_template="Process: {text}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="neutral", confidence=0.75),
            concurrency=1,
            hooks=recording_hooks,
        )

        df = pd.DataFrame({"text": ["Hello", "World"]})
        step.run(df)

        # Check on_start
        start_calls = recording_hooks.get_calls("on_start")
        assert len(start_calls) == 1
        assert start_calls[0]["step_name"] == "my_step"
        assert start_calls[0]["total"] == 2

        # Check on_end
        end_calls = recording_hooks.get_calls("on_end")
        assert len(end_calls) == 1
        assert end_calls[0]["successful"] == 2
        assert end_calls[0]["total"] == 2
        assert end_calls[0]["errors"] == []


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Tests for error handling in LLMStep."""

    def test_llm_error_captured(self, recording_hooks, mock_dbos):
        """Test that LLM errors are captured and reported."""
        call_count = 0

        def failing_llm(prompt: str) -> SentimentOutput:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("API Error")
            return SentimentOutput(sentiment="ok", confidence=0.5)

        step = LLMStep(
            name="test",
            input_columns=["text"],
            prompt_template="{text}",
            output_schema=SentimentOutput,
            llm_fn=failing_llm,
            concurrency=1,
            hooks=recording_hooks,
        )

        df = pd.DataFrame({"text": ["fail", "succeed"]})
        result = step.run(df)

        # First row should have error status
        assert result["test_status"].iloc[0] == "error"
        # Second row should succeed
        assert result["test_status"].iloc[1] == "success"

        # Check error hook was called
        error_calls = recording_hooks.get_calls("on_row_error")
        assert len(error_calls) == 1
        assert "API Error" in str(error_calls[0]["error"])


# ============================================================================
# Token/Cost Tracking Tests
# ============================================================================


class TestTokenTracking:
    """Tests for token and cost tracking via llm_fn return tuple."""

    def test_metrics_from_tuple_return(self, recording_hooks, mock_dbos):
        """Test that metrics are extracted from (result, metrics) tuple."""

        def llm_with_metrics(prompt: str):
            result = SentimentOutput(sentiment="positive", confidence=0.9)
            metrics = {
                "tokens_in": 100,
                "tokens_out": 50,
                "cost": 0.005,
            }
            return (result, metrics)

        step = LLMStep(
            name="test",
            input_columns=["text"],
            prompt_template="{text}",
            output_schema=SentimentOutput,
            llm_fn=llm_with_metrics,
            concurrency=1,
            hooks=recording_hooks,
        )

        df = pd.DataFrame({"text": ["test"]})
        step.run(df)

        # Check that hooks received token metrics
        success_calls = recording_hooks.get_calls("on_row_success")
        assert len(success_calls) == 1
        assert success_calls[0]["tokens_in"] == 100
        assert success_calls[0]["tokens_out"] == 50
        assert success_calls[0]["cost"] == 0.005
