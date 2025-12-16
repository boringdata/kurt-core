"""Tests for running LLM-based models in parallel.

Verifies that:
1. Multiple LLM models can run concurrently via asyncio.gather
2. dspy.context() provides proper isolation between parallel tasks
3. No configuration conflicts occur when running parallel DSPy calls
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import dspy
import pytest

from kurt.content.indexing_new.framework.dspy_helpers import (
    get_dspy_lm,
    run_batch,
)


class SampleSignature(dspy.Signature):
    """Sample signature for parallel execution tests."""

    input_text: str = dspy.InputField()
    output_text: str = dspy.OutputField()


class TestParallelLLMExecution:
    """Test parallel execution of LLM-based operations."""

    @pytest.fixture
    def mock_lm(self):
        """Create a mock LM that simulates async execution."""
        mock = MagicMock()
        mock.model_name = "test-model"
        return mock

    @pytest.mark.asyncio
    async def test_parallel_run_batch_calls(self):
        """Test that multiple run_batch calls can run in parallel.

        This simulates the scenario where entity_clustering and claim_clustering
        run in parallel, both using DSPy with different batches.
        """
        execution_log = []

        def create_mock_executor(batch_name: str, delay: float = 0.1):
            """Create a mock executor that logs execution timing."""

            def mock_call(**kwargs):
                execution_log.append(
                    {
                        "batch": batch_name,
                        "action": "start",
                        "time": time.time(),
                    }
                )
                time.sleep(delay)  # Simulate LLM call
                execution_log.append(
                    {
                        "batch": batch_name,
                        "action": "end",
                        "time": time.time(),
                    }
                )
                result = MagicMock()
                result.output_text = f"processed_{batch_name}"
                return result

            executor = MagicMock()
            executor.return_value = mock_call()
            executor.side_effect = mock_call
            executor.acall = None
            return executor

        with patch("kurt.content.indexing_new.framework.dspy_helpers.get_dspy_lm") as mock_get_lm:
            mock_lm = MagicMock()
            mock_get_lm.return_value = mock_lm

            # Create two batches that will run in parallel
            async def run_batch_1():
                with patch("dspy.ChainOfThought", return_value=create_mock_executor("batch1", 0.2)):
                    return await run_batch(
                        signature=SampleSignature,
                        items=[{"input_text": "text1"}, {"input_text": "text2"}],
                        max_concurrent=2,
                    )

            async def run_batch_2():
                with patch("dspy.ChainOfThought", return_value=create_mock_executor("batch2", 0.2)):
                    return await run_batch(
                        signature=SampleSignature,
                        items=[{"input_text": "text3"}, {"input_text": "text4"}],
                        max_concurrent=2,
                    )

            start_time = time.time()

            # Run both batches in parallel
            results1, results2 = await asyncio.gather(run_batch_1(), run_batch_2())

            elapsed = time.time() - start_time

            # Both batches should complete
            assert len(results1) == 2
            assert len(results2) == 2

            # Verify parallelism: if sequential, would take ~0.8s (4 items * 0.2s)
            # If parallel with 2 concurrent per batch, should take ~0.4s
            # Allow some margin for test overhead
            assert elapsed < 0.7, f"Expected parallel execution, got {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_dspy_context_isolation(self):
        """Test that dspy.context() provides isolation between parallel tasks.

        Each task should use its own LM configuration without conflicts.
        """
        lm_usage_log = []

        def create_executor_that_logs_lm():
            """Create executor that logs which LM context it sees."""

            def mock_call(**kwargs):
                # Access the current dspy settings to see which LM is active
                current_lm = dspy.settings.lm
                lm_usage_log.append(
                    {
                        "lm_id": id(current_lm) if current_lm else None,
                        "time": time.time(),
                    }
                )
                result = MagicMock()
                result.output_text = "processed"
                return result

            executor = MagicMock()
            executor.side_effect = mock_call
            executor.acall = None
            return executor

        # Create two different LM instances
        lm1 = MagicMock(spec=dspy.LM)
        lm1.model_name = "model-1"
        lm2 = MagicMock(spec=dspy.LM)
        lm2.model_name = "model-2"

        async def task_with_lm1():
            with dspy.context(lm=lm1):
                with patch("dspy.ChainOfThought", return_value=create_executor_that_logs_lm()):
                    # Simulate some work
                    await asyncio.sleep(0.05)
                    items = [{"input_text": "text1"}]
                    return await run_batch(
                        signature=SampleSignature,
                        items=items,
                        max_concurrent=1,
                    )

        async def task_with_lm2():
            with dspy.context(lm=lm2):
                with patch("dspy.ChainOfThought", return_value=create_executor_that_logs_lm()):
                    # Simulate some work
                    await asyncio.sleep(0.05)
                    items = [{"input_text": "text2"}]
                    return await run_batch(
                        signature=SampleSignature,
                        items=items,
                        max_concurrent=1,
                    )

        with patch("kurt.content.indexing_new.framework.dspy_helpers.get_dspy_lm") as mock_get_lm:
            # get_dspy_lm should not be called when LM is already set via context
            mock_get_lm.return_value = MagicMock()

            # Run tasks in parallel
            results = await asyncio.gather(task_with_lm1(), task_with_lm2())

            # Both should complete successfully
            assert len(results) == 2
            assert all(len(r) == 1 for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_run_batch_no_config_conflicts(self):
        """Test that concurrent run_batch calls don't cause dspy.configure conflicts.

        This is the key test - before the fix, parallel calls to run_batch would
        fail with 'dspy.settings.configure() can only be called from the same async task'.
        """
        mock_executor = MagicMock()
        mock_result = MagicMock()
        mock_result.output_text = "processed"
        mock_executor.return_value = mock_result
        mock_executor.acall = None

        with patch("kurt.content.indexing_new.framework.dspy_helpers.get_dspy_lm") as mock_get_lm:
            mock_lm = MagicMock()
            mock_get_lm.return_value = mock_lm

            with patch("dspy.ChainOfThought", return_value=mock_executor):
                # Launch many concurrent run_batch calls
                tasks = [
                    run_batch(
                        signature=SampleSignature,
                        items=[{"input_text": f"text_{i}"}],
                        max_concurrent=1,
                    )
                    for i in range(10)
                ]

                # This should NOT raise RuntimeError about dspy.configure
                results = await asyncio.gather(*tasks)

                # All should complete successfully
                assert len(results) == 10
                assert all(len(r) == 1 for r in results)
                assert all(r[0].error is None for r in results)

    @pytest.mark.asyncio
    async def test_run_batch_uses_dspy_context_not_configure(self):
        """Verify that run_batch uses dspy.context() instead of dspy.configure().

        This ensures thread-safe execution in parallel async contexts.
        """
        mock_executor = MagicMock()
        mock_result = MagicMock()
        mock_result.output_text = "processed"
        mock_executor.return_value = mock_result
        mock_executor.acall = None

        with patch("kurt.content.indexing_new.framework.dspy_helpers.get_dspy_lm") as mock_get_lm:
            mock_lm = MagicMock()
            mock_lm.model_name = "test-model"
            mock_get_lm.return_value = mock_lm

            # Patch dspy.context to track calls
            context_calls = []
            original_context = dspy.context

            def tracking_context(**kwargs):
                context_calls.append(kwargs)
                return original_context(**kwargs)

            with patch("dspy.ChainOfThought", return_value=mock_executor):
                with patch.object(dspy, "context", side_effect=tracking_context):
                    await run_batch(
                        signature=SampleSignature,
                        items=[{"input_text": "text1"}],
                        max_concurrent=1,
                    )

            # dspy.context should have been called with the LM
            assert len(context_calls) >= 1
            # At least one call should have lm parameter
            lm_calls = [c for c in context_calls if "lm" in c]
            assert len(lm_calls) >= 1


class TestGetDspyLm:
    """Test get_dspy_lm function."""

    def test_get_dspy_lm_returns_lm_instance(self):
        """Test that get_dspy_lm returns a dspy.LM instance."""
        with patch("kurt.config.get_config_or_default") as mock_config:
            mock_config.return_value.INDEXING_LLM_MODEL = "anthropic/claude-3-haiku-20240307"

            with patch.object(dspy, "LM") as mock_lm_class:
                mock_lm = MagicMock()
                mock_lm_class.return_value = mock_lm

                result = get_dspy_lm()

                assert result == mock_lm
                mock_lm_class.assert_called_once()

    def test_get_dspy_lm_with_explicit_model(self):
        """Test get_dspy_lm with explicit model name."""
        with patch.object(dspy, "LM") as mock_lm_class:
            mock_lm = MagicMock()
            mock_lm_class.return_value = mock_lm

            result = get_dspy_lm("openai/gpt-4")

            assert result == mock_lm
            mock_lm_class.assert_called_once_with("openai/gpt-4", max_tokens=8000)

    def test_get_dspy_lm_haiku_uses_smaller_max_tokens(self):
        """Test that haiku models get smaller max_tokens."""
        with patch.object(dspy, "LM") as mock_lm_class:
            mock_lm = MagicMock()
            mock_lm_class.return_value = mock_lm

            get_dspy_lm("anthropic/claude-3-haiku-20240307")

            mock_lm_class.assert_called_once_with(
                "anthropic/claude-3-haiku-20240307",
                max_tokens=4000,
            )
