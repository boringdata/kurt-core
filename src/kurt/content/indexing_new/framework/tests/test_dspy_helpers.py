"""Tests for DSPy helpers."""

import asyncio
from unittest.mock import MagicMock, patch

import dspy
import pytest

from kurt.content.indexing_new.framework.dspy_helpers import DSPyResult, run_batch, run_batch_sync


class SampleDSPySignature(dspy.Signature):
    """Test signature for DSPy."""

    input_text: str = dspy.InputField()
    output_text: str = dspy.OutputField()


class TestRunBatch:
    """Tests for run_batch function."""

    @pytest.mark.asyncio
    async def test_run_batch_basic(self):
        """Test basic batch execution."""
        # Mock DSPy ChainOfThought
        mock_executor = MagicMock()
        mock_result = MagicMock()
        mock_result.output_text = "processed"
        mock_result.prompt_tokens = 10
        mock_result.completion_tokens = 5

        # Make it sync callable (no acall method)
        mock_executor.return_value = mock_result
        mock_executor.acall = None  # Explicitly no async method

        with patch("dspy.ChainOfThought", return_value=mock_executor):
            items = [
                {"input_text": "text1"},
                {"input_text": "text2"},
            ]

            results = await run_batch(
                signature=SampleDSPySignature,
                items=items,
                max_concurrent=2,
            )

            assert len(results) == 2
            assert all(isinstance(r, DSPyResult) for r in results)
            assert all(r.error is None for r in results)
            assert all(r.result == mock_result for r in results)

    @pytest.mark.asyncio
    async def test_run_batch_with_context(self):
        """Test batch execution with shared context."""
        mock_executor = MagicMock()
        mock_executor.return_value = MagicMock()
        mock_executor.acall = None  # Explicitly no async method

        with patch("dspy.ChainOfThought", return_value=mock_executor):
            items = [{"input_text": "text1"}]
            context = {"shared_param": "value"}

            await run_batch(
                signature=SampleDSPySignature,
                items=items,
                context=context,
            )

            # Check that context was merged into payload
            mock_executor.assert_called_once()
            call_args = mock_executor.call_args[1]
            assert "shared_param" in call_args
            assert call_args["shared_param"] == "value"

    @pytest.mark.asyncio
    async def test_run_batch_handles_errors(self):
        """Test batch execution handles errors gracefully."""
        mock_executor = MagicMock()
        mock_executor.side_effect = ValueError("Test error")
        mock_executor.acall = None  # Explicitly no async method

        with patch("dspy.ChainOfThought", return_value=mock_executor):
            items = [{"input_text": "text1"}]

            results = await run_batch(
                signature=SampleDSPySignature,
                items=items,
            )

            assert len(results) == 1
            result = results[0]
            assert result.error is not None
            assert isinstance(result.error, ValueError)
            assert str(result.error) == "Test error"
            assert result.result is None

    @pytest.mark.asyncio
    async def test_run_batch_respects_concurrency_limit(self):
        """Test that concurrency limit is respected."""
        call_times = []

        async def mock_acall(**kwargs):
            """Track when calls happen."""
            start_time = asyncio.get_event_loop().time()
            call_times.append(start_time)
            await asyncio.sleep(0.1)  # Simulate work
            return MagicMock()

        mock_executor = MagicMock()
        mock_executor.acall = mock_acall

        with patch("dspy.ChainOfThought", return_value=mock_executor):
            items = [{"input_text": f"text{i}"} for i in range(4)]

            await run_batch(
                signature=SampleDSPySignature,
                items=items,
                max_concurrent=2,  # Only 2 at a time
            )

            # With max_concurrent=2, we should see two groups of calls
            # Check that not all 4 calls started at the same time
            assert len(call_times) == 4
            # The third call should start after the first completes
            # (with some tolerance for timing)
            time_diffs = [call_times[i + 1] - call_times[i] for i in range(3)]
            # At least one gap should be significant (waiting for slot)
            assert any(diff > 0.05 for diff in time_diffs)

    @pytest.mark.asyncio
    async def test_run_batch_with_timeout(self):
        """Test batch execution with timeout."""

        async def slow_acall(**kwargs):
            """Simulate slow execution."""
            await asyncio.sleep(10)  # Much longer than timeout
            return MagicMock()

        mock_executor = MagicMock()
        mock_executor.acall = slow_acall

        with patch("dspy.ChainOfThought", return_value=mock_executor):
            items = [{"input_text": "text1"}]

            results = await run_batch(
                signature=SampleDSPySignature,
                items=items,
                timeout=0.1,  # Very short timeout
            )

            assert len(results) == 1
            result = results[0]
            assert result.error is not None
            assert isinstance(result.error, asyncio.TimeoutError)


class TestRunBatchSync:
    """Tests for run_batch_sync function."""

    def test_run_batch_sync_basic(self):
        """Test synchronous batch execution."""
        mock_executor = MagicMock()
        mock_result = MagicMock()
        mock_result.output_text = "processed"
        mock_result.prompt_tokens = 10
        mock_result.completion_tokens = 5
        mock_executor.return_value = mock_result

        with patch("dspy.ChainOfThought", return_value=mock_executor):
            items = [
                {"input_text": "text1"},
                {"input_text": "text2"},
            ]

            results = run_batch_sync(
                signature=SampleDSPySignature,
                items=items,
                max_concurrent=2,
            )

            assert len(results) == 2
            assert all(isinstance(r, DSPyResult) for r in results)
            assert all(r.error is None for r in results)

    def test_run_batch_sync_handles_errors(self):
        """Test sync batch handles errors."""
        mock_executor = MagicMock()
        mock_executor.side_effect = ValueError("Test error")

        with patch("dspy.ChainOfThought", return_value=mock_executor):
            items = [{"input_text": "text1"}]

            results = run_batch_sync(
                signature=SampleDSPySignature,
                items=items,
            )

            assert len(results) == 1
            result = results[0]
            assert result.error is not None
            assert isinstance(result.error, ValueError)
