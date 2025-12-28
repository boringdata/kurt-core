"""Tests for LLM call tracker."""

import threading
import time
from unittest.mock import patch

from kurt.core.llm_tracker import (
    LLMCall,
    LLMTracker,
    TimelineBucket,
    llm_tracker,
    track_embedding_call,
    track_llm_call,
)


class TestLLMCall:
    """Tests for LLMCall dataclass."""

    def test_llm_call_creation(self):
        """Test basic LLMCall creation."""
        call = LLMCall(
            timestamp=1000.0,
            call_type="embedding",
            model="text-embedding-3-small",
            count=100,
            step_name="entity_clustering",
            duration_ms=1234.5,
        )

        assert call.timestamp == 1000.0
        assert call.call_type == "embedding"
        assert call.model == "text-embedding-3-small"
        assert call.count == 100
        assert call.step_name == "entity_clustering"
        assert call.duration_ms == 1234.5

    def test_llm_call_optional_fields(self):
        """Test LLMCall with optional fields as None."""
        call = LLMCall(
            timestamp=1000.0,
            call_type="llm",
            model="gpt-4o-mini",
            count=1,
        )

        assert call.step_name is None
        assert call.duration_ms is None
        assert call.tokens_prompt is None
        assert call.tokens_completion is None

    def test_llm_call_with_tokens(self):
        """Test LLMCall with token tracking."""
        call = LLMCall(
            timestamp=1000.0,
            call_type="llm",
            model="gpt-4o-mini",
            count=1,
            tokens_prompt=100,
            tokens_completion=50,
        )

        assert call.tokens_prompt == 100
        assert call.tokens_completion == 50


class TestLLMTracker:
    """Tests for LLMTracker class."""

    def test_track_call_basic(self):
        """Test basic call tracking."""
        tracker = LLMTracker()
        tracker.configure(workflow_id="test-123")

        tracker.track_call(
            call_type="embedding",
            model="text-embedding-3-small",
            count=50,
            step_name="entity_clustering",
            duration_ms=500.0,
        )

        stats = tracker.get_stats()
        assert stats["total_calls"] == 1
        assert stats["total_items"] == 50
        assert stats["by_type"]["embedding"]["calls"] == 1
        assert stats["by_type"]["embedding"]["items"] == 50
        assert stats["by_step"]["entity_clustering"]["calls"] == 1
        assert stats["by_model"]["text-embedding-3-small"]["calls"] == 1

    def test_track_multiple_calls(self):
        """Test tracking multiple calls."""
        tracker = LLMTracker()
        tracker.configure(workflow_id="test-456")

        tracker.track_call("embedding", "model-a", count=10, step_name="step1")
        tracker.track_call("embedding", "model-a", count=20, step_name="step1")
        tracker.track_call("llm", "model-b", count=1, step_name="step2")

        stats = tracker.get_stats()
        assert stats["total_calls"] == 3
        assert stats["total_items"] == 31  # 10 + 20 + 1
        assert stats["by_type"]["embedding"]["calls"] == 2
        assert stats["by_type"]["llm"]["calls"] == 1
        assert stats["by_step"]["step1"]["calls"] == 2
        assert stats["by_step"]["step2"]["calls"] == 1

    def test_thread_safety(self):
        """Test concurrent track_call from multiple threads."""
        tracker = LLMTracker()
        tracker.configure(workflow_id="thread-test")

        num_threads = 10
        calls_per_thread = 100
        errors = []

        def track_calls(thread_id):
            try:
                for i in range(calls_per_thread):
                    tracker.track_call(
                        call_type="embedding",
                        model=f"model-{thread_id}",
                        count=1,
                        step_name=f"step-{thread_id}",
                    )
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=track_calls, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors: {errors}"

        stats = tracker.get_stats()
        assert stats["total_calls"] == num_threads * calls_per_thread

    def test_sliding_window_pruning(self):
        """Test that old calls are removed from sliding window."""
        tracker = LLMTracker(window_seconds=0.5)  # Very short window for testing
        tracker.configure(workflow_id="prune-test")

        # Track a call
        tracker.track_call("embedding", "model-a", count=10)

        # Wait for window to expire
        time.sleep(0.6)

        # Track another call (this should trigger pruning)
        tracker.track_call("embedding", "model-b", count=20)

        # The first call should be pruned from sliding window
        # But cumulative totals should still include it
        stats = tracker.get_stats()
        assert stats["total_calls"] == 2  # Cumulative total
        assert stats["total_items"] == 30  # Cumulative total

        # Rate should only reflect the second call
        # (since the first was pruned from sliding window)
        # Using a window that includes only the recent call
        rate = tracker.get_calls_per_second(window=0.3)
        assert rate > 0  # At least the recent call

    def test_calls_per_second(self):
        """Test rate calculation accuracy."""
        tracker = LLMTracker()
        tracker.configure(workflow_id="rate-test")

        # Track 10 calls quickly
        for _ in range(10):
            tracker.track_call("embedding", "model-a", count=1)

        # Rate should be approximately 10 / window
        rate = tracker.get_calls_per_second(window=5.0)
        assert rate > 0
        assert rate <= 10.0  # Can't be more than 10 calls in 5 seconds

    def test_items_per_second(self):
        """Test items per second calculation."""
        tracker = LLMTracker()
        tracker.configure(workflow_id="items-rate-test")

        # Track calls with varying item counts
        tracker.track_call("embedding", "model-a", count=100)
        tracker.track_call("embedding", "model-a", count=50)

        items_rate = tracker.get_items_per_second(window=5.0)
        assert items_rate > 0
        assert items_rate <= 150.0 / 5.0  # 150 items max over 5 seconds

    def test_rate_by_step(self):
        """Test rate breakdown by step."""
        tracker = LLMTracker()
        tracker.configure(workflow_id="step-rate-test")

        tracker.track_call("embedding", "model-a", count=10, step_name="step1")
        tracker.track_call("embedding", "model-a", count=20, step_name="step2")
        tracker.track_call("embedding", "model-a", count=30, step_name="step1")

        rates = tracker.get_rate_by_step(window=5.0)
        assert "step1" in rates
        assert "step2" in rates
        assert rates["step1"]["calls_per_sec"] > 0
        assert rates["step1"]["items_per_sec"] > 0
        assert rates["step2"]["calls_per_sec"] > 0

    def test_rate_by_model(self):
        """Test rate breakdown by model."""
        tracker = LLMTracker()
        tracker.configure(workflow_id="model-rate-test")

        tracker.track_call("embedding", "model-a", count=10)
        tracker.track_call("embedding", "model-b", count=20)

        rates = tracker.get_rate_by_model(window=5.0)
        assert "model-a" in rates
        assert "model-b" in rates
        assert rates["model-a"]["calls_per_sec"] > 0
        assert rates["model-b"]["calls_per_sec"] > 0

    def test_stats_breakdown(self):
        """Test by_type, by_step, by_model grouping."""
        tracker = LLMTracker()
        tracker.configure(workflow_id="breakdown-test")

        tracker.track_call("embedding", "embed-model", count=100, step_name="embed_step")
        tracker.track_call("llm", "llm-model", count=1, step_name="llm_step")
        tracker.track_call("embedding", "embed-model", count=50, step_name="embed_step")

        stats = tracker.get_stats()

        # Check by_type breakdown
        assert "embedding" in stats["by_type"]
        assert "llm" in stats["by_type"]
        assert stats["by_type"]["embedding"]["calls"] == 2
        assert stats["by_type"]["embedding"]["items"] == 150
        assert stats["by_type"]["llm"]["calls"] == 1
        assert stats["by_type"]["llm"]["items"] == 1

        # Check by_step breakdown
        assert "embed_step" in stats["by_step"]
        assert "llm_step" in stats["by_step"]
        assert stats["by_step"]["embed_step"]["calls"] == 2
        assert stats["by_step"]["llm_step"]["calls"] == 1

        # Check by_model breakdown
        assert "embed-model" in stats["by_model"]
        assert "llm-model" in stats["by_model"]
        assert stats["by_model"]["embed-model"]["items"] == 150

    def test_timeline_bucketing(self):
        """Test time bucket aggregation."""
        tracker = LLMTracker()
        tracker.configure(workflow_id="timeline-test")

        # Track calls with small delays
        tracker.track_call("embedding", "model-a", count=10)
        time.sleep(0.05)
        tracker.track_call("embedding", "model-a", count=20)

        timeline = tracker.get_timeline(bucket_seconds=0.1)

        assert len(timeline) > 0
        assert all(isinstance(b, TimelineBucket) for b in timeline)

        # Check bucket aggregation
        total_calls = sum(b.total_calls for b in timeline)
        assert total_calls == 2

        total_items = sum(b.total_items for b in timeline)
        assert total_items == 30

    def test_timeline_empty(self):
        """Test timeline with no calls."""
        tracker = LLMTracker()
        tracker.configure(workflow_id="empty-test")

        timeline = tracker.get_timeline()
        assert timeline == []

    def test_configure_resets(self):
        """Test that configure() clears previous data."""
        tracker = LLMTracker()
        tracker.configure(workflow_id="first-workflow")

        # Track some calls
        tracker.track_call("embedding", "model-a", count=100)
        tracker.track_call("llm", "model-b", count=1)

        # Verify calls were tracked
        stats1 = tracker.get_stats()
        assert stats1["total_calls"] == 2
        assert stats1["workflow_id"] == "first-workflow"

        # Reconfigure for new workflow
        tracker.configure(workflow_id="second-workflow")

        # Verify data was reset
        stats2 = tracker.get_stats()
        assert stats2["total_calls"] == 0
        assert stats2["total_items"] == 0
        assert stats2["by_type"] == {}
        assert stats2["by_step"] == {}
        assert stats2["by_model"] == {}
        assert stats2["workflow_id"] == "second-workflow"

    def test_token_tracking(self):
        """Test tracking of prompt and completion tokens."""
        tracker = LLMTracker()
        tracker.configure(workflow_id="token-test")

        # Track calls with tokens
        tracker.track_call(
            "llm",
            "gpt-4o-mini",
            count=1,
            step_name="step1",
            tokens_prompt=100,
            tokens_completion=50,
        )
        tracker.track_call(
            "llm", "gpt-4o", count=1, step_name="step2", tokens_prompt=200, tokens_completion=100
        )
        tracker.track_call(
            "llm",
            "gpt-4o-mini",
            count=1,
            step_name="step1",
            tokens_prompt=150,
            tokens_completion=75,
        )

        stats = tracker.get_stats()

        # Check total tokens
        assert stats["total_tokens_prompt"] == 450  # 100 + 200 + 150
        assert stats["total_tokens_completion"] == 225  # 50 + 100 + 75
        assert stats["total_tokens"] == 675

        # Check tokens by step
        assert stats["by_step"]["step1"]["tokens_prompt"] == 250  # 100 + 150
        assert stats["by_step"]["step1"]["tokens_completion"] == 125  # 50 + 75
        assert stats["by_step"]["step1"]["tokens_total"] == 375
        assert stats["by_step"]["step2"]["tokens_prompt"] == 200
        assert stats["by_step"]["step2"]["tokens_completion"] == 100
        assert stats["by_step"]["step2"]["tokens_total"] == 300

        # Check tokens by model
        assert stats["by_model"]["gpt-4o-mini"]["tokens_prompt"] == 250
        assert stats["by_model"]["gpt-4o-mini"]["tokens_completion"] == 125
        assert stats["by_model"]["gpt-4o-mini"]["tokens_total"] == 375
        assert stats["by_model"]["gpt-4o"]["tokens_prompt"] == 200
        assert stats["by_model"]["gpt-4o"]["tokens_completion"] == 100

    def test_token_tracking_with_none(self):
        """Test that None tokens don't affect totals."""
        tracker = LLMTracker()
        tracker.configure(workflow_id="none-token-test")

        # Track calls without tokens (embedding calls typically don't have tokens)
        tracker.track_call("embedding", "text-embedding-3-small", count=100)
        tracker.track_call("llm", "gpt-4o-mini", count=1, tokens_prompt=100, tokens_completion=50)
        tracker.track_call("embedding", "text-embedding-3-small", count=50)

        stats = tracker.get_stats()
        assert stats["total_tokens_prompt"] == 100
        assert stats["total_tokens_completion"] == 50
        assert stats["total_tokens"] == 150

    def test_print_summary(self, capsys):
        """Test print_summary output."""
        tracker = LLMTracker()
        tracker.configure(workflow_id="summary-test")

        tracker.track_call("embedding", "text-embedding-3-small", count=100, step_name="step1")
        tracker.track_call("llm", "gpt-4o-mini", count=1, step_name="step2")

        tracker.print_summary()

        captured = capsys.readouterr()
        assert "LLM Call Tracker Summary" in captured.out
        assert "summary-test" in captured.out
        assert "Total Calls: 2" in captured.out
        assert "embedding" in captured.out
        assert "llm" in captured.out
        assert "text-embedding-3-small" in captured.out
        assert "gpt-4o-mini" in captured.out


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_track_embedding_call(self):
        """Test track_embedding_call convenience function."""
        # Reset global tracker
        llm_tracker.configure(workflow_id="embed-func-test")

        track_embedding_call(
            model="text-embedding-3-small",
            count=50,
            step_name="test_step",
            duration_ms=123.4,
        )

        stats = llm_tracker.get_stats()
        assert stats["total_calls"] == 1
        assert stats["by_type"]["embedding"]["calls"] == 1
        assert stats["by_type"]["embedding"]["items"] == 50

    def test_track_llm_call(self):
        """Test track_llm_call convenience function."""
        # Reset global tracker
        llm_tracker.configure(workflow_id="llm-func-test")

        track_llm_call(
            model="gpt-4o-mini",
            step_name="test_step",
            duration_ms=567.8,
        )

        stats = llm_tracker.get_stats()
        assert stats["total_calls"] == 1
        assert stats["by_type"]["llm"]["calls"] == 1
        assert stats["by_type"]["llm"]["items"] == 1  # LLM calls always count as 1


class TestDBOSIntegration:
    """Tests for DBOS stream integration."""

    def test_emit_to_dbos_when_available(self):
        """Test that calls are emitted to DBOS stream when available."""
        tracker = LLMTracker()
        tracker.configure(workflow_id="dbos-test")

        with patch("kurt.core.llm_tracker.HAS_DBOS", True):
            with patch("kurt.core.llm_tracker.DBOS") as mock_dbos:
                tracker.track_call("embedding", "model-a", count=10)

                mock_dbos.write_stream.assert_called_once()
                call_args = mock_dbos.write_stream.call_args
                assert call_args[0][0] == "llm_calls_dbos-test"
                # Second arg is JSON string
                assert "embedding" in call_args[0][1]
                assert "model-a" in call_args[0][1]

    def test_emit_to_dbos_handles_error(self):
        """Test that DBOS errors are handled gracefully."""
        tracker = LLMTracker()
        tracker.configure(workflow_id="dbos-error-test")

        with patch("kurt.core.llm_tracker.HAS_DBOS", True):
            with patch("kurt.core.llm_tracker.DBOS") as mock_dbos:
                mock_dbos.write_stream.side_effect = Exception("DBOS error")

                # Should not raise
                tracker.track_call("embedding", "model-a", count=10)

                # Call should still be tracked locally
                stats = tracker.get_stats()
                assert stats["total_calls"] == 1

    def test_no_emit_when_dbos_unavailable(self):
        """Test that no emission happens when DBOS is unavailable."""
        tracker = LLMTracker()
        tracker.configure(workflow_id="no-dbos-test")

        with patch("kurt.core.llm_tracker.HAS_DBOS", False):
            # Should not raise even without DBOS
            tracker.track_call("embedding", "model-a", count=10)

            stats = tracker.get_stats()
            assert stats["total_calls"] == 1

    def test_no_emit_without_workflow_id(self):
        """Test that no emission happens without workflow_id."""
        tracker = LLMTracker()
        tracker.configure(workflow_id=None)

        with patch("kurt.core.llm_tracker.HAS_DBOS", True):
            with patch("kurt.core.llm_tracker.DBOS") as mock_dbos:
                tracker.track_call("embedding", "model-a", count=10)

                # Should not call write_stream without workflow_id
                mock_dbos.write_stream.assert_not_called()


class TestGlobalSingleton:
    """Tests for the global singleton instance."""

    def test_global_singleton_exists(self):
        """Test that the global singleton is available."""
        assert llm_tracker is not None
        assert isinstance(llm_tracker, LLMTracker)

    def test_global_singleton_is_reused(self):
        """Test that importing returns the same instance."""
        from kurt.core.llm_tracker import llm_tracker as tracker1
        from kurt.core.llm_tracker import llm_tracker as tracker2

        assert tracker1 is tracker2


class TestWorkflowIntegration:
    """Tests for workflow integration behavior."""

    def test_tracker_configured_in_workflow_context(self):
        """Test that tracker can be configured and used in workflow-like context."""
        # Simulate workflow configuration
        llm_tracker.configure(workflow_id="test-workflow-123")

        # Simulate embedding calls from parallel steps
        track_embedding_call(
            model="text-embedding-3-small",
            count=100,
            step_name="entity_clustering",
            duration_ms=500.0,
        )
        track_embedding_call(
            model="text-embedding-3-small",
            count=50,
            step_name="claim_clustering",
            duration_ms=300.0,
        )

        # Simulate LLM calls with tokens
        track_llm_call(
            model="gpt-4o-mini",
            step_name="entity_clustering",
            duration_ms=1000.0,
            tokens_prompt=500,
            tokens_completion=100,
        )

        stats = llm_tracker.get_stats()

        # Verify workflow context
        assert stats["workflow_id"] == "test-workflow-123"
        assert stats["total_calls"] == 3
        assert stats["total_items"] == 151  # 100 + 50 + 1

        # Verify rate by step
        rate_by_step = stats["rate_by_step"]
        assert "entity_clustering" in rate_by_step
        assert "claim_clustering" in rate_by_step

        # Verify rate by model
        rate_by_model = stats["rate_by_model"]
        assert "text-embedding-3-small" in rate_by_model
        assert "gpt-4o-mini" in rate_by_model

        # Verify tokens tracked
        assert stats["total_tokens"] == 600  # 500 + 100
        assert stats["by_step"]["entity_clustering"]["tokens_total"] == 600

    def test_parallel_step_rate_tracking(self):
        """Test that rates are tracked correctly for parallel steps."""
        tracker = LLMTracker()
        tracker.configure(workflow_id="parallel-test")

        # Simulate calls from two parallel steps
        for i in range(10):
            tracker.track_call(
                "embedding", "text-embedding-3-small", count=100, step_name="entity_clustering"
            )
            tracker.track_call(
                "embedding", "text-embedding-3-small", count=50, step_name="claim_clustering"
            )

        stats = tracker.get_stats()

        # Both steps should have calls tracked
        assert stats["by_step"]["entity_clustering"]["calls"] == 10
        assert stats["by_step"]["entity_clustering"]["items"] == 1000
        assert stats["by_step"]["claim_clustering"]["calls"] == 10
        assert stats["by_step"]["claim_clustering"]["items"] == 500

        # Rate should reflect calls from both steps
        rate_by_step = tracker.get_rate_by_step(window=60.0)
        assert rate_by_step["entity_clustering"]["calls_per_sec"] > 0
        assert rate_by_step["claim_clustering"]["calls_per_sec"] > 0
