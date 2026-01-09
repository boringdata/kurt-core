"""
Unit tests for LLMStep.

Demonstrates mocking patterns for testing LLM workflows.
"""

from __future__ import annotations

from unittest.mock import Mock

import pandas as pd
import pytest
from pydantic import BaseModel

from kurt.core.hooks import NoopStepHooks
from kurt.core.llm_step import LLMStep, llm_step
from kurt.core.mocking import (
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


# ============================================================================
# LLMStep Initialization Tests
# ============================================================================


class TestLLMStepInit:
    """Test LLMStep initialization behaviors."""

    def test_queue_created_with_correct_name(self, mock_dbos):
        """Queue name is {step_name}_queue."""
        step = LLMStep(
            name="extract",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="ok", confidence=0.5),
            concurrency=1,
        )
        assert step.queue.name == "extract_queue"

    def test_queue_concurrency_setting(self, mock_dbos):
        """Queue concurrency matches parameter."""
        step = LLMStep(
            name="extract",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="ok", confidence=0.5),
            concurrency=5,
        )
        assert step.concurrency == 5

    def test_queue_priority_disabled_by_default(self, mock_dbos):
        """Priority is disabled unless explicitly enabled."""
        step = LLMStep(
            name="extract",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="ok", confidence=0.5),
            concurrency=1,
        )
        assert step._priority_enabled is False

    def test_queue_priority_enabled(self, mock_dbos):
        """Priority can be enabled via parameter."""
        step = LLMStep(
            name="extract",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="ok", confidence=0.5),
            concurrency=1,
            priority_enabled=True,
        )
        assert step._priority_enabled is True

    def test_step_function_registered(self, mock_dbos):
        """_process_row is a callable after init."""
        step = LLMStep(
            name="extract",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="ok", confidence=0.5),
            concurrency=1,
        )
        assert callable(step._process_row)

    def test_hooks_default_to_noop(self, mock_dbos):
        """Without hooks param, uses NoopStepHooks."""
        step = LLMStep(
            name="extract",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="ok", confidence=0.5),
            concurrency=1,
        )
        assert isinstance(step._hooks, NoopStepHooks)

    def test_custom_hooks_assigned(self, recording_hooks, mock_dbos):
        """Custom hooks are used when provided."""
        step = LLMStep(
            name="extract",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="ok", confidence=0.5),
            concurrency=1,
            hooks=recording_hooks,
        )
        assert step._hooks is recording_hooks


# ============================================================================
# Prompt Building Tests
# ============================================================================


class TestPromptBuilding:
    """Test _build_prompt() method."""

    def test_template_formatting_single_column(self, mock_dbos):
        """Single column is formatted into template."""
        step = LLMStep(
            name="test",
            input_columns=["content"],
            prompt_template="Extract from: {content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="ok", confidence=0.5),
            concurrency=1,
        )
        result = step._build_prompt({"content": "hello world"})
        assert result == "Extract from: hello world"

    def test_template_formatting_multiple_columns(self, mock_dbos):
        """Multiple columns are formatted into template."""
        step = LLMStep(
            name="test",
            input_columns=["title", "body"],
            prompt_template="Title: {title}\nBody: {body}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="ok", confidence=0.5),
            concurrency=1,
        )
        result = step._build_prompt({"title": "Test", "body": "Content"})
        assert result == "Title: Test\nBody: Content"

    def test_missing_column_defaults_to_empty(self, mock_dbos):
        """Missing columns default to empty string."""
        step = LLMStep(
            name="test",
            input_columns=["content", "missing"],
            prompt_template="{content} - {missing}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="ok", confidence=0.5),
            concurrency=1,
        )
        result = step._build_prompt({"content": "hello"})
        assert result == "hello - "

    def test_extra_columns_ignored(self, mock_dbos):
        """Extra columns in row_dict are ignored."""
        step = LLMStep(
            name="test",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="ok", confidence=0.5),
            concurrency=1,
        )
        result = step._build_prompt({"content": "hello", "extra": "ignored"})
        assert result == "hello"


# ============================================================================
# LLM Calling Tests
# ============================================================================


class TestLLMCalling:
    """Test _call_llm() method."""

    def test_llm_fn_invoked_with_prompt(self, mock_dbos):
        """llm_fn is called with the prompt string."""
        mock_fn = Mock(return_value=SentimentOutput(sentiment="ok", confidence=0.5))
        step = LLMStep(
            name="test",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=mock_fn,
            concurrency=1,
        )
        step._call_llm("test prompt")
        mock_fn.assert_called_once_with("test prompt")

    def test_pydantic_result_converted_to_dict(self, mock_dbos):
        """Pydantic model result is converted via model_dump()."""
        step = LLMStep(
            name="test",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="positive", confidence=0.9),
            concurrency=1,
        )
        result = step._call_llm("prompt")
        assert result == {"sentiment": "positive", "confidence": 0.9}
        assert isinstance(result, dict)

    def test_dict_result_passed_through(self, mock_dbos):
        """Dict results are passed through directly."""
        step = LLMStep(
            name="test",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: {"sentiment": "positive", "confidence": 0.9},
            concurrency=1,
        )
        result = step._call_llm("prompt")
        assert result == {"sentiment": "positive", "confidence": 0.9}

    def test_metrics_tuple_extracts_result(self, mock_dbos):
        """(result, metrics) tuple: result is extracted."""
        step = LLMStep(
            name="test",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: (
                SentimentOutput(sentiment="positive", confidence=0.9),
                {"tokens_in": 100},
            ),
            concurrency=1,
        )
        result = step._call_llm("prompt")
        assert result == {"sentiment": "positive", "confidence": 0.9}

    def test_metrics_tuple_tracks_tokens_in(self, mock_dbos):
        """(result, metrics) tuple: tokens_in is tracked."""
        step = LLMStep(
            name="test",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: (
                SentimentOutput(sentiment="ok", confidence=0.5),
                {"tokens_in": 150},
            ),
            concurrency=1,
        )
        step._call_llm("prompt")
        assert step._last_tokens_in == 150

    def test_metrics_tuple_tracks_tokens_out(self, mock_dbos):
        """(result, metrics) tuple: tokens_out is tracked."""
        step = LLMStep(
            name="test",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: (
                SentimentOutput(sentiment="ok", confidence=0.5),
                {"tokens_out": 75},
            ),
            concurrency=1,
        )
        step._call_llm("prompt")
        assert step._last_tokens_out == 75

    def test_metrics_tuple_tracks_cost(self, mock_dbos):
        """(result, metrics) tuple: cost is tracked."""
        step = LLMStep(
            name="test",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: (
                SentimentOutput(sentiment="ok", confidence=0.5),
                {"cost": 0.05},
            ),
            concurrency=1,
        )
        step._call_llm("prompt")
        assert step._last_cost == 0.05

    def test_metrics_alternative_keys(self, mock_dbos):
        """Metrics support alternative key names (input_tokens, output_tokens)."""
        step = LLMStep(
            name="test",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: (
                SentimentOutput(sentiment="ok", confidence=0.5),
                {"input_tokens": 100, "output_tokens": 50},
            ),
            concurrency=1,
        )
        step._call_llm("prompt")
        assert step._last_tokens_in == 100
        assert step._last_tokens_out == 50

    def test_missing_llm_fn_raises(self, mock_dbos):
        """RuntimeError raised when llm_fn is None."""
        step = LLMStep(
            name="test",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=None,
            concurrency=1,
        )
        with pytest.raises(RuntimeError, match="llm_fn is required"):
            step._call_llm("prompt")

    def test_invalid_return_type_raises(self, mock_dbos):
        """TypeError raised for invalid return types."""
        step = LLMStep(
            name="test",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: "invalid string",
            concurrency=1,
        )
        with pytest.raises(TypeError):
            step._call_llm("prompt")


# ============================================================================
# Row Preparation Tests
# ============================================================================


class TestRowPreparation:
    """Test prepare_fn behavior."""

    def test_prepare_fn_can_add_columns(self, mock_dbos):
        """prepare_fn can add new columns to the row."""

        def prepare(row):
            row["extra"] = "added"
            return row

        step = LLMStep(
            name="test",
            input_columns=["content", "extra"],
            prompt_template="{content} {extra}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="ok", confidence=0.5),
            concurrency=1,
            prepare_fn=prepare,
        )
        result = step._build_prompt(prepare({"content": "hello"}))
        assert "added" in result

    def test_no_prepare_fn_uses_row_directly(self, mock_dbos):
        """Without prepare_fn, row is used as-is."""
        step = LLMStep(
            name="test",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="ok", confidence=0.5),
            concurrency=1,
            prepare_fn=None,
        )
        assert step._prepare_fn is None


# ============================================================================
# run() Method Tests
# ============================================================================


class TestLLMStepRun:
    """Test LLMStep.run() method."""

    def test_all_rows_enqueued(self, mock_dbos):
        """All DataFrame rows are enqueued to the queue."""
        df = pd.DataFrame({"content": ["a", "b", "c"]})
        step = LLMStep(
            name="test",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="ok", confidence=0.5),
            concurrency=1,
        )
        result = step.run(df)
        assert len(result) == 3

    def test_results_collected_in_order(self, mock_dbos):
        """Results map back to correct row indices."""
        df = pd.DataFrame({"content": ["a", "b", "c"]})

        call_idx = [0]

        def llm_fn(prompt):
            idx = call_idx[0]
            call_idx[0] += 1
            return SentimentOutput(sentiment=f"result_{idx}", confidence=0.5)

        step = LLMStep(
            name="test",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=llm_fn,
            concurrency=1,
        )
        result = step.run(df)
        assert len(result) == 3
        # Check that results are in order
        assert result["sentiment"].iloc[0] == "result_0"
        assert result["sentiment"].iloc[1] == "result_1"
        assert result["sentiment"].iloc[2] == "result_2"

    def test_output_columns_added(self, mock_dbos):
        """Output schema fields are added as columns."""
        df = pd.DataFrame({"content": ["a"]})
        step = LLMStep(
            name="test",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="ok", confidence=0.5),
            concurrency=1,
        )
        result = step.run(df)
        assert "sentiment" in result.columns
        assert "confidence" in result.columns

    def test_status_column_added(self, mock_dbos):
        """{step_name}_status column is added."""
        df = pd.DataFrame({"content": ["a"]})
        step = LLMStep(
            name="extract",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="ok", confidence=0.5),
            concurrency=1,
        )
        result = step.run(df)
        assert "extract_status" in result.columns

    def test_successful_rows_have_success_status(self, mock_dbos):
        """Successful rows have status='success'."""
        df = pd.DataFrame({"content": ["a"]})
        step = LLMStep(
            name="extract",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="ok", confidence=0.5),
            concurrency=1,
        )
        result = step.run(df)
        assert result["extract_status"].iloc[0] == "success"

    def test_error_rows_have_error_status(self, mock_dbos):
        """Failed rows have status='error'."""

        def failing_fn(prompt):
            raise ValueError("LLM error")

        step = LLMStep(
            name="extract",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=failing_fn,
            concurrency=1,
        )
        result = step.run(pd.DataFrame({"content": ["a"]}))
        assert result["extract_status"].iloc[0] == "error"

    def test_partial_success_mixed_status(self, mock_dbos):
        """DataFrame can have mix of success/error rows."""
        call_count = [0]

        def sometimes_fail(prompt):
            call_count[0] += 1
            if call_count[0] == 2:
                raise ValueError("fail")
            return SentimentOutput(sentiment="ok", confidence=0.5)

        step = LLMStep(
            name="step",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=sometimes_fail,
            concurrency=1,
        )
        result = step.run(pd.DataFrame({"content": ["a", "b", "c"]}))
        statuses = result["step_status"].tolist()
        assert "success" in statuses
        assert "error" in statuses

    def test_original_dataframe_unchanged(self, mock_dbos):
        """Original DataFrame is not mutated."""
        df = pd.DataFrame({"content": ["a", "b"]})
        original_columns = list(df.columns)
        step = LLMStep(
            name="test",
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="ok", confidence=0.5),
            concurrency=1,
        )
        step.run(df)
        assert list(df.columns) == original_columns


# ============================================================================
# @llm_step Decorator Tests
# ============================================================================


class TestLLMStepDecorator:
    """Test @llm_step decorator."""

    def test_returns_llm_step_instance(self, mock_dbos):
        """Decorator returns an LLMStep instance."""

        @llm_step(
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="ok", confidence=0.5),
        )
        def my_step(row):
            return row

        assert isinstance(my_step, LLMStep)

    def test_name_from_function(self, mock_dbos):
        """Step name is derived from function name."""

        @llm_step(
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="ok", confidence=0.5),
        )
        def extract_entities(row):
            return row

        assert extract_entities.name == "extract_entities"

    def test_prepare_fn_captured(self, mock_dbos):
        """Decorated function is used as prepare_fn."""

        @llm_step(
            input_columns=["content"],
            prompt_template="{content}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="ok", confidence=0.5),
        )
        def my_step(row):
            row["modified"] = True
            return row

        assert my_step._prepare_fn is not None

    def test_all_params_forwarded(self, mock_dbos):
        """All decorator params are forwarded to LLMStep."""

        @llm_step(
            input_columns=["a", "b"],
            prompt_template="{a} {b}",
            output_schema=SentimentOutput,
            llm_fn=lambda p: SentimentOutput(sentiment="ok", confidence=0.5),
            concurrency=10,
            priority_enabled=True,
        )
        def my_step(row):
            return row

        assert my_step.input_columns == ["a", "b"]
        assert my_step.concurrency == 10
        assert my_step._priority_enabled is True
