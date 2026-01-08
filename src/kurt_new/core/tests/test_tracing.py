"""
Unit tests for LLMTracer and TracingHooks.

Tests LLMTracer.record(), query(), stats(), stats_by_step(), and TracingHooks integration.
"""

from __future__ import annotations

import time

from kurt_new.core.tracing import LLMTracer, TracingHooks

# ============================================================================
# LLMTracer.record() Tests
# ============================================================================


class TestLLMTracerRecord:
    """Test LLMTracer.record() method."""

    def test_inserts_trace_record(self, tmp_database):
        """Record is inserted into llm_traces table."""
        tracer = LLMTracer()
        tracer.record(
            prompt="test prompt",
            response="test response",
            model="gpt-4",
            latency_ms=100,
        )

        traces = tracer.query()
        assert len(traces) == 1
        assert traces[0]["prompt"] == "test prompt"

    def test_all_fields_stored(self, tmp_database):
        """All provided fields are stored."""
        tracer = LLMTracer()
        tracer.record(
            prompt="p",
            response="r",
            model="gpt-4",
            latency_ms=150,
            tokens_in=100,
            tokens_out=50,
            cost=0.02,
            workflow_id="wf-123",
            step_name="extract",
            provider="openai",
            structured_output='{"key": "val"}',
            error="error msg",
            retry_count=2,
        )

        trace = tracer.query()[0]
        assert trace["model"] == "gpt-4"
        assert trace["latency_ms"] == 150
        assert trace["input_tokens"] == 100
        assert trace["output_tokens"] == 50
        assert trace["cost"] == 0.02
        assert trace["workflow_id"] == "wf-123"
        assert trace["step_name"] == "extract"
        assert trace["provider"] == "openai"
        assert trace["error"] == "error msg"
        assert trace["retry_count"] == 2

    def test_workflow_id_defaults_to_unknown(self, tmp_database):
        """workflow_id defaults to 'unknown' when not in DBOS context."""
        tracer = LLMTracer()
        tracer.record(prompt="p", response="r", model="m", latency_ms=0)
        trace = tracer.query()[0]
        assert trace["workflow_id"] == "unknown"

    def test_step_name_defaults_to_unknown(self, tmp_database):
        """step_name defaults to 'unknown'."""
        tracer = LLMTracer()
        tracer.record(prompt="p", response="r", model="m", latency_ms=0)
        trace = tracer.query()[0]
        assert trace["step_name"] == "unknown"

    def test_total_tokens_computed(self, tmp_database):
        """total_tokens = tokens_in + tokens_out."""
        tracer = LLMTracer()
        tracer.record(
            prompt="p",
            response="r",
            model="m",
            latency_ms=0,
            tokens_in=100,
            tokens_out=50,
        )
        trace = tracer.query()[0]
        assert trace["total_tokens"] == 150

    def test_response_stored(self, tmp_database):
        """Response is stored correctly."""
        tracer = LLMTracer()
        tracer.record(
            prompt="p",
            response="This is the response",
            model="m",
            latency_ms=0,
        )
        trace = tracer.query()[0]
        assert trace["response"] == "This is the response"


# ============================================================================
# LLMTracer.query() Tests
# ============================================================================


class TestLLMTracerQuery:
    """Test LLMTracer.query() method."""

    def test_returns_all_traces(self, tmp_database):
        """Returns all traces when no filters."""
        tracer = LLMTracer()
        tracer.record(prompt="p1", response="r", model="m", latency_ms=0)
        tracer.record(prompt="p2", response="r", model="m", latency_ms=0)

        traces = tracer.query()
        assert len(traces) == 2

    def test_filter_by_workflow_id(self, tmp_database):
        """Filter by workflow_id."""
        tracer = LLMTracer()
        tracer.record(prompt="p1", response="r", model="m", latency_ms=0, workflow_id="wf1")
        tracer.record(prompt="p2", response="r", model="m", latency_ms=0, workflow_id="wf2")

        traces = tracer.query(workflow_id="wf1")
        assert len(traces) == 1
        assert traces[0]["prompt"] == "p1"

    def test_filter_by_step_name(self, tmp_database):
        """Filter by step_name."""
        tracer = LLMTracer()
        tracer.record(prompt="p1", response="r", model="m", latency_ms=0, step_name="step1")
        tracer.record(prompt="p2", response="r", model="m", latency_ms=0, step_name="step2")

        traces = tracer.query(step_name="step1")
        assert len(traces) == 1

    def test_limit_parameter(self, tmp_database):
        """Respects limit parameter."""
        tracer = LLMTracer()
        for i in range(10):
            tracer.record(prompt=f"p{i}", response="r", model="m", latency_ms=0)

        traces = tracer.query(limit=5)
        assert len(traces) == 5

    def test_ordered_by_created_at_desc(self, tmp_database):
        """Results ordered by created_at descending."""
        tracer = LLMTracer()
        tracer.record(prompt="first", response="r", model="m", latency_ms=0)
        # Small delay to ensure different timestamps
        time.sleep(0.01)
        tracer.record(prompt="second", response="r", model="m", latency_ms=0)

        traces = tracer.query()
        assert traces[0]["prompt"] == "second"  # most recent first


# ============================================================================
# LLMTracer.stats() Tests
# ============================================================================


class TestLLMTracerStats:
    """Test LLMTracer.stats() method."""

    def test_total_calls(self, tmp_database):
        """Counts total calls."""
        tracer = LLMTracer()
        for _ in range(5):
            tracer.record(prompt="p", response="r", model="m", latency_ms=0)

        stats = tracer.stats()
        assert stats["total_calls"] == 5

    def test_token_totals(self, tmp_database):
        """Sums token counts."""
        tracer = LLMTracer()
        tracer.record(
            prompt="p", response="r", model="m", latency_ms=0, tokens_in=100, tokens_out=50
        )
        tracer.record(
            prompt="p", response="r", model="m", latency_ms=0, tokens_in=200, tokens_out=100
        )

        stats = tracer.stats()
        assert stats["total_tokens_in"] == 300
        assert stats["total_tokens_out"] == 150

    def test_total_cost(self, tmp_database):
        """Sums cost."""
        tracer = LLMTracer()
        tracer.record(prompt="p", response="r", model="m", latency_ms=0, cost=0.01)
        tracer.record(prompt="p", response="r", model="m", latency_ms=0, cost=0.02)

        stats = tracer.stats()
        assert abs(stats["total_cost"] - 0.03) < 0.001

    def test_latency_stats(self, tmp_database):
        """Computes avg, min, max latency."""
        tracer = LLMTracer()
        tracer.record(prompt="p", response="r", model="m", latency_ms=100)
        tracer.record(prompt="p", response="r", model="m", latency_ms=200)
        tracer.record(prompt="p", response="r", model="m", latency_ms=300)

        stats = tracer.stats()
        assert stats["avg_latency_ms"] == 200
        assert stats["min_latency_ms"] == 100
        assert stats["max_latency_ms"] == 300

    def test_success_error_counts(self, tmp_database):
        """Counts success vs error."""
        tracer = LLMTracer()
        tracer.record(prompt="p", response="r", model="m", latency_ms=0)
        tracer.record(prompt="p", response="r", model="m", latency_ms=0)
        tracer.record(prompt="p", response="r", model="m", latency_ms=0, error="failed")

        stats = tracer.stats()
        assert stats["success_count"] == 2
        assert stats["error_count"] == 1

    def test_filter_by_workflow_id(self, tmp_database):
        """Stats can be filtered by workflow_id."""
        tracer = LLMTracer()
        tracer.record(prompt="p", response="r", model="m", latency_ms=0, workflow_id="wf1")
        tracer.record(prompt="p", response="r", model="m", latency_ms=0, workflow_id="wf2")

        stats = tracer.stats(workflow_id="wf1")
        assert stats["total_calls"] == 1

    def test_empty_database_returns_zeros(self, tmp_database):
        """Empty database returns zero values."""
        tracer = LLMTracer()
        stats = tracer.stats()
        assert stats["total_calls"] == 0
        assert stats["total_tokens_in"] == 0
        assert stats["total_cost"] == 0.0


# ============================================================================
# LLMTracer.stats_by_step() Tests
# ============================================================================


class TestLLMTracerStatsByStep:
    """Test LLMTracer.stats_by_step() method."""

    def test_groups_by_step(self, tmp_database):
        """Returns stats grouped by step_name."""
        tracer = LLMTracer()
        tracer.record(prompt="p", response="r", model="m", latency_ms=100, step_name="step1")
        tracer.record(prompt="p", response="r", model="m", latency_ms=200, step_name="step1")
        tracer.record(prompt="p", response="r", model="m", latency_ms=300, step_name="step2")

        stats = tracer.stats_by_step()
        assert len(stats) == 2

        step1_stats = next(s for s in stats if s["step"] == "step1")
        assert step1_stats["calls"] == 2

    def test_per_step_metrics(self, tmp_database):
        """Each step has its own metrics."""
        tracer = LLMTracer()
        tracer.record(
            prompt="p",
            response="r",
            model="m",
            latency_ms=0,
            step_name="step1",
            tokens_in=100,
            tokens_out=50,
            cost=0.01,
        )
        tracer.record(
            prompt="p",
            response="r",
            model="m",
            latency_ms=0,
            step_name="step2",
            tokens_in=200,
            tokens_out=100,
            cost=0.02,
        )

        stats = tracer.stats_by_step()
        step1 = next(s for s in stats if s["step"] == "step1")
        step2 = next(s for s in stats if s["step"] == "step2")

        assert step1["total_cost"] == 0.01
        assert step2["total_cost"] == 0.02

    def test_empty_database_returns_empty_list(self, tmp_database):
        """Empty database returns empty list."""
        tracer = LLMTracer()
        stats = tracer.stats_by_step()
        assert stats == []


# ============================================================================
# TracingHooks Tests
# ============================================================================


class TestTracingHooks:
    """Test TracingHooks integration with LLMTracer."""

    def test_on_row_success_records_trace(self, tmp_database):
        """on_row_success calls tracer.record()."""
        tracer = LLMTracer()
        hooks = TracingHooks(tracer, model_name="gpt-4", provider="openai")

        hooks.on_row_success(
            step_name="extract",
            idx=0,
            total=10,
            latency_ms=100,
            prompt="test prompt",
            tokens_in=50,
            tokens_out=25,
            cost=0.01,
            result={"key": "value"},
        )

        traces = tracer.query()
        assert len(traces) == 1
        assert traces[0]["prompt"] == "test prompt"
        assert traces[0]["model"] == "gpt-4"

    def test_on_row_error_records_trace(self, tmp_database):
        """on_row_error calls tracer.record() with error."""
        tracer = LLMTracer()
        hooks = TracingHooks(tracer)

        hooks.on_row_error(
            step_name="extract",
            idx=0,
            total=10,
            latency_ms=100,
            prompt="test prompt",
            tokens_in=50,
            tokens_out=0,
            cost=0.0,
            error=ValueError("LLM failed"),
        )

        traces = tracer.query()
        assert traces[0]["error"] == "LLM failed"

    def test_model_provider_passed_through(self, tmp_database):
        """model_name and provider are stored in traces."""
        tracer = LLMTracer()
        hooks = TracingHooks(tracer, model_name="claude-3", provider="anthropic")

        hooks.on_row_success(
            step_name="s",
            idx=0,
            total=1,
            latency_ms=0,
            prompt="p",
            tokens_in=0,
            tokens_out=0,
            cost=0,
            result={},
        )

        trace = tracer.query()[0]
        assert trace["model"] == "claude-3"
        assert trace["provider"] == "anthropic"

    def test_creates_tracer_if_not_provided(self, tmp_database):
        """TracingHooks creates a tracer if none provided."""
        hooks = TracingHooks(model_name="gpt-4")
        hooks.on_row_success(
            step_name="test",
            idx=0,
            total=1,
            latency_ms=0,
            prompt="p",
            tokens_in=0,
            tokens_out=0,
            cost=0,
            result={},
        )
        # Should not raise - tracer was created internally
        assert hooks._tracer is not None

    def test_step_name_stored(self, tmp_database):
        """step_name is correctly stored in trace."""
        tracer = LLMTracer()
        hooks = TracingHooks(tracer)

        hooks.on_row_success(
            step_name="my_custom_step",
            idx=0,
            total=1,
            latency_ms=0,
            prompt="p",
            tokens_in=0,
            tokens_out=0,
            cost=0,
            result={},
        )

        trace = tracer.query()[0]
        assert trace["step_name"] == "my_custom_step"

    def test_result_stored_as_json(self, tmp_database):
        """Result dict is stored as JSON in structured_output."""
        tracer = LLMTracer()
        hooks = TracingHooks(tracer)

        hooks.on_row_success(
            step_name="test",
            idx=0,
            total=1,
            latency_ms=0,
            prompt="p",
            tokens_in=0,
            tokens_out=0,
            cost=0,
            result={"sentiment": "positive", "confidence": 0.95},
        )

        trace = tracer.query()[0]
        assert trace["structured_output"] is not None
        assert "positive" in trace["structured_output"]
