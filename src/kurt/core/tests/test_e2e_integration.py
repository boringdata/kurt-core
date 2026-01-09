"""
End-to-end integration tests for kurt.

Tests the full flow including database persistence for tracing,
and DBOS events/streams for tracking.
"""

from __future__ import annotations

import pandas as pd
import pytest
from pydantic import BaseModel

from kurt.core.hooks import CompositeStepHooks
from kurt.core.llm_step import LLMStep
from kurt.core.mocking import (
    create_content_aware_factory,
    create_content_aware_factory_with_metrics,
)
from kurt.core.tracing import LLMTracer, TracingHooks
from kurt.core.tracking import TrackingHooks, WorkflowTracker

# ============================================================================
# Test Schemas
# ============================================================================


class ExtractionOutput(BaseModel):
    entity: str
    entity_type: str
    confidence: float


class ClassificationOutput(BaseModel):
    category: str
    confidence: float


# ============================================================================
# Database Integration Tests (Tracing)
# ============================================================================


class TestTracingIntegration:
    """Tests for LLMTracer database persistence."""

    def test_tracer_records_to_database(self, tmp_database):
        """Test that LLMTracer persists traces to database."""
        tracer = LLMTracer(auto_init=False)

        tracer.record(
            prompt="Test prompt",
            response="Test response",
            model="gpt-4",
            provider="openai",
            latency_ms=500,
            tokens_in=100,
            tokens_out=50,
            cost=0.01,
            workflow_id="test-wf-1",
            step_name="extract",
        )

        # Query back
        traces = tracer.query(workflow_id="test-wf-1")
        assert len(traces) == 1
        assert traces[0]["prompt"] == "Test prompt"
        assert traces[0]["model"] == "gpt-4"
        assert traces[0]["input_tokens"] == 100

    def test_tracer_stats(self, tmp_database):
        """Test aggregated statistics from tracer."""
        tracer = LLMTracer(auto_init=False)

        # Record multiple traces
        for i in range(5):
            tracer.record(
                prompt=f"Prompt {i}",
                response=f"Response {i}",
                model="gpt-4",
                provider="openai",
                latency_ms=100 + i * 10,
                tokens_in=50,
                tokens_out=25,
                cost=0.005,
                workflow_id="stats-test",
                step_name="extract",
            )

        stats = tracer.stats(workflow_id="stats-test")
        assert stats["total_calls"] == 5
        assert stats["total_tokens_in"] == 250  # 50 * 5
        assert stats["total_tokens_out"] == 125  # 25 * 5
        assert stats["total_cost"] == pytest.approx(0.025, rel=0.01)

    def test_tracer_stats_by_step(self, tmp_database):
        """Test per-step statistics."""
        tracer = LLMTracer(auto_init=False)

        # Record traces for different steps
        for step in ["extract", "extract", "classify"]:
            tracer.record(
                prompt="p",
                response="r",
                model="gpt-4",
                provider="openai",
                latency_ms=100,
                tokens_in=50,
                tokens_out=25,
                workflow_id="step-stats",
                step_name=step,
            )

        stats = tracer.stats_by_step(workflow_id="step-stats")
        stats_by_name = {s["step"]: s for s in stats}

        assert stats_by_name["extract"]["calls"] == 2
        assert stats_by_name["classify"]["calls"] == 1


# ============================================================================
# Tracking Integration Tests (DBOS Events/Streams)
# ============================================================================


class TestTrackingIntegration:
    """Tests for WorkflowTracker DBOS integration."""

    def test_tracker_methods_dont_error_without_dbos(self):
        """Test that tracker methods work gracefully without DBOS context."""
        # These should not raise even without DBOS initialized
        tracker = WorkflowTracker()

        tracker.start_step("test", step_type="llm_step", total=10)
        tracker.update_progress(5, step_name="test")
        tracker.log("Test message", step_name="test")
        tracker.end_step("test", status="success")

    def test_tracking_hooks_lifecycle(self, recording_hooks):
        """Test TrackingHooks lifecycle calls."""
        # TrackingHooks wraps WorkflowTracker but also inherits StepHooks
        # We can't easily test DBOS events without DBOS, but we can verify
        # the hooks don't error
        tracker = WorkflowTracker()
        hooks = TrackingHooks(tracker)

        # Simulate lifecycle - should not raise
        hooks.on_start(step_name="test", total=3, concurrency=1)
        hooks.on_row_success(
            step_name="test",
            idx=0,
            total=3,
            latency_ms=100,
            prompt="p",
            tokens_in=50,
            tokens_out=25,
            cost=0.01,
            result={"key": "value"},
        )
        hooks.on_result(step_name="test", idx=0, total=3, status="success", error=None)
        hooks.on_end(step_name="test", successful=1, total=1, errors=[])


# ============================================================================
# Full Pipeline E2E Tests
# ============================================================================


class TestFullPipelineE2E:
    """End-to-end tests for complete LLM pipelines with tracing."""

    def test_llm_step_with_tracing_hooks(self, tmp_database, mock_dbos):
        """Test LLMStep with TracingHooks persists to database."""
        tracer = LLMTracer(auto_init=False)
        tracing_hooks = TracingHooks(tracer, model_name="test-model", provider="test")

        # Create mock llm_fn that returns metrics
        def mock_llm_with_metrics(prompt: str):
            result = ExtractionOutput(entity="TestEntity", entity_type="test", confidence=0.9)
            metrics = {"tokens_in": 100, "tokens_out": 50, "cost": 0.01}
            return (result, metrics)

        step = LLMStep(
            name="extract_entities",
            input_columns=["text"],
            prompt_template="Extract entities from: {text}",
            output_schema=ExtractionOutput,
            llm_fn=mock_llm_with_metrics,
            concurrency=1,
            hooks=tracing_hooks,
        )

        df = pd.DataFrame({"text": ["PostgreSQL is a database", "Python is a language"]})

        # Run with DBOS mocked (workflow_id defaults to "unknown")
        result = step.run(df)

        # Verify results
        assert len(result) == 2
        assert result["entity"].iloc[0] == "TestEntity"

        # Verify traces were persisted
        traces = tracer.query(step_name="extract_entities", limit=10)
        assert len(traces) == 2
        assert traces[0]["input_tokens"] == 100
        assert traces[0]["output_tokens"] == 50

    def test_llm_step_with_tracking_hooks(self, mock_dbos):
        """Test LLMStep with TrackingHooks doesn't error."""
        tracker = WorkflowTracker()
        tracking_hooks = TrackingHooks(tracker, step_type="llm_step")

        def mock_llm(prompt: str):
            return ClassificationOutput(category="tech", confidence=0.85)

        step = LLMStep(
            name="classify",
            input_columns=["text"],
            prompt_template="Classify: {text}",
            output_schema=ClassificationOutput,
            llm_fn=mock_llm,
            concurrency=1,
            hooks=tracking_hooks,
        )

        df = pd.DataFrame({"text": ["doc1", "doc2", "doc3"]})
        result = step.run(df)

        # Verify step ran successfully
        assert len(result) == 3
        assert all(result["classify_status"] == "success")

    def test_composite_hooks(self, tmp_database, mock_dbos):
        """Test multiple hooks via CompositeStepHooks."""
        tracer = LLMTracer(auto_init=False)
        tracker = WorkflowTracker()

        tracing_hooks = TracingHooks(tracer, model_name="gpt-4")
        tracking_hooks = TrackingHooks(tracker)
        composite = CompositeStepHooks([tracing_hooks, tracking_hooks])

        def mock_llm(prompt: str):
            result = ExtractionOutput(entity="Test", entity_type="test", confidence=0.9)
            return (result, {"tokens_in": 50, "tokens_out": 25, "cost": 0.005})

        step = LLMStep(
            name="multi_hook_step",
            input_columns=["text"],
            prompt_template="{text}",
            output_schema=ExtractionOutput,
            llm_fn=mock_llm,
            concurrency=1,
            hooks=composite,
        )

        df = pd.DataFrame({"text": ["test1", "test2"]})
        step.run(df)

        # Tracing hooks should have recorded data to DB
        traces = tracer.query(step_name="multi_hook_step")
        assert len(traces) == 2


# ============================================================================
# Content-Aware E2E Tests
# ============================================================================


class TestContentAwareE2E:
    """E2E tests using content-aware mocking for realistic scenarios."""

    def test_entity_extraction_pipeline(self, tmp_database, mock_dbos):
        """Test realistic entity extraction with content-aware responses."""
        tracer = LLMTracer(auto_init=False)

        # Content-aware factory simulates realistic LLM behavior
        factory = create_content_aware_factory(
            ExtractionOutput,
            keyword_responses={
                "postgresql": {
                    "entity": "PostgreSQL",
                    "entity_type": "database",
                    "confidence": 0.95,
                },
                "python": {
                    "entity": "Python",
                    "entity_type": "programming_language",
                    "confidence": 0.92,
                },
                "kubernetes": {
                    "entity": "Kubernetes",
                    "entity_type": "orchestration_platform",
                    "confidence": 0.90,
                },
            },
            default_values={
                "entity": "Unknown",
                "entity_type": "unknown",
                "confidence": 0.5,
            },
        )

        step = LLMStep(
            name="extract",
            input_columns=["content"],
            prompt_template="Extract the main entity from: {content}",
            output_schema=ExtractionOutput,
            llm_fn=factory,
            concurrency=1,
            hooks=TracingHooks(tracer, model_name="mock-model"),
        )

        # Test documents
        df = pd.DataFrame(
            {
                "doc_id": [1, 2, 3, 4],
                "content": [
                    "PostgreSQL is a powerful open source database",
                    "Python is great for data science",
                    "Deploy with Kubernetes for scalability",
                    "Some random content without keywords",
                ],
            }
        )

        result = step.run(df)

        # Verify content-aware extraction
        assert result["entity"].iloc[0] == "PostgreSQL"
        assert result["entity_type"].iloc[0] == "database"

        assert result["entity"].iloc[1] == "Python"
        assert result["entity_type"].iloc[1] == "programming_language"

        assert result["entity"].iloc[2] == "Kubernetes"
        assert result["entity_type"].iloc[2] == "orchestration_platform"

        # Default for no keyword match
        assert result["entity"].iloc[3] == "Unknown"
        assert result["confidence"].iloc[3] == 0.5

        # Verify all traces recorded
        traces = tracer.query(step_name="extract")
        assert len(traces) == 4

    def test_content_aware_with_metrics(self, tmp_database, mock_dbos):
        """Test content-aware factory that also returns metrics."""
        tracer = LLMTracer(auto_init=False)

        factory = create_content_aware_factory_with_metrics(
            ExtractionOutput,
            keyword_responses={
                "database": {"entity": "DB", "entity_type": "technology", "confidence": 0.9},
            },
            metrics={"tokens_in": 200, "tokens_out": 100, "cost": 0.02},
        )

        step = LLMStep(
            name="extract_with_metrics",
            input_columns=["text"],
            prompt_template="{text}",
            output_schema=ExtractionOutput,
            llm_fn=factory,
            concurrency=1,
            hooks=TracingHooks(tracer, model_name="gpt-4"),
        )

        df = pd.DataFrame({"text": ["database query optimization"]})
        step.run(df)

        traces = tracer.query(step_name="extract_with_metrics")
        assert len(traces) == 1
        # Metrics should be recorded (scaled by prompt length)
        assert traces[0]["input_tokens"] > 0
        assert traces[0]["output_tokens"] == 100


# ============================================================================
# Multi-Step Pipeline Tests
# ============================================================================


class TestMultiStepPipeline:
    """Tests for multi-step LLM pipelines."""

    def test_chained_steps(self, tmp_database, mock_dbos):
        """Test multiple LLMSteps in sequence."""
        tracer = LLMTracer(auto_init=False)

        # Step 1: Extract entities
        extract_step = LLMStep(
            name="extract",
            input_columns=["text"],
            prompt_template="Extract: {text}",
            output_schema=ExtractionOutput,
            llm_fn=lambda p: ExtractionOutput(
                entity="Entity1", entity_type="type1", confidence=0.9
            ),
            concurrency=1,
            hooks=TracingHooks(tracer, model_name="gpt-4"),
        )

        # Step 2: Classify
        classify_step = LLMStep(
            name="classify",
            input_columns=["entity"],
            prompt_template="Classify entity: {entity}",
            output_schema=ClassificationOutput,
            llm_fn=lambda p: ClassificationOutput(category="technology", confidence=0.85),
            concurrency=1,
            hooks=TracingHooks(tracer, model_name="gpt-4"),
        )

        # Run pipeline
        df = pd.DataFrame({"text": ["PostgreSQL database", "Python language"]})

        df = extract_step.run(df)
        df = classify_step.run(df)

        # Verify final output has columns from both steps
        assert "entity" in df.columns
        assert "entity_type" in df.columns
        assert "category" in df.columns

        # Verify traces for both steps
        extract_traces = tracer.query(step_name="extract")
        classify_traces = tracer.query(step_name="classify")

        assert len(extract_traces) == 2
        assert len(classify_traces) == 2

    def test_error_in_pipeline_step(self, tmp_database, mock_dbos, recording_hooks):
        """Test that errors in one step are captured and don't crash pipeline."""
        tracer = LLMTracer(auto_init=False)

        call_count = 0

        def flaky_llm(prompt: str):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise ValueError("Simulated API error")
            return ExtractionOutput(entity="OK", entity_type="test", confidence=0.9)

        step = LLMStep(
            name="flaky_step",
            input_columns=["text"],
            prompt_template="{text}",
            output_schema=ExtractionOutput,
            llm_fn=flaky_llm,
            concurrency=1,
            hooks=CompositeStepHooks([TracingHooks(tracer), recording_hooks]),
        )

        df = pd.DataFrame({"text": ["ok1", "fail", "ok2"]})
        result = step.run(df)

        # Check statuses
        assert result["flaky_step_status"].iloc[0] == "success"
        assert result["flaky_step_status"].iloc[1] == "error"
        assert result["flaky_step_status"].iloc[2] == "success"

        # Error should be recorded
        error_calls = recording_hooks.get_calls("on_row_error")
        assert len(error_calls) == 1
        assert "Simulated API error" in str(error_calls[0]["error"])
